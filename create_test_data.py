#!/usr/bin/env python
import os
import django
import random
from decimal import Decimal
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mbaosmart_project.settings')
django.setup()

from accounts.models import User
from hr.models import Employee, WorkLog, Attendance, Payroll, LeaveApplication
from production.models import Product, ProductionOrder, LabourTask, ProductionTask
from django.utils import timezone

def create_test_users():
    """Create test users for different roles"""
    users_data = [
        # Fundis (Workers)
        {'username': 'john_fundi', 'email': 'john@mbaosmart.com', 'first_name': 'John', 'last_name': 'Kamau', 'role': 'fundi', 'password': 'password123'},
        {'username': 'peter_fundi', 'email': 'peter@mbaosmart.com', 'first_name': 'Peter', 'last_name': 'Mwangi', 'role': 'fundi', 'password': 'password123'},
        {'username': 'mary_fundi', 'email': 'mary@mbaosmart.com', 'first_name': 'Mary', 'last_name': 'Wambui', 'role': 'fundi', 'password': 'password123'},
        
        # Supervisor
        {'username': 'supervisor_james', 'email': 'james@mbaosmart.com', 'first_name': 'James', 'last_name': 'Omondi', 'role': 'supervisor', 'password': 'password123'},
        
        # HR Manager
        {'username': 'hr_sarah', 'email': 'sarah@mbaosmart.com', 'first_name': 'Sarah', 'last_name': 'Atieno', 'role': 'production_manager', 'password': 'password123'},
        
        # Accountant
        {'username': 'accountant_david', 'email': 'david@mbaosmart.com', 'first_name': 'David', 'last_name': 'Kiprop', 'role': 'accountant', 'password': 'password123'},
    ]
    
    created_users = []
    for user_data in users_data:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'email': user_data['email'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'role': user_data['role'],
                'is_active': True,
                'is_staff': True
            }
        )
        if created:
            user.set_password(user_data['password'])
            user.save()
            print(f"Created user: {user.username} ({user.get_role_display()})")
        else:
            print(f"User already exists: {user.username}")
        
        created_users.append(user)
    
    return created_users

def create_employees(users):
    """Create employee records for users"""
    departments = ['production', 'upholstery', 'finishing', 'assembly', 'cutting']
    
    for user in users:
        if user.role == 'fundi':
            # Only create employees for fundis and supervisors
            employee, created = Employee.objects.get_or_create(
                user=user,
                defaults={
                    'hire_date': timezone.now().date() - timedelta(days=random.randint(30, 365)),
                    'hourly_rate': Decimal(str(random.choice([200, 250, 300, 350, 400]))),
                    'department': random.choice(departments),
                    'bank_name': 'Equity Bank',
                    'bank_account': f'123456{random.randint(1000, 9999)}',
                    'branch': 'Nairobi CBD',
                    'is_active': True
                }
            )
            if created:
                print(f"Created employee: {employee.full_name} - {employee.employee_id}")
            else:
                print(f"Employee exists: {employee.full_name}")

def create_test_attendance():
    """Create test attendance records for the last 30 days"""
    employees = Employee.objects.filter(is_active=True)
    today = timezone.now().date()
    
    for employee in employees:
        for days_ago in range(30):
            date = today - timedelta(days=days_ago)
            
            # Skip weekends (Saturday=5, Sunday=6)
            if date.weekday() >= 5:
                continue
            
            # Create attendance record
            status = random.choices(
                ['present', 'present', 'present', 'present', 'late', 'absent'],
                weights=[0.7, 0.7, 0.7, 0.7, 0.1, 0.1]
            )[0]
            
            Attendance.objects.get_or_create(
                employee=employee,
                date=date,
                defaults={
                    'status': status,
                    'check_in': datetime.combine(date, datetime.min.time().replace(hour=8, minute=random.randint(0, 30))),
                    'check_out': datetime.combine(date, datetime.min.time().replace(hour=17, minute=random.randint(0, 30))),
                    'notes': 'Test data'
                }
            )
    
    print(f"Created attendance records for {employees.count()} employees")

def create_test_work_logs():
    """Create test work logs for employees"""
    employees = Employee.objects.filter(is_active=True)
    today = timezone.now().date()
    
    tasks = [
        'Cutting sofa covers',
        'Laying upholstery',
        'Sanding wood pieces',
        'Assemble chair frames',
        'Painting furniture',
        'Polishing finished products',
        'Packaging for delivery'
    ]
    
    for employee in employees:
        for days_ago in range(14):
            date = today - timedelta(days=days_ago)
            
            # Skip weekends
            if date.weekday() >= 5:
                continue
            
            # Create 1-3 work logs per day
            for _ in range(random.randint(1, 3)):
                hours = random.uniform(2, 8)
                amount = Decimal(str(hours)) * employee.hourly_rate
                
                WorkLog.objects.create(
                    employee=employee,
                    date=date,
                    task_description=random.choice(tasks),
                    hours_worked=hours,
                    amount_earned=amount,
                    is_paid=random.choice([True, False]),
                    notes=f"Work log for {date.strftime('%d-%m-%Y')}"
                )
    
    print(f"Created work logs for {employees.count()} employees")

def create_test_payroll():
    """Create test payroll records"""
    employees = Employee.objects.filter(is_active=True)
    
    for employee in employees:
        # Create payroll for current month
        month = timezone.now().date().replace(day=1)
        
        # Calculate total from work logs
        work_logs = WorkLog.objects.filter(
            employee=employee,
            date__month=month.month,
            date__year=month.year
        )
        
        total_earnings = sum(log.amount_earned for log in work_logs)
        
        if total_earnings > 0:
            Payroll.objects.get_or_create(
                employee=employee,
                month=month,
                defaults={
                    'basic_salary': total_earnings * Decimal('0.8'),
                    'overtime': total_earnings * Decimal('0.1'),
                    'allowances': total_earnings * Decimal('0.05'),
                    'deductions': total_earnings * Decimal('0.05'),
                    'status': random.choice(['draft', 'calculated', 'approved', 'paid']),
                    'payment_method': random.choice(['mpesa', 'bank', 'cash']),
                    'notes': f'Payroll for {month.strftime("%B %Y")}'
                }
            )
    
    print(f"Created payroll records for {employees.count()} employees")

def create_test_leaves():
    """Create test leave applications"""
    employees = Employee.objects.filter(is_active=True)
    
    for employee in employees:
        # Create a past leave
        start_date = timezone.now().date() - timedelta(days=random.randint(60, 90))
        end_date = start_date + timedelta(days=random.randint(1, 5))
        
        LeaveApplication.objects.create(
            employee=employee,
            leave_type=random.choice(['annual', 'sick', 'compassionate']),
            start_date=start_date,
            end_date=end_date,
            reason=f"Test leave application",
            status=random.choice(['approved', 'rejected', 'pending']),
            notes="Test data"
        )
    
    print(f"Created leave applications for {employees.count()} employees")

if __name__ == "__main__":
    print("=== Creating Test Data for HR App ===")
    
    # Create users
    users = create_test_users()
    
    # Create employees for fundis
    create_employees(users)
    
    # Create test data
    create_test_attendance()
    create_test_work_logs()
    create_test_payroll()
    create_test_leaves()
    
    print("\n=== Test Data Creation Complete ===")
    print("\nTest Users Created:")
    print("- Username: john_fundi, Password: password123 (Fundi)")
    print("- Username: peter_fundi, Password: password123 (Fundi)")
    print("- Username: mary_fundi, Password: password123 (Fundi)")
    print("- Username: supervisor_james, Password: password123 (Supervisor)")
    print("- Username: hr_sarah, Password: password123 (HR Manager)")
    print("- Username: accountant_david, Password: password123 (Accountant)")