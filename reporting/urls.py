from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    path('', views.report_dashboard, name='report_dashboard'),
    path('sales/', views.sales_report, name='sales_report'),
    path('inventory/', views.inventory_report, name='inventory_report'),
    path('production/', views.production_report, name='production_report'),
    path('payroll/', views.payroll_report, name='payroll_report'),
    path('procurement/', views.procurement_report, name='procurement_report'),
    path('custom/', views.custom_report, name='custom_report'),
    path('export/csv/<str:report_type>/', views.export_report_csv, name='export_csv'),
    path('export/pdf/<str:report_type>/', views.export_report_pdf, name='export_pdf'),
]