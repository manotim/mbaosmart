from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Avg
from django.db import transaction
from .models import (
    Product, ProductFormula, LabourTask, 
    ProductionOrder, ProductionTask, 
    WorkStation, ProductionLine
)

class ProductFormulaInline(admin.TabularInline):
    model = ProductFormula
    extra = 1
    fields = ['raw_material', 'quantity_required', 'notes', 'material_cost_display']
    readonly_fields = ['material_cost_display']
    autocomplete_fields = ['raw_material']
    
    def material_cost_display(self, obj):
        if obj.pk:
            return f"Ksh {obj.material_cost:,.2f}"
        return "N/A"
    
    material_cost_display.short_description = 'Material Cost'

class LabourTaskInline(admin.TabularInline):
    model = LabourTask
    extra = 1
    fields = ['task_type', 'task_name', 'labour_cost', 'estimated_hours', 'sequence', 'description']
    ordering = ['sequence']

class ProductionTaskInline(admin.TabularInline):
    model = ProductionTask
    extra = 0
    can_delete = False
    fields = ['labour_task', 'assigned_to', 'status_badge', 'sequence', 'start_date', 'completed_date']
    readonly_fields = ['labour_task', 'status_badge', 'start_date', 'completed_date']
    
    def status_badge(self, obj):
        colors = {
            'pending': 'secondary',
            'assigned': 'warning',
            'in_progress': 'info',
            'completed': 'success',
            'verified': 'primary',
            'cancelled': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'

class ProductionLineInline(admin.TabularInline):
    model = ProductionLine
    extra = 0
    can_delete = False
    fields = ['workstation', 'task', 'status', 'start_time', 'end_time']
    readonly_fields = ['workstation', 'task', 'status', 'start_time', 'end_time']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'sku_link',
        'product_type_badge',
        'selling_price_formatted',
        'production_cost_formatted',
        'profit_margin_badge',
        'is_active_badge',
        'created_at_short'
    ]
    
    list_filter = [
        'product_type',
        'is_active',
        'created_at',
        'updated_at'
    ]
    
    search_fields = [
        'name',
        'sku',
        'description',
        'product_type'
    ]
    
    readonly_fields = [
        'sku',
        'production_cost',
        'profit_margin',
        'created_at',
        'updated_at',
        'cost_breakdown'
    ]
    
    fieldsets = [
        ('Basic Information', {
            'fields': [
                'name',
                'product_type',
                'sku',
                'description',
                'image'
            ]
        }),
        ('Pricing & Cost', {
            'fields': [
                'selling_price',
                'cost_breakdown',
                'production_cost',
                'profit_margin'
            ]
        }),
        ('Status', {
            'fields': ['is_active']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [ProductFormulaInline, LabourTaskInline]
    
    actions = [
        'update_production_costs',
        'activate_products',
        'deactivate_products',
        'export_products_csv'
    ]
    
    def sku_link(self, obj):
        return format_html('<strong>{}</strong>', obj.sku)
    
    sku_link.short_description = 'SKU'
    sku_link.admin_order_field = 'sku'
    
    def product_type_badge(self, obj):
        colors = {
            'chair': 'primary',
            'bed': 'success',
            'table': 'info',
            'sofa': 'warning',
            'cabinet': 'secondary',
            'shelf': 'dark',
            'stool': 'danger',
            'bench': 'light'
        }
        color = colors.get(obj.product_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_product_type_display()
        )
    
    product_type_badge.short_description = 'Type'
    
    def selling_price_formatted(self, obj):
        return format_html('<strong>Ksh {:,.2f}</strong>', obj.selling_price)
    
    selling_price_formatted.short_description = 'Selling Price'
    
    def production_cost_formatted(self, obj):
        return format_html('Ksh {:,.2f}', obj.production_cost)
    
    production_cost_formatted.short_description = 'Production Cost'
    
    def profit_margin_badge(self, obj):
        if obj.profit_margin >= 40:
            color = 'success'
        elif obj.profit_margin >= 20:
            color = 'warning'
        else:
            color = 'danger'
        
        return format_html(
            '<span class="badge bg-{}">{:.1f}%</span>',
            color,
            obj.profit_margin
        )
    
    profit_margin_badge.short_description = 'Profit Margin'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge bg-success">Active</span>')
        return format_html('<span class="badge bg-danger">Inactive</span>')
    
    is_active_badge.short_description = 'Status'
    
    def created_at_short(self, obj):
        return obj.created_at.strftime('%d/%m/%Y')
    
    created_at_short.short_description = 'Created'
    
    def cost_breakdown(self, obj):
        material_cost = sum(formula.material_cost for formula in obj.formulas.all())
        labour_cost = sum(task.labour_cost for task in obj.labour_tasks.all())
        
        html = f"""
        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
            <strong>Material Cost:</strong> Ksh {material_cost:,.2f}<br>
            <strong>Labour Cost:</strong> Ksh {labour_cost:,.2f}<br>
            <strong>Total Cost:</strong> Ksh {obj.production_cost:,.2f}<br>
            <hr style="margin: 5px 0;">
            <strong>Profit per unit:</strong> Ksh {obj.selling_price - obj.production_cost:,.2f}
        </div>
        """
        return format_html(html)
    
    cost_breakdown.short_description = 'Cost Breakdown'
    
    def update_production_costs(self, request, queryset):
        """Update production costs for selected products"""
        updated = 0
        for product in queryset:
            product.update_production_cost()
            updated += 1
        
        self.message_user(
            request,
            f'Updated production costs for {updated} product(s)',
            messages.SUCCESS
        )
    
    update_production_costs.short_description = "Update production costs"
    
    def activate_products(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(
            request,
            f'Activated {queryset.count()} product(s)',
            messages.SUCCESS
        )
    
    activate_products.short_description = "Activate selected products"
    
    def deactivate_products(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(
            request,
            f'Deactivated {queryset.count()} product(s)',
            messages.WARNING
        )
    
    deactivate_products.short_description = "Deactivate selected products"
    
    def export_products_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'SKU', 'Name', 'Type', 'Selling Price', 'Production Cost',
            'Profit Margin %', 'Material Cost', 'Labour Cost', 'Status'
        ])
        
        for product in queryset:
            material_cost = sum(formula.material_cost for formula in product.formulas.all())
            labour_cost = sum(task.labour_cost for task in product.labour_tasks.all())
            
            writer.writerow([
                product.sku,
                product.name,
                product.get_product_type_display(),
                product.selling_price,
                product.production_cost,
                product.profit_margin,
                material_cost,
                labour_cost,
                'Active' if product.is_active else 'Inactive'
            ])
        
        self.message_user(request, f'Exported {queryset.count()} products to CSV')
        return response
    
    export_products_csv.short_description = "Export selected products to CSV"
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'formulas', 'formulas__raw_material', 'labour_tasks'
        )

@admin.register(ProductFormula)
class ProductFormulaAdmin(admin.ModelAdmin):
    list_display = [
        'product_link',
        'raw_material_link',
        'quantity_with_unit',
        'unit_price_formatted',
        'material_cost_formatted',
        'created_at_short'
    ]
    
    list_filter = [
        'product__product_type',
        'raw_material__category',
        'created_at'
    ]
    
    search_fields = [
        'product__name',
        'product__sku',
        'raw_material__name',
        'raw_material__code',
        'notes'
    ]
    
    readonly_fields = ['material_cost']
    
    autocomplete_fields = ['product', 'raw_material']
    
    def product_link(self, obj):
        url = reverse('admin:production_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    
    product_link.short_description = 'Product'
    
    def raw_material_link(self, obj):
        url = reverse('admin:inventory_rawmaterial_change', args=[obj.raw_material.id])
        return format_html('<a href="{}">{}</a>', url, obj.raw_material.name)
    
    raw_material_link.short_description = 'Raw Material'
    
    def quantity_with_unit(self, obj):
        return f"{obj.quantity_required} {obj.raw_material.unit_of_measure}"
    
    quantity_with_unit.short_description = 'Quantity Required'
    
    def unit_price_formatted(self, obj):
        return f"Ksh {obj.raw_material.unit_price:,.2f}"
    
    unit_price_formatted.short_description = 'Unit Price'
    
    def material_cost_formatted(self, obj):
        return format_html('<strong>Ksh {:,.2f}</strong>', obj.material_cost)
    
    material_cost_formatted.short_description = 'Material Cost'
    
    def created_at_short(self, obj):
        return obj.created_at.strftime('%d/%m/%Y')
    
    created_at_short.short_description = 'Created'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product', 'raw_material'
        )

@admin.register(LabourTask)
class LabourTaskAdmin(admin.ModelAdmin):
    list_display = [
        'task_name',
        'product_link',
        'task_type_badge',
        'labour_cost_formatted',
        'estimated_hours',
        'sequence',
        'created_at_short'
    ]
    
    list_filter = [
        'task_type',
        'product__product_type',
        'created_at'
    ]
    
    search_fields = [
        'task_name',
        'product__name',
        'product__sku',
        'description'
    ]
    
    autocomplete_fields = ['product']
    
    def product_link(self, obj):
        url = reverse('admin:production_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    
    product_link.short_description = 'Product'
    
    def task_type_badge(self, obj):
        colors = {
            'cutting': 'primary',
            'laying': 'success',
            'finishing': 'info',
            'skeleton': 'warning',
            'assembly': 'secondary',
            'upholstery': 'dark',
            'sanding': 'danger',
            'painting': 'light',
            'polishing': 'primary',
            'packaging': 'success'
        }
        color = colors.get(obj.task_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_task_type_display()
        )
    
    task_type_badge.short_description = 'Task Type'
    
    def labour_cost_formatted(self, obj):
        return format_html('<strong>Ksh {:,.2f}</strong>', obj.labour_cost)
    
    labour_cost_formatted.short_description = 'Labour Cost'
    
    def created_at_short(self, obj):
        return obj.created_at.strftime('%d/%m/%Y')
    
    created_at_short.short_description = 'Created'

@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number_link',
        'product_link',
        'quantity_badge',
        'status_badge',
        'priority_badge',
        'progress_bar',
        'cost_summary',
        'created_by_display',
        'expected_completion_date_formatted'
    ]
    
    list_filter = [
        'status',
        'priority',
        'start_date',
        'expected_completion_date',
        'created_by',
        'created_at'
    ]
    
    search_fields = [
        'order_number',
        'product__name',
        'product__sku',
        'notes',
        'created_by__username',
        'created_by__first_name',
        'created_by__last_name'
    ]
    
    readonly_fields = [
        'order_number',
        'total_labour_cost',
        'total_material_cost',
        'total_production_cost',
        'progress_percentage',
        'created_at',
        'updated_at',
        'material_requirements_display'
    ]
    
    fieldsets = [
        ('Order Information', {
            'fields': [
                'order_number',
                'product',
                'quantity',
                'status',
                'priority',
                'progress_percentage'
            ]
        }),
        ('Dates', {
            'fields': [
                'start_date',
                'expected_completion_date',
                'actual_completion_date'
            ]
        }),
        ('Cost Summary', {
            'fields': [
                'total_material_cost',
                'total_labour_cost',
                'total_production_cost'
            ],
            'classes': ['collapse']
        }),
        ('Material Requirements', {
            'fields': ['material_requirements_display'],
            'classes': ['collapse']
        }),
        ('Additional Information', {
            'fields': ['notes', 'created_by'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [ProductionTaskInline, ProductionLineInline]
    
    autocomplete_fields = ['product', 'created_by']
    
    actions = [
        'start_production_action',
        'complete_production_action',
        'check_material_availability',
        'generate_production_tasks',
        'export_production_orders_csv'
    ]
    
    def order_number_link(self, obj):
        url = reverse('admin:production_productionorder_change', args=[obj.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.order_number)
    
    order_number_link.short_description = 'Order Number'
    
    def product_link(self, obj):
        url = reverse('admin:production_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    
    product_link.short_description = 'Product'
    
    def quantity_badge(self, obj):
        return format_html(
            '<span class="badge bg-info" style="font-size: 1.1em;">×{}</span>',
            obj.quantity
        )
    
    quantity_badge.short_description = 'Quantity'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'secondary',
            'planned': 'info',
            'in_progress': 'warning',
            'completed': 'success',
            'cancelled': 'danger',
            'on_hold': 'dark'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'
    
    def priority_badge(self, obj):
        colors = {1: 'success', 2: 'warning', 3: 'danger'}
        color = colors.get(obj.priority, 'secondary')
        priority_text = dict(obj._meta.get_field('priority').choices).get(obj.priority, 'Unknown')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            priority_text
        )
    
    priority_badge.short_description = 'Priority'
    
    def progress_bar(self, obj):
        progress = obj.progress_percentage
        color = 'success' if progress >= 80 else 'warning' if progress >= 50 else 'danger'
        
        return format_html(
            '''
            <div style="width: 100px; background-color: #e9ecef; border-radius: 3px; height: 20px;">
                <div style="width: {}%; background-color: var(--bs-{}); height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">
                    {}%
                </div>
            </div>
            ''',
            progress, color, progress
        )
    
    progress_bar.short_description = 'Progress'
    
    def cost_summary(self, obj):
        return format_html(
            '<small>Material: Ksh {:,.0f}<br>Labour: Ksh {:,.0f}<br>Total: Ksh {:,.0f}</small>',
            obj.total_material_cost,
            obj.total_labour_cost,
            obj.total_production_cost
        )
    
    cost_summary.short_description = 'Costs'
    
    def created_by_display(self, obj):
        return f"{obj.created_by.get_full_name() or obj.created_by.username}"
    
    created_by_display.short_description = 'Created By'
    
    def expected_completion_date_formatted(self, obj):
        today = timezone.now().date()
        if obj.expected_completion_date < today:
            return format_html(
                '<span style="color: red;"><strong>{}</strong> (Overdue)</span>',
                obj.expected_completion_date.strftime('%d/%m/%Y')
            )
        elif obj.expected_completion_date == today:
            return format_html(
                '<span style="color: orange;"><strong>Today</strong></span>'
            )
        else:
            return obj.expected_completion_date.strftime('%d/%m/%Y')
    
    expected_completion_date_formatted.short_description = 'Expected Completion'
    
    def material_requirements_display(self, obj):
        requirements = obj.calculate_material_requirements()
        if not requirements:
            return "No material requirements defined for this product."
        
        html = '<div style="max-height: 300px; overflow-y: auto;">'
        html += '<table class="table table-sm">'
        html += '<thead><tr><th>Material</th><th>Required</th><th>Available</th><th>Status</th></tr></thead>'
        html += '<tbody>'
        
        for material, data in requirements.items():
            status_color = 'success' if data['sufficient'] else 'danger'
            status_text = '✓ Sufficient' if data['sufficient'] else '✗ Insufficient'
            
            html += f"""
            <tr>
                <td>{material.name}</td>
                <td>{data['quantity_required']} {data['unit']}</td>
                <td>{data['current_stock']} {data['unit']}</td>
                <td><span style="color: {status_color};">{status_text}</span></td>
            </tr>
            """
        
        html += '</tbody></table></div>'
        return format_html(html)
    
    material_requirements_display.short_description = 'Material Requirements'
    
    def start_production_action(self, request, queryset):
        """Start production for selected orders"""
        success_count = 0
        failed_count = 0
        
        for order in queryset:
            if order.start_production():
                success_count += 1
            else:
                failed_count += 1
        
        if success_count > 0:
            self.message_user(
                request,
                f'Started production for {success_count} order(s)',
                messages.SUCCESS
            )
        
        if failed_count > 0:
            self.message_user(
                request,
                f'Failed to start {failed_count} order(s). Check material availability.',
                messages.ERROR
            )
    
    start_production_action.short_description = "Start production"
    
    def complete_production_action(self, request, queryset):
        """Complete production for selected orders"""
        success_count = 0
        failed_count = 0
        
        for order in queryset:
            if order.complete_production():
                success_count += 1
            else:
                failed_count += 1
        
        if success_count > 0:
            self.message_user(
                request,
                f'Completed {success_count} production order(s)',
                messages.SUCCESS
            )
        
        if failed_count > 0:
            self.message_user(
                request,
                f'Failed to complete {failed_count} order(s). All tasks must be verified.',
                messages.ERROR
            )
    
    complete_production_action.short_description = "Complete production"
    
    def check_material_availability(self, request, queryset):
        """Check material availability for selected orders"""
        all_available = True
        unavailable_orders = []
        
        for order in queryset:
            available, insufficient = order.check_material_availability()
            if not available:
                all_available = False
                unavailable_orders.append({
                    'order': order,
                    'insufficient': insufficient
                })
        
        if all_available:
            self.message_user(
                request,
                'All selected orders have sufficient materials',
                messages.SUCCESS
            )
        else:
            message = "Some orders have insufficient materials:\n"
            for item in unavailable_orders:
                message += f"\n• {item['order'].order_number}:\n"
                for material in item['insufficient']:
                    message += f"  - {material['material'].name}: Need {material['required']}, Have {material['available']}\n"
            
            self.message_user(
                request,
                message,
                messages.WARNING
            )
    
    check_material_availability.short_description = "Check material availability"
    
    def generate_production_tasks(self, request, queryset):
        """Generate production tasks for selected orders"""
        for order in queryset:
            if not order.tasks.exists():
                order.generate_production_tasks()
        
        self.message_user(
            request,
            f'Generated tasks for {queryset.count()} order(s)',
            messages.SUCCESS
        )
    
    generate_production_tasks.short_description = "Generate production tasks"
    
    def export_production_orders_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="production_orders.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Order Number', 'Product', 'Quantity', 'Status', 'Priority',
            'Start Date', 'Expected Completion', 'Actual Completion',
            'Material Cost', 'Labour Cost', 'Total Cost', 'Progress %'
        ])
        
        for order in queryset:
            writer.writerow([
                order.order_number,
                order.product.name,
                order.quantity,
                order.get_status_display(),
                dict(order._meta.get_field('priority').choices).get(order.priority, ''),
                order.start_date.strftime('%Y-%m-%d'),
                order.expected_completion_date.strftime('%Y-%m-%d'),
                order.actual_completion_date.strftime('%Y-%m-%d') if order.actual_completion_date else '',
                order.total_material_cost,
                order.total_labour_cost,
                order.total_production_cost,
                order.progress_percentage
            ])
        
        self.message_user(request, f'Exported {queryset.count()} production orders to CSV')
        return response
    
    export_production_orders_csv.short_description = "Export production orders to CSV"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product', 'created_by'
        ).prefetch_related('tasks')

@admin.register(ProductionTask)
class ProductionTaskAdmin(admin.ModelAdmin):
    list_display = [
        'task_name',
        'production_order_link',
        'assigned_to_display',
        'status_badge',
        'quantity_badge',
        'labour_cost_formatted',
        'start_date_short',
        'completed_date_short'
    ]
    
    list_filter = [
        'status',
        'assigned_to',
        'labour_task__task_type',
        'created_at',
        'start_date',
        'completed_date'
    ]
    
    search_fields = [
        'production_order__order_number',
        'labour_task__task_name',
        'assigned_to__username',
        'assigned_to__first_name',
        'assigned_to__last_name',
        'notes'
    ]
    
    readonly_fields = [
        'labour_cost',
        'created_at',
        'updated_at',
        'task_details'
    ]
    
    fieldsets = [
        ('Task Information', {
            'fields': [
                'production_order',
                'labour_task',
                'quantity',
                'task_details'
            ]
        }),
        ('Assignment & Status', {
            'fields': [
                'assigned_to',
                'status',
                'sequence'
            ]
        }),
        ('Dates', {
            'fields': [
                'start_date',
                'completed_date',
                'verified_by',
                'verified_at'
            ],
            'classes': ['collapse']
        }),
        ('Cost Information', {
            'fields': ['labour_cost'],
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
    
    autocomplete_fields = ['production_order', 'labour_task', 'assigned_to', 'verified_by']
    
    actions = [
        'assign_to_selected_worker',
        'mark_as_completed',
        'mark_as_verified',
        'export_tasks_csv'
    ]
    
    def task_name(self, obj):
        return obj.labour_task.task_name
    
    task_name.short_description = 'Task Name'
    
    def production_order_link(self, obj):
        url = reverse('admin:production_productionorder_change', args=[obj.production_order.id])
        return format_html('<a href="{}">{}</a>', url, obj.production_order.order_number)
    
    production_order_link.short_description = 'Production Order'
    
    def assigned_to_display(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.get_full_name() or obj.assigned_to.username}"
        return format_html('<span class="text-muted">Unassigned</span>')
    
    assigned_to_display.short_description = 'Assigned To'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'secondary',
            'assigned': 'warning',
            'in_progress': 'info',
            'completed': 'success',
            'verified': 'primary',
            'cancelled': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'
    
    def quantity_badge(self, obj):
        return format_html('<span class="badge bg-info">×{}</span>', obj.quantity)
    
    quantity_badge.short_description = 'Quantity'
    
    def labour_cost_formatted(self, obj):
        return format_html('<strong>Ksh {:,.2f}</strong>', obj.labour_cost)
    
    labour_cost_formatted.short_description = 'Labour Cost'
    
    def start_date_short(self, obj):
        if obj.start_date:
            return obj.start_date.strftime('%d/%m/%Y')
        return '-'
    
    start_date_short.short_description = 'Started'
    
    def completed_date_short(self, obj):
        if obj.completed_date:
            return obj.completed_date.strftime('%d/%m/%Y')
        return '-'
    
    completed_date_short.short_description = 'Completed'
    
    def task_details(self, obj):
        html = f"""
        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
            <strong>Task Type:</strong> {obj.labour_task.get_task_type_display()}<br>
            <strong>Estimated Hours:</strong> {obj.labour_task.estimated_hours} hours<br>
            <strong>Description:</strong> {obj.labour_task.description}<br>
            <strong>Per Unit Cost:</strong> Ksh {obj.labour_task.labour_cost:,.2f}
        </div>
        """
        return format_html(html)
    
    task_details.short_description = 'Task Details'
    
    def assign_to_selected_worker(self, request, queryset):
        """Assign tasks to selected worker"""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        selected_ids = queryset.values_list('id', flat=True)
        url = reverse('admin:assign_tasks_bulk') + f'?ids={",".join(str(id) for id in selected_ids)}'
        return HttpResponseRedirect(url)
    
    assign_to_selected_worker.short_description = "Assign to worker..."
    
    def mark_as_completed(self, request, queryset):
        """Mark selected tasks as completed"""
        for task in queryset:
            if task.status == 'in_progress' and task.assigned_to:
                task.status = 'completed'
                task.completed_date = timezone.now()
                task.save()
        
        self.message_user(
            request,
            f'Marked {queryset.count()} task(s) as completed',
            messages.SUCCESS
        )
    
    mark_as_completed.short_description = "Mark as completed"
    
    def mark_as_verified(self, request, queryset):
        """Mark selected tasks as verified"""
        for task in queryset:
            if task.status == 'completed':
                task.status = 'verified'
                task.verified_by = request.user
                task.verified_at = timezone.now()
                task.save()
        
        self.message_user(
            request,
            f'Verified {queryset.count()} task(s)',
            messages.SUCCESS
        )
    
    mark_as_verified.short_description = "Mark as verified"
    
    def export_tasks_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="production_tasks.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Production Order', 'Task Name', 'Assigned To', 'Status',
            'Quantity', 'Labour Cost', 'Start Date', 'Completed Date',
            'Verified By', 'Verified At'
        ])
        
        for task in queryset:
            writer.writerow([
                task.production_order.order_number,
                task.labour_task.task_name,
                task.assigned_to.get_full_name() if task.assigned_to else '',
                task.get_status_display(),
                task.quantity,
                task.labour_cost,
                task.start_date.strftime('%Y-%m-%d %H:%M') if task.start_date else '',
                task.completed_date.strftime('%Y-%m-%d %H:%M') if task.completed_date else '',
                task.verified_by.get_full_name() if task.verified_by else '',
                task.verified_at.strftime('%Y-%m-%d %H:%M') if task.verified_at else ''
            ])
        
        self.message_user(request, f'Exported {queryset.count()} tasks to CSV')
        return response
    
    export_tasks_csv.short_description = "Export tasks to CSV"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'production_order',
            'labour_task',
            'assigned_to',
            'verified_by'
        )

@admin.register(WorkStation)
class WorkStationAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'is_active_badge', 'created_at_short']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'location', 'description']
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge bg-success">Active</span>')
        return format_html('<span class="badge bg-danger">Inactive</span>')
    
    is_active_badge.short_description = 'Status'
    
    def created_at_short(self, obj):
        return obj.created_at.strftime('%d/%m/%Y')
    
    created_at_short.short_description = 'Created'

@admin.register(ProductionLine)
class ProductionLineAdmin(admin.ModelAdmin):
    list_display = [
        'workstation_link',
        'production_order_link',
        'task_link',
        'status_badge',
        'start_time_short',
        'end_time_short'
    ]
    
    list_filter = ['status', 'workstation', 'start_time', 'end_time']
    
    search_fields = [
        'workstation__name',
        'production_order__order_number',
        'task__labour_task__task_name',
        'notes'
    ]
    
    readonly_fields = ['workstation', 'production_order', 'task', 'status']
    
    def workstation_link(self, obj):
        url = reverse('admin:production_workstation_change', args=[obj.workstation.id])
        return format_html('<a href="{}">{}</a>', url, obj.workstation.name)
    
    workstation_link.short_description = 'Workstation'
    
    def production_order_link(self, obj):
        url = reverse('admin:production_productionorder_change', args=[obj.production_order.id])
        return format_html('<a href="{}">{}</a>', url, obj.production_order.order_number)
    
    production_order_link.short_description = 'Production Order'
    
    def task_link(self, obj):
        if obj.task:
            return obj.task.labour_task.task_name
        return '-'
    
    task_link.short_description = 'Task'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'secondary',
            'assigned': 'warning',
            'in_progress': 'info',
            'completed': 'success',
            'verified': 'primary',
            'cancelled': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'
    
    def start_time_short(self, obj):
        if obj.start_time:
            return obj.start_time.strftime('%d/%m/%Y %H:%M')
        return '-'
    
    start_time_short.short_description = 'Start Time'
    
    def end_time_short(self, obj):
        if obj.end_time:
            return obj.end_time.strftime('%d/%m/%Y %H:%M')
        return '-'
    
    end_time_short.short_description = 'End Time'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'workstation', 'production_order', 'task', 'task__labour_task'
        )

# Custom admin site header for production module
admin.site.site_header = "MbaoSmart Production Administration"
admin.site.site_title = "MbaoSmart Production Admin"
admin.site.index_title = "Production Module Administration"