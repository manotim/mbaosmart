# inventory/models.py
from django.db import models
from django.db.models import F, ExpressionWrapper, DecimalField
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings

class RawMaterialCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Raw Material Category"
        verbose_name_plural = "Raw Material Categories"
    
    def __str__(self):
        return self.name

class RawMaterial(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilograms (kg)'),
        ('pcs', 'Pieces (pcs)'),
        ('ft', 'Feet (ft)'),
        ('m', 'Meters (m)'),
        ('l', 'Liters (l)'),
        ('roll', 'Rolls'),
        ('box', 'Boxes'),
        ('yard', 'Yards'),
        ('sheet', 'Sheets'),
        ('bundle', 'Bundles'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, verbose_name="Material Code")
    category = models.ForeignKey(RawMaterialCategory, on_delete=models.CASCADE, related_name='raw_materials')
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='pcs')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    min_stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=10, verbose_name="Minimum Stock Level")
    max_stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=100, verbose_name="Maximum Stock Level")
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Current Stock")
    location = models.CharField(max_length=100, default='Main Store')
    supplier = models.ForeignKey('procurement.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='raw_materials')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Raw Material"
        verbose_name_plural = "Raw Materials"
    
    def __str__(self):
        return f"{self.name} ({self.unit})"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('inventory:raw_material_detail', args=[str(self.id)])
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_instance = None
        
        if not is_new:
            old_instance = RawMaterial.objects.get(pk=self.pk)
        
        super().save(*args, **kwargs)
        
        # Check if we need to create or update alerts after save
        if not is_new and old_instance:
            # Only check if stock has changed
            if old_instance.current_stock != self.current_stock:
                self._check_and_create_alerts()
    
    def _check_and_create_alerts(self):
        """Create or update alerts based on current stock levels"""
        from .models import StockAlert
        
        # Deactivate any existing active alerts for this material first
        StockAlert.objects.filter(
            raw_material=self,
            is_active=True
        ).update(is_active=False)
        
        # Check for out of stock (priority 1)
        if self.current_stock <= 0:
            StockAlert.objects.create(
                raw_material=self,
                alert_type='out_of_stock',
                message=f'{self.name} is out of stock! Current stock: 0 {self.unit}',
                is_active=True
            )
        
        # Check for low stock (priority 2)
        elif self.current_stock <= self.min_stock_level:
            StockAlert.objects.create(
                raw_material=self,
                alert_type='low_stock',
                message=f'{self.name} is below minimum stock level. Current: {self.current_stock} {self.unit}, Minimum: {self.min_stock_level} {self.unit}',
                is_active=True
            )
    
    @property
    def total_value(self):
        try:
            return self.current_stock * self.unit_price
        except (TypeError, ValueError):
            return 0
    
    @property
    def stock_status(self):
        try:
            if self.current_stock <= 0:
                return 'out_of_stock'
            elif self.current_stock <= self.min_stock_level:
                return 'low_stock'
            elif self.current_stock >= self.max_stock_level:
                return 'over_stock'
            else:
                return 'normal'
        except (TypeError, ValueError):
            return 'normal'
    
    @property
    def stock_status_color(self):
        status_colors = {
            'out_of_stock': 'danger',
            'low_stock': 'warning',
            'normal': 'success',
            'over_stock': 'info'
        }
        return status_colors.get(self.stock_status, 'secondary')
    
    @property
    def stock_status_text(self):
        status_text = {
            'out_of_stock': 'Out of Stock',
            'low_stock': 'Low Stock',
            'normal': 'In Stock',
            'over_stock': 'Over Stock'
        }
        return status_text.get(self.stock_status, 'Unknown')
    
    @classmethod
    def get_inventory_summary(cls):
        """Get summary statistics for all raw materials"""
        from django.db.models import Sum, Count, Q
        
        queryset = cls.objects.all()
        
        total_materials = queryset.count()
        total_value = sum(mat.total_value for mat in queryset)
        
        low_stock_count = queryset.filter(
            current_stock__gt=0,
            current_stock__lte=F('min_stock_level')
        ).count()
        
        out_of_stock_count = queryset.filter(
            current_stock=0
        ).count()
        
        return {
            'total_materials': total_materials,
            'total_value': total_value,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
        }


class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('production_usage', 'Production Usage'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
        ('transfer', 'Transfer'),
        ('damage', 'Damage/Wastage'),
    ]
    
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reference = models.CharField(max_length=100, help_text="PO Number, Production Order, etc.")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inventory_transactions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Inventory Transaction"
        verbose_name_plural = "Inventory Transactions"
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.raw_material.name}"
    
    def save(self, *args, **kwargs):
        # Calculate total value
        if not self.total_value and self.unit_price:
            self.total_value = self.quantity * self.unit_price
        
        # Check if this is an update or new creation
        is_new = self.pk is None
        
        if is_new:
            # Get the raw material
            raw_material = self.raw_material
            previous_stock = raw_material.current_stock
            
            # Update raw material stock based on transaction type
            if self.transaction_type in ['purchase', 'return']:
                raw_material.current_stock += self.quantity
            elif self.transaction_type in ['production_usage', 'damage', 'transfer']:
                raw_material.current_stock -= self.quantity
                # Ensure stock doesn't go negative
                if raw_material.current_stock < 0:
                    raw_material.current_stock = 0
            
            raw_material.save()  # This will trigger alert creation in RawMaterial.save()
        
        super().save(*args, **kwargs)


class StockAdjustment(models.Model):
    ADJUSTMENT_TYPES = [
        ('add', 'Add Stock'),
        ('remove', 'Remove Stock'),
        ('set', 'Set Stock Level'),
    ]
    
    REASONS = [
        ('physical_count', 'Physical Count'),
        ('damage', 'Damaged Goods'),
        ('expired', 'Expired Items'),
        ('theft', 'Theft/Loss'),
        ('other', 'Other'),
    ]
    
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='adjustments')
    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    reason = models.CharField(max_length=20, choices=REASONS)
    notes = models.TextField(blank=True)
    adjusted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stock_adjustments')
    adjusted_at = models.DateTimeField(auto_now_add=True)
    previous_stock = models.DecimalField(max_digits=10, decimal_places=2)
    new_stock = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        ordering = ['-adjusted_at']
        verbose_name = "Stock Adjustment"
        verbose_name_plural = "Stock Adjustments"
    
    def __str__(self):
        return f"{self.get_adjustment_type_display()} - {self.raw_material.name}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        if is_new:
            self.previous_stock = self.raw_material.current_stock
            
            if self.adjustment_type == 'add':
                self.new_stock = self.previous_stock + self.quantity
            elif self.adjustment_type == 'remove':
                self.new_stock = self.previous_stock - self.quantity
                # Ensure stock doesn't go negative
                if self.new_stock < 0:
                    self.new_stock = 0
                    self.quantity = self.previous_stock  # Adjust quantity to remove only available stock
            elif self.adjustment_type == 'set':
                self.new_stock = self.quantity
                # Calculate the quantity difference for the transaction
                self.quantity = abs(self.new_stock - self.previous_stock)
            
            # Update raw material stock
            self.raw_material.current_stock = self.new_stock
            self.raw_material.save()  # This will trigger alert creation in RawMaterial.save()
            
            # Create inventory transaction
            InventoryTransaction.objects.create(
                raw_material=self.raw_material,
                transaction_type='adjustment',
                quantity=self.quantity,
                reference=f"ADJ-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                notes=f"{self.get_reason_display()}: {self.notes}",
                created_by=self.adjusted_by
            )
        
        super().save(*args, **kwargs)


class StockAlert(models.Model):
    ALERT_TYPES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('expiring', 'Expiring Soon'),
    ]
    
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Stock Alert"
        verbose_name_plural = "Stock Alerts"
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.raw_material.name}"
    
    def acknowledge(self, user):
        """Mark alert as acknowledged"""
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.is_active = False
        self.save()