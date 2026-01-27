# sales/urls.py
from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Shop URLs
    path('shops/', views.shop_list, name='shop_list'),
    path('shops/<int:pk>/', views.shop_detail, name='shop_detail'),
    path('shops/create/', views.shop_create, name='shop_create'),
    path('shops/<int:pk>/update/', views.shop_update, name='shop_update'),
    
    # Stock Transfer URLs
    path('transfers/', views.stock_transfer_list, name='stock_transfer_list'),
    path('transfers/<int:pk>/', views.stock_transfer_detail, name='stock_transfer_detail'),
    path('transfers/create/', views.stock_transfer_create, name='stock_transfer_create'),
    path('transfers/<int:pk>/update/', views.stock_transfer_update, name='stock_transfer_update'),
    path('transfers/<int:pk>/items/', views.stock_transfer_items, name='stock_transfer_items'),
    path('transfers/<int:pk>/items/<int:item_pk>/delete/', views.stock_transfer_item_delete, name='stock_transfer_item_delete'),
    path('transfers/<int:pk>/deliver/', views.stock_transfer_deliver, name='stock_transfer_deliver'),
    path('transfers/<int:pk>/receive/', views.stock_transfer_receive, name='stock_transfer_receive'),
    path('transfers/<int:pk>/items/<int:item_pk>/update-qty/', views.update_received_quantity, name='update_received_quantity'),
    
    # Sale URLs
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('sales/create/', views.sale_create, name='sale_create'),
    path('sales/<int:pk>/items/', views.sale_items, name='sale_items'),
    path('sales/<int:pk>/items/<int:item_pk>/delete/', views.sale_item_delete, name='sale_item_delete'),
    path('sales/<int:pk>/complete/', views.sale_complete, name='sale_complete'),
    path('sales/<int:pk>/add-payment/', views.sale_add_payment, name='sale_add_payment'),
    
    # Customer URLs
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/update/', views.customer_update, name='customer_update'),
    
    # Stock Management URLs
    path('stock/', views.shop_stock_list, name='shop_stock_list'),
    path('stock/shop/<int:shop_pk>/', views.shop_stock_list, name='shop_stock_detail'),
    path('stock/take/', views.stock_take, name='stock_take'),
    
    # Reporting URLs
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/daily/create/', views.daily_sales_report_create, name='daily_report_create'),
    path('reports/daily/', views.daily_reports, name='daily_reports'),
    
    # Export URLs
    path('export/stock/<int:shop_pk>/', views.export_shop_stock, name='export_shop_stock'),
    path('export/sales/', views.export_sales_report, name='export_sales_report'),
    
    # Dashboard
    path('dashboard/', views.sales_dashboard, name='dashboard'),
]