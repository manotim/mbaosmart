from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

class Shop(models.Model):
    """Selling shops/outlets"""
    SHOP_TYPES = [
        ('main', 'Main Shop'),
        ('branch', 'Branch'),
        ('warehouse', 'Warehouse'),
        ('showroom', 'Showroom'),
    ]
    
    name = models.CharField(max_length=200)
    shop_code = models.CharField(max_length=50, unique=True, verbose_name="Shop Code")
    shop_type = models.CharField(max_length=20, choices=SHOP_TYPES, default='branch')
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_shops'
    )
    location = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField()
    opening_date = models.DateField()
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Shop"
        verbose_name_plural = "Shops"
    
    def __str__(self):
        return f"{self.name} ({self.shop_code})"
    
    def save(self, *args, **kwargs):
        if not self.shop_code:
            last_shop = Shop.objects.order_by('-id').first()
            if last_shop:
                try:
                    last_num = int(last_shop.shop_code.split('-')[1])
                    self.shop_code = f"SHOP-{str(last_num + 1).zfill(3)}"
                except:
                    self.shop_code = f"SHOP-{str(last_shop.id + 1).zfill(3)}"
            else:
                self.shop_code = "SHOP-001"
        super().save(*args, **kwargs)
    
    @property
    def total_stock_value(self):
        total = self.stock_items.aggregate(
            total=models.Sum(models.F('quantity') * models.F('product__selling_price'))
        )['total'] or Decimal('0')
        return total
    
    @property
    def stock_count(self):
        return self.stock_items.count()

class ShopStock(models.Model):
    """Stock items at each shop"""
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='stock_items')
    product = models.ForeignKey('production.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    min_stock_level = models.IntegerField(default=5)
    max_stock_level = models.IntegerField(default=50)
    last_restocked = models.DateTimeField(null=True, blank=True)
    last_sold = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['shop', 'product']
        ordering = ['product__name']
        verbose_name = "Shop Stock"
        verbose_name_plural = "Shop Stocks"
    
    def __str__(self):
        return f"{self.product.name} - {self.shop.name} (Qty: {self.quantity})"
    
    @property
    def stock_value(self):
        return self.quantity * self.product.selling_price
    
    @property
    def stock_status(self):
        if self.quantity <= 0:
            return 'out_of_stock'
        elif self.quantity <= self.min_stock_level:
            return 'low_stock'
        elif self.quantity >= self.max_stock_level:
            return 'over_stock'
        else:
            return 'normal'
    
    @property
    def needs_restocking(self):
        return self.quantity <= self.min_stock_level

class StockTransfer(models.Model):
    """Transfer stock from manufacturing to shops or between shops"""
    TRANSFER_TYPES = [
        ('manufacturing_to_shop', 'Manufacturing to Shop'),
        ('shop_to_shop', 'Shop to Shop'),
        ('shop_to_manufacturing', 'Shop to Manufacturing'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
        ('partially_received', 'Partially Received'),
    ]
    
    transfer_number = models.CharField(max_length=50, unique=True, verbose_name="Transfer Number")
    transfer_type = models.CharField(max_length=30, choices=TRANSFER_TYPES)
    from_location = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='transfers_out',
        null=True,
        blank=True
    )
    to_shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='transfers_in'
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='initiated_transfers'
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_transfers'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transfer_date = models.DateTimeField(default=timezone.now)
    expected_delivery_date = models.DateField()
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    delivery_notes = models.TextField(blank=True)
    receiving_notes = models.TextField(blank=True)
    vehicle_number = models.CharField(max_length=50, blank=True, verbose_name="Vehicle Registration")
    driver_name = models.CharField(max_length=100, blank=True)
    driver_contact = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-transfer_date']
        verbose_name = "Stock Transfer"
        verbose_name_plural = "Stock Transfers"
    
    def __str__(self):
        return f"TRF-{self.transfer_number} ({self.get_transfer_type_display()})"
    
    def save(self, *args, **kwargs):
        if not self.transfer_number:
            last_transfer = StockTransfer.objects.order_by('-id').first()
            if last_transfer:
                try:
                    last_num = int(last_transfer.transfer_number.split('-')[1])
                    self.transfer_number = f"TRF-{str(last_num + 1).zfill(5)}"
                except:
                    self.transfer_number = f"TRF-{str(last_transfer.id + 1).zfill(5)}"
            else:
                self.transfer_number = "TRF-00001"
        super().save(*args, **kwargs)
    
    @property
    def total_items(self):
        return self.items.count()
    
    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_value(self):
        return sum(item.quantity * item.product.selling_price for item in self.items.all())
    
    def can_complete(self):
        """Check if all items have been received"""
        items = self.items.all()
        if not items.exists():
            return False
        return all(item.received_quantity == item.quantity for item in items)
    
    def mark_delivered(self):
        """Mark as delivered - ready for receiving"""
        if self.status in ['pending', 'in_transit']:
            self.status = 'delivered'
            self.actual_delivery_date = timezone.now()
            self.save()
            return True
        return False
    
    def mark_received(self, user):
        """Mark as received by shop"""
        if self.status == 'delivered':
            self.status = 'received'
            self.received_by = user
            self.save()
            
            # Update shop stock for all items
            for item in self.items.all():
                shop_stock, created = ShopStock.objects.get_or_create(
                    shop=self.to_shop,
                    product=item.product,
                    defaults={'quantity': item.received_quantity}
                )
                if not created:
                    shop_stock.quantity += item.received_quantity
                    shop_stock.last_restocked = timezone.now()
                    shop_stock.save()
            
            # If transferring from another shop, reduce their stock
            if self.from_location and self.transfer_type == 'shop_to_shop':
                for item in self.items.all():
                    from_stock = ShopStock.objects.filter(
                        shop=self.from_location,
                        product=item.product
                    ).first()
                    if from_stock:
                        from_stock.quantity -= item.quantity
                        from_stock.save()
            return True
        return False

class StockTransferItem(models.Model):
    """Items in a stock transfer"""
    stock_transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('production.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    received_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Stock Transfer Item"
        verbose_name_plural = "Stock Transfer Items"
        unique_together = ['stock_transfer', 'product']
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"
    
    @property
    def is_fully_received(self):
        return self.received_quantity == self.quantity
    
    @property
    def pending_quantity(self):
        return self.quantity - self.received_quantity
    
    @property
    def item_value(self):
        return self.quantity * self.product.selling_price

class Sale(models.Model):
    """Sales transactions at shops"""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('card', 'Credit/Debit Card'),
        ('bank', 'Bank Transfer'),
        ('credit', 'Credit Sale'),
        ('cheque', 'Cheque'),
    ]
    
    SALE_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_paid', 'Partially Paid'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True, verbose_name="Invoice Number")
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='sales')
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_id = models.CharField(max_length=50, blank=True, verbose_name="Customer ID/Passport")
    sold_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sales_made'
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    status = models.CharField(max_length=20, choices=SALE_STATUS, default='pending')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    sale_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-sale_date']
        verbose_name = "Sale"
        verbose_name_plural = "Sales"
    
    def __str__(self):
        return f"INV-{self.invoice_number} - {self.shop.name}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_sale = Sale.objects.order_by('-id').first()
            if last_sale:
                try:
                    last_num = int(last_sale.invoice_number.split('-')[1])
                    self.invoice_number = f"INV-{str(last_num + 1).zfill(6)}"
                except:
                    self.invoice_number = f"INV-{str(last_sale.id + 1).zfill(6)}"
            else:
                self.invoice_number = "INV-000001"
        
        # Calculate balance
        self.balance = self.total_amount - self.amount_paid
        
        super().save(*args, **kwargs)
    
    @property
    def is_fully_paid(self):
        return self.balance <= 0
    
    @property
    def sale_items_count(self):
        return self.items.count()
    
    def calculate_totals(self):
        """Recalculate sale totals from items"""
        subtotal = sum(item.total_price for item in self.items.all())
        self.subtotal = subtotal
        self.total_amount = subtotal - self.discount_amount + self.tax_amount
        self.balance = self.total_amount - self.amount_paid
        self.save()
    
    def complete_sale(self):
        """Complete sale and update stock"""
        if self.status == 'pending':
            # Check if all items are in stock
            for item in self.items.all():
                shop_stock = ShopStock.objects.filter(
                    shop=self.shop,
                    product=item.product
                ).first()
                
                if not shop_stock or shop_stock.quantity < item.quantity:
                    return False, f"Insufficient stock for {item.product.name}"
            
            # Update stock
            for item in self.items.all():
                shop_stock = ShopStock.objects.get(
                    shop=self.shop,
                    product=item.product
                )
                shop_stock.quantity -= item.quantity
                shop_stock.last_sold = timezone.now()
                shop_stock.save()
            
            self.status = 'completed'
            self.save()
            return True, "Sale completed successfully"
        return False, "Sale is not in pending status"

class SaleItem(models.Model):
    """Items in a sale"""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('production.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Sale Item"
        verbose_name_plural = "Sale Items"
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} x {self.unit_price}"
    
    def save(self, *args, **kwargs):
        # Calculate total price
        discount_amount = (self.unit_price * self.discount_percentage / 100) * self.quantity
        self.total_price = (self.unit_price * self.quantity) - discount_amount
        super().save(*args, **kwargs)
        
        # Update parent sale totals
        self.sale.calculate_totals()

class Customer(models.Model):
    """Customer information"""
    name = models.CharField(max_length=200)
    customer_type = models.CharField(max_length=20, choices=[
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
        ('corporate', 'Corporate'),
        ('institutional', 'Institutional'),
    ], default='retail')
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    id_number = models.CharField(max_length=50, blank=True, verbose_name="ID/Passport Number")
    address = models.TextField(blank=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    loyalty_points = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
    
    def __str__(self):
        return f"{self.name} ({self.customer_type})"
    
    @property
    def total_purchases(self):
        total = self.sales.aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0')
        return total
    
    @property
    def sales_count(self):
        return self.sales.count()

class DailySalesReport(models.Model):
    """Daily sales summary for each shop"""
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='daily_reports')
    report_date = models.DateField()
    total_sales = models.IntegerField(default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cash_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mpesa_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    card_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discounts_given = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['shop', 'report_date']
        ordering = ['-report_date']
        verbose_name = "Daily Sales Report"
        verbose_name_plural = "Daily Sales Reports"
    
    def __str__(self):
        return f"{self.shop.name} - {self.report_date}"

class StockAdjustmentShop(models.Model):
    """Stock adjustments at shop level"""
    ADJUSTMENT_TYPES = [
        ('add', 'Add Stock'),
        ('remove', 'Remove Stock'),
        ('damage', 'Damage'),
        ('theft', 'Theft/Loss'),
        ('expired', 'Expired'),
        ('other', 'Other'),
    ]
    
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='stock_adjustments')
    product = models.ForeignKey('production.Product', on_delete=models.CASCADE)
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPES)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    reason = models.TextField()
    adjusted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    adjusted_at = models.DateTimeField(auto_now_add=True)
    previous_quantity = models.IntegerField()
    new_quantity = models.IntegerField()
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-adjusted_at']
        verbose_name = "Shop Stock Adjustment"
        verbose_name_plural = "Shop Stock Adjustments"
    
    def __str__(self):
        return f"{self.get_adjustment_type_display()} - {self.product.name} at {self.shop.name}"
    
    def save(self, *args, **kwargs):
        if not self.pk:
            # Get current stock
            shop_stock, created = ShopStock.objects.get_or_create(
                shop=self.shop,
                product=self.product,
                defaults={'quantity': 0}
            )
            self.previous_quantity = shop_stock.quantity
            
            # Calculate new quantity
            if self.adjustment_type == 'add':
                self.new_quantity = self.previous_quantity + self.quantity
            else:
                self.new_quantity = self.previous_quantity - self.quantity
            
            # Update shop stock
            shop_stock.quantity = self.new_quantity
            shop_stock.save()
        
        super().save(*args, **kwargs)

