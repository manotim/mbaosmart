# inventory/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Q, F, Value, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import timedelta
import json
import csv

from .models import RawMaterial, RawMaterialCategory, InventoryTransaction, StockAdjustment, StockAlert
from .forms import (RawMaterialForm, RawMaterialCategoryForm, InventoryTransactionForm, 
                   StockAdjustmentForm, StockTransferForm)
from procurement.models import PurchaseOrder

# Category Views
class CategoryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = RawMaterialCategory
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'
    permission_required = 'inventory.view_rawmaterialcategory'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Raw Material Categories'
        return context

class CategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = RawMaterialCategory
    form_class = RawMaterialCategoryForm
    template_name = 'inventory/category_form.html'
    permission_required = 'inventory.add_rawmaterialcategory'
    success_url = reverse_lazy('inventory:category_list')  # Fixed namespace
    
    def form_valid(self, form):
        messages.success(self.request, 'Category created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Category'
        return context

class CategoryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = RawMaterialCategory
    form_class = RawMaterialCategoryForm
    template_name = 'inventory/category_form.html'
    permission_required = 'inventory.change_rawmaterialcategory'
    success_url = reverse_lazy('inventory:category_list')  # Fixed namespace
    
    def form_valid(self, form):
        messages.success(self.request, 'Category updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Category'
        return context

class CategoryDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = RawMaterialCategory
    template_name = 'inventory/category_confirm_delete.html'
    permission_required = 'inventory.delete_rawmaterialcategory'
    success_url = reverse_lazy('inventory:category_list')  # Fixed namespace
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Category deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Raw Material Views
class RawMaterialListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = RawMaterial
    template_name = 'inventory/raw_material_list.html'
    context_object_name = 'raw_materials'
    permission_required = 'inventory.view_rawmaterial'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        
        # Filter by category
        category_id = self.request.GET.get('category', '')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by stock status
        stock_status = self.request.GET.get('stock_status', '')
        if stock_status:
            if stock_status == 'low':
                queryset = queryset.filter(
                    current_stock__gt=0,
                    current_stock__lte=F('min_stock_level')
                )
            elif stock_status == 'out':
                queryset = queryset.filter(current_stock__lte=0)
            elif stock_status == 'normal':
                queryset = queryset.filter(
                    current_stock__gt=F('min_stock_level'),
                    current_stock__lt=F('max_stock_level')
                )
        
        # Annotate with total value using a different name to avoid conflict
        queryset = queryset.annotate(
            calculated_value=ExpressionWrapper(
                F('current_stock') * F('unit_price'),
                output_field=DecimalField(max_digits=20, decimal_places=2)
            )
        )
        
        # Handle sorting
        order_by = self.request.GET.get('order_by', 'name')
        if order_by == 'total_value':
            queryset = queryset.order_by('-calculated_value')
        elif order_by == '-total_value':
            queryset = queryset.order_by('calculated_value')
        elif order_by in ['name', 'code', 'current_stock', 'unit_price']:
            queryset = queryset.order_by(order_by)
        elif order_by == 'category':
            queryset = queryset.order_by('category__name', 'name')
        else:
            queryset = queryset.order_by('name')
        
        return queryset.select_related('category', 'supplier')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = RawMaterialCategory.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_status'] = self.request.GET.get('stock_status', '')
        context['order_by'] = self.request.GET.get('order_by', 'name')
        
        # Calculate totals using Python (since we can't use property in aggregation)
        queryset = self.get_queryset()
        context['total_items'] = queryset.count()
        
        # Calculate total value in Python
        total_value = 0
        for material in queryset:
            try:
                total_value += float(material.current_stock) * float(material.unit_price)
            except (TypeError, ValueError):
                pass
        context['total_value'] = total_value
        
        # Stock status counts
        all_materials = RawMaterial.objects.all()
        context['low_stock_count'] = all_materials.filter(
            current_stock__gt=0,
            current_stock__lte=F('min_stock_level')
        ).count()
        context['out_of_stock_count'] = all_materials.filter(current_stock__lte=0).count()
        context['normal_stock_count'] = all_materials.filter(
            current_stock__gt=F('min_stock_level'),
            current_stock__lt=F('max_stock_level')
        ).count()
        
        return context

class RawMaterialCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = RawMaterial
    form_class = RawMaterialForm
    template_name = 'inventory/raw_material_form.html'
    permission_required = 'inventory.add_rawmaterial'
    success_url = reverse_lazy('inventory:raw_material_list')  # Fixed namespace
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Raw material added successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Raw Material'
        return context


class RawMaterialUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = RawMaterial
    form_class = RawMaterialForm
    template_name = 'inventory/raw_material_form.html'
    permission_required = 'inventory.change_rawmaterial'
    success_url = reverse_lazy('inventory:raw_material_list')  # Fixed namespace
    
    def form_valid(self, form):
        messages.success(self.request, 'Raw material updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Raw Material'
        return context

class RawMaterialDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = RawMaterial
    template_name = 'inventory/raw_material_detail.html'
    permission_required = 'inventory.view_rawmaterial'
    context_object_name = 'material'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transactions'] = self.object.transactions.all()[:50]
        context['stock_value'] = self.object.total_value
        
        # Get recent purchase orders for this material
        context['recent_purchases'] = PurchaseOrder.objects.filter(
            items__raw_material=self.object
        ).distinct()[:10]
        
        return context

@login_required
@permission_required('inventory.delete_rawmaterial')
def delete_raw_material(request, pk):
    material = get_object_or_404(RawMaterial, pk=pk)
    
    # Check if material is used in any transactions
    if material.transactions.exists():
        messages.error(request, 'Cannot delete raw material that has transaction history.')
        return redirect('inventory:raw_material_detail', pk=pk)  # Fixed namespace
    
    material.delete()
    messages.success(request, 'Raw material deleted successfully!')
    return redirect('inventory:raw_material_list')  # Fixed namespace

# Inventory Transaction Views
class InventoryTransactionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = InventoryTransaction
    template_name = 'inventory/transaction_list.html'
    context_object_name = 'transactions'
    permission_required = 'inventory.view_inventorytransaction'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('raw_material', 'created_by')
        
        # Filter by date range
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        # Filter by transaction type
        transaction_type = self.request.GET.get('transaction_type', '')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        # Filter by raw material
        material_id = self.request.GET.get('material', '')
        if material_id:
            queryset = queryset.filter(raw_material_id=material_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['materials'] = RawMaterial.objects.all()
        context['transaction_types'] = InventoryTransaction.TRANSACTION_TYPES
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['selected_type'] = self.request.GET.get('transaction_type', '')
        context['selected_material'] = self.request.GET.get('material', '')
        
        # Summary statistics
        queryset = self.get_queryset()
        context['total_transactions'] = queryset.count()
        context['total_quantity'] = queryset.aggregate(total=Sum('quantity'))['total'] or 0
        context['total_value'] = queryset.aggregate(total=Sum('total_value'))['total'] or 0
        
        return context

@login_required
@permission_required('inventory.add_inventorytransaction')
def create_inventory_transaction(request):
    if request.method == 'POST':
        form = InventoryTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            
            # Calculate total value if not provided
            if not transaction.total_value and transaction.unit_price:
                transaction.total_value = transaction.quantity * transaction.unit_price
            
            transaction.save()
            
            messages.success(request, 'Inventory transaction recorded successfully!')
            return redirect('inventory:transaction_list')  # Fixed namespace
    else:
        form = InventoryTransactionForm()
    
    return render(request, 'inventory/transaction_form.html', {
        'form': form,
        'title': 'Record Inventory Transaction'
    })

# Stock Adjustment Views
@login_required
@permission_required('inventory.add_stockadjustment')
def adjust_stock(request):
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            adjustment = form.save(commit=False)
            adjustment.adjusted_by = request.user
            adjustment.save()
            
            messages.success(request, 'Stock adjusted successfully!')
            return redirect('inventory:adjustment_list')  # Fixed namespace
    else:
        form = StockAdjustmentForm()
    
    return render(request, 'inventory/adjustment_form.html', {
        'form': form,
        'title': 'Adjust Stock Level'
    })

class StockAdjustmentListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = StockAdjustment
    template_name = 'inventory/adjustment_list.html'
    context_object_name = 'adjustments'
    permission_required = 'inventory.view_stockadjustment'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('raw_material', 'adjusted_by')
        
        # Filter by date
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        
        if date_from:
            queryset = queryset.filter(adjusted_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(adjusted_at__lte=date_to)
        
        return queryset

# Stock Transfer Views
@login_required
@permission_required('inventory.add_inventorytransaction')
def transfer_stock(request):
    if request.method == 'POST':
        form = StockTransferForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            raw_material = cleaned_data['raw_material']
            quantity = cleaned_data['quantity']
            
            # Check if enough stock exists
            if raw_material.current_stock < quantity:
                messages.error(request, f'Insufficient stock. Only {raw_material.current_stock} {raw_material.unit} available.')
                return redirect('inventory:transfer_stock')  # Fixed namespace
            
            # Create outgoing transaction
            InventoryTransaction.objects.create(
                raw_material=raw_material,
                transaction_type='transfer',
                quantity=quantity,
                reference=f"TRANSFER-OUT-{timezone.now().strftime('%Y%m%d')}",
                notes=f"Transfer from {cleaned_data['from_location']} to {cleaned_data['to_location']}. {cleaned_data['notes']}",
                created_by=request.user
            )
            
            messages.success(request, 'Stock transfer completed successfully!')
            return redirect('inventory:transaction_list')  # Fixed namespace
    else:
        form = StockTransferForm()
    
    return render(request, 'inventory/transfer_form.html', {
        'form': form,
        'title': 'Transfer Stock'
    })


# Stock Alert Views
@login_required
@permission_required('inventory.view_stockalert')
def stock_alerts(request):
    alerts = StockAlert.objects.filter(is_active=True).select_related('raw_material')
    
    # Auto-create low stock alerts
    low_stock_materials = RawMaterial.objects.filter(
        current_stock__gt=0,
        current_stock__lte=F('min_stock_level')
    )
    
    for material in low_stock_materials:
        if not StockAlert.objects.filter(
            raw_material=material, 
            alert_type='low_stock',
            is_active=True
        ).exists():
            StockAlert.objects.create(
                raw_material=material,
                alert_type='low_stock',
                message=f'{material.name} is below minimum stock level. Current: {material.current_stock} {material.unit}, Minimum: {material.min_stock_level} {material.unit}'
            )
    
    # Auto-create out of stock alerts
    out_of_stock_materials = RawMaterial.objects.filter(current_stock__lte=0)
    
    for material in out_of_stock_materials:
        if not StockAlert.objects.filter(
            raw_material=material, 
            alert_type='out_of_stock',
            is_active=True
        ).exists():
            StockAlert.objects.create(
                raw_material=material,
                alert_type='out_of_stock',
                message=f'{material.name} is out of stock!'
            )
    
    return render(request, 'inventory/stock_alerts.html', {
        'alerts': alerts,
        'title': 'Stock Alerts'
    })

@login_required
@permission_required('inventory.change_stockalert')
def acknowledge_alert(request, alert_id):
    alert = get_object_or_404(StockAlert, id=alert_id)
    
    if request.method == 'POST':
        alert.is_active = False
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        
        messages.success(request, 'Alert acknowledged successfully!')
    
    return redirect('inventory:stock_alerts')  # Fixed namespace

# Reports and Dashboard Views
@login_required
@permission_required('inventory.view_rawmaterial')
def inventory_dashboard(request):
    # Use the class method from model
    summary = RawMaterial.get_inventory_summary()
    
    # Recent transactions
    recent_transactions = InventoryTransaction.objects.select_related(
        'raw_material', 'created_by'
    ).order_by('-created_at')[:10]
    
    # Low stock items
    low_stock_items = RawMaterial.objects.filter(
        current_stock__gt=0,
        current_stock__lte=F('min_stock_level')
    ).order_by('current_stock')[:10]
    
    # Category distribution - Use property in Python instead of annotation
    categories = RawMaterialCategory.objects.all()
    category_distribution = []
    
    for category in categories:
        materials = RawMaterial.objects.filter(category=category)
        total_value = sum(mat.total_value for mat in materials)
        if materials.exists() or total_value > 0:
            category_distribution.append({
                'category__name': category.name,
                'count': materials.count(),
                'total_value': total_value
            })
    
    # Add uncategorized
    uncategorized_materials = RawMaterial.objects.filter(category__isnull=True)
    if uncategorized_materials.exists():
        total_value = sum(mat.total_value for mat in uncategorized_materials)
        category_distribution.append({
            'category__name': 'Uncategorized',
            'count': uncategorized_materials.count(),
            'total_value': total_value
        })
    
    context = {
        'total_materials': summary['total_materials'],
        'low_stock_count': summary['low_stock_count'],
        'out_of_stock_count': summary['out_of_stock_count'],
        'total_value': summary['total_value'],
        'recent_transactions': recent_transactions,
        'low_stock_items': low_stock_items,
        'category_distribution': category_distribution,
        'title': 'Inventory Dashboard'
    }
    
    return render(request, 'inventory/dashboard.html', context)

@login_required
@permission_required('inventory.view_rawmaterial')
def stock_report(request):
    materials = RawMaterial.objects.select_related('category', 'supplier').order_by('name')
    
    # Calculate totals and status counts
    total_value = 0
    low_stock_count = 0
    out_of_stock_count = 0
    normal_stock_count = 0
    
    for material in materials:
        total_value += material.total_value if hasattr(material, 'total_value') else 0
        
        # Calculate stock status dynamically
        if material.current_stock <= 0:
            out_of_stock_count += 1
        elif (material.min_stock_level is not None and 
              material.current_stock <= material.min_stock_level):
            low_stock_count += 1
        else:
            normal_stock_count += 1
    
    # Calculate average unit price
    materials_with_price = materials.exclude(unit_price=None).filter(unit_price__gt=0)
    if materials_with_price.exists():
        total_price = sum(m.unit_price for m in materials_with_price)
        avg_unit_price = total_price / materials_with_price.count()
    else:
        avg_unit_price = 0
    
    # Most expensive material
    most_expensive = materials.order_by('-unit_price').first()
    
    # Least expensive material
    least_expensive = materials.exclude(unit_price=None).filter(unit_price__gt=0).order_by('unit_price').first()
    
    # Export options
    export_format = request.GET.get('export', '')
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="stock_report_{}.csv"'.format(
            timezone.now().strftime('%Y%m%d_%H%M%S')
        )
        
        writer = csv.writer(response)
        writer.writerow(['Code', 'Name', 'Category', 'Unit', 'Current Stock', 
                         'Min Stock', 'Max Stock', 'Unit Price', 'Total Value', 'Status', 'Location'])
        
        for material in materials:
            # Determine stock status for CSV
            if material.current_stock <= 0:
                status = 'Out of Stock'
            elif (material.min_stock_level is not None and 
                  material.current_stock <= material.min_stock_level):
                status = 'Low Stock'
            else:
                status = 'Normal'
            
            writer.writerow([
                material.code,
                material.name,
                material.category.name if material.category else 'Uncategorized',
                material.get_unit_display(),
                float(material.current_stock),
                float(material.min_stock_level) if material.min_stock_level else 0,
                float(material.max_stock_level) if material.max_stock_level else 0,
                float(material.unit_price) if material.unit_price else 0,
                float(material.total_value) if hasattr(material, 'total_value') else 0,
                status,
                material.location
            ])
        
        return response
    
    context = {
        'materials': materials,
        'total_value': total_value,
        'avg_unit_price': avg_unit_price,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'normal_stock_count': normal_stock_count,
        'most_expensive': most_expensive,
        'least_expensive': least_expensive,
        'title': 'Stock Report'
    }
    
    return render(request, 'inventory/stock_report.html', context)


# API Views for AJAX
@login_required
def get_material_details(request, material_id):
    try:
        material = RawMaterial.objects.get(id=material_id)
        data = {
            'id': material.id,
            'name': material.name,
            'unit': material.unit,
            'unit_display': material.get_unit_display(),
            'current_stock': float(material.current_stock),
            'unit_price': float(material.unit_price),
            'min_stock': float(material.min_stock_level),
            'max_stock': float(material.max_stock_level),
            'total_value': float(material.total_value),
        }
        return JsonResponse(data)
    except RawMaterial.DoesNotExist:
        return JsonResponse({'error': 'Material not found'}, status=404)

@login_required
def inventory_chart_data(request):
    # Get low stock materials
    low_stock = RawMaterial.objects.filter(
        current_stock__gt=0,
        current_stock__lte=F('min_stock_level')
    ).count()
    
    out_of_stock = RawMaterial.objects.filter(current_stock__lte=0).count()
    normal_stock = RawMaterial.objects.filter(
        current_stock__gt=F('min_stock_level')
    ).count()
    
    data = {
        'labels': ['Low Stock', 'Out of Stock', 'Normal Stock'],
        'datasets': [{
            'data': [low_stock, out_of_stock, normal_stock],
            'backgroundColor': ['#ffc107', '#dc3545', '#28a745']
        }]
    }
    
    return JsonResponse(data)

@login_required
def api_stock_data(request):
    """API endpoint to get current stock data for all materials"""
    materials = RawMaterial.objects.select_related('category').all()
    data = {
        str(material.id): {
            'name': material.name,
            'stock': float(material.current_stock),
            'unit': material.unit,
            'min_stock': float(material.min_stock) if material.min_stock else 0,
            'max_stock': float(material.max_stock) if material.max_stock else 0,
        }
        for material in materials
    }
    return JsonResponse(data)