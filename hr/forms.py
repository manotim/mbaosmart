from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Employee, WorkLog, Attendance, Payroll, LeaveApplication
from production.models import ProductionTask

User = get_user_model()

class EmployeeForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(employee__isnull=True),
        label="Select User",
        help_text="Only users without employee records are shown"
    )
    
    class Meta:
        model = Employee
        fields = ['user', 'hire_date', 'hourly_rate', 'department', 'supervisor', 
                 'bank_name', 'bank_account', 'branch', 'is_active']
        widgets = {
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'supervisor': forms.Select(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['user'].queryset = User.objects.all()
            self.fields['user'].initial = self.instance.user
            self.fields['user'].disabled = True

class WorkLogForm(forms.ModelForm):
    class Meta:
        model = WorkLog
        fields = ['employee', 'production_task', 'date', 'hours_worked', 
                 'amount_earned', 'task_description', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'production_task': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hours_worked': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'amount_earned': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'task_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show production tasks that don't have work logs yet
        if self.instance and not self.instance.pk:
            self.fields['production_task'].queryset = ProductionTask.objects.filter(
                work_logs__isnull=True
            )

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'check_in', 'check_out', 'status', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_in': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'check_out': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class PayrollForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = ['employee', 'month', 'basic_salary', 'overtime', 'allowances', 
                 'deductions', 'status', 'payment_date', 'payment_method', 
                 'transaction_id', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'month': forms.DateInput(attrs={'type': 'month', 'class': 'form-control'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'overtime': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'allowances': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deductions': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_month(self):
        month = self.cleaned_data['month']
        # Ensure it's the first day of the month
        return month.replace(day=1)

class LeaveApplicationForm(forms.ModelForm):
    class Meta:
        model = LeaveApplication
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'reason', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'leave_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError("End date cannot be before start date.")
        
        return cleaned_data