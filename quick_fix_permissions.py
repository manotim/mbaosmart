# quick_fix_permissions.py
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mbaosmart_project.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

User = get_user_model()

def quick_fix():
    """Give all inventory permissions to test users"""
    
    users_to_fix = ['store_manager', 'production_manager', 'accountant']
    
    for username in users_to_fix:
        try:
            user = User.objects.get(username=username)
            
            # Get ALL permissions
            all_perms = Permission.objects.all()
            
            # Give all permissions (or just inventory if you prefer)
            user.user_permissions.set(all_perms)
            
            # Make them staff
            user.is_staff = True
            user.save()
            
            print(f"\n✅ Fixed {username}:")
            print(f"   Staff: {user.is_staff}")
            print(f"   Permissions: {user.user_permissions.count()}")
            
        except User.DoesNotExist:
            print(f"❌ User {username} not found")
    
    print("\n" + "="*50)
    print("NOW LOGIN WITH:")
    print("  store_manager / password123")
    print("  production_manager / password123")
    print("  accountant / password123")
    print("\nThey should have FULL ACCESS now!")
    print("="*50)

if __name__ == '__main__':
    quick_fix()