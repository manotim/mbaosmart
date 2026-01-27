from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import datetime, timedelta
import csv

from .models import *
from .forms import *
from production.models import Product

# Shop Views
@login_required
def shop_list(request):
    shops = Shop.objects.filter(is_active=True)
    return render(request, 'sales/shop_list.html', {'shops': shops})

@login_required
def shop_detail(request, pk):
    shop = get_object_or_404(Shop, pk=pk)
    stock_items = shop.stock_items.all().select_related('product')
    sales = shop.sales.all().order_by('-sale_date')[:10]
    
    # Statistics
    total_stock_value = shop.total_stock_value
    low_stock_items = stock_items.filter(quantity__lte=F('min_stock_level')).count()
    
    context = {
        'shop': shop,
        'stock_items': stock_items,
        'sales': sales,
        'total_stock_value': total_stock_value,
        'low_stock_items': low_stock_items,
    }
    return render(request, 'sales/shop_detail.html', context)

@permission_required('sales.add_shop')
def shop_create(request):
    if request.method == 'POST':
        form = ShopForm(request.POST)
        if form.is_valid():
            shop = form.save()
            messages.success(request, f'Shop "{shop.name}" created successfully!')
            return redirect('sales:shop_detail', pk=shop.pk)
    else:
        form = ShopForm()
    return render(request, 'sales/shop_form.html', {'form': form, 'title': 'Create Shop'})

@permission_required('sales.change_shop')
def shop_update(request, pk):
    shop = get_object_or_404(Shop, pk=pk)
    if request.method == 'POST':
        form = ShopForm(request.POST, instance=shop)
        if form.is_valid():
            shop = form.save()
            messages.success(request, f'Shop "{shop.name}" updated successfully!')
            return redirect('sales:shop_detail', pk=shop.pk)
    else:
        form = ShopForm(instance=shop)
    return render(request, 'sales/shop_form.html', {'form': form, 'title': 'Update Shop'})

# Stock Transfer Views
@login_required
def stock_transfer_list(request):
    transfers = StockTransfer.objects.all().order_by('-transfer_date')
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        transfers = transfers.filter(status=status)
    
    return render(request, 'sales/stock_transfer_list.html', {'transfers': transfers})

@login_required
def stock_transfer_detail(request, pk):
    transfer = get_object_or_404(StockTransfer, pk=pk)
    items = transfer.items.all().select_related('product')
    
    context = {
        'transfer': transfer,
        'items': items,
        'can_edit': request.user.has_perm('sales.change_stocktransfer'),
    }
    return render(request, 'sales/stock_transfer_detail.html', context)

@permission_required('sales.add_stocktransfer')
def stock_transfer_create(request):
    if request.method == 'POST':
        form = StockTransferForm(request.POST, user=request.user)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.initiated_by = request.user
            transfer.save()
            
            messages.success(request, f'Stock transfer created successfully! Transfer Number: {transfer.transfer_number}')
            return redirect('sales:stock_transfer_items', pk=transfer.pk)
    else:
        form = StockTransferForm(user=request.user)
    
    return render(request, 'sales/stock_transfer_form.html', {'form': form, 'title': 'Create Stock Transfer'})

@permission_required('sales.change_stocktransfer')
def stock_transfer_update(request, pk):
    transfer = get_object_or_404(StockTransfer, pk=pk)
    
    if transfer.status not in ['pending', 'in_transit']:
        messages.error(request, 'Cannot edit transfer that is already delivered or received.')
        return redirect('sales:stock_transfer_detail', pk=pk)
    
    if request.method == 'POST':
        form = StockTransferForm(request.POST, instance=transfer, user=request.user)
        if form.is_valid():
            transfer = form.save()
            messages.success(request, f'Stock transfer updated successfully!')
            return redirect('sales:stock_transfer_detail', pk=pk)
    else:
        form = StockTransferForm(instance=transfer, user=request.user)
    
    return render(request, 'sales/stock_transfer_form.html', {'form': form, 'title': 'Update Stock Transfer'})

@login_required
def stock_transfer_items(request, pk):
    transfer = get_object_or_404(StockTransfer, pk=pk)
    items = transfer.items.all()
    
    if request.method == 'POST':
        form = StockTransferItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.stock_transfer = transfer
            item.save()
            messages.success(request, f'Item added to transfer.')
            return redirect('sales:stock_transfer_items', pk=pk)
    else:
        form = StockTransferItemForm()
    
    context = {
        'transfer': transfer,
        'items': items,
        'form': form,
    }
    return render(request, 'sales/stock_transfer_items.html', context)

@permission_required('sales.delete_stocktransferitem')
def stock_transfer_item_delete(request, pk, item_pk):
    item = get_object_or_404(StockTransferItem, pk=item_pk, stock_transfer__pk=pk)
    transfer = item.stock_transfer
    
    if transfer.status not in ['pending', 'in_transit']:
        messages.error(request, 'Cannot delete items from transfer that is already delivered.')
        return redirect('sales:stock_transfer_items', pk=pk)
    
    item.delete()
    messages.success(request, 'Item removed from transfer.')
    return redirect('sales:stock_transfer_items', pk=pk)

@login_required
def stock_transfer_deliver(request, pk):
    transfer = get_object_or_404(StockTransfer, pk=pk)
    
    if request.user.has_perm('sales.change_stocktransfer') and transfer.mark_delivered():
        messages.success(request, f'Stock transfer marked as delivered!')
    else:
        messages.error(request, 'Cannot mark as delivered. Check permissions or transfer status.')
    
    return redirect('sales:stock_transfer_detail', pk=pk)

@login_required
def stock_transfer_receive(request, pk):
    transfer = get_object_or_404(StockTransfer, pk=pk)
    
    if transfer.to_shop.manager == request.user or request.user.has_perm('sales.change_stocktransfer'):
        if transfer.mark_received(request.user):
            messages.success(request, f'Stock transfer received successfully!')
        else:
            messages.error(request, 'Cannot receive transfer. Check transfer status.')
    else:
        messages.error(request, 'You are not authorized to receive this transfer.')
    
    return redirect('sales:stock_transfer_detail', pk=pk)

@login_required
def update_received_quantity(request, pk, item_pk):
    """AJAX view to update received quantity"""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        item = get_object_or_404(StockTransferItem, pk=item_pk, stock_transfer__pk=pk)
        transfer = item.stock_transfer
        
        if transfer.status != 'delivered':
            return JsonResponse({'error': 'Transfer is not delivered yet'}, status=400)
        
        try:
            received_qty = int(request.POST.get('received_quantity'))
            if 0 <= received_qty <= item.quantity:
                item.received_quantity = received_qty
                item.save()
                return JsonResponse({
                    'success': True,
                    'received_quantity': item.received_quantity,
                    'pending_quantity': item.pending_quantity,
                    'is_fully_received': item.is_fully_received
                })
            else:
                return JsonResponse({'error': f'Quantity must be between 0 and {item.quantity}'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'Invalid quantity'}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

# Sale Views
@login_required
def sale_list(request):
    sales = Sale.objects.all().order_by('-sale_date')
    
    # Filter by shop if user is shop staff
    if request.user.role in ['sales_person', 'shop_manager']:
        managed_shops = Shop.objects.filter(manager=request.user)
        sales = sales.filter(shop__in=managed_shops)
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        sales = sales.filter(status=status)
    
    # Filter by date range if provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            sales = sales.filter(sale_date__date__range=[start, end])
        except ValueError:
            pass
    
    return render(request, 'sales/sale_list.html', {'sales': sales})

@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.items.all().select_related('product')
    
    # Check if user can view this sale
    if request.user.role in ['sales_person', 'shop_manager']:
        if sale.shop.manager != request.user and sale.sold_by != request.user:
            messages.error(request, 'You are not authorized to view this sale.')
            return redirect('sales:sale_list')
    
    context = {
        'sale': sale,
        'items': items,
        'can_edit': request.user.has_perm('sales.change_sale'),
    }
    return render(request, 'sales/sale_detail.html', context)

@permission_required('sales.add_sale')
def sale_create(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.sold_by = request.user
            sale.save()
            
            messages.success(request, f'Sale created successfully! Invoice: {sale.invoice_number}')
            return redirect('sales:sale_items', pk=sale.pk)
    else:
        form = SaleForm()
        # Set default shop for shop staff
        if request.user.role in ['sales_person', 'shop_manager']:
            managed_shop = Shop.objects.filter(manager=request.user).first()
            if managed_shop:
                form.fields['shop'].initial = managed_shop
    
    return render(request, 'sales/sale_form.html', {'form': form, 'title': 'Create Sale'})

@login_required
def sale_items(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.items.all()
    
    # Check if user can edit this sale
    if not (request.user.has_perm('sales.change_sale') or 
            sale.sold_by == request.user or 
            sale.shop.manager == request.user):
        messages.error(request, 'You are not authorized to edit this sale.')
        return redirect('sales:sale_detail', pk=pk)
    
    if request.method == 'POST':
        form = SaleItemForm(request.POST, shop=sale.shop)
        if form.is_valid():
            item = form.save(commit=False)
            item.sale = sale
            
            # Check stock availability
            shop_stock = ShopStock.objects.filter(shop=sale.shop, product=item.product).first()
            if shop_stock and shop_stock.quantity < item.quantity:
                messages.error(request, f'Insufficient stock for {item.product.name}. Available: {shop_stock.quantity}')
            else:
                item.save()
                messages.success(request, f'Item added to sale.')
            return redirect('sales:sale_items', pk=pk)
    else:
        form = SaleItemForm(shop=sale.shop)
    
    context = {
        'sale': sale,
        'items': items,
        'form': form,
    }
    return render(request, 'sales/sale_items.html', context)

@login_required
def sale_item_delete(request, pk, item_pk):
    item = get_object_or_404(SaleItem, pk=item_pk, sale__pk=pk)
    sale = item.sale
    
    # Check if user can edit this sale
    if not (request.user.has_perm('sales.change_sale') or 
            sale.sold_by == request.user or 
            sale.shop.manager == request.user):
        messages.error(request, 'You are not authorized to edit this sale.')
        return redirect('sales:sale_detail', pk=pk)
    
    if sale.status != 'pending':
        messages.error(request, 'Cannot delete items from completed sale.')
        return redirect('sales:sale_items', pk=pk)
    
    item.delete()
    messages.success(request, 'Item removed from sale.')
    return redirect('sales:sale_items', pk=pk)

@login_required
def sale_complete(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    
    # Check if user can complete this sale
    if not (request.user.has_perm('sales.change_sale') or 
            sale.sold_by == request.user or 
            sale.shop.manager == request.user):
        messages.error(request, 'You are not authorized to complete this sale.')
        return redirect('sales:sale_detail', pk=pk)
    
    if sale.status == 'pending':
        success, message = sale.complete_sale()
        if success:
            messages.success(request, f'Sale completed successfully! {message}')
        else:
            messages.error(request, f'Cannot complete sale: {message}')
    else:
        messages.error(request, 'Sale is already completed or cancelled.')
    
    return redirect('sales:sale_detail', pk=pk)

@login_required
def sale_add_payment(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    
    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount', 0))
            if amount > 0:
                sale.amount_paid += amount
                sale.save()
                
                # Update status if fully paid
                if sale.is_fully_paid and sale.status == 'completed':
                    sale.status = 'completed'
                    sale.save()
                
                messages.success(request, f'Payment of Ksh {amount:,.2f} recorded successfully!')
            else:
                messages.error(request, 'Invalid amount.')
        except ValueError:
            messages.error(request, 'Invalid amount format.')
    
    return redirect('sales:sale_detail', pk=pk)

# Customer Views
@login_required
def customer_list(request):
    customers = Customer.objects.filter(is_active=True)
    
    # Search
    search = request.GET.get('search')
    if search:
        customers = customers.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search) |
            Q(id_number__icontains=search)
        )
    
    return render(request, 'sales/customer_list.html', {'customers': customers})

@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    sales = customer.sales.all().order_by('-sale_date')[:20]
    
    context = {
        'customer': customer,
        'sales': sales,
        'can_edit': request.user.has_perm('sales.change_customer'),
    }
    return render(request, 'sales/customer_detail.html', context)

@permission_required('sales.add_customer')
def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Customer "{customer.name}" created successfully!')
            return redirect('sales:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()
    return render(request, 'sales/customer_form.html', {'form': form, 'title': 'Create Customer'})

@permission_required('sales.change_customer')
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Customer "{customer.name}" updated successfully!')
            return redirect('sales:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'sales/customer_form.html', {'form': form, 'title': 'Update Customer'})

# Stock Management Views
@login_required
def shop_stock_list(request, shop_pk=None):
    if shop_pk:
        shop = get_object_or_404(Shop, pk=shop_pk)
        stock_items = shop.stock_items.all().select_related('product')
    else:
        shop = None
        stock_items = ShopStock.objects.all().select_related('shop', 'product')
    
    # Filter by shop if user is shop staff
    if not shop and request.user.role in ['sales_person', 'shop_manager']:
        managed_shops = Shop.objects.filter(manager=request.user)
        stock_items = stock_items.filter(shop__in=managed_shops)
    
    # Filter by stock status
    status = request.GET.get('status')
    if status == 'low':
        stock_items = stock_items.filter(quantity__lte=F('min_stock_level'))
    elif status == 'out':
        stock_items = stock_items.filter(quantity=0)
    
    return render(request, 'sales/shop_stock_list.html', {
        'shop': shop,
        'stock_items': stock_items,
    })

@login_required
def stock_take(request):
    if request.method == 'POST':
        form = StockTakeForm(request.POST)
        if form.is_valid():
            shop = form.cleaned_data['shop']
            product = form.cleaned_data['product']
            physical_count = form.cleaned_data['physical_count']
            notes = form.cleaned_data['notes']
            
            # Get current stock
            shop_stock, created = ShopStock.objects.get_or_create(
                shop=shop,
                product=product,
                defaults={'quantity': 0}
            )
            
            difference = physical_count - shop_stock.quantity
            
            if difference != 0:
                # Create adjustment
                if difference > 0:
                    adj_type = 'add'
                else:
                    adj_type = 'remove'
                    difference = abs(difference)
                
                StockAdjustmentShop.objects.create(
                    shop=shop,
                    product=product,
                    adjustment_type=adj_type,
                    quantity=difference,
                    reason=f'Physical stock count. {notes}',
                    adjusted_by=request.user,
                    previous_quantity=shop_stock.quantity,
                    new_quantity=physical_count
                )
                
                messages.success(request, f'Stock adjusted by {difference} units for {product.name}.')
            else:
                messages.info(request, f'Stock count matches system records for {product.name}.')
            
            return redirect('sales:stock_take')
    else:
        form = StockTakeForm()
    
    return render(request, 'sales/stock_take.html', {'form': form})

# Reporting Views
@login_required
def sales_report(request):
    """Sales report with filters"""
    shops = Shop.objects.filter(is_active=True)
    
    # Default to current month
    today = timezone.now().date()
    start_date = request.GET.get('start_date', today.replace(day=1).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    shop_id = request.GET.get('shop')
    
    # Filter sales
    sales = Sale.objects.filter(
        sale_date__date__range=[start_date, end_date],
        status='completed'
    )
    
    if shop_id:
        sales = sales.filter(shop_id=shop_id)
        selected_shop = Shop.objects.get(id=shop_id)
    else:
        selected_shop = None
    
    # Calculate totals
    total_sales = sales.count()
    total_amount = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    total_items = SaleItem.objects.filter(sale__in=sales).aggregate(total=Sum('quantity'))['total'] or 0
    
    # Payment method breakdown
    payment_breakdown = sales.values('payment_method').annotate(
        count=Count('id'),
        amount=Sum('total_amount')
    )
    
    # Daily sales
    daily_sales = sales.values('sale_date__date').annotate(
        count=Count('id'),
        amount=Sum('total_amount')
    ).order_by('sale_date__date')
    
    context = {
        'shops': shops,
        'selected_shop': selected_shop,
        'start_date': start_date,
        'end_date': end_date,
        'sales': sales[:100],  # Limit for display
        'total_sales': total_sales,
        'total_amount': total_amount,
        'total_items': total_items,
        'payment_breakdown': payment_breakdown,
        'daily_sales': daily_sales,
    }
    return render(request, 'sales/sales_report.html', context)

@permission_required('sales.view_dailysalesreport')
def daily_sales_report_create(request):
    """Create daily sales report (should be run at end of day)"""
    if request.method == 'POST':
        form = DailySalesReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            
            # Calculate totals for the day
            sales = Sale.objects.filter(
                shop=report.shop,
                sale_date__date=report.report_date,
                status='completed'
            )
            
            report.total_sales = sales.count()
            report.total_amount = sales.aggregate(total=Sum('total_amount'))['total'] or 0
            
            # Payment method breakdown
            for payment_method, _ in Sale.PAYMENT_METHODS:
                amount = sales.filter(payment_method=payment_method).aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
                
                if payment_method == 'cash':
                    report.cash_sales = amount
                elif payment_method == 'mpesa':
                    report.mpesa_sales = amount
                elif payment_method == 'card':
                    report.card_sales = amount
                elif payment_method == 'credit':
                    report.credit_sales = amount
            
            report.save()
            messages.success(request, f'Daily sales report created for {report.report_date}')
            return redirect('sales:daily_reports')
    else:
        # Default to yesterday
        yesterday = timezone.now().date() - timedelta(days=1)
        form = DailySalesReportForm(initial={'report_date': yesterday})
    
    return render(request, 'sales/daily_report_form.html', {'form': form})

@login_required
def daily_reports(request):
    reports = DailySalesReport.objects.all().order_by('-report_date')
    
    # Filter by shop if user is shop staff
    if request.user.role in ['sales_person', 'shop_manager']:
        managed_shops = Shop.objects.filter(manager=request.user)
        reports = reports.filter(shop__in=managed_shops)
    
    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            reports = reports.filter(report_date__range=[start, end])
        except ValueError:
            pass
    
    return render(request, 'sales/daily_reports.html', {'reports': reports})

# Export Views
@login_required
def export_shop_stock(request, shop_pk):
    """Export shop stock to CSV"""
    shop = get_object_or_404(Shop, pk=shop_pk)
    stock_items = shop.stock_items.all().select_related('product')
    
    # Check permissions
    if request.user.role in ['sales_person', 'shop_manager']:
        if shop.manager != request.user:
            messages.error(request, 'You are not authorized to export stock for this shop.')
            return redirect('sales:shop_detail', pk=shop_pk)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{shop.shop_code}_stock_{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Shop', shop.name, 'Date', timezone.now().date()])
    writer.writerow([])
    writer.writerow(['SKU', 'Product Name', 'Category', 'Current Stock', 'Min Level', 'Max Level', 'Stock Status', 'Unit Price', 'Stock Value'])
    
    for item in stock_items:
        writer.writerow([
            item.product.sku,
            item.product.name,
            item.product.get_product_type_display(),
            item.quantity,
            item.min_stock_level,
            item.max_stock_level,
            item.get_stock_status_display(),
            item.product.selling_price,
            item.stock_value
        ])
    
    return response

@login_required
def export_sales_report(request):
    """Export sales report to CSV"""
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    shop_id = request.GET.get('shop')
    
    # Filter sales
    sales = Sale.objects.filter(
        sale_date__date__range=[start_date, end_date],
        status='completed'
    )
    
    if shop_id:
        sales = sales.filter(shop_id=shop_id)
        shop = Shop.objects.get(id=shop_id)
        filename = f"{shop.shop_code}_sales_{start_date}_to_{end_date}.csv"
    else:
        filename = f"all_shops_sales_{start_date}_to_{end_date}.csv"
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow(['Sales Report', f'{start_date} to {end_date}'])
    writer.writerow([])
    writer.writerow(['Invoice No', 'Date', 'Shop', 'Customer', 'Payment Method', 'Items', 'Subtotal', 'Discount', 'Tax', 'Total', 'Amount Paid', 'Balance'])
    
    for sale in sales:
        writer.writerow([
            sale.invoice_number,
            sale.sale_date.date(),
            sale.shop.name,
            sale.customer_name or 'Walk-in',
            sale.get_payment_method_display(),
            sale.sale_items_count,
            sale.subtotal,
            sale.discount_amount,
            sale.tax_amount,
            sale.total_amount,
            sale.amount_paid,
            sale.balance
        ])
    
    return response

# Dashboard Views
@login_required
def sales_dashboard(request):
    """Sales dashboard for shop managers and sales persons"""
    today = timezone.now().date()
    
    if request.user.role in ['sales_person', 'shop_manager']:
        # User can only see their managed shops
        managed_shops = Shop.objects.filter(manager=request.user)
        shops = managed_shops
    else:
        # Admin/owner can see all shops
        shops = Shop.objects.filter(is_active=True)
        managed_shops = shops
    
    # Today's sales
    today_sales = Sale.objects.filter(
        shop__in=managed_shops,
        sale_date__date=today,
        status='completed'
    )
    
    # Monthly sales
    first_day = today.replace(day=1)
    monthly_sales = Sale.objects.filter(
        shop__in=managed_shops,
        sale_date__date__gte=first_day,
        sale_date__date__lte=today,
        status='completed'
    )
    
    # Low stock items
    low_stock_items = ShopStock.objects.filter(
        shop__in=managed_shops,
        quantity__lte=F('min_stock_level')
    ).select_related('product', 'shop')[:10]
    
    # Pending transfers
    pending_transfers = StockTransfer.objects.filter(
        to_shop__in=managed_shops,
        status__in=['pending', 'in_transit', 'delivered']
    )[:10]
    
    context = {
        'today': today,
        'shops': shops,
        'today_sales_count': today_sales.count(),
        'today_sales_amount': today_sales.aggregate(total=Sum('total_amount'))['total'] or 0,
        'monthly_sales_count': monthly_sales.count(),
        'monthly_sales_amount': monthly_sales.aggregate(total=Sum('total_amount'))['total'] or 0,
        'low_stock_items': low_stock_items,
        'pending_transfers': pending_transfers,
    }
    
    return render(request, 'sales/dashboard.html', context)

