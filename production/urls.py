# production/urls.py
from django.urls import path
from . import views

app_name = 'production'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.production_dashboard, name='dashboard'),
    
    # Product URLs
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:product_id>/formula/', views.edit_product_formula, name='edit_product_formula'),
    path('products/<int:product_id>/labour-tasks/', views.edit_product_labour_tasks, name='edit_labour_tasks'),
    
    # Production Order URLs
    path('production-orders/', views.ProductionOrderListView.as_view(), name='production_order_list'),
    path('production-orders/create/', views.ProductionOrderCreateView.as_view(), name='production_order_create'),
    path('production-orders/<int:pk>/', views.ProductionOrderDetailView.as_view(), name='production_order_detail'),
    path('production-orders/<int:order_id>/plan/', views.plan_production_order, name='plan_production_order'),
    path('production-orders/<int:order_id>/start/', views.start_production, name='start_production'),
    path('production-orders/<int:order_id>/complete/', views.complete_production, name='complete_production'),
    
    # Production Task URLs
    path('worker-dashboard/', views.worker_dashboard, name='worker_dashboard'),

    path('tasks/<int:task_id>/assign/', views.assign_task_view, name='assign_task'),
    path('tasks/start/', views.start_task_view, name='start_task'),
    path('tasks/complete/', views.complete_task_view, name='complete_task'),
    path('tasks/verify/', views.verify_task_view, name='verify_task'),
    
    # Work Station URLs
    path('workstations/', views.WorkStationListView.as_view(), name='workstation_list'),
    path('workstations/create/', views.WorkStationCreateView.as_view(), name='workstation_create'),
    path('workstations/<int:pk>/edit/', views.WorkStationUpdateView.as_view(), name='workstation_edit'),
    path('workstations/<int:pk>/delete/', views.WorkStationDeleteView.as_view(), name='workstation_delete'),
    
    # API URLs
    path('api/product/<int:product_id>/', views.get_product_details, name='api_product_details'),
    path('api/production-order/<int:order_id>/', views.get_production_order_details, name='api_production_order_details'),
    path('api/chart-data/', views.production_chart_data, name='api_chart_data'),

    
]

