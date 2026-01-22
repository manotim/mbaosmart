from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Avg, Q, F
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO

from procurement.models import PurchaseOrder, Supplier
from inventory.models import RawMaterial, InventoryTransaction
from production.models import Product, ProductionOrder, ProductionTask
from sales.models import Sale, Shop, StockTransfer
from hr.models import Employee, WorkLog
from accounts.models import User

@login_required
def report_dashboard(request):
    """Main reporting dashboard"""
    if not request.user.has_perm('reporting.view_report'):
        return render(request, '403.html')
    
    # Get date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    year_ago = today - timedelta(days=365)
    
    # Summary statistics for dashboard
    summary = {
        'total_sales': Sale.objects.filter(
            sale_date__gte=month_ago
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
        
        'total_purchases': PurchaseOrder.objects.filter(
            status='completed',
            created_at__gte=month_ago
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
        
        'production_completed': ProductionOrder.objects.filter(
            status='completed',
            completion_date__gte=month_ago
        ).count(),
        
        'total_employees': User.objects.filter(is_active=True).count(),
        
        'low_stock_items': RawMaterial.objects.filter(
            current_quantity__lt=F('minimum_quantity')
        ).count(),
        
        'pending_payments': WorkLog.objects.filter(is_paid=False).count(),
    }
    
    # Recent reports
    recent_reports = [
        {'name': 'Monthly Sales Report', 'date': today, 'type': 'sales'},
        {'name': 'Inventory Stock Report', 'date': today - timedelta(days=1), 'type': 'inventory'},
        {'name': 'Payroll Summary', 'date': today - timedelta(days=2), 'type': 'hr'},
        {'name': 'Production Efficiency', 'date': today - timedelta(days=3), 'type': 'production'},
    ]
    
    context = {
        'summary': summary,
        'recent_reports': recent_reports,
        'date_ranges': {
            'today': today,
            'week': week_ago,
            'month': month_ago,
            'year': year_ago,
        }
    }
    
    return render(request, 'reporting/report_dashboard.html', context)

@login_required
def sales_report(request):
    """Generate sales reports"""
    if not request.user.has_perm('sales.view_sale'):
        return render(request, '403.html')
    
    # Get filters from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    shop_id = request.GET.get('shop')
    
    # Build query
    sales = Sale.objects.all()
    
    if start_date:
        sales = sales.filter(sale_date__gte=start_date)
    if end_date:
        sales = sales.filter(sale_date__lte=end_date)
    if shop_id:
        sales = sales.filter(shop_id=shop_id)
    
    # Summary statistics
    total_sales = sales.count()
    total_amount = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    avg_sale = sales.aggregate(avg=Avg('total_amount'))['avg'] or 0
    
    # Group by shop
    shop_summary = sales.values('shop__name').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    ).order_by('-total')
    
    # Group by product
    product_summary = []
    for sale in sales:
        for item in sale.saleitem_set.all():
            product_summary.append({
                'product': item.product.name,
                'quantity': item.quantity,
                'amount': item.total_price
            })
    
    # Format for context
    context = {
        'sales': sales.order_by('-sale_date'),
        'total_sales': total_sales,
        'total_amount': total_amount,
        'avg_sale': avg_sale,
        'shop_summary': shop_summary,
        'product_summary': product_summary,
        'shops': Shop.objects.all(),
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'shop': shop_id,
        }
    }
    
    return render(request, 'reporting/sales_report.html', context)

@login_required
def inventory_report(request):
    """Generate inventory reports"""
    if not request.user.has_perm('inventory.view_rawmaterial'):
        return render(request, '403.html')
    
    # Get filters
    low_stock = request.GET.get('low_stock', False)
    category = request.GET.get('category')
    
    # Build query
    materials = RawMaterial.objects.all()
    
    if low_stock:
        materials = materials.filter(current_quantity__lt=F('minimum_quantity'))
    if category:
        materials = materials.filter(category=category)
    
    # Summary statistics
    total_items = materials.count()
    total_value = sum(m.current_quantity * m.unit_price for m in materials)
    
    # Stock movement (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    movements = InventoryTransaction.objects.filter(
        transaction_date__gte=thirty_days_ago
    ).values('material__name').annotate(
        received=Sum('quantity_in'),
        issued=Sum('quantity_out')
    )
    
    # Low stock items
    low_stock_items = RawMaterial.objects.filter(
        current_quantity__lt=F('minimum_quantity')
    ).order_by('current_quantity')
    
    context = {
        'materials': materials.order_by('name'),
        'total_items': total_items,
        'total_value': total_value,
        'movements': movements,
        'low_stock_items': low_stock_items,
        'categories': RawMaterial.objects.values_list('category', flat=True).distinct(),
    }
    
    return render(request, 'reporting/inventory_report.html', context)

@login_required
def production_report(request):
    """Generate production reports"""
    if not request.user.has_perm('production.view_productionorder'):
        return render(request, '403.html')
    
    # Get filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    
    # Build query
    orders = ProductionOrder.objects.all()
    
    if start_date:
        orders = orders.filter(created_at__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__lte=end_date)
    if status:
        orders = orders.filter(status=status)
    
    # Summary statistics
    total_orders = orders.count()
    completed_orders = orders.filter(status='completed').count()
    in_progress = orders.filter(status='in_progress').count()
    
    # Efficiency metrics
    total_products = 0
    total_materials_cost = 0
    total_labor_cost = 0
    
    for order in orders:
        total_products += order.quantity
        total_materials_cost += order.total_material_cost or 0
        total_labor_cost += order.total_labor_cost or 0
    
    # Task completion rates
    tasks = ProductionTask.objects.filter(
        production_order__in=orders
    )
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status='completed').count()
    task_completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    context = {
        'orders': orders.order_by('-created_at'),
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'in_progress': in_progress,
        'total_products': total_products,
        'total_materials_cost': total_materials_cost,
        'total_labor_cost': total_labor_cost,
        'task_completion_rate': task_completion_rate,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'status': status,
        }
    }
    
    return render(request, 'reporting/production_report.html', context)

@login_required
def payroll_report(request):
    """Generate payroll reports"""
    if not request.user.has_perm('hr.view_worklog'):
        return render(request, '403.html')
    
    # Get filters
    month = request.GET.get('month', timezone.now().month)
    year = request.GET.get('year', timezone.now().year)
    employee_id = request.GET.get('employee')
    
    # Build query
    work_logs = WorkLog.objects.filter(
        date__month=month,
        date__year=year
    )
    
    if employee_id:
        work_logs = work_logs.filter(employee_id=employee_id)
    
    # Summary statistics
    total_employees = work_logs.values('employee').distinct().count()
    total_hours = work_logs.aggregate(total=Sum('hours_worked'))['total'] or 0
    total_amount = work_logs.aggregate(total=Sum('amount'))['total'] or 0
    paid_amount = work_logs.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or 0
    unpaid_amount = total_amount - paid_amount
    
    # Employee breakdown
    employee_summary = work_logs.values(
        'employee__username',
        'employee__first_name',
        'employee__last_name'
    ).annotate(
        hours=Sum('hours_worked'),
        amount=Sum('amount'),
        paid=Sum('amount', filter=Q(is_paid=True))
    ).order_by('-amount')
    
    # Monthly trends (last 6 months)
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_trends = WorkLog.objects.filter(
        date__gte=six_months_ago
    ).extra(
        {'month': "EXTRACT(month FROM date)", 'year': "EXTRACT(year FROM date)"}
    ).values('month', 'year').annotate(
        total_amount=Sum('amount'),
        total_hours=Sum('hours_worked')
    ).order_by('year', 'month')
    
    context = {
        'work_logs': work_logs.order_by('-date'),
        'total_employees': total_employees,
        'total_hours': total_hours,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'unpaid_amount': unpaid_amount,
        'employee_summary': employee_summary,
        'monthly_trends': monthly_trends,
        'employees': User.objects.filter(role='fundi'),
        'filters': {
            'month': month,
            'year': year,
            'employee': employee_id,
        }
    }
    
    return render(request, 'reporting/payroll_report.html', context)

@login_required
def procurement_report(request):
    """Generate procurement reports"""
    if not request.user.has_perm('procurement.view_purchaseorder'):
        return render(request, '403.html')
    
    # Get filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    supplier_id = request.GET.get('supplier')
    status = request.GET.get('status')
    
    # Build query
    orders = PurchaseOrder.objects.all()
    
    if start_date:
        orders = orders.filter(created_at__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__lte=end_date)
    if supplier_id:
        orders = orders.filter(supplier_id=supplier_id)
    if status:
        orders = orders.filter(status=status)
    
    # Summary statistics
    total_orders = orders.count()
    total_amount = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    pending_orders = orders.filter(status='pending').count()
    approved_orders = orders.filter(status='approved').count()
    
    # Supplier breakdown
    supplier_summary = orders.values(
        'supplier__name',
        'supplier__contact_person'
    ).annotate(
        count=Count('id'),
        total=Sum('total_amount'),
        avg=Avg('total_amount')
    ).order_by('-total')
    
    # Monthly spending
    monthly_spending = orders.extra(
        {'month': "EXTRACT(month FROM created_at)", 'year': "EXTRACT(year FROM created_at)"}
    ).values('month', 'year').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('year', 'month')
    
    context = {
        'orders': orders.order_by('-created_at'),
        'total_orders': total_orders,
        'total_amount': total_amount,
        'pending_orders': pending_orders,
        'approved_orders': approved_orders,
        'supplier_summary': supplier_summary,
        'monthly_spending': monthly_spending,
        'suppliers': Supplier.objects.all(),
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'supplier': supplier_id,
            'status': status,
        }
    }
    
    return render(request, 'reporting/procurement_report.html', context)

@login_required
def export_report_csv(request, report_type):
    """Export report as CSV"""
    if not request.user.has_perm('reporting.export_report'):
        return HttpResponse('Permission Denied', status=403)
    
    # Create response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
    
    writer = csv.writer(response)
    
    if report_type == 'sales':
        writer.writerow(['Date', 'Shop', 'Product', 'Quantity', 'Unit Price', 'Total', 'Payment Method'])
        sales = Sale.objects.all().order_by('-sale_date')
        for sale in sales:
            for item in sale.saleitem_set.all():
                writer.writerow([
                    sale.sale_date,
                    sale.shop.name,
                    item.product.name,
                    item.quantity,
                    item.unit_price,
                    item.total_price,
                    sale.payment_method
                ])
    
    elif report_type == 'inventory':
        writer.writerow(['Material', 'Category', 'Current Quantity', 'Unit', 'Unit Price', 'Total Value', 'Min Quantity'])
        materials = RawMaterial.objects.all().order_by('name')
        for material in materials:
            writer.writerow([
                material.name,
                material.category,
                material.current_quantity,
                material.unit_of_measure,
                material.unit_price,
                material.current_quantity * material.unit_price,
                material.minimum_quantity
            ])
    
    elif report_type == 'payroll':
        writer.writerow(['Date', 'Employee', 'Hours', 'Rate', 'Amount', 'Task', 'Paid'])
        work_logs = WorkLog.objects.all().order_by('-date')
        for log in work_logs:
            writer.writerow([
                log.date,
                f"{log.employee.first_name} {log.employee.last_name}",
                log.hours_worked,
                log.hourly_rate,
                log.amount,
                log.task_description,
                'Yes' if log.is_paid else 'No'
            ])
    
    return response

@login_required
def export_report_pdf(request, report_type):
    """Export report as PDF"""
    if not request.user.has_perm('reporting.export_report'):
        return HttpResponse('Permission Denied', status=403)
    
    # Create response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Add title
    title = Paragraph(f"MbaoSmart - {report_type.title()} Report", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Add date
    date_text = Paragraph(f"Generated on: {timezone.now().strftime('%d %B %Y %H:%M')}", styles['Normal'])
    elements.append(date_text)
    elements.append(Spacer(1, 24))
    
    # Add data based on report type
    if report_type == 'sales':
        data = [['Date', 'Shop', 'Amount', 'Items', 'Payment']]
        sales = Sale.objects.all().order_by('-sale_date')[:50]
        for sale in sales:
            data.append([
                sale.sale_date.strftime('%d/%m/%Y'),
                sale.shop.name,
                f"Ksh {sale.total_amount:,.2f}",
                sale.saleitem_set.count(),
                sale.payment_method
            ])
    
    elif report_type == 'inventory':
        data = [['Material', 'Category', 'Quantity', 'Unit Price', 'Total Value']]
        materials = RawMaterial.objects.all().order_by('category', 'name')[:50]
        for material in materials:
            total_value = material.current_quantity * material.unit_price
            data.append([
                material.name,
                material.category,
                f"{material.current_quantity} {material.unit_of_measure}",
                f"Ksh {material.unit_price:,.2f}",
                f"Ksh {total_value:,.2f}"
            ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF value and write to response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response

@login_required
def custom_report(request):
    """Custom report builder"""
    if not request.user.has_perm('reporting.create_custom_report'):
        return render(request, '403.html')
    
    if request.method == 'POST':
        # Process custom report request
        report_type = request.POST.get('report_type')
        filters = request.POST.get('filters', {})
        
        # Generate report based on parameters
        # This is a simplified example
        return render(request, 'reporting/custom_report_result.html', {
            'report_type': report_type,
            'filters': filters
        })
    
    return render(request, 'reporting/custom_report.html')