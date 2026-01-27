from django import forms
from django.contrib.auth import get_user_model
from .models import *
from production.models import Product

User = get_user_model()

class ShopForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = '__all__'
        widgets = {
            'opening_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class StockTransferForm(forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = ['transfer_type', 'from_location', 'to_shop', 'expected_delivery_date', 
                  'delivery_notes', 'vehicle_number', 'driver_name', 'driver_contact']
        widgets = {
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'delivery_notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.has_perm('sales.change_stocktransfer'):
            # Add more fields for managers
            self.fields['status'] = forms.ChoiceField(choices=StockTransfer.STATUS_CHOICES)

class StockTransferItemForm(forms.ModelForm):
    class Meta:
        model = StockTransferItem
        fields = ['product', 'quantity', 'notes']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(is_active=True)

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['shop', 'customer_name', 'customer_phone', 'customer_email', 
                  'customer_id', 'payment_method', 'discount_amount', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'unit_price', 'discount_percentage', 'notes']
    
    def __init__(self, *args, **kwargs):
        shop = kwargs.pop('shop', None)
        super().__init__(*args, **kwargs)
        if shop:
            # Only show products available at this shop
            available_products = Product.objects.filter(
                is_active=True,
                shopstock__shop=shop
            ).distinct()
            self.fields['product'].queryset = available_products

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class StockAdjustmentShopForm(forms.ModelForm):
    class Meta:
        model = StockAdjustmentShop
        fields = ['shop', 'product', 'adjustment_type', 'quantity', 'reason', 'notes']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class DailySalesReportForm(forms.ModelForm):
    class Meta:
        model = DailySalesReport
        fields = ['shop', 'report_date', 'opening_balance', 'notes']
        widgets = {
            'report_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class StockTakeForm(forms.Form):
    """Form for physical stock taking"""
    shop = forms.ModelChoiceField(queryset=Shop.objects.filter(is_active=True))
    product = forms.ModelChoiceField(queryset=Product.objects.filter(is_active=True))
    physical_count = forms.IntegerField(min_value=0)
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically update product choices based on shop
        if 'shop' in self.data:
            try:
                shop_id = int(self.data.get('shop'))
                self.fields['product'].queryset = Product.objects.filter(
                    shopstock__shop_id=shop_id,
                    is_active=True
                ).distinct()
            except (ValueError, TypeError):
                pass

