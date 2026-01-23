from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, WorkLog, Attendance, Payroll, LeaveApplication

class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'full_name', 'department', 'hire_date', 'hourly_rate', 'is_active')
    list_filter = ('department', 'is_active', 'hire_date')
    search_fields = ('employee_id', 'user__first_name', 'user__last_name', 'user__email')
    readonly_fields = ('employee_id', 'created_at', 'updated_at')
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'employee_id', 'department', 'supervisor')
        }),
        ('Employment Details', {
            'fields': ('hire_date', 'hourly_rate', 'is_active')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'bank_account', 'branch'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def full_name(self, obj):
        return obj.user.get_full_name()
    full_name.short_description = 'Full Name'
    
    def phone_number(self, obj):
        return obj.user.phone_number
    phone_number.short_description = 'Phone'
    
    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'

class WorkLogAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'task_name', 'hours_worked', 'amount_earned', 'is_paid', 'payment_date')
    list_filter = ('date', 'is_paid', 'employee__department')
    search_fields = ('employee__user__first_name', 'employee__user__last_name', 'task_description')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'
    
    def task_name(self, obj):
        if obj.production_task:
            return obj.production_task.task_name
        return obj.task_description or "Manual Entry"
    task_name.short_description = 'Task'

class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'status', 'check_in', 'check_out', 'hours_worked')
    list_filter = ('date', 'status', 'employee__department')
    search_fields = ('employee__user__first_name', 'employee__user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'
    
    def hours_worked(self, obj):
        return obj.hours_worked
    hours_worked.short_description = 'Hours'

class PayrollAdmin(admin.ModelAdmin):
    list_display = ('employee', 'month_name', 'basic_salary', 'overtime', 'allowances', 'deductions', 'net_salary', 'status')
    list_filter = ('month', 'status', 'employee__department')
    search_fields = ('employee__user__first_name', 'employee__user__last_name', 'transaction_id')
    readonly_fields = ('created_at', 'updated_at', 'net_salary')
    date_hierarchy = 'month'
    
    def month_name(self, obj):
        return obj.month.strftime('%B %Y')
    month_name.short_description = 'Month'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only on creation
            obj.created_by = request.user
        obj.save()

class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'number_of_days', 'status', 'approved_by')
    list_filter = ('leave_type', 'status', 'start_date')
    search_fields = ('employee__user__first_name', 'employee__user__last_name', 'reason')
    readonly_fields = ('created_at', 'updated_at', 'number_of_days')
    date_hierarchy = 'start_date'
    
    actions = ['approve_leaves', 'reject_leaves']
    
    def approve_leaves(self, request, queryset):
        updated = queryset.update(status='approved', approved_by=request.user, approved_date=timezone.now())
        self.message_user(request, f'{updated} leave applications approved.')
    approve_leaves.short_description = "Approve selected leaves"
    
    def reject_leaves(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} leave applications rejected.')
    reject_leaves.short_description = "Reject selected leaves"

admin.site.register(Employee, EmployeeAdmin)
admin.site.register(WorkLog, WorkLogAdmin)
admin.site.register(Attendance, AttendanceAdmin)
admin.site.register(Payroll, PayrollAdmin)
admin.site.register(LeaveApplication, LeaveApplicationAdmin)