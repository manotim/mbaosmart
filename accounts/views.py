# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.views.generic import CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import User
from .forms import UserRegistrationForm, UserProfileForm, UserLoginForm, PasswordChangeCustomForm
from .decorators import role_required, owner_required, store_manager_required, accountant_required, production_manager_required, any_staff_required

# Login View
def login_view(request):
    if request.user.is_authenticated:
        return redirect('inventory:dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                # Redirect based on user role
                if user.role == 'owner':
                    return redirect('inventory:dashboard')
                elif user.role == 'store_manager':
                    return redirect('inventory:dashboard')
                elif user.role == 'production_manager':
                    return redirect('inventory:dashboard')
                elif user.role == 'accountant':
                    return redirect('inventory:dashboard')
                elif user.role == 'fundi':
                    return redirect('inventory:dashboard')
                else:
                    return redirect('inventory:dashboard')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


# Logout View
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


# Registration View (Public)
def register_user(request):
    """Public user registration"""
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return redirect('inventory:dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(
                    request, 
                    f'Account created successfully! Please login with your credentials.'
                )
                return redirect('accounts:login')
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=user)
    
    # Get role-specific data for profile
    from inventory.models import StockAlert, InventoryTransaction
    
    context = {
        'form': form,
        'user': user,
        'user_role_display': user.get_role_display(),
        'recent_activity': InventoryTransaction.objects.filter(created_by=user).order_by('-created_at')[:5],
        'active_alerts_count': StockAlert.objects.filter(is_active=True).count() if user.role in ['owner', 'store_manager'] else 0
    }
    return render(request, 'accounts/profile.html', context)


# Change Password View
@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeCustomForm(request.user, request.POST)
        if form.is_valid():
            user = request.user
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeCustomForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})


# User List View (Owner Only)
@login_required
@owner_required
def user_list_view(request):
    users = User.objects.all().order_by('-date_joined')
    
    # Filter by role if specified
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)
    
    context = {
        'users': users,
        'user_roles': User.USER_ROLES,
    }
    return render(request, 'accounts/user_list.html', context)


# User Detail View (Owner Only)
@login_required
@owner_required
def user_detail_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    context = {'user_detail': user}
    return render(request, 'accounts/user_detail.html', context)


# Toggle User Active Status (Owner Only)
@login_required
@owner_required
def toggle_user_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    
    # Prevent owner from deactivating themselves
    if user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('accounts:user_list')
    
    user.is_active = not user.is_active
    user.save()
    
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f'User {user.username} has been {status}.')
    
    return redirect('accounts:user_list')