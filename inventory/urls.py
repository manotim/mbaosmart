# inventory/urls.py
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.inventory_dashboard, name='dashboard'),
    
    # Category URLs
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
    
    # Raw Material URLs
    path('raw-materials/', views.RawMaterialListView.as_view(), name='raw_material_list'),
    path('raw-materials/create/', views.RawMaterialCreateView.as_view(), name='raw_material_create'),
    path('raw-materials/<int:pk>/', views.RawMaterialDetailView.as_view(), name='raw_material_detail'),
    path('raw-materials/<int:pk>/edit/', views.RawMaterialUpdateView.as_view(), name='raw_material_edit'),
    path('raw-materials/<int:pk>/delete/', views.delete_raw_material, name='raw_material_delete'),
    
    # Transaction URLs
    path('transactions/', views.InventoryTransactionListView.as_view(), name='transaction_list'),
    path('transactions/create/', views.create_inventory_transaction, name='transaction_create'),
    
    # Stock Adjustment URLs
    path('adjustments/', views.StockAdjustmentListView.as_view(), name='adjustment_list'),
    path('adjustments/create/', views.adjust_stock, name='adjustment_create'),
    
    # Stock Transfer URLs
    path('transfer/', views.transfer_stock, name='transfer_stock'),
    
    # Stock Alert URLs
    path('alerts/', views.stock_alerts, name='stock_alerts'),
    path('alerts/<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    
    # Report URLs
    path('reports/stock/', views.stock_report, name='stock_report'),
    
    # API URLs
    path('api/material/<int:material_id>/', views.get_material_details, name='api_material_details'),
    path('api/chart-data/', views.inventory_chart_data, name='api_chart_data'),
    path('api/stock-data/', views.api_stock_data, name='api_stock_data'),
]