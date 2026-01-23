from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST

from .models import Employee, WorkLog, Attendance, Payroll, LeaveApplication
from .forms import EmployeeForm, WorkLogForm, AttendanceForm, PayrollForm, LeaveApplicationForm
from production.models import ProductionTask

# ========== EMPLOYEE VIEWS ==========
class EmployeeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Employee
    template_name = 'hr/employee_list.html'
    context_object_name = 'employees'
    permission_required = 'hr.view_employee'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(employee_id__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(department__icontains=search_query)
            )
        
        # Filter by department
        department = self.request.GET.get('department', '')
        if department:
            queryset = queryset.filter(department=department)
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Employee.DEPARTMENT_CHOICES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_department'] = self.request.GET.get('department', '')
        context['selected_status'] = self.request.GET.get('status', '')
        
        # Statistics
        context['total_employees'] = Employee.objects.count()
        context['active_employees'] = Employee.objects.filter(is_active=True).count()
        context['total_payroll'] = Employee.objects.aggregate(
            total=Sum('hourly_rate')
        )['total'] or 0
        
        return context

class EmployeeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    permission_required = 'hr.add_employee'
    success_url = reverse_lazy('hr:employee_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Employee created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Employee'
        return context

class EmployeeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    permission_required = 'hr.change_employee'
    success_url = reverse_lazy('hr:employee_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Employee updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Employee: {self.object.full_name}'
        return context

class EmployeeDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Employee
    template_name = 'hr/employee_detail.html'
    permission_required = 'hr.view_employee'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.object
        
        # Get recent work logs
        context['recent_work_logs'] = employee.work_logs.order_by('-date')[:10]
        
        # Get recent attendance
        context['recent_attendance'] = employee.attendances.order_by('-date')[:10]
        
        # Get payroll history
        context['payroll_history'] = employee.payrolls.order_by('-month')[:6]
        
        # Get leave applications
        context['leave_applications'] = employee.leave_applications.order_by('-created_at')[:5]
        
        # Statistics
        context['total_earnings'] = employee.total_earnings
        context['unpaid_earnings'] = employee.unpaid_earnings
        context['current_month_earnings'] = employee.current_month_earnings
        
        # Get assigned tasks
        if employee.user.assigned_tasks.exists():
            context['assigned_tasks'] = employee.user.assigned_tasks.filter(
                status__in=['assigned', 'in_progress']
            )
            context['completed_tasks'] = employee.user.assigned_tasks.filter(
                status='completed'
            )
        
        return context
    
class EmployeeDeleteView(DeleteView):
    model = Employee
    template_name = 'hr/employee_confirm_delete.html'
    success_url = reverse_lazy('hr:employee_list')

# ========== WORK LOG VIEWS ==========
class WorkLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = WorkLog
    template_name = 'hr/worklog_list.html'
    context_object_name = 'work_logs'
    permission_required = 'hr.view_worklog'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by employee
        employee_id = self.request.GET.get('employee', '')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        # Filter by date range
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        # Filter by payment status
        payment_status = self.request.GET.get('payment_status', '')
        if payment_status == 'paid':
            queryset = queryset.filter(is_paid=True)
        elif payment_status == 'unpaid':
            queryset = queryset.filter(is_paid=False)
        
        return queryset.order_by('-date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = Employee.objects.filter(is_active=True)
        context['selected_employee'] = self.request.GET.get('employee', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['payment_status'] = self.request.GET.get('payment_status', '')
        
        # Statistics
        queryset = self.get_queryset()
        context['total_hours'] = queryset.aggregate(total=Sum('hours_worked'))['total'] or 0
        context['total_amount'] = queryset.aggregate(total=Sum('amount_earned'))['total'] or 0
        context['unpaid_amount'] = queryset.filter(is_paid=False).aggregate(
            total=Sum('amount_earned')
        )['total'] or 0
        
        return context

class WorkLogCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = WorkLog
    form_class = WorkLogForm
    template_name = 'hr/worklog_form.html'
    permission_required = 'hr.add_worklog'
    success_url = reverse_lazy('hr:worklog_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Work log created successfully!')
        return super().form_valid(form)

class WorkLogUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = WorkLog
    form_class = WorkLogForm
    template_name = 'hr/worklog_form.html'
    permission_required = 'hr.change_worklog'
    success_url = reverse_lazy('hr:worklog_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Work log updated successfully!')
        return super().form_valid(form)

# ========== ATTENDANCE VIEWS ==========
class AttendanceListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Attendance
    template_name = 'hr/attendance_list.html'
    context_object_name = 'attendance_records'
    permission_required = 'hr.view_attendance'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Default to current month
        today = timezone.now().date()
        month = self.request.GET.get('month', today.strftime('%Y-%m'))
        
        if month:
            year, month_num = map(int, month.split('-'))
            queryset = queryset.filter(
                date__year=year,
                date__month=month_num
            )
        
        # Filter by employee
        employee_id = self.request.GET.get('employee', '')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-date', 'employee__user__first_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = Employee.objects.filter(is_active=True)
        context['status_choices'] = Attendance.ATTENDANCE_STATUS
        
        today = timezone.now().date()
        context['selected_month'] = self.request.GET.get('month', today.strftime('%Y-%m'))
        context['selected_employee'] = self.request.GET.get('employee', '')
        context['selected_status'] = self.request.GET.get('status', '')
        
        # Statistics
        queryset = self.get_queryset()
        context['total_present'] = queryset.filter(status='present').count()
        context['total_absent'] = queryset.filter(status='absent').count()
        context['total_late'] = queryset.filter(status='late').count()
        
        return context

class AttendanceCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = 'hr/attendance_form.html'
    permission_required = 'hr.add_attendance'
    success_url = reverse_lazy('hr:attendance_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Attendance record created successfully!')
        return super().form_valid(form)

class AttendanceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = 'hr/attendance_form.html'
    permission_required = 'hr.change_attendance'
    success_url = reverse_lazy('hr:attendance_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Attendance record updated successfully!')
        return super().form_valid(form)

# ========== PAYROLL VIEWS ==========
class PayrollListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Payroll
    template_name = 'hr/payroll_list.html'
    context_object_name = 'payrolls'
    permission_required = 'hr.view_payroll'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by month
        month = self.request.GET.get('month', '')
        if month:
            year, month_num = map(int, month.split('-'))
            queryset = queryset.filter(
                month__year=year,
                month__month=month_num
            )
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by employee
        employee_id = self.request.GET.get('employee', '')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        return queryset.order_by('-month', 'employee__user__first_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = Employee.objects.filter(is_active=True)
        context['status_choices'] = Payroll.PAYROLL_STATUS
        
        # Statistics
        queryset = self.get_queryset()
        context['total_salary'] = queryset.aggregate(total=Sum('net_salary'))['total'] or 0
        context['total_paid'] = queryset.filter(status='paid').aggregate(
            total=Sum('net_salary')
        )['total'] or 0
        context['total_unpaid'] = queryset.exclude(status='paid').aggregate(
            total=Sum('net_salary')
        )['total'] or 0
        
        return context

class PayrollCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Payroll
    form_class = PayrollForm
    template_name = 'hr/payroll_form.html'
    permission_required = 'hr.add_payroll'
    success_url = reverse_lazy('hr:payroll_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Payroll record created successfully!')
        return super().form_valid(form)

class PayrollUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Payroll
    form_class = PayrollForm
    template_name = 'hr/payroll_form.html'
    permission_required = 'hr.change_payroll'
    success_url = reverse_lazy('hr:payroll_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Payroll record updated successfully!')
        return super().form_valid(form)

# ========== LEAVE APPLICATION VIEWS ==========
class LeaveApplicationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = LeaveApplication
    template_name = 'hr/leave_list.html'
    context_object_name = 'leaves'
    permission_required = 'hr.view_leaveapplication'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by employee
        employee_id = self.request.GET.get('employee', '')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        # Filter by date range
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = Employee.objects.filter(is_active=True)
        context['status_choices'] = LeaveApplication.LEAVE_STATUS
        return context

class LeaveApplicationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = LeaveApplication
    form_class = LeaveApplicationForm
    template_name = 'hr/leave_form.html'
    permission_required = 'hr.add_leaveapplication'
    success_url = reverse_lazy('hr:leave_list')
    
    def get_initial(self):
        initial = super().get_initial()
        # Set current user as employee if they have an employee record
        if hasattr(self.request.user, 'employee'):
            initial['employee'] = self.request.user.employee
        return initial
    
    def form_valid(self, form):
        messages.success(self.request, 'Leave application submitted successfully!')
        return super().form_valid(form)

class LeaveApplicationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = LeaveApplication
    form_class = LeaveApplicationForm
    template_name = 'hr/leave_form.html'
    permission_required = 'hr.change_leaveapplication'
    success_url = reverse_lazy('hr:leave_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Leave application updated successfully!')
        return super().form_valid(form)


# ========== TASK DASHBOARD VIEWS (For Fundis) ==========

class TaskDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'hr/task_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Current date and time
        today = timezone.now().date()
        now = timezone.now()
        
        # Calculate start of week (Monday)
        start_of_week = today - timedelta(days=today.weekday())
        
        # Initialize context variables
        employee = None
        assigned_tasks = []
        completed_tasks = []
        verified_tasks = []
        recent_work_logs = []
        today_attendance = None
        weekly_attendance = []
        
        # Statistics
        total_earnings = 0
        unpaid_earnings = 0
        current_month_earnings = 0
        pending_verification = 0
        
        # Task counts
        pending_count = 0
        in_progress_count = 0
        completed_count = 0
        verified_count = 0
        
        if hasattr(user, 'employee'):
            employee = user.employee
            
            try:
                # Import the ProductionTask model here to avoid circular imports
                from .models import ProductionTask, WorkLog, Attendance
                
                # Get all tasks assigned to this user
                all_tasks = ProductionTask.objects.filter(assigned_to=user)
                
                # Get assigned tasks (pending, assigned, or in progress) - ORDER BY sequence only
                assigned_tasks = all_tasks.filter(
                    status__in=['assigned', 'in_progress', 'pending']
                ).order_by('sequence', 'created_at')  # Removed 'priority' from order_by
                
                # Get completed tasks (waiting verification) - limit to 10
                completed_tasks = all_tasks.filter(
                    status='completed'
                ).order_by('-completed_date')[:10]
                
                # Get verified tasks - limit to 10
                verified_tasks = all_tasks.filter(
                    status='verified'
                ).order_by('-verified_at')[:10]
                
                # Get recent work logs - last 10
                recent_work_logs = WorkLog.objects.filter(
                    employee=employee
                ).order_by('-date')[:10]
                
                # Task statistics
                pending_count = all_tasks.filter(status='pending').count()
                in_progress_count = all_tasks.filter(status='in_progress').count()
                completed_count = all_tasks.filter(status='completed').count()
                verified_count = all_tasks.filter(status='verified').count()
                
                # Get earnings statistics from WorkLog
                earnings_data = WorkLog.objects.filter(
                    employee=employee
                ).aggregate(
                    total_earned=Sum('amount_earned'),
                    unpaid=Sum('amount_earned', filter=Q(paid=False))
                )
                
                total_earnings = earnings_data['total_earned'] or 0
                unpaid_earnings = earnings_data['unpaid'] or 0
                
                # Current month earnings
                current_month = now.month
                current_year = now.year
                month_earnings = WorkLog.objects.filter(
                    employee=employee,
                    date__month=current_month,
                    date__year=current_year,
                    paid=True
                ).aggregate(total=Sum('amount_earned'))['total'] or 0
                current_month_earnings = month_earnings
                
                # Calculate pending verification earnings (completed but not paid)
                pending_verification_qs = WorkLog.objects.filter(
                    employee=employee,
                    paid=False,
                    task__status='completed'
                )
                pending_verification = pending_verification_qs.aggregate(
                    total=Sum('amount_earned')
                )['total'] or 0
                
                # Get attendance data
                # Today's attendance
                today_attendance = Attendance.objects.filter(
                    employee=user,
                    date=today
                ).first()
                
                # Weekly attendance
                weekly_attendance = Attendance.objects.filter(
                    employee=user,
                    date__gte=start_of_week,
                    date__lte=today
                ).order_by('-date')
                
            except Exception as e:
                # Log error for debugging
                print(f"Error in TaskDashboardView: {e}")
                # Continue with default values
                pass
        
        # If employee doesn't exist, try to get basic task data directly
        else:
            try:
                from .models import ProductionTask
                # Get tasks directly assigned to user
                all_tasks = ProductionTask.objects.filter(assigned_to=user)
                assigned_tasks = all_tasks.filter(
                    status__in=['assigned', 'in_progress', 'pending']
                ).order_by('sequence', 'created_at')
                
                completed_tasks = all_tasks.filter(
                    status='completed'
                ).order_by('-completed_date')[:10]
                
                # Task statistics
                pending_count = all_tasks.filter(status='pending').count()
                in_progress_count = all_tasks.filter(status='in_progress').count()
                completed_count = all_tasks.filter(status='completed').count()
                verified_count = all_tasks.filter(status='verified').count()
                
            except Exception as e:
                print(f"Error getting task data: {e}")
        
        # Update context with all data
        context.update({
            'employee': employee,
            'assigned_tasks': assigned_tasks,
            'completed_tasks': completed_tasks,
            'verified_tasks': verified_tasks,
            'recent_work_logs': recent_work_logs,
            'today_attendance': today_attendance,
            'weekly_attendance': weekly_attendance,
            'today': today,
            'now': now,
            
            # Earnings
            'total_earnings': total_earnings,
            'unpaid_earnings': unpaid_earnings,
            'current_month_earnings': current_month_earnings,
            'pending_verification': pending_verification,
            
            # Task statistics
            'pending_count': pending_count,
            'in_progress_count': in_progress_count,
            'completed_count': completed_count,
            'verified_count': verified_count,
            
            # Additional useful data
            'user': user,
            'user_name': user.get_full_name() or user.username,
        })
        
        return context
    

@login_required
@require_POST
def mark_task_complete(request, task_id):
    """Mark a task as complete (called by worker)"""
    task = get_object_or_404(ProductionTask, id=task_id, assigned_to=request.user)
    
    if task.status in ['assigned', 'in_progress']:
        task.status = 'completed'
        task.completed_date = timezone.now()
        task.save()
        
        messages.success(request, f'Task "{task.task_name}" marked as complete!')
        return JsonResponse({'success': True, 'message': 'Task marked as complete'})
    
    return JsonResponse({'success': False, 'error': 'Task cannot be marked as complete'})

@login_required
@permission_required('hr.add_worklog')
@require_POST
def verify_task(request, task_id):
    """Verify a completed task (called by supervisor)"""
    task = get_object_or_404(ProductionTask, id=task_id, status='completed')
    
    # Verify the task
    task.status = 'verified'
    task.verified_by = request.user
    task.verified_at = timezone.now()
    task.save()
    
    # Create work log for payment
    from hr.models import WorkLog, Employee
    
    try:
        employee = Employee.objects.get(user=task.assigned_to)
        WorkLog.objects.create(
            employee=employee,
            production_task=task,
            date=task.completed_date.date() if task.completed_date else timezone.now().date(),
            hours_worked=task.labour_task.estimated_hours * task.quantity,
            amount_earned=task.labour_cost,
            task_description=f"{task.task_name} - {task.production_order.order_number}",
            notes=f"Verified by {request.user.get_full_name()}"
        )
        
        messages.success(request, f'Task "{task.task_name}" verified and work log created!')
        return JsonResponse({'success': True, 'message': 'Task verified successfully'})
    
    except Employee.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Employee record not found'})
    

@login_required
def start_task(request, pk):
    """Start a task"""
    task = get_object_or_404(ProductionTask, pk=pk)
    
    # Check if user can start this task
    if task.status == 'pending' or task.status == 'assigned':
        task.status = 'in_progress'
        task.assigned_to = request.user
        task.started_at = timezone.now()
        task.save()
        
        # Create work log entry
        WorkLog.objects.create(
            employee=request.user,
            task=task,
            action='started',
            description=f"Started task: {task.task_name}"
        )
        
        messages.success(request, f"Task '{task.task_name}' started successfully.")
    else:
        messages.error(request, "Cannot start this task.")
    
    return redirect('hr:task_dashboard')

@login_required
def complete_task(request, pk):
    """Complete a task"""
    task = get_object_or_404(ProductionTask, pk=pk)
    
    # Check if user can complete this task
    if task.status == 'in_progress' and task.assigned_to == request.user:
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()
        
        # Create work log entry
        WorkLog.objects.create(
            employee=request.user,
            task=task,
            action='completed',
            description=f"Completed task: {task.task_name}"
        )
        
        messages.success(request, f"Task '{task.task_name}' completed successfully.")
    else:
        messages.error(request, "Cannot complete this task.")
    
    return redirect('hr:task_dashboard')

@login_required
def update_task_progress(request, pk):
    """Update task progress percentage"""
    task = get_object_or_404(ProductionTask, pk=pk)
    
    if request.method == 'POST':
        progress = request.POST.get('progress')
        if progress and task.assigned_to == request.user:
            try:
                task.progress = int(progress)
                task.save()
                messages.success(request, "Progress updated.")
            except ValueError:
                messages.error(request, "Invalid progress value.")
    
    return redirect('hr:task_dashboard')


@login_required
def attendance_checkin(request):
    """Handle employee check-in/check-out"""
    today = timezone.now().date()
    
    # Get today's attendance record for this user
    attendance, created = Attendance.objects.get_or_create(
        employee=request.user,
        date=today,
        defaults={'status': 'present'}
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'check_in' and not attendance.check_in:
            attendance.check_in = timezone.now()
            attendance.status = 'present'
            attendance.save()
            messages.success(request, "Checked in successfully!")
            
        elif action == 'check_out' and attendance.check_in and not attendance.check_out:
            attendance.check_out = timezone.now()
            attendance.save()
            messages.success(request, "Checked out successfully!")
            
        elif action == 'break_start':
            # Handle break start logic
            pass
            
        elif action == 'break_end':
            # Handle break end logic
            pass
            
        return redirect('hr:task_dashboard')
    
    context = {
        'attendance': attendance,
        'today': today,
    }
    return render(request, 'hr/attendance_checkin.html', context)


class AttendanceListView(ListView):
    """List all attendance records (for supervisors)"""
    model = Attendance
    template_name = 'hr/attendance_list.html'
    context_object_name = 'attendances'
    paginate_by = 20
    
    def get_queryset(self):
        return Attendance.objects.select_related('employee').order_by('-date', '-check_in')


class MyAttendanceListView(ListView):
    """List attendance records for current user"""
    model = Attendance
    template_name = 'hr/my_attendance.html'
    context_object_name = 'attendances'
    paginate_by = 20
    
    def get_queryset(self):
        return Attendance.objects.filter(
            employee=self.request.user
        ).order_by('-date', '-check_in')


class WorkLogListView(ListView):
    """List work logs for current user"""
    model = WorkLog
    template_name = 'hr/worklog_list.html'
    context_object_name = 'worklogs'
    paginate_by = 20
    
    def get_queryset(self):
        return WorkLog.objects.filter(
            employee=self.request.user
        ).select_related('task').order_by('-created_at')


class CompletedTaskListView(ListView):
    """List completed tasks for current user"""
    model = ProductionTask
    template_name = 'hr/completed_tasks.html'
    context_object_name = 'tasks'
    paginate_by = 20
    
    def get_queryset(self):
        return ProductionTask.objects.filter(
            assigned_to=self.request.user,
            status='completed'
        ).select_related('production_order', 'production_order__product').order_by('-completed_date')

# ========== API VIEWS ==========
@login_required
def get_employee_tasks(request, employee_id):
    """Get tasks for a specific employee (AJAX)"""
    employee = get_object_or_404(Employee, id=employee_id)
    tasks = ProductionTask.objects.filter(
        assigned_to=employee.user,
        status__in=['assigned', 'in_progress']
    ).order_by('sequence')
    
    data = []
    for task in tasks:
        data.append({
            'id': task.id,
            'task_name': task.task_name,
            'production_order': task.production_order.order_number,
            'product': task.production_order.product.name,
            'quantity': task.quantity,
            'status': task.get_status_display(),
            'sequence': task.sequence,
            'due_date': task.production_order.expected_completion_date.strftime('%d-%m-%Y') if task.production_order.expected_completion_date else '',
        })
    
    return JsonResponse({'tasks': data})

@login_required
def dashboard_stats(request):
    """Get dashboard statistics (AJAX)"""
    stats = {}
    
    # Employee stats
    stats['total_employees'] = Employee.objects.count()
    stats['active_employees'] = Employee.objects.filter(is_active=True).count()
    
    # Attendance stats for today
    today = timezone.now().date()
    stats['present_today'] = Attendance.objects.filter(date=today, status='present').count()
    stats['absent_today'] = Attendance.objects.filter(date=today, status='absent').count()
    
    # Payroll stats for current month
    current_month = today.replace(day=1)
    stats['monthly_payroll'] = Payroll.objects.filter(
        month=current_month, 
        status='paid'
    ).aggregate(total=Sum('net_salary'))['total'] or 0
    
    # Work log stats for current month
    stats['monthly_work_hours'] = WorkLog.objects.filter(
        date__month=today.month,
        date__year=today.year
    ).aggregate(total=Sum('hours_worked'))['total'] or 0
    
    stats['monthly_earnings'] = WorkLog.objects.filter(
        date__month=today.month,
        date__year=today.year
    ).aggregate(total=Sum('amount_earned'))['total'] or 0
    
    return JsonResponse(stats)


class LeaveDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = LeaveApplication
    template_name = 'hr/leave_detail.html'
    permission_required = 'hr.view_leaveapplication'

@login_required
@permission_required('hr.change_leaveapplication')
def leave_process(request):
    """Process leave applications (approve/reject)"""
    if request.method == 'POST':
        import json
        leave_ids = request.POST.get('leave_ids')
        action = request.POST.get('action')
        reason = request.POST.get('reason', '')
        
        try:
            # Handle single ID or list of IDs
            if leave_ids.startswith('['):
                leave_ids = json.loads(leave_ids)
                leaves = LeaveApplication.objects.filter(id__in=leave_ids, status='pending')
            else:
                leaves = LeaveApplication.objects.filter(id=leave_ids, status='pending')
            
            if action == 'approve':
                leaves.update(status='approved', approved_by=request.user, approved_date=timezone.now())
                return JsonResponse({'success': True, 'message': f'{leaves.count()} leave(s) approved'})
            elif action == 'reject':
                leaves.update(status='rejected', rejection_reason=reason)
                return JsonResponse({'success': True, 'message': f'{leaves.count()} leave(s) rejected'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
@permission_required('hr.change_worklog')
def worklog_mark_paid(request, pk):
    """Mark work log as paid"""
    work_log = get_object_or_404(WorkLog, pk=pk)
    
    if not work_log.is_paid:
        work_log.is_paid = True
        work_log.payment_date = timezone.now().date()
        work_log.save()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Work log already paid'})

@login_required
@permission_required('hr.change_payroll')
def payroll_mark_paid(request, pk):
    """Mark payroll as paid and update related work logs"""
    payroll = get_object_or_404(Payroll, pk=pk)
    
    if payroll.status == 'approved':
        payroll.status = 'paid'
        payroll.payment_date = timezone.now().date()
        payroll.save()
        
        # Mark all related work logs as paid
        WorkLog.objects.filter(
            employee=payroll.employee,
            date__year=payroll.month.year,
            date__month=payroll.month.month,
            is_paid=False
        ).update(is_paid=True, payment_date=timezone.now().date())
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Payroll must be approved first'})