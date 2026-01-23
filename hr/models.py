from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal

class Employee(models.Model):
    """Links User to employee details"""
    DEPARTMENT_CHOICES = [
        ('production', 'Production'),
        ('upholstery', 'Upholstery'),
        ('finishing', 'Finishing'),
        ('assembly', 'Assembly'),
        ('packaging', 'Packaging'),
        ('cutting', 'Cutting'),
        ('skeleton', 'Skeleton Building'),
        ('general', 'General Worker'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='employee'
    )
    employee_id = models.CharField(max_length=20, unique=True, verbose_name="Employee ID")
    hire_date = models.DateField()
    hourly_rate = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    department = models.CharField(
        max_length=50, 
        choices=DEPARTMENT_CHOICES, 
        default='general'
    )
    supervisor = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='subordinates'
    )
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    branch = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user__first_name', 'user__last_name']
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"
    
    @property
    def full_name(self):
        return self.user.get_full_name()
    
    @property
    def phone_number(self):
        return self.user.phone_number
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def total_earnings(self):
        total = self.work_logs.aggregate(
            total=models.Sum('amount_earned')
        )['total'] or Decimal('0')
        return total
    
    @property
    def unpaid_earnings(self):
        unpaid = self.work_logs.filter(is_paid=False).aggregate(
            total=models.Sum('amount_earned')
        )['total'] or Decimal('0')
        return unpaid
    
    @property
    def current_month_earnings(self):
        today = timezone.now().date()
        first_day = today.replace(day=1)
        
        earnings = self.work_logs.filter(
            date__gte=first_day,
            date__lte=today
        ).aggregate(
            total=models.Sum('amount_earned')
        )['total'] or Decimal('0')
        return earnings
    
    def save(self, *args, **kwargs):
        if not self.employee_id:
            # Generate employee ID
            department_prefix = self.department[:3].upper()
            last_employee = Employee.objects.order_by('-id').first()
            if last_employee:
                last_id = last_employee.id + 1
            else:
                last_id = 1
            self.employee_id = f"{department_prefix}-{str(last_id).zfill(4)}"
        
        super().save(*args, **kwargs)

class WorkLog(models.Model):
    """Tracks work done by employees for payroll"""
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='work_logs'
    )
    production_task = models.ForeignKey(
        'production.ProductionTask', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='work_logs'
    )
    date = models.DateField()
    hours_worked = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0.1)]
    )
    amount_earned = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    task_description = models.TextField(blank=True)
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Work Log"
        verbose_name_plural = "Work Logs"
        unique_together = ['employee', 'production_task']  # One work log per task
    
    def __str__(self):
        return f"{self.employee} - {self.date} - Ksh {self.amount_earned}"
    
    @property
    def task_name(self):
        if self.production_task:
            return self.production_task.task_name
        return self.task_description or "Manual Entry"

class Attendance(models.Model):
    """Daily attendance tracking"""
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('leave', 'On Leave'),
        ('half_day', 'Half Day'),
        ('off_duty', 'Off Duty'),
    ]
    
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='attendances'
    )
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, 
        choices=ATTENDANCE_STATUS, 
        default='present'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['employee', 'date']
        ordering = ['-date', 'employee__user__first_name']
        verbose_name = "Attendance"
        verbose_name_plural = "Attendance Records"
    
    def __str__(self):
        return f"{self.employee} - {self.date} ({self.status})"
    
    @property
    def hours_worked(self):
        if self.check_in and self.check_out:
            # Calculate hours between check_in and check_out
            from datetime import datetime
            check_in_dt = datetime.combine(self.date, self.check_in)
            check_out_dt = datetime.combine(self.date, self.check_out)
            hours = (check_out_dt - check_in_dt).seconds / 3600
            return round(hours, 2)
        return 0

class Payroll(models.Model):
    """Monthly payroll processing"""
    PAYROLL_STATUS = [
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='payrolls'
    )
    month = models.DateField()  # First day of month
    basic_salary = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    overtime = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    allowances = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    deductions = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    net_salary = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=20, 
        choices=PAYROLL_STATUS, 
        default='draft'
    )
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('cash', 'Cash'),
            ('mpesa', 'M-Pesa'),
            ('bank', 'Bank Transfer'),
            ('cheque', 'Cheque'),
        ],
        default='mpesa'
    )
    transaction_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_payrolls'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['employee', 'month']
        ordering = ['-month', 'employee__user__first_name']
        verbose_name = "Payroll"
        verbose_name_plural = "Payrolls"
    
    def __str__(self):
        return f"{self.employee} - {self.month.strftime('%B %Y')} - Ksh {self.net_salary}"
    
    def save(self, *args, **kwargs):
        # Calculate net salary
        self.net_salary = (
            self.basic_salary + 
            self.overtime + 
            self.allowances - 
            self.deductions
        )
        super().save(*args, **kwargs)
    
    @property
    def month_name(self):
        return self.month.strftime('%B %Y')

class LeaveApplication(models.Model):
    """Employee leave applications"""
    LEAVE_TYPES = [
        ('annual', 'Annual Leave'),
        ('sick', 'Sick Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('compassionate', 'Compassionate Leave'),
        ('study', 'Study Leave'),
        ('unpaid', 'Unpaid Leave'),
    ]
    
    LEAVE_STATUS = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_applications'
    )
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    number_of_days = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=LEAVE_STATUS, default='pending')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves'
    )
    approved_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Leave Application"
        verbose_name_plural = "Leave Applications"
    
    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.start_date} to {self.end_date})"
    
    def save(self, *args, **kwargs):
        # Calculate number of days
        if self.start_date and self.end_date:
            days = (self.end_date - self.start_date).days + 1
            self.number_of_days = days
        
        # Update status
        if self.status == 'approved' and not self.approved_date:
            self.approved_date = timezone.now()
        
        super().save(*args, **kwargs)