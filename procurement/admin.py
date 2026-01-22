from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceivedNote

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    readonly_fields = ['total_price']
    fields = ['raw_material', 'quantity', 'unit_price', 'total_price']
    autocomplete_fields = ['raw_material']
    
    def get_queryset(self, request):
        # Optimize queryset
        return super().get_queryset(request).select_related('raw_material')

class GoodsReceivedNoteInline(admin.StackedInline):
    model = GoodsReceivedNote
    extra = 0
    max_num = 1
    can_delete = False
    fields = ['grn_number', 'received_by', 'checked_by', 'received_date', 'notes', 'is_verified']
    readonly_fields = ['grn_number', 'received_date']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('received_by', 'checked_by')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'email', 'tin_number', 'purchase_order_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'contact_person', 'phone', 'email', 'tin_number', 'address']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'contact_person', 'phone', 'email']
        }),
        ('Address Details', {
            'fields': ['address'],
            'classes': ['collapse']
        }),
        ('Tax Information', {
            'fields': ['tin_number']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def purchase_order_count(self, obj):
        count = obj.purchase_orders.count()
        url = reverse('admin:procurement_purchaseorder_changelist') + f'?supplier__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, f"{count} PO(s)")
    
    purchase_order_count.short_description = 'Purchase Orders'
    
    actions = ['export_suppliers_csv']
    
    def export_suppliers_csv(self, request, queryset):
        """Custom admin action to export suppliers"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="suppliers.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'Contact Person', 'Phone', 'Email', 'TIN', 'Address', 'Created At'])
        
        for supplier in queryset:
            writer.writerow([
                supplier.name,
                supplier.contact_person,
                supplier.phone,
                supplier.email,
                supplier.tin_number,
                supplier.address,
                supplier.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        self.message_user(request, f'Exported {queryset.count()} suppliers to CSV')
        return response
    
    export_suppliers_csv.short_description = "Export selected suppliers to CSV"

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        'po_number', 
        'supplier_link', 
        'status_badge', 
        'total_amount_formatted', 
        'requested_by_display',
        'approved_by_display',
        'created_at_formatted',
        'actions_column'
    ]
    
    list_filter = [
        'status',
        'created_at',
        'supplier',
        'requested_by',
        'approved_by'
    ]
    
    search_fields = [
        'po_number',
        'supplier__name',
        'requested_by__username',
        'requested_by__first_name',
        'requested_by__last_name',
        'notes'
    ]
    
    readonly_fields = [
        'po_number',
        'total_amount',
        'created_at',
        'approved_at',
        'payment_date',
        'delivery_date',
        'get_grn_link'
    ]
    
    fieldsets = [
        ('Order Information', {
            'fields': [
                'po_number',
                'supplier',
                'status',
                'total_amount',
                'notes'
            ]
        }),
        ('Personnel', {
            'fields': [
                'requested_by',
                'approved_by',
                'approved_at'
            ],
            'classes': ['collapse']
        }),
        ('Dates', {
            'fields': [
                'created_at',
                'delivery_date',
                'payment_date'
            ],
            'classes': ['collapse']
        }),
        ('Related Documents', {
            'fields': ['get_grn_link'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [PurchaseOrderItemInline, GoodsReceivedNoteInline]
    
    autocomplete_fields = ['supplier', 'requested_by', 'approved_by']
    
    actions = [
        'mark_as_approved',
        'mark_as_paid',
        'mark_as_completed',
        'export_to_csv',
        'generate_bulk_grn'
    ]
    
    def supplier_link(self, obj):
        url = reverse('admin:procurement_supplier_change', args=[obj.supplier.id])
        return format_html('<a href="{}">{}</a>', url, obj.supplier.name)
    
    supplier_link.short_description = 'Supplier'
    supplier_link.admin_order_field = 'supplier__name'
    
    def status_badge(self, obj):
        colors = {
            'draft': 'secondary',
            'pending_approval': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'paid': 'info',
            'completed': 'primary',
            'cancelled': 'dark'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def total_amount_formatted(self, obj):
        return format_html('<strong>Ksh {:,.2f}</strong>', obj.total_amount)
    
    total_amount_formatted.short_description = 'Total Amount'
    total_amount_formatted.admin_order_field = 'total_amount'
    
    def requested_by_display(self, obj):
        return f"{obj.requested_by.get_full_name() or obj.requested_by.username}"
    
    requested_by_display.short_description = 'Requested By'
    requested_by_display.admin_order_field = 'requested_by__username'
    
    def approved_by_display(self, obj):
        if obj.approved_by:
            return f"{obj.approved_by.get_full_name() or obj.approved_by.username}"
        return "-"
    
    approved_by_display.short_description = 'Approved By'
    
    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def actions_column(self, obj):
        links = []
        
        # View button
        view_url = reverse('admin:procurement_purchaseorder_change', args=[obj.id])
        links.append(f'<a href="{view_url}" class="btn btn-sm btn-info" title="View/Edit">View</a>')
        
        # GRN button if applicable
        if obj.status == 'paid' and not hasattr(obj, 'grn'):
            grn_url = reverse('accounts:create_grn', args=[obj.id])
            links.append(f'<a href="{grn_url}" class="btn btn-sm btn-success" title="Create GRN">Create GRN</a>')
        
        return format_html(' '.join(links))
    
    actions_column.short_description = 'Actions'
    
    def get_grn_link(self, obj):
        if hasattr(obj, 'grn'):
            url = reverse('admin:procurement_goodsreceivednote_change', args=[obj.grn.id])
            return format_html('<a href="{}">View GRN #{}</a>', url, obj.grn.grn_number)
        return "No GRN created yet"
    
    get_grn_link.short_description = 'Goods Received Note'
    
    def mark_as_approved(self, request, queryset):
        updated = queryset.filter(status='pending_approval').update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(
            request, 
            f'Successfully approved {updated} purchase order(s)',
            messages.SUCCESS
        )
    
    mark_as_approved.short_description = "Approve selected POs"
    
    def mark_as_paid(self, request, queryset):
        updated = queryset.filter(status='approved').update(
            status='paid',
            payment_date=timezone.now().date()
        )
        self.message_user(
            request,
            f'Marked {updated} purchase order(s) as paid',
            messages.SUCCESS
        )
    
    mark_as_paid.short_description = "Mark selected POs as paid"
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status='paid').update(status='completed')
        self.message_user(
            request,
            f'Marked {updated} purchase order(s) as completed',
            messages.SUCCESS
        )
    
    mark_as_completed.short_description = "Mark selected POs as completed"
    
    def export_to_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="purchase_orders.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'PO Number', 'Supplier', 'Status', 'Total Amount', 
            'Requested By', 'Approved By', 'Created Date', 
            'Delivery Date', 'Payment Date', 'Notes'
        ])
        
        for po in queryset:
            writer.writerow([
                po.po_number,
                po.supplier.name,
                po.get_status_display(),
                po.total_amount,
                po.requested_by.get_full_name() or po.requested_by.username,
                po.approved_by.get_full_name() if po.approved_by else '',
                po.created_at.strftime('%Y-%m-%d'),
                po.delivery_date.strftime('%Y-%m-%d') if po.delivery_date else '',
                po.payment_date.strftime('%Y-%m-%d') if po.payment_date else '',
                po.notes[:100]  # First 100 characters
            ])
        
        self.message_user(request, f'Exported {queryset.count()} purchase orders to CSV')
        return response
    
    export_to_csv.short_description = "Export selected POs to CSV"
    
    def generate_bulk_grn(self, request, queryset):
        """Admin action to generate GRN for multiple POs"""
        eligible_pos = queryset.filter(status='paid', grn__isnull=True)
        
        if not eligible_pos.exists():
            self.message_user(
                request,
                "No eligible POs found. POs must be paid and have no existing GRN.",
                messages.WARNING
            )
            return
        
        # In a real implementation, you would redirect to a bulk GRN creation page
        self.message_user(
            request,
            f"Found {eligible_pos.count()} eligible POs for GRN creation. Use individual PO pages to create GRNs.",
            messages.INFO
        )
    
    generate_bulk_grn.short_description = "Generate GRN for selected POs"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'supplier', 
            'requested_by', 
            'approved_by'
        ).prefetch_related('items', 'items__raw_material')
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        # Add custom context for change view
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = True
        extra_context['show_save_and_add_another'] = True
        return super().change_view(request, object_id, form_url, extra_context)

@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'purchase_order_link',
        'raw_material_link',
        'quantity_with_unit',
        'unit_price_formatted',
        'total_price_formatted'
    ]
    
    list_filter = ['purchase_order__supplier', 'raw_material__category']
    
    search_fields = [
        'purchase_order__po_number',
        'raw_material__name',
        'raw_material__code'
    ]
    
    readonly_fields = ['total_price']
    
    autocomplete_fields = ['purchase_order', 'raw_material']
    
    def purchase_order_link(self, obj):
        url = reverse('admin:procurement_purchaseorder_change', args=[obj.purchase_order.id])
        return format_html('<a href="{}">{}</a>', url, obj.purchase_order.po_number)
    
    purchase_order_link.short_description = 'Purchase Order'
    purchase_order_link.admin_order_field = 'purchase_order__po_number'
    
    def raw_material_link(self, obj):
        url = reverse('admin:inventory_rawmaterial_change', args=[obj.raw_material.id])
        return format_html('<a href="{}">{}</a>', url, obj.raw_material.name)
    
    raw_material_link.short_description = 'Raw Material'
    raw_material_link.admin_order_field = 'raw_material__name'
    
    def quantity_with_unit(self, obj):
        return f"{obj.quantity} {obj.raw_material.unit_of_measure}"
    
    quantity_with_unit.short_description = 'Quantity'
    
    def unit_price_formatted(self, obj):
        return f"Ksh {obj.unit_price:,.2f}"
    
    unit_price_formatted.short_description = 'Unit Price'
    
    def total_price_formatted(self, obj):
        return format_html('<strong>Ksh {:,.2f}</strong>', obj.total_price)
    
    total_price_formatted.short_description = 'Total Price'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'purchase_order', 
            'purchase_order__supplier',
            'raw_material'
        )

@admin.register(GoodsReceivedNote)
class GoodsReceivedNoteAdmin(admin.ModelAdmin):
    actions = ["mark_as_verified", "mark_as_unverified", "export_grns_csv"]
    list_display = [
        'grn_number',
        'purchase_order_link',
        'received_by_display',
        'checked_by_display',
        'received_date_formatted',
        'is_verified_badge',
        'actions'
    ]
    
    list_filter = [
        'is_verified',
        'received_date',
        'received_by',
        'checked_by'
    ]
    
    search_fields = [
        'grn_number',
        'purchase_order__po_number',
        'received_by__username',
        'received_by__first_name',
        'received_by__last_name',
        'notes'
    ]
    
    readonly_fields = [
        'grn_number',
        'purchase_order',
        'received_date',
        'get_purchase_order_details'
    ]
    
    fieldsets = [
        ('GRN Information', {
            'fields': [
                'grn_number',
                'get_purchase_order_details',
                'received_date'
            ]
        }),
        ('Personnel', {
            'fields': [
                'received_by',
                'checked_by',
                'is_verified'
            ]
        }),
        ('Additional Information', {
            'fields': ['notes'],
            'classes': ['collapse']
        }),
    ]
    
    autocomplete_fields = ['received_by', 'checked_by']
    
    actions = ['mark_as_verified', 'mark_as_unverified', 'export_grns_csv']
    
    def purchase_order_link(self, obj):
        url = reverse('admin:procurement_purchaseorder_change', args=[obj.purchase_order.id])
        return format_html('<a href="{}">{}</a>', url, obj.purchase_order.po_number)
    
    purchase_order_link.short_description = 'Purchase Order'
    purchase_order_link.admin_order_field = 'purchase_order__po_number'
    
    def received_by_display(self, obj):
        return f"{obj.received_by.get_full_name() or obj.received_by.username}"
    
    received_by_display.short_description = 'Received By'
    received_by_display.admin_order_field = 'received_by__username'
    
    def checked_by_display(self, obj):
        if obj.checked_by:
            return f"{obj.checked_by.get_full_name() or obj.checked_by.username}"
        return "-"
    
    checked_by_display.short_description = 'Checked By'
    
    def received_date_formatted(self, obj):
        return obj.received_date.strftime('%d/%m/%Y %H:%M')
    
    received_date_formatted.short_description = 'Received Date'
    received_date_formatted.admin_order_field = 'received_date'
    
    def is_verified_badge(self, obj):
        if obj.is_verified:
            return format_html('<span class="badge bg-success">Verified</span>')
        return format_html('<span class="badge bg-warning">Pending Verification</span>')
    
    is_verified_badge.short_description = 'Verification Status'
    
    def action_buttons(self, obj):
        view_url = reverse('admin:procurement_goodsreceivednote_change', args=[obj.id])
        po_url = reverse('admin:procurement_purchaseorder_change', args=[obj.purchase_order.id])
        
        return format_html(
            '''
            <a href="{}" class="btn btn-sm btn-info" title="View GRN">View</a>
            <a href="{}" class="btn btn-sm btn-secondary" title="View PO">View PO</a>
            ''',
            view_url, po_url
        )
    
    
    def get_purchase_order_details(self, obj):
        po = obj.purchase_order
        details = f"""
        <div class="grn-po-details">
            <strong>PO:</strong> {po.po_number}<br>
            <strong>Supplier:</strong> {po.supplier.name}<br>
            <strong>Amount:</strong> Ksh {po.total_amount:,.2f}<br>
            <strong>Status:</strong> {po.get_status_display()}
        </div>
        """
        return format_html(details)
    
    get_purchase_order_details.short_description = 'Purchase Order Details'
    
    def mark_as_verified(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(
            request,
            f'Marked {updated} GRN(s) as verified',
            messages.SUCCESS
        )
    
    mark_as_verified.short_description = "Mark selected GRNs as verified"
    
    def mark_as_unverified(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(
            request,
            f'Marked {updated} GRN(s) as unverified',
            messages.WARNING
        )
    
    mark_as_unverified.short_description = "Mark selected GRNs as unverified"
    
    def export_grns_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="goods_received_notes.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'GRN Number', 'PO Number', 'Supplier', 'Received By', 
            'Checked By', 'Received Date', 'Verified', 'Notes'
        ])
        
        for grn in queryset:
            writer.writerow([
                grn.grn_number,
                grn.purchase_order.po_number,
                grn.purchase_order.supplier.name,
                grn.received_by.get_full_name() or grn.received_by.username,
                grn.checked_by.get_full_name() if grn.checked_by else '',
                grn.received_date.strftime('%Y-%m-%d %H:%M'),
                'Yes' if grn.is_verified else 'No',
                grn.notes[:200]
            ])
        
        self.message_user(request, f'Exported {queryset.count()} GRNs to CSV')
        return response
    
    export_grns_csv.short_description = "Export selected GRNs to CSV"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'purchase_order',
            'purchase_order__supplier',
            'received_by',
            'checked_by'
        )
    
    def has_add_permission(self, request):
        # Only allow adding through PurchaseOrder admin or custom views
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of GRNs as they are critical records
        return False

# Custom admin site header
admin.site.site_header = "MbaoSmart Procurement Administration"
admin.site.site_title = "MbaoSmart Procurement Admin"
admin.site.index_title = "Procurement Module Administration"