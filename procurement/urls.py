# procurement/urls.py
from django.urls import path
from . import views

app_name = 'procurement'

urlpatterns = [
    # Supplier URLs
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier_delete'),
    
    # Purchase Order URLs
    path('purchase-orders/', views.PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('purchase-orders/create/', views.create_purchase_order, name='purchase_order_create'),
    path('purchase-orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='purchase_order_detail'),
    path('purchase-orders/<int:pk>/approve/', views.approve_purchase_order, name='purchase_order_approve'),
    path('purchase-orders/<int:pk>/reject/', views.reject_purchase_order, name='purchase_order_reject'),
    path('purchase-orders/<int:pk>/mark-paid/', views.mark_purchase_order_paid, name='purchase_order_mark_paid'),
    
    # Goods Received Note URLs
    path('purchase-orders/<int:po_id>/create-grn/', views.create_goods_received_note, name='grn_create'),
    path('grn/<int:pk>/', views.GoodsReceivedNoteDetailView.as_view(), name='grn_detail'),
    
    # API/Data URLs
    path('dashboard-data/', views.procurement_dashboard_data, name='dashboard_data'),
]