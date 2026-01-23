from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import User
from hr.models import Employee, WorkLog, Attendance, Payroll, LeaveApplication

class Command(BaseCommand):
    help = 'Setup permissions for HR app'
    
    def handle(self, *args, **kwargs):
        # Get content types for HR models
        employee_ct = ContentType.objects.get_for_model(Employee)
        worklog_ct = ContentType.objects.get_for_model(WorkLog)
        attendance_ct = ContentType.objects.get_for_model(Attendance)
        payroll_ct = ContentType.objects.get_for_model(Payroll)
        leave_ct = ContentType.objects.get_for_model(LeaveApplication)
        
        # Define permission sets for each role
        role_permissions = {
            'owner': {
                'hr': ['view', 'add', 'change', 'delete'],
                'worklog': ['view', 'add', 'change', 'delete'],
                'attendance': ['view', 'add', 'change', 'delete'],
                'payroll': ['view', 'add', 'change', 'delete'],
                'leave': ['view', 'add', 'change', 'delete'],
            },
            'supervisor': {
                'hr': ['view'],
                'worklog': ['view', 'add', 'change'],
                'attendance': ['view', 'add', 'change'],
                'payroll': ['view'],
                'leave': ['view', 'change'],  # Can approve/reject leaves
            },
            'production_manager': {
                'hr': ['view'],
                'worklog': ['view', 'add', 'change'],
                'attendance': ['view', 'add', 'change'],
                'payroll': ['view'],
                'leave': ['view'],
            },
            'accountant': {
                'hr': ['view'],
                'worklog': ['view', 'change'],  # Can mark as paid
                'attendance': ['view'],
                'payroll': ['view', 'add', 'change', 'delete'],
                'leave': ['view'],
            },
            'fundi': {
                'hr': ['view'],  # Can view own employee record
                'worklog': ['view'],  # Can view own work logs
                'attendance': ['view'],  # Can view own attendance
                'payroll': ['view'],  # Can view own payroll
                'leave': ['view', 'add'],  # Can view and apply for leave
            },
        }
        
        # Map model names to content types
        model_map = {
            'hr': employee_ct,
            'worklog': worklog_ct,
            'attendance': attendance_ct,
            'payroll': payroll_ct,
            'leave': leave_ct,
        }
        
        # Create or get groups
        groups = {}
        for role in role_permissions.keys():
            group, created = Group.objects.get_or_create(name=role.capitalize())
            groups[role] = group
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created group: {role.capitalize()}'))
        
        # Assign permissions to groups
        for role, permissions in role_permissions.items():
            group = groups[role]
            
            # Clear existing permissions
            group.permissions.clear()
            
            # Add new permissions
            for model_name, actions in permissions.items():
                content_type = model_map[model_name]
                
                for action in actions:
                    codename = f'{action}_{model_name}'
                    if model_name == 'hr':
                        codename = f'{action}_employee'
                    
                    try:
                        perm = Permission.objects.get(
                            codename=codename,
                            content_type=content_type
                        )
                        group.permissions.add(perm)
                    except Permission.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'Permission not found: {codename}'))
            
            self.stdout.write(self.style.SUCCESS(f'Assigned permissions to {role.capitalize()} group'))
        
        # Assign users to groups based on their role
        for user in User.objects.all():
            if user.role in groups:
                user.groups.add(groups[user.role])
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Assigned {user.username} to {user.role.capitalize()} group'))
        
        self.stdout.write(self.style.SUCCESS('Permission setup complete!'))