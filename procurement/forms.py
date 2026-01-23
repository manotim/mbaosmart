# procurement/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceivedNote
from inventory.models import RawMaterial

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 'address', 'tin_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Supplier Name'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Physical Address'}),
            'tin_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'TIN Number'}),
        }
        labels = {
            'tin_number': 'TIN Number',
        }

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'delivery_date', 'notes']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Any special instructions...'}),
        }

class PurchaseOrderItemForm(forms.ModelForm):
    raw_material = forms.ModelChoiceField(
        queryset=RawMaterial.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    class Meta:
        model = PurchaseOrderItem
        fields = ['raw_material', 'quantity', 'unit_price']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class GoodsReceivedNoteForm(forms.ModelForm):
    class Meta:
        model = GoodsReceivedNote
        fields = ['checked_by', 'notes']
        widgets = {
            'checked_by': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes about received goods...'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Only show store keepers and supervisors as checked_by options
            from django.contrib.auth.models import Group
            store_group = Group.objects.get(name='Store Keeper')
            supervisor_group = Group.objects.get(name='Supervisor')
            self.fields['checked_by'].queryset = User.objects.filter(
                groups__in=[store_group, supervisor_group]
            ).distinct()

PurchaseOrderItemFormSet = forms.inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=5,
    can_delete=True
)