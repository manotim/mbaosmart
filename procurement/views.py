from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Sum, Count
from django.http import JsonResponse

from .models import Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceivedNote
from .forms import SupplierForm, PurchaseOrderForm, PurchaseOrderItemFormSet, GoodsReceivedNoteForm
from inventory.models import InventoryTransaction

# Supplier Views
class SupplierListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Supplier
    template_name = 'procurement/supplier_list.html'
    context_object_name = 'suppliers'
    permission_required = 'procurement.view_supplier'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                models.Q(name__icontains=search_query) |
                models.Q(contact_person__icontains=search_query) |
                models.Q(phone__icontains=search_query) |
                models.Q(tin_number__icontains=search_query)
            )
        return queryset

class SupplierCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'procurement/supplier_form.html'
    permission_required = 'procurement.add_supplier'
    success_url = reverse_lazy('accounts:supplier_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Supplier created successfully!')
        return super().form_valid(form)

class SupplierUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'procurement/supplier_form.html'
    permission_required = 'procurement.change_supplier'
    success_url = reverse_lazy('accounts:supplier_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Supplier updated successfully!')
        return super().form_valid(form)

class SupplierDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Supplier
    template_name = 'procurement/supplier_confirm_delete.html'
    permission_required = 'procurement.delete_supplier'
    success_url = reverse_lazy('accounts:supplier_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Supplier deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Purchase Order Views
class PurchaseOrderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'procurement/purchase_order_list.html'
    context_object_name = 'purchase_orders'
    permission_required = 'procurement.view_purchaseorder'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = PurchaseOrder.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', '')
        return context

@login_required
@permission_required('procurement.add_purchaseorder')
def create_purchase_order(request):
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            purchase_order = form.save(commit=False)
            purchase_order.requested_by = request.user
            purchase_order.status = 'pending_approval'
            purchase_order.save()
            
            # Save items
            instances = formset.save(commit=False)
            for instance in instances:
                instance.purchase_order = purchase_order
                instance.save()
            
            # Delete marked items
            for obj in formset.deleted_objects:
                obj.delete()
            
            messages.success(request, 'Purchase Order created successfully and sent for approval!')
            return redirect('accounts:purchase_order_detail', pk=purchase_order.pk)
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet()
    
    return render(request, 'procurement/purchase_order_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Create Purchase Order'
    })

class PurchaseOrderDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = 'procurement/purchase_order_detail.html'
    permission_required = 'procurement.view_purchaseorder'
    context_object_name = 'purchase_order'

@login_required
@permission_required('procurement.change_purchaseorder')
def approve_purchase_order(request, pk):
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if purchase_order.status != 'pending_approval':
        messages.error(request, 'This purchase order cannot be approved.')
        return redirect('accounts:purchase_order_detail', pk=pk)
    
    purchase_order.status = 'approved'
    purchase_order.approved_by = request.user
    purchase_order.approved_at = timezone.now()
    purchase_order.save()
    
    messages.success(request, 'Purchase Order approved successfully!')
    return redirect('accounts:purchase_order_detail', pk=pk)

@login_required
@permission_required('procurement.change_purchaseorder')
def reject_purchase_order(request, pk):
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if purchase_order.status != 'pending_approval':
        messages.error(request, 'This purchase order cannot be rejected.')
        return redirect('accounts:purchase_order_detail', pk=pk)
    
    purchase_order.status = 'rejected'
    purchase_order.save()
    
    messages.warning(request, 'Purchase Order rejected.')
    return redirect('accounts:purchase_order_detail', pk=pk)

@login_required
@permission_required('procurement.change_purchaseorder')
def mark_purchase_order_paid(request, pk):
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if purchase_order.status != 'approved':
        messages.error(request, 'Only approved purchase orders can be marked as paid.')
        return redirect('accounts:purchase_order_detail', pk=pk)
    
    purchase_order.status = 'paid'
    purchase_order.payment_date = timezone.now().date()
    purchase_order.save()
    
    messages.success(request, 'Purchase Order marked as paid.')
    return redirect('accounts:purchase_order_detail', pk=pk)

# Goods Received Note Views
@login_required
@permission_required('procurement.add_goodsreceivednote')
def create_goods_received_note(request, po_id):
    purchase_order = get_object_or_404(PurchaseOrder, pk=po_id)
    
    # Check if PO is paid
    if purchase_order.status != 'paid':
        messages.error(request, 'Purchase Order must be marked as paid before creating GRN.')
        return redirect('accounts:purchase_order_detail', pk=po_id)
    
    # Check if GRN already exists
    if hasattr(purchase_order, 'grn'):
        messages.error(request, 'GRN already exists for this Purchase Order.')
        return redirect('accounts:purchase_order_detail', pk=po_id)
    
    if request.method == 'POST':
        form = GoodsReceivedNoteForm(request.POST, user=request.user)
        if form.is_valid():
            grn = form.save(commit=False)
            grn.purchase_order = purchase_order
            grn.received_by = request.user
            grn.save()
            
            # Update inventory for each item
            for item in purchase_order.items.all():
                InventoryTransaction.objects.create(
                    raw_material=item.raw_material,
                    transaction_type='purchase',
                    quantity=item.quantity,
                    reference=purchase_order.po_number,
                    notes=f'Received via {grn.grn_number}',
                    created_by=request.user
                )
            
            # Update PO status
            purchase_order.status = 'completed'
            purchase_order.save()
            
            messages.success(request, 'Goods Received Note created and inventory updated successfully!')
            return redirect('accounts:grn_detail', pk=grn.pk)
    else:
        form = GoodsReceivedNoteForm(user=request.user)
    
    return render(request, 'procurement/grn_form.html', {
        'form': form,
        'purchase_order': purchase_order,
        'title': 'Create Goods Received Note'
    })

class GoodsReceivedNoteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = GoodsReceivedNote
    template_name = 'procurement/grn_detail.html'
    permission_required = 'procurement.view_goodsreceivednote'
    context_object_name = 'grn'

# Dashboard data
@login_required
def procurement_dashboard_data(request):
    data = {
        'total_pos': PurchaseOrder.objects.count(),
        'pending_approval': PurchaseOrder.objects.filter(status='pending_approval').count(),
        'total_suppliers': Supplier.objects.count(),
        'monthly_spending': PurchaseOrder.objects.filter(
            created_at__month=timezone.now().month,
            status__in=['paid', 'completed']
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
    }
    return JsonResponse(data)