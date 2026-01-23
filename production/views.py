from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Q, F
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.forms import modelformset_factory
import json

from .models import Product, ProductFormula, LabourTask, ProductionOrder, ProductionTask, WorkStation
from .forms import (ProductForm, ProductionOrderForm, ProductionTaskAssignmentForm, 
                   WorkStationForm, ProductFormulaForm, LabourTaskForm)
from inventory.models import RawMaterial
from accounts.models import *

# Product Views
class ProductListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Product
    template_name = 'production/product_list.html'
    context_object_name = 'products'
    permission_required = 'production.view_product'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Filter by product type
        product_type = self.request.GET.get('product_type', '')
        if product_type:
            queryset = queryset.filter(product_type=product_type)
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product_types'] = Product.PRODUCT_TYPES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_type'] = self.request.GET.get('product_type', '')
        context['selected_status'] = self.request.GET.get('status', '')
        
        # Statistics
        context['total_products'] = Product.objects.count()
        context['active_products'] = Product.objects.filter(is_active=True).count()
        
        return context


class ProductCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'production/product_form.html'
    permission_required = 'production.add_product'
    success_url = reverse_lazy('production:product_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Product created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Product'
        return context

class ProductDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Product
    template_name = 'production/product_detail.html'
    permission_required = 'production.view_product'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get formulas and calculate total material cost
        formulas = self.object.formulas.all().select_related('raw_material')
        total_material_cost = sum(f.material_cost for f in formulas)
        
        # Get labour tasks and calculate total labour cost
        labour_tasks = self.object.labour_tasks.all()
        total_labour_cost = sum(t.labour_cost for t in labour_tasks)
        
        # Update product cost if needed
        if not self.object.production_cost:
            self.object.production_cost = total_material_cost + total_labour_cost
            self.object.save()
        
        context['formulas'] = formulas
        context['labour_tasks'] = labour_tasks
        context['total_material_cost'] = total_material_cost
        context['total_labour_cost'] = total_labour_cost
        context['profit'] = self.object.selling_price - self.object.production_cost
        
        return context

@login_required
@permission_required('production.change_product')
def edit_product_formula(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    FormulaFormSet = modelformset_factory(ProductFormula, form=ProductFormulaForm, extra=3, can_delete=True)
    
    if request.method == 'POST':
        formset = FormulaFormSet(request.POST, queryset=product.formulas.all())
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.product = product
                instance.save()
            
            # Delete marked instances
            for obj in formset.deleted_objects:
                obj.delete()
            
            # Update product production cost
            product.update_production_cost()
            
            messages.success(request, 'Product formula updated successfully!')
            return redirect('accounts:product_detail', pk=product_id)
    else:
        formset = FormulaFormSet(queryset=product.formulas.all())
    
    return render(request, 'production/product_formula_form.html', {
        'product': product,
        'formset': formset,
        'title': 'Edit Product Formula'
    })

@login_required
@permission_required('production.change_product')
def edit_product_labour_tasks(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    TaskFormSet = modelformset_factory(LabourTask, form=LabourTaskForm, extra=2, can_delete=True)
    
    if request.method == 'POST':
        formset = TaskFormSet(request.POST, queryset=product.labour_tasks.all())
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.product = product
                instance.save()
            
            # Delete marked instances
            for obj in formset.deleted_objects:
                obj.delete()
            
            # Update product production cost
            product.update_production_cost()
            
            messages.success(request, 'Labour tasks updated successfully!')
            return redirect('accounts:product_detail', pk=product_id)
    else:
        formset = TaskFormSet(queryset=product.labour_tasks.all())
    
    return render(request, 'production/product_labour_form.html', {
        'product': product,
        'formset': formset,
        'title': 'Edit Labour Tasks'
    })

# Production Order Views
class ProductionOrderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ProductionOrder
    template_name = 'production/production_order_list.html'
    context_object_name = 'production_orders'
    permission_required = 'production.view_productionorder'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('product', 'created_by')
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by date
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        
        if date_from:
            queryset = queryset.filter(start_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(start_date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ProductionOrder.STATUS_CHOICES
        context['selected_status'] = self.request.GET.get('status', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        # Statistics
        context['total_orders'] = ProductionOrder.objects.count()
        context['in_progress'] = ProductionOrder.objects.filter(status='in_progress').count()
        context['completed'] = ProductionOrder.objects.filter(status='completed').count()
        
        return context

class ProductionOrderCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = ProductionOrder
    form_class = ProductionOrderForm
    template_name = 'production/production_order_form.html'
    permission_required = 'production.add_productionorder'
    
    def form_valid(self, form):
        production_order = form.save(commit=False)
        production_order.created_by = self.request.user
        production_order.status = 'pending'
        production_order.save()
        
        messages.success(self.request, 'Production order created successfully!')
        return redirect('accounts:production_order_detail', pk=production_order.pk)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Production Order'
        return context

class ProductionOrderDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = ProductionOrder
    template_name = 'production/production_order_detail.html'
    permission_required = 'production.view_productionorder'
    context_object_name = 'production_order'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get material requirements
        context['material_requirements'] = self.object.calculate_material_requirements()
        
        # Check material availability
        sufficient, insufficient = self.object.check_material_availability()
        context['materials_sufficient'] = sufficient
        context['insufficient_materials'] = insufficient
        
        # Get production tasks
        context['tasks'] = self.object.tasks.select_related('labour_task', 'assigned_to').order_by('sequence')
        
        return context

@login_required
@permission_required('production.change_productionorder')
def start_production(request, order_id):
    production_order = get_object_or_404(ProductionOrder, id=order_id)
    
    if production_order.status != 'planned':
        messages.error(request, 'Production order must be in "Planned" status to start.')
        return redirect('accounts:production_order_detail', pk=order_id)
    
    # Check material availability
    sufficient, insufficient = production_order.check_material_availability()
    if not sufficient:
        messages.error(request, 'Insufficient materials to start production.')
        return redirect('accounts:production_order_detail', pk=order_id)
    
    # Start production
    if production_order.start_production():
        messages.success(request, 'Production started successfully! Materials have been consumed.')
    else:
        messages.error(request, 'Failed to start production.')
    
    return redirect('accounts:production_order_detail', pk=order_id)

@login_required
@permission_required('production.change_productionorder')
def complete_production(request, order_id):
    production_order = get_object_or_404(ProductionOrder, id=order_id)
    
    if production_order.status != 'in_progress':
        messages.error(request, 'Production must be in progress to complete.')
        return redirect('accounts:production_order_detail', pk=order_id)
    
    # Check if all tasks are completed
    incomplete_tasks = production_order.tasks.exclude(status='verified')
    if incomplete_tasks.exists():
        messages.error(request, 'All tasks must be completed and verified before completing production.')
        return redirect('accounts:production_order_detail', pk=order_id)
    
    # Complete production
    if production_order.complete_production():
        messages.success(request, 'Production completed successfully!')
    else:
        messages.error(request, 'Failed to complete production.')
    
    return redirect('accounts:production_order_detail', pk=order_id)

@login_required
@permission_required('production.change_productionorder')
def plan_production_order(request, order_id):
    production_order = get_object_or_404(ProductionOrder, id=order_id)
    
    if production_order.status != 'pending':
        messages.error(request, 'Only pending orders can be planned.')
        return redirect('accounts:production_order_detail', pk=order_id)
    
    # Check material availability
    sufficient, insufficient = production_order.check_material_availability()
    if not sufficient:
        messages.error(request, 'Cannot plan production - insufficient materials.')
        return redirect('accounts:production_order_detail', pk=order_id)
    
    production_order.status = 'planned'
    production_order.save()
    
    messages.success(request, 'Production order planned successfully!')
    return redirect('accounts:production_order_detail', pk=order_id)

# Production Task Views
@login_required
def worker_dashboard(request):
    """Dashboard for workers to see their assigned tasks"""
    if not hasattr(request.user, 'employee'):
        messages.error(request, 'You are not registered as an employee.')
        return redirect('accounts:dashboard')
    
    # Get assigned tasks
    assigned_tasks = ProductionTask.objects.filter(
        assigned_to=request.user,
        status__in=['assigned', 'in_progress']
    ).select_related('production_order', 'labour_task')
    
    # Get completed tasks (recent)
    completed_tasks = ProductionTask.objects.filter(
        assigned_to=request.user,
        status='completed'
    ).select_related('production_order', 'labour_task').order_by('-completed_date')[:10]
    
    # Get available tasks (not assigned, previous tasks completed)
    available_tasks = ProductionTask.objects.filter(
        status='pending',
        production_order__status='in_progress'
    ).select_related('production_order', 'labour_task')
    
    # Filter tasks that can be started
    tasks_can_start = []
    for task in available_tasks:
        if task.can_start():
            tasks_can_start.append(task)
    
    context = {
        'assigned_tasks': assigned_tasks,
        'completed_tasks': completed_tasks,
        'available_tasks': tasks_can_start,
        'title': 'Worker Dashboard'
    }
    
    return render(request, 'production/worker_dashboard.html', context)


@login_required
def complete_task(request, task_id):
    """Worker marks task as complete"""
    task = get_object_or_404(ProductionTask, id=task_id)
    
    # Check if user is assigned to this task
    if task.assigned_to != request.user and not request.user.has_perm('production.change_productiontask'):
        messages.error(request, 'You are not assigned to this task.')
        return redirect('accounts:worker_dashboard')
    
    if task.status != 'in_progress':
        messages.error(request, 'Task must be in progress to mark as complete.')
        return redirect('accounts:worker_dashboard')
    
    task.complete_task(request.user)
    messages.success(request, 'Task marked as complete! Waiting for supervisor verification.')
    
    return redirect('accounts:worker_dashboard')

@login_required
@permission_required('production.change_productiontask')
def verify_task(request, task_id):
    """Supervisor verifies completed task"""
    task = get_object_or_404(ProductionTask, id=task_id)
    
    if task.status != 'completed':
        messages.error(request, 'Task must be completed by worker before verification.')
        return redirect('accounts:production_order_detail', pk=task.production_order.id)
    
    task.verify_task(request.user)
    messages.success(request, 'Task verified successfully!')
    
    return redirect('accounts:production_order_detail', pk=task.production_order.id)

# Work Station Views
class WorkStationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = WorkStation
    template_name = 'production/workstation_list.html'
    context_object_name = 'workstations'
    permission_required = 'production.view_workstation'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Work Stations'
        return context

class WorkStationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = WorkStation
    form_class = WorkStationForm
    template_name = 'production/workstation_form.html'
    permission_required = 'production.add_workstation'
    success_url = reverse_lazy('accounts:workstation_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Work station created successfully!')
        return super().form_valid(form)

class WorkStationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = WorkStation
    form_class = WorkStationForm
    template_name = 'production/workstation_form.html'
    permission_required = 'production.change_workstation'
    success_url = reverse_lazy('accounts:workstation_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Work station updated successfully!')
        return super().form_valid(form)

class WorkStationDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = WorkStation
    template_name = 'production/workstation_confirm_delete.html'
    permission_required = 'production.delete_workstation'
    success_url = reverse_lazy('accounts:workstation_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Work station deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Production Dashboard
@login_required
@permission_required('production.view_productionorder')
def production_dashboard(request):
    # Summary statistics
    total_orders = ProductionOrder.objects.count()
    in_progress = ProductionOrder.objects.filter(status='in_progress').count()
    completed_today = ProductionOrder.objects.filter(
        actual_completion_date=timezone.now().date(),
        status='completed'
    ).count()
    pending_orders = ProductionOrder.objects.filter(status='pending').count()
    
    # Recent production orders
    recent_orders = ProductionOrder.objects.select_related('product').order_by('-created_at')[:10]
    
    # Tasks by status
    tasks_by_status = ProductionTask.objects.values('status').annotate(count=Count('id'))
    
    # Production efficiency (completed vs planned)
    today = timezone.now().date()
    completed_this_week = ProductionOrder.objects.filter(
        actual_completion_date__week=today.isocalendar()[1],
        status='completed'
    ).count()
    
    planned_this_week = ProductionOrder.objects.filter(
        expected_completion_date__week=today.isocalendar()[1]
    ).count()
    
    efficiency = 0
    if planned_this_week > 0:
        efficiency = (completed_this_week / planned_this_week) * 100
    
    context = {
        'total_orders': total_orders,
        'in_progress': in_progress,
        'completed_today': completed_today,
        'pending_orders': pending_orders,
        'recent_orders': recent_orders,
        'tasks_by_status': tasks_by_status,
        'efficiency': efficiency,
        'completed_this_week': completed_this_week,
        'planned_this_week': planned_this_week,      
        'title': 'Production Dashboard'
    }
    
    return render(request, 'production/dashboard.html', context)


# API Views
@login_required
def get_product_details(request, product_id):
    """Get product details for AJAX requests"""
    try:
        product = Product.objects.get(id=product_id)
        data = {
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'production_cost': float(product.production_cost),
            'selling_price': float(product.selling_price),
            'profit_margin': float(product.profit_margin),
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

@login_required
def get_production_order_details(request, order_id):
    """Get production order details for AJAX requests"""
    try:
        order = ProductionOrder.objects.get(id=order_id)
        data = {
            'id': order.id,
            'order_number': order.order_number,
            'product': order.product.name,
            'quantity': order.quantity,
            'status': order.status,
            'progress': order.progress_percentage,
            'total_cost': float(order.total_production_cost),
        }
        return JsonResponse(data)
    except ProductionOrder.DoesNotExist:
        return JsonResponse({'error': 'Production order not found'}, status=404)

@login_required
def production_chart_data(request):
    """Get data for production charts"""
    # Orders by status
    orders_by_status = ProductionOrder.objects.values('status').annotate(
        count=Count('id')
    )
    
    # Production by product type
    production_by_type = ProductionOrder.objects.values(
        'product__product_type'
    ).annotate(
        count=Count('id'),
        total_quantity=Sum('quantity')
    )
    
    data = {
        'orders_by_status': list(orders_by_status),
        'production_by_type': list(production_by_type),
    }
    
    return JsonResponse(data)


@login_required
@permission_required('production.change_productiontask')
def assign_task_to_worker(request, task_id):
    """Supervisor assigns a task to a worker"""
    task = get_object_or_404(ProductionTask, id=task_id)
    
    if request.method == 'POST':
        worker_id = request.POST.get('worker_id')
        worker = get_object_or_404(get_user_model(), id=worker_id, role='fundi')
        
        task.assigned_to = worker
        task.status = 'assigned'
        task.save()
        
        messages.success(request, f'Task assigned to {worker.get_full_name()}!')
        return redirect('production:production_order_detail', pk=task.production_order.id)
    
    # Get all fundis
    workers = get_user_model().objects.filter(role='fundi', is_active=True)
    
    return render(request, 'production/assign_task.html', {
        'task': task,
        'workers': workers,
    })



@login_required
@permission_required('production.change_productiontask')
def assign_task_view(request, task_id):
    """View to assign a task to a worker"""
    task = get_object_or_404(ProductionTask, id=task_id)
    
    if request.method == 'POST':
        worker_id = request.POST.get('worker_id')
        worker = get_object_or_404(User, id=worker_id, role='fundi', is_active=True)
        
        success, message = task.assign_to_worker(worker)
        if success:
            messages.success(request, f'Task assigned to {worker.get_full_name()}')
        else:
            messages.error(request, message)
        
        return redirect('production:production_order_detail', pk=task.production_order.id)
    
    # Get all active fundis
    workers = User.objects.filter(role='fundi', is_active=True)
    
    return render(request, 'production/assign_task.html', {
        'task': task,
        'workers': workers,
    })

@login_required
@require_POST
def start_task_view(request):
    """Worker starts a task (AJAX)"""
    task_id = request.POST.get('task_id')
    task = get_object_or_404(ProductionTask, id=task_id, assigned_to=request.user)
    
    success, message = task.start_work(request.user)
    if success:
        messages.success(request, message)
        return JsonResponse({'success': True, 'message': message})
    
    return JsonResponse({'success': False, 'error': message})

@login_required
@require_POST
def complete_task_view(request):
    """Worker marks task as complete (AJAX)"""
    task_id = request.POST.get('task_id')
    task = get_object_or_404(ProductionTask, id=task_id, assigned_to=request.user)
    
    success, message = task.mark_complete(request.user)
    if success:
        messages.success(request, message)
        return JsonResponse({'success': True, 'message': message})
    
    return JsonResponse({'success': False, 'error': message})

@login_required
@permission_required('production.change_productiontask')
@require_POST
def verify_task_view(request):
    """Supervisor verifies a task (AJAX)"""
    task_id = request.POST.get('task_id')
    task = get_object_or_404(ProductionTask, id=task_id)
    
    success, message = task.verify_completion(request.user)
    if success:
        messages.success(request, message)
        return JsonResponse({'success': True, 'message': message})
    
    return JsonResponse({'success': False, 'error': message})

