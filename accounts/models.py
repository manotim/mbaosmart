# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

class User(AbstractUser):
    """Custom User model with additional fields"""
    USER_ROLES = (
        ('owner', 'Owner'),
        ('store_manager', 'Store Manager'),
        ('production_manager', 'Production Manager'),
        ('supervisor', 'Supervisor'),
        ('accountant', 'Accountant'),
        ('fundi', 'Fundi/Worker'),
        ('sales_person', 'Sales Person'),
        ('shop_manager', 'Shop Manager'),
    )
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+254700123456'. Up to 15 digits allowed."
    )
    
    role = models.CharField(max_length=20, choices=USER_ROLES, default='fundi')
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    address = models.TextField(blank=True)
    id_number = models.CharField(max_length=20, blank=True)
    kra_pin = models.CharField(max_length=20, blank=True)
    nhif_number = models.CharField(max_length=20, blank=True)
    nssf_number = models.CharField(max_length=20, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    branch = models.CharField(max_length=100, blank=True)
    date_joined = models.DateField(auto_now_add=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.get_full_name()} - {self.get_role_display()}"
    
    def get_role_display_name(self):
        return dict(self.USER_ROLES).get(self.role, self.role)