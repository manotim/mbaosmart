from django import forms
from django.core.exceptions import ValidationError
from .models import Product, ProductFormula, LabourTask, ProductionOrder, ProductionTask, WorkStation
from inventory.models import RawMaterial

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'product_type', 'sku', 'description', 'selling_price', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'product_type': forms.Select(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Auto-generated if empty'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Product description...'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_sku(self):
        sku = self.cleaned_data['sku']
        if not sku:
            return sku  # Will be auto-generated in save method
        
        if Product.objects.filter(sku=sku).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A product with this SKU already exists.')
        return sku

class ProductFormulaForm(forms.ModelForm):
    class Meta:
        model = ProductFormula
        fields = ['raw_material', 'quantity_required', 'notes']
        widgets = {
            'raw_material': forms.Select(attrs={'class': 'form-control'}),
            'quantity_required': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notes about this material usage...'}),
        }
    
    def clean_quantity_required(self):
        quantity = self.cleaned_data['quantity_required']
        if quantity <= 0:
            raise ValidationError('Quantity must be greater than 0.')
        return quantity

class LabourTaskForm(forms.ModelForm):
    class Meta:
        model = LabourTask
        fields = ['task_type', 'task_name', 'labour_cost', 'estimated_hours', 'description', 'sequence']
        widgets = {
            'task_type': forms.Select(attrs={'class': 'form-control'}),
            'task_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Task name (optional)'}),
            'labour_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Cost per unit'}),
            'estimated_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Hours per unit'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Task description...'}),
            'sequence': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def clean_labour_cost(self):
        cost = self.cleaned_data['labour_cost']
        if cost < 0:
            raise ValidationError('Labour cost cannot be negative.')
        return cost

class ProductionOrderForm(forms.ModelForm):
    class Meta:
        model = ProductionOrder
        fields = ['product', 'quantity', 'priority', 'start_date', 'expected_completion_date', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Production notes...'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        expected_completion_date = cleaned_data.get('expected_completion_date')
        
        if start_date and expected_completion_date:
            if expected_completion_date < start_date:
                raise ValidationError('Expected completion date cannot be before start date.')
        
        return cleaned_data

class ProductionTaskAssignmentForm(forms.ModelForm):
    class Meta:
        model = ProductionTask
        fields = ['assigned_to', 'start_date']
        widgets = {
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

class WorkStationForm(forms.ModelForm):
    class Meta:
        model = WorkStation
        fields = ['name', 'location', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Workstation Name'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location in factory'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# Formset for product formulas
ProductFormulaFormSet = forms.inlineformset_factory(
    Product,
    ProductFormula,
    form=ProductFormulaForm,
    extra=5,
    can_delete=True
)

# Formset for labour tasks
LabourTaskFormSet = forms.inlineformset_factory(
    Product,
    LabourTask,
    form=LabourTaskForm,
    extra=3,
    can_delete=True
)