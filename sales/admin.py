from django.contrib import admin
from .models import *

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'shop_code', 'shop_type', 'location', 'manager', 'is_active')
    list_filter = ('shop_type', 'is_active', 'opening_date')
    search_fields = ('name', 'shop_code', 'location', 'phone')
    list_per_page = 20

@admin.register(ShopStock)
class ShopStockAdmin(admin.ModelAdmin):
    list_display = ('shop', 'product', 'quantity', 'min_stock_level', 'max_stock_level', 'stock_status')
    list_filter = ('shop', 'product__product_type')
    search_fields = ('product__name', 'product__sku')
    list_per_page = 30

@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('transfer_number', 'transfer_type', 'from_location', 'to_shop', 'status', 'transfer_date')
    list_filter = ('transfer_type', 'status', 'transfer_date')
    search_fields = ('transfer_number', 'driver_name', 'vehicle_number')
    readonly_fields = ('transfer_number',)
    list_per_page = 20

@admin.register(StockTransferItem)
class StockTransferItemAdmin(admin.ModelAdmin):
    list_display = ('stock_transfer', 'product', 'quantity', 'received_quantity', 'is_fully_received')
    list_filter = ('stock_transfer__status',)
    search_fields = ('product__name', 'stock_transfer__transfer_number')
    list_per_page = 30

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'shop', 'customer_name', 'total_amount', 'payment_method', 'status', 'sale_date')
    list_filter = ('shop', 'status', 'payment_method', 'sale_date')
    search_fields = ('invoice_number', 'customer_name', 'customer_phone')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at')
    list_per_page = 30

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'unit_price', 'total_price')
    list_filter = ('sale__shop', 'sale__sale_date')
    search_fields = ('product__name', 'sale__invoice_number')
    list_per_page = 30

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer_type', 'phone', 'email', 'credit_limit', 'current_balance', 'is_active')
    list_filter = ('customer_type', 'is_active')
    search_fields = ('name', 'phone', 'email', 'id_number')
    list_per_page = 30

@admin.register(DailySalesReport)
class DailySalesReportAdmin(admin.ModelAdmin):
    list_display = ('shop', 'report_date', 'total_sales', 'total_amount', 'cash_sales', 'mpesa_sales')
    list_filter = ('shop', 'report_date')
    search_fields = ('shop__name', 'report_date')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 30

@admin.register(StockAdjustmentShop)
class StockAdjustmentShopAdmin(admin.ModelAdmin):
    list_display = ('shop', 'product', 'adjustment_type', 'quantity', 'adjusted_by', 'adjusted_at')
    list_filter = ('shop', 'adjustment_type', 'adjusted_at')
    search_fields = ('product__name', 'shop__name', 'reason')
    readonly_fields = ('adjusted_at', 'previous_quantity', 'new_quantity')
    list_per_page = 30

