# accounts/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(allowed_roles=[]):
    """Decorator to restrict access based on user roles"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "You don't have permission to access this page.")
                # Redirect based on user role
                if request.user.role == 'owner':
                    return redirect('inventory:dashboard')
                elif request.user.role == 'store_manager':
                    return redirect('inventory:dashboard')
                elif request.user.role == 'production_manager':
                    return redirect('inventory:dashboard')
                elif request.user.role == 'accountant':
                    return redirect('inventory:dashboard')
                else:
                    return redirect('inventory:dashboard')
        return _wrapped_view
    return decorator


def owner_required(view_func):
    """Decorator for owner-only access"""
    return role_required(['owner'])(view_func)


def store_manager_required(view_func):
    """Decorator for store manager access (includes store_manager and owner)"""
    return role_required(['owner', 'store_manager'])(view_func)


def accountant_required(view_func):
    """Decorator for accountant access (includes accountant and owner)"""
    return role_required(['owner', 'accountant'])(view_func)


def production_manager_required(view_func):
    """Decorator for production manager access (includes production_manager and owner)"""
    return role_required(['owner', 'production_manager'])(view_func)


def any_staff_required(view_func):
    """Decorator for any staff (all authenticated users)"""
    return role_required(['owner', 'store_manager', 'production_manager', 
                         'accountant', 'supervisor', 'fundi', 'sales_person', 
                         'shop_manager'])(view_func)