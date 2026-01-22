from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from hr.models import Employee

User = get_user_model()

@receiver(post_save, sender=User)
def create_employee_profile(sender, instance, created, **kwargs):
    """Create employee profile when user is created"""
    if created and instance.role == 'fundi':
        Employee.objects.get_or_create(
            user=instance,
            defaults={
                'employment_date': instance.date_joined,
                'is_active': instance.is_active
            }
        )