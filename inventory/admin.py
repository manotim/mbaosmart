from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count, F, Case, When, Value
from django.db.models.functions import Coalesce
from django.db import models
from .models import (
    RawMaterialCategory, RawMaterial, 
    InventoryTransaction, StockAdjustment, StockAlert
)

class RawMaterialInline(admin.TabularInline):
    model = RawMaterial
    extra = 0
    can_delete = False
    fields = ['name', 'code', 'current_stock', 'unit_price', 'stock_status_badge']
    readonly_fields = ['current_stock', 'stock_status_badge']
    show_change_link = True
    
    def stock_status_badge(self, obj):
        colors = {
            'out_of_stock': 'danger',
            'low_stock': 'warning',
            'normal': 'success',
            'over_stock': 'info'
        }
        color = colors.get(obj.stock_status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.stock_status_text
        )
    
    stock_status_badge.short_description = 'Status'

class InventoryTransactionInline(admin.TabularInline):
    model = InventoryTransaction
    extra = 0
    can_delete = False
    fields = ['transaction_type_badge', 'quantity', 'unit_price_formatted', 'total_value_formatted', 'reference', 'created_at_short']
    readonly_fields = ['transaction_type_badge', 'quantity', 'unit_price_formatted', 'total_value_formatted', 'reference', 'created_at_short']
    
    def transaction_type_badge(self, obj):
        colors = {
            'purchase': 'success',
            'production_usage': 'warning',
            'adjustment': 'info',
            'return': 'primary',
            'transfer': 'secondary',
            'damage': 'danger'
        }
        color = colors.get(obj.transaction_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_transaction_type_display()
        )
    
    transaction_type_badge.short_description = 'Type'
    
    def unit_price_formatted(self, obj):
        if obj.unit_price:
            return f"Ksh {obj.unit_price:,.2f}"
        return "-"
    
    unit_price_formatted.short_description = 'Unit Price'
    
    def total_value_formatted(self, obj):
        if obj.total_value:
            return format_html('<strong>Ksh {:,.2f}</strong>', obj.total_value)
        return "-"
    
    total_value_formatted.short_description = 'Total Value'
    
    def created_at_short(self, obj):
        return obj.created_at.strftime('%d/%m/%Y')
    
    created_at_short.short_description = 'Date'

class StockAlertInline(admin.TabularInline):
    model = StockAlert
    extra = 0
    can_delete = False
    fields = ['alert_type_badge', 'message_short', 'is_active_badge', 'acknowledged_status', 'created_at_short']
    readonly_fields = ['alert_type_badge', 'message_short', 'is_active_badge', 'acknowledged_status', 'created_at_short']
    
    def alert_type_badge(self, obj):
        colors = {
            'low_stock': 'warning',
            'out_of_stock': 'danger',
            'expiring': 'info'
        }
        color = colors.get(obj.alert_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_alert_type_display()
        )
    
    alert_type_badge.short_description = 'Alert Type'
    
    def message_short(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    
    message_short.short_description = 'Message'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge bg-success">Active</span>')
        return format_html('<span class="badge bg-secondary">Inactive</span>')
    
    is_active_badge.short_description = 'Active'
    
    def acknowledged_status(self, obj):
        if obj.acknowledged_by:
            return format_html(
                '<small>Acknowledged by {}<br>on {}</small>',
                obj.acknowledged_by.get_full_name() or obj.acknowledged_by.username,
                obj.acknowledged_at.strftime('%d/%m/%Y %H:%M') if obj.acknowledged_at else ''
            )
        return format_html('<span class="badge bg-warning">Pending</span>')
    
    acknowledged_status.short_description = 'Acknowledgment'
    
    def created_at_short(self, obj):
        return obj.created_at.strftime('%d/%m/%Y')
    
    created_at_short.short_description = 'Created'

@admin.register(RawMaterialCategory)
class RawMaterialCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'material_count', 'created_at_short']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'materials_summary']
    fieldsets = [
        ('Category Information', {
            'fields': ['name', 'description']
        }),
        ('Statistics', {
            'fields': ['materials_summary'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at'],
            'classes': ['collapse']
        }),
    ]
    inlines = [RawMaterialInline]
    
    def material_count(self, obj):
        count = obj.raw_materials.count()
        url = reverse('admin:inventory_rawmaterial_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, f"{count} material(s)")
    
    material_count.short_description = 'Materials'
    
    def created_at_short(self, obj):
        return obj.created_at.strftime('%d/%m/%Y')
    
    created_at_short.short_description = 'Created'
    
    def materials_summary(self, obj):
        materials = obj.raw_materials.all()
        if not materials:
            return "No materials in this category."
        
        total_value = sum(m.total_value for m in materials)
        low_stock_count = sum(1 for m in materials if m.stock_status == 'low_stock')
        out_of_stock_count = sum(1 for m in materials if m.stock_status == 'out_of_stock')
        
        html = f"""
        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
            <strong>Total Materials:</strong> {materials.count()}<br>
            <strong>Total Inventory Value:</strong> Ksh {total_value:,.2f}<br>
            <strong>Low Stock Items:</strong> <span class="badge bg-warning">{low_stock_count}</span><br>
            <strong>Out of Stock Items:</strong> <span class="badge bg-danger">{out_of_stock_count}</span>
        </div>
        """
        return format_html(html)
    
    materials_summary.short_description = 'Category Summary'
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            material_count=Count('raw_materials')
        )

@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'code',
        'category_link',
        'current_stock_with_unit',
        'unit_price_formatted',
        'total_value_formatted',
        'stock_status_badge',
        'supplier_link',
        'last_updated'
    ]
    
    list_filter = ['category',
        'unit',
        'supplier',
        'created_at',
        'updated_at']
    
    search_fields = [
        'name',
        'code',
        'category__name',
        'supplier__name',
        'location',
        'notes'
    ]
    
    readonly_fields = [
        'code',
        'current_stock',
        'total_value',
        'stock_status',
        'stock_status_text',
        'created_at',
        'updated_at',
        'stock_history_summary',
        'stock_level_indicator'
    ]
    
    fieldsets = [
        ('Basic Information', {
            'fields': [
                'name',
                'code',
                'category',
                'unit',
                'location',
                'supplier'
            ]
        }),
        ('Pricing & Stock Levels', {
            'fields': [
                'unit_price',
                'min_stock_level',
                'max_stock_level',
                'current_stock',
                'total_value'
            ]
        }),
        ('Stock Status', {
            'fields': [
                'stock_status',
                'stock_status_text',
                'stock_level_indicator'
            ],
            'classes': ['collapse']
        }),
        ('Transaction History', {
            'fields': ['stock_history_summary'],
            'classes': ['collapse']
        }),
        ('Additional Information', {
            'fields': ['notes'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [InventoryTransactionInline, StockAlertInline]
    
    autocomplete_fields = ['category', 'supplier']
    
    actions = [
        'check_stock_levels',
        'generate_low_stock_alerts',
        'export_inventory_csv',
        'update_unit_prices',
        'perform_physical_count'
    ]
    
    def category_link(self, obj):
        url = reverse('admin:inventory_rawmaterialcategory_change', args=[obj.category.id])
        return format_html('<a href="{}">{}</a>', url, obj.category.name)
    
    category_link.short_description = 'Category'
    category_link.admin_order_field = 'category__name'
    
    def current_stock_with_unit(self, obj):
        return f"{obj.current_stock} {obj.get_unit_display()}"
    
    current_stock_with_unit.short_description = 'Current Stock'
    current_stock_with_unit.admin_order_field = 'current_stock'
    
    def unit_price_formatted(self, obj):
        return f"Ksh {obj.unit_price:,.2f}"
    
    unit_price_formatted.short_description = 'Unit Price'
    
    def total_value_formatted(self, obj):
        return format_html('<strong>Ksh {:,.2f}</strong>', obj.total_value)
    
    total_value_formatted.short_description = 'Total Value'
    total_value_formatted.admin_order_field = 'total_value'
    
    def stock_status_badge(self, obj):
        colors = {
            'out_of_stock': 'danger',
            'low_stock': 'warning',
            'normal': 'success',
            'over_stock': 'info'
        }
        color = colors.get(obj.stock_status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.stock_status_text
        )
    
    stock_status_badge.short_description = 'Stock Status'
    stock_status_badge.admin_order_field = 'stock_status'
    
    def supplier_link(self, obj):
        if obj.supplier:
            url = reverse('admin:procurement_supplier_change', args=[obj.supplier.id])
            return format_html('<a href="{}">{}</a>', url, obj.supplier.name)
        return "-"
    
    supplier_link.short_description = 'Supplier'
    
    def last_updated(self, obj):
        return obj.updated_at.strftime('%d/%m/%Y')
    
    last_updated.short_description = 'Last Updated'
    last_updated.admin_order_field = 'updated_at'
    
    def stock_history_summary(self, obj):
        transactions = obj.transactions.all()[:10]
        if not transactions:
            return "No transaction history."
        
        html = '<div style="max-height: 300px; overflow-y: auto;">'
        html += '<table class="table table-sm">'
        html += '<thead><tr><th>Date</th><th>Type</th><th>Quantity</th><th>Value</th><th>Reference</th></tr></thead>'
        html += '<tbody>'
        
        for txn in transactions:
            html += f"""
            <tr>
                <td>{txn.created_at.strftime('%d/%m/%Y')}</td>
                <td><span class="badge bg-{txn.get_transaction_type_display().lower().replace(' ', '_')}">{txn.get_transaction_type_display()}</span></td>
                <td>{txn.quantity} {obj.unit}</td>
                <td>Ksh {txn.total_value:,.2f if txn.total_value else 0}</td>
                <td><small>{txn.reference}</small></td>
            </tr>
            """
        
        html += '</tbody></table>'
        html += f'<div class="text-end"><small><a href="{reverse("admin:inventory_inventorytransaction_changelist")}?raw_material__id__exact={obj.id}">View all transactions →</a></small></div>'
        html += '</div>'
        
        return format_html(html)
    
    stock_history_summary.short_description = 'Recent Transactions'
    
    def stock_level_indicator(self, obj):
        if obj.max_stock_level <= 0:
            return "Max stock level not set"
        
        percentage = (obj.current_stock / obj.max_stock_level) * 100
        if percentage <= 10:
            color = 'danger'
        elif percentage <= 30:
            color = 'warning'
        elif percentage <= 80:
            color = 'success'
        else:
            color = 'info'
        
        html = f"""
        <div style="margin-top: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span>Min: {obj.min_stock_level} {obj.unit}</span>
                <span>Current: {obj.current_stock} {obj.unit}</span>
                <span>Max: {obj.max_stock_level} {obj.unit}</span>
            </div>
            <div style="width: 100%; background-color: #e9ecef; border-radius: 3px; height: 20px;">
                <div style="width: {min(percentage, 100)}%; background-color: var(--bs-{color}); height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">
                    {percentage:.1f}%
                </div>
            </div>
            <div style="text-align: center; margin-top: 5px; font-size: 12px;">
                <span style="color: #dc3545;">● Low</span> | 
                <span style="color: #ffc107;">● Warning</span> | 
                <span style="color: #28a745;">● Good</span> | 
                <span style="color: #17a2b8;">● Overstock</span>
            </div>
        </div>
        """
        return format_html(html)
    
    stock_level_indicator.short_description = 'Stock Level Indicator'
    
    def check_stock_levels(self, request, queryset):
        """Check and report stock levels"""
        low_stock = []
        out_of_stock = []
        over_stock = []
        
        for material in queryset:
            if material.stock_status == 'low_stock':
                low_stock.append(material)
            elif material.stock_status == 'out_of_stock':
                out_of_stock.append(material)
            elif material.stock_status == 'over_stock':
                over_stock.append(material)
        
        message = f"""
        <strong>Stock Level Report:</strong><br>
        • Low Stock: {len(low_stock)} items<br>
        • Out of Stock: {len(out_of_stock)} items<br>
        • Over Stock: {len(over_stock)} items<br>
        • Normal: {queryset.count() - len(low_stock) - len(out_of_stock) - len(over_stock)} items
        """
        
        self.message_user(request, format_html(message), messages.INFO)
    
    check_stock_levels.short_description = "Check stock levels"
    
    def generate_low_stock_alerts(self, request, queryset):
        """Generate alerts for low stock items"""
        created_count = 0
        for material in queryset:
            if material.stock_status in ['low_stock', 'out_of_stock'] and not StockAlert.objects.filter(
                raw_material=material, 
                alert_type='low_stock', 
                is_active=True
            ).exists():
                
                if material.stock_status == 'out_of_stock':
                    alert_type = 'out_of_stock'
                    message = f"{material.name} is out of stock. Current stock: {material.current_stock} {material.unit}"
                else:
                    alert_type = 'low_stock'
                    message = f"{material.name} is below minimum stock level. Current: {material.current_stock} {material.unit}, Min: {material.min_stock_level} {material.unit}"
                
                StockAlert.objects.create(
                    raw_material=material,
                    alert_type=alert_type,
                    message=message,
                    is_active=True
                )
                created_count += 1
        
        self.message_user(
            request,
            f'Generated {created_count} new stock alerts',
            messages.SUCCESS
        )
    
    generate_low_stock_alerts.short_description = "Generate stock alerts"
    
    def export_inventory_csv(self, request, queryset):
        """Export inventory data to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="inventory_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Code', 'Name', 'Category', 'Unit', 'Current Stock',
            'Unit Price', 'Total Value', 'Min Stock', 'Max Stock',
            'Stock Status', 'Location', 'Supplier'
        ])
        
        for material in queryset:
            writer.writerow([
                material.code,
                material.name,
                material.category.name,
                material.get_unit_display(),
                material.current_stock,
                material.unit_price,
                material.total_value,
                material.min_stock_level,
                material.max_stock_level,
                material.stock_status_text,
                material.location,
                material.supplier.name if material.supplier else ''
            ])
        
        self.message_user(request, f'Exported {queryset.count()} inventory items to CSV')
        return response
    
    export_inventory_csv.short_description = "Export inventory to CSV"
    
    def update_unit_prices(self, request, queryset):
        """Update unit prices for selected materials"""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        selected_ids = queryset.values_list('id', flat=True)
        url = reverse('admin:bulk_update_prices') + f'?ids={",".join(str(id) for id in selected_ids)}'
        return HttpResponseRedirect(url)
    
    update_unit_prices.short_description = "Update unit prices..."
    
    def perform_physical_count(self, request, queryset):
        """Initiate physical count for selected materials"""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        selected_ids = queryset.values_list('id', flat=True)
        url = reverse('admin:physical_count') + f'?ids={",".join(str(id) for id in selected_ids)}'
        return HttpResponseRedirect(url)
    
    perform_physical_count.short_description = "Perform physical count..."
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category', 'supplier'
        )

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'created_at_formatted',
        'raw_material_link',
        'transaction_type_badge',
        'quantity_with_unit',
        'unit_price_formatted',
        'total_value_formatted',
        'reference_link',
        'created_by_display'
    ]
    
    list_filter = [
        'transaction_type',
        'created_at',
        'raw_material__category',
        'created_by'
    ]
    
    search_fields = [
        'raw_material__name',
        'raw_material__code',
        'reference',
        'notes',
        'created_by__username',
        'created_by__first_name',
        'created_by__last_name'
    ]
    
    readonly_fields = [
        'total_value',
        'created_at',
        'transaction_impact'
    ]
    
    fieldsets = [
        ('Transaction Details', {
            'fields': [
                'raw_material',
                'transaction_type',
                'quantity',
                'unit_price',
                'total_value'
            ]
        }),
        ('Reference Information', {
            'fields': ['reference', 'notes']
        }),
        ('Impact Analysis', {
            'fields': ['transaction_impact'],
            'classes': ['collapse']
        }),
        ('Personnel', {
            'fields': ['created_by'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at'],
            'classes': ['collapse']
        }),
    ]
    
    autocomplete_fields = ['raw_material', 'created_by']
    
    actions = [
        'export_transactions_csv',
        'bulk_update_references'
    ]
    
    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    
    created_at_formatted.short_description = 'Date & Time'
    created_at_formatted.admin_order_field = 'created_at'
    
    def raw_material_link(self, obj):
        url = reverse('admin:inventory_rawmaterial_change', args=[obj.raw_material.id])
        return format_html('<a href="{}">{}</a>', url, obj.raw_material.name)
    
    raw_material_link.short_description = 'Raw Material'
    
    def transaction_type_badge(self, obj):
        colors = {
            'purchase': 'success',
            'production_usage': 'warning',
            'adjustment': 'info',
            'return': 'primary',
            'transfer': 'secondary',
            'damage': 'danger'
        }
        color = colors.get(obj.transaction_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_transaction_type_display()
        )
    
    transaction_type_badge.short_description = 'Type'
    
    def quantity_with_unit(self, obj):
        return f"{obj.quantity} {obj.raw_material.unit}"
    
    quantity_with_unit.short_description = 'Quantity'
    
    def unit_price_formatted(self, obj):
        if obj.unit_price:
            return f"Ksh {obj.unit_price:,.2f}"
        return "-"
    
    unit_price_formatted.short_description = 'Unit Price'
    
    def total_value_formatted(self, obj):
        if obj.total_value:
            return format_html('<strong>Ksh {:,.2f}</strong>', obj.total_value)
        return "-"
    
    total_value_formatted.short_description = 'Total Value'
    
    def reference_link(self, obj):
        # Try to find related object based on reference
        if obj.reference.startswith('PO-'):
            # Purchase Order reference
            try:
                from procurement.models import PurchaseOrder
                po = PurchaseOrder.objects.get(po_number=obj.reference)
                url = reverse('admin:procurement_purchaseorder_change', args=[po.id])
                return format_html('<a href="{}">{}</a>', url, obj.reference)
            except:
                pass
        elif obj.reference.startswith('PROD-'):
            # Production Order reference
            try:
                from production.models import ProductionOrder
                prod = ProductionOrder.objects.get(order_number=obj.reference)
                url = reverse('admin:production_productionorder_change', args=[prod.id])
                return format_html('<a href="{}">{}</a>', url, obj.reference)
            except:
                pass
        
        return obj.reference
    
    reference_link.short_description = 'Reference'
    
    def created_by_display(self, obj):
        return f"{obj.created_by.get_full_name() or obj.created_by.username}"
    
    created_by_display.short_description = 'Created By'
    
    def transaction_impact(self, obj):
        material = obj.raw_material
        before_stock = material.current_stock
        
        if obj.transaction_type in ['purchase', 'return']:
            before_stock -= obj.quantity
            impact = "increased"
        else:
            before_stock += obj.quantity
            impact = "decreased"
        
        html = f"""
        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
            <strong>Stock Impact:</strong><br>
            • Before: {before_stock} {material.unit}<br>
            • Change: {obj.quantity} {material.unit}<br>
            • After: {material.current_stock} {material.unit}<br>
            • Stock {impact} by {obj.quantity} {material.unit}
        </div>
        """
        return format_html(html)
    
    transaction_impact.short_description = 'Stock Impact'
    
    def export_transactions_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="inventory_transactions.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Material', 'Type', 'Quantity', 'Unit',
            'Unit Price', 'Total Value', 'Reference', 'Created By', 'Notes'
        ])
        
        for txn in queryset:
            writer.writerow([
                txn.created_at.strftime('%Y-%m-%d %H:%M'),
                txn.raw_material.name,
                txn.get_transaction_type_display(),
                txn.quantity,
                txn.raw_material.unit,
                txn.unit_price,
                txn.total_value,
                txn.reference,
                txn.created_by.get_full_name() or txn.created_by.username,
                txn.notes[:100]
            ])
        
        self.message_user(request, f'Exported {queryset.count()} transactions to CSV')
        return response
    
    export_transactions_csv.short_description = "Export transactions to CSV"
    
    def bulk_update_references(self, request, queryset):
        """Bulk update transaction references"""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        selected_ids = queryset.values_list('id', flat=True)
        url = reverse('admin:bulk_update_references') + f'?ids={",".join(str(id) for id in selected_ids)}'
        return HttpResponseRedirect(url)
    
    bulk_update_references.short_description = "Update references..."
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'raw_material', 'raw_material__category', 'created_by'
        )

@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = [
        'adjusted_at_formatted',
        'raw_material_link',
        'adjustment_type_badge',
        'quantity_with_unit',
        'reason_badge',
        'stock_change_display',
        'adjusted_by_display'
    ]
    
    list_filter = [
        'adjustment_type',
        'reason',
        'adjusted_at',
        'adjusted_by'
    ]
    
    search_fields = [
        'raw_material__name',
        'raw_material__code',
        'notes',
        'adjusted_by__username',
        'adjusted_by__first_name',
        'adjusted_by__last_name'
    ]
    
    readonly_fields = [
        'previous_stock',
        'new_stock',
        'adjusted_at',
        'adjustment_summary'
    ]
    
    fieldsets = [
        ('Adjustment Details', {
            'fields': [
                'raw_material',
                'adjustment_type',
                'quantity',
                'reason',
                'notes'
            ]
        }),
        ('Stock Levels', {
            'fields': [
                'previous_stock',
                'new_stock',
                'adjustment_summary'
            ]
        }),
        ('Personnel', {
            'fields': ['adjusted_by'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['adjusted_at'],
            'classes': ['collapse']
        }),
    ]
    
    autocomplete_fields = ['raw_material', 'adjusted_by']
    
    actions = ['export_adjustments_csv']
    
    def adjusted_at_formatted(self, obj):
        return obj.adjusted_at.strftime('%d/%m/%Y %H:%M')
    
    adjusted_at_formatted.short_description = 'Adjusted At'
    
    def raw_material_link(self, obj):
        url = reverse('admin:inventory_rawmaterial_change', args=[obj.raw_material.id])
        return format_html('<a href="{}">{}</a>', url, obj.raw_material.name)
    
    raw_material_link.short_description = 'Raw Material'
    
    def adjustment_type_badge(self, obj):
        colors = {
            'add': 'success',
            'remove': 'danger',
            'set': 'info'
        }
        color = colors.get(obj.adjustment_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_adjustment_type_display()
        )
    
    adjustment_type_badge.short_description = 'Type'
    
    def quantity_with_unit(self, obj):
        return f"{obj.quantity} {obj.raw_material.unit}"
    
    quantity_with_unit.short_description = 'Quantity'
    
    def reason_badge(self, obj):
        colors = {
            'physical_count': 'primary',
            'damage': 'danger',
            'expired': 'warning',
            'theft': 'dark',
            'other': 'secondary'
        }
        color = colors.get(obj.reason, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_reason_display()
        )
    
    reason_badge.short_description = 'Reason'
    
    def stock_change_display(self, obj):
        change = obj.new_stock - obj.previous_stock
        if change > 0:
            return format_html('<span style="color: green;">+{} {}</span>', change, obj.raw_material.unit)
        elif change < 0:
            return format_html('<span style="color: red;">{} {}</span>', change, obj.raw_material.unit)
        return format_html('<span>No change</span>')
    
    stock_change_display.short_description = 'Stock Change'
    
    def adjusted_by_display(self, obj):
        return f"{obj.adjusted_by.get_full_name() or obj.adjusted_by.username}"
    
    adjusted_by_display.short_description = 'Adjusted By'
    
    def adjustment_summary(self, obj):
        change = obj.new_stock - obj.previous_stock
        change_percentage = (change / obj.previous_stock * 100) if obj.previous_stock > 0 else 100
        
        html = f"""
        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
            <strong>Adjustment Summary:</strong><br>
            • Previous Stock: {obj.previous_stock} {obj.raw_material.unit}<br>
            • New Stock: {obj.new_stock} {obj.raw_material.unit}<br>
            • Change: {change:+.2f} {obj.raw_material.unit}<br>
            • Change Percentage: {change_percentage:+.1f}%<br>
            • Reason: {obj.get_reason_display()}<br>
            • Notes: {obj.notes or 'No additional notes'}
        </div>
        """
        return format_html(html)
    
    adjustment_summary.short_description = 'Summary'
    
    def export_adjustments_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="stock_adjustments.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Material', 'Type', 'Quantity', 'Reason',
            'Previous Stock', 'New Stock', 'Change', 'Adjusted By', 'Notes'
        ])
        
        for adj in queryset:
            change = adj.new_stock - adj.previous_stock
            writer.writerow([
                adj.adjusted_at.strftime('%Y-%m-%d %H:%M'),
                adj.raw_material.name,
                adj.get_adjustment_type_display(),
                adj.quantity,
                adj.get_reason_display(),
                adj.previous_stock,
                adj.new_stock,
                change,
                adj.adjusted_by.get_full_name() or adj.adjusted_by.username,
                adj.notes[:100]
            ])
        
        self.message_user(request, f'Exported {queryset.count()} adjustments to CSV')
        return response
    
    export_adjustments_csv.short_description = "Export adjustments to CSV"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'raw_material', 'adjusted_by'
        )

@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = [
        'created_at_formatted',
        'raw_material_link',
        'alert_type_badge',
        'message_short',
        'is_active_badge',
        'acknowledged_status',
        'actions_column'
    ]
    
    list_filter = [
        'alert_type',
        'is_active',
        'acknowledged_by',
        'created_at'
    ]
    
    search_fields = [
        'raw_material__name',
        'raw_material__code',
        'message',
        'acknowledged_by__username'
    ]
    
    readonly_fields = [
        'created_at',
        'acknowledged_at',
        'alert_details'
    ]
    
    fieldsets = [
        ('Alert Information', {
            'fields': [
                'raw_material',
                'alert_type',
                'message',
                'is_active'
            ]
        }),
        ('Acknowledgment', {
            'fields': [
                'acknowledged_by',
                'acknowledged_at'
            ],
            'classes': ['collapse']
        }),
        ('Alert Details', {
            'fields': ['alert_details'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at'],
            'classes': ['collapse']
        }),
    ]
    
    autocomplete_fields = ['raw_material', 'acknowledged_by']
    
    actions = [
        'mark_as_acknowledged',
        'mark_as_resolved',
        'export_alerts_csv'
    ]
    
    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    
    created_at_formatted.short_description = 'Created'
    
    def raw_material_link(self, obj):
        url = reverse('admin:inventory_rawmaterial_change', args=[obj.raw_material.id])
        return format_html('<a href="{}">{}</a>', url, obj.raw_material.name)
    
    raw_material_link.short_description = 'Raw Material'
    
    def alert_type_badge(self, obj):
        colors = {
            'low_stock': 'warning',
            'out_of_stock': 'danger',
            'expiring': 'info'
        }
        color = colors.get(obj.alert_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_alert_type_display()
        )
    
    alert_type_badge.short_description = 'Alert Type'
    
    def message_short(self, obj):
        return obj.message[:60] + '...' if len(obj.message) > 60 else obj.message
    
    message_short.short_description = 'Message'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge bg-success">Active</span>')
        return format_html('<span class="badge bg-secondary">Resolved</span>')
    
    is_active_badge.short_description = 'Status'
    
    def acknowledged_status(self, obj):
        if obj.acknowledged_by:
            return format_html(
                '<small>Acknowledged by {}<br>on {}</small>',
                obj.acknowledged_by.get_full_name() or obj.acknowledged_by.username,
                obj.acknowledged_at.strftime('%d/%m/%Y') if obj.acknowledged_at else ''
            )
        return format_html('<span class="badge bg-warning">Pending</span>')
    
    acknowledged_status.short_description = 'Acknowledgment'
    
    def actions_column(self, obj):
        buttons = []
        
        # View button
        view_url = reverse('admin:inventory_stockalert_change', args=[obj.id])
        buttons.append(f'<a href="{view_url}" class="btn btn-sm btn-info" title="View">View</a>')
        
        # Acknowledge button
        if not obj.acknowledged_by:
            ack_url = reverse('admin:acknowledge_alert', args=[obj.id])
            buttons.append(f'<a href="{ack_url}" class="btn btn-sm btn-warning" title="Acknowledge">Ack</a>')
        
        # Resolve button
        if obj.is_active:
            resolve_url = reverse('admin:resolve_alert', args=[obj.id])
            buttons.append(f'<a href="{resolve_url}" class="btn btn-sm btn-success" title="Resolve">✓</a>')
        
        return format_html(' '.join(buttons))
    
    actions_column.short_description = 'Actions'
    
    def alert_details(self, obj):
        material = obj.raw_material
        html = f"""
        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
            <strong>Material Details:</strong><br>
            • Name: {material.name}<br>
            • Code: {material.code}<br>
            • Current Stock: {material.current_stock} {material.unit}<br>
            • Min Stock Level: {material.min_stock_level} {material.unit}<br>
            • Max Stock Level: {material.max_stock_level} {material.unit}<br>
            • Unit Price: Ksh {material.unit_price:,.2f}<br>
            • Total Value: Ksh {material.total_value:,.2f}<br>
            • Location: {material.location}<br>
            • Supplier: {material.supplier.name if material.supplier else 'N/A'}
        </div>
        """
        return format_html(html)
    
    alert_details.short_description = 'Material Details'
    
    def mark_as_acknowledged(self, request, queryset):
        """Mark selected alerts as acknowledged"""
        updated = queryset.filter(acknowledged_by__isnull=True).update(
            acknowledged_by=request.user,
            acknowledged_at=timezone.now()
        )
        
        self.message_user(
            request,
            f'Acknowledged {updated} alert(s)',
            messages.SUCCESS
        )
    
    mark_as_acknowledged.short_description = "Mark as acknowledged"
    
    def mark_as_resolved(self, request, queryset):
        """Mark selected alerts as resolved"""
        updated = queryset.update(is_active=False)
        
        self.message_user(
            request,
            f'Resolved {updated} alert(s)',
            messages.SUCCESS
        )
    
    mark_as_resolved.short_description = "Mark as resolved"
    
    def export_alerts_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="stock_alerts.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Created', 'Material', 'Alert Type', 'Message',
            'Is Active', 'Acknowledged By', 'Acknowledged At'
        ])
        
        for alert in queryset:
            writer.writerow([
                alert.created_at.strftime('%Y-%m-%d %H:%M'),
                alert.raw_material.name,
                alert.get_alert_type_display(),
                alert.message,
                'Yes' if alert.is_active else 'No',
                alert.acknowledged_by.get_full_name() if alert.acknowledged_by else '',
                alert.acknowledged_at.strftime('%Y-%m-%d %H:%M') if alert.acknowledged_at else ''
            ])
        
        self.message_user(request, f'Exported {queryset.count()} alerts to CSV')
        return response
    
    export_alerts_csv.short_description = "Export alerts to CSV"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'raw_material', 'acknowledged_by'
        )

# Custom admin site header for inventory module
admin.site.site_header = "MbaoSmart Inventory Administration"
admin.site.site_title = "MbaoSmart Inventory Admin"
admin.site.index_title = "Inventory Module Administration"