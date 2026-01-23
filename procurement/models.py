# procurement/models.py
from django.db import models

from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    tin_number = models.CharField(max_length=50, verbose_name="TIN Number")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('accounts:supplier_detail', args=[str(self.id)])

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    po_number = models.CharField(max_length=50, unique=True, verbose_name="PO Number")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requested_pos')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_pos')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"
    
    def __str__(self):
        return f"{self.po_number} - {self.supplier.name}"
    
    def save(self, *args, **kwargs):
        if not self.po_number:
            last_po = PurchaseOrder.objects.order_by('-id').first()
            if last_po:
                try:
                    last_num = int(last_po.po_number.split('-')[1])
                    self.po_number = f"PO-{str(last_num + 1).zfill(5)}"
                except:
                    self.po_number = f"PO-{str(last_po.id + 1).zfill(5)}"
            else:
                self.po_number = "PO-00001"
        
        if self.status == 'approved' and not self.approved_at:
            self.approved_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('accounts:purchase_order_detail', args=[str(self.id)])
    
    @property
    def can_approve(self):
        return self.status == 'pending_approval'
    
    @property
    def can_mark_paid(self):
        return self.status == 'approved'
    
    @property
    def can_create_grn(self):
        return self.status == 'paid'

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    raw_material = models.ForeignKey('inventory.RawMaterial', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    total_price = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    class Meta:
        verbose_name = "Purchase Order Item"
        verbose_name_plural = "Purchase Order Items"
    
    def __str__(self):
        return f"{self.raw_material.name} - {self.quantity} {self.raw_material.unit}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        
        # Update parent PO total
        po_total = sum(item.total_price for item in self.purchase_order.items.all())
        self.purchase_order.total_amount = po_total
        self.purchase_order.save()

class GoodsReceivedNote(models.Model):
    grn_number = models.CharField(max_length=50, unique=True, verbose_name="GRN Number")
    purchase_order = models.OneToOneField(PurchaseOrder, on_delete=models.CASCADE, related_name='grn')
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_grns')
    checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='checked_grns')
    received_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-received_date']
        verbose_name = "Goods Received Note"
        verbose_name_plural = "Goods Received Notes"
    
    def __str__(self):
        return f"GRN-{self.grn_number}"
    
    def save(self, *args, **kwargs):
        if not self.grn_number:
            last_grn = GoodsReceivedNote.objects.order_by('-id').first()
            if last_grn:
                try:
                    last_num = int(last_grn.grn_number.split('-')[1])
                    self.grn_number = f"GRN-{str(last_num + 1).zfill(5)}"
                except:
                    self.grn_number = f"GRN-{str(last_grn.id + 1).zfill(5)}"
            else:
                self.grn_number = "GRN-00001"
        super().save(*args, **kwargs)