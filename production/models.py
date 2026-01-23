# production/models.py
from django.db import models

from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from django.conf import settings

class Product(models.Model):
    PRODUCT_TYPES = [
        ('chair', 'Chair'),
        ('bed', 'Bed'),
        ('table', 'Table'),
        ('sofa', 'Sofa'),
        ('cabinet', 'Cabinet'),
        ('shelf', 'Shelf'),
        ('stool', 'Stool'),
        ('bench', 'Bench'),
    ]
    
    name = models.CharField(max_length=200)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    sku = models.CharField(max_length=50, unique=True, verbose_name="SKU")
    description = models.TextField(blank=True)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    production_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Product"
        verbose_name_plural = "Products"
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('production:product_detail', args=[str(self.id)])
    
    def save(self, *args, **kwargs):
        if not self.sku:
            # Generate SKU automatically
            prefix = self.product_type[:3].upper()
            count = Product.objects.filter(product_type=self.product_type).count() + 1
            self.sku = f"{prefix}-{str(count).zfill(4)}"
        
        # Calculate profit margin
        if self.selling_price > 0 and self.production_cost > 0:
            self.profit_margin = ((self.selling_price - self.production_cost) / self.selling_price) * 100
        
        super().save(*args, **kwargs)
    
    def update_production_cost(self):
        """Update production cost based on formula and labour costs"""
        material_cost = Decimal('0')
        labour_cost = Decimal('0')
        
        # Calculate material cost from formula
        for formula in self.formulas.all():
            material_cost += formula.quantity_required * formula.raw_material.unit_price
        
        # Calculate labour cost from tasks
        for task in self.labour_tasks.all():
            labour_cost += task.labour_cost
        
        self.production_cost = material_cost + labour_cost
        
        # Update profit margin
        if self.selling_price > 0:
            self.profit_margin = ((self.selling_price - self.production_cost) / self.selling_price) * 100
        
        self.save()

class ProductFormula(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='formulas')
    raw_material = models.ForeignKey('inventory.RawMaterial', on_delete=models.CASCADE)
    quantity_required = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['product', 'raw_material']
        verbose_name = "Product Formula"
        verbose_name_plural = "Product Formulas"
    
    def __str__(self):
        return f"{self.product.name} - {self.raw_material.name}"
    
    @property
    def material_cost(self):
        return self.quantity_required * self.raw_material.unit_price

class LabourTask(models.Model):
    TASK_TYPES = [
        ('cutting', 'Cutting Cover'),
        ('laying', 'Laying Cover'),
        ('finishing', 'Finishing'),
        ('skeleton', 'Skeleton Building'),
        ('assembly', 'Assembly'),
        ('upholstery', 'Upholstery'),
        ('sanding', 'Sanding'),
        ('painting', 'Painting'),
        ('polishing', 'Polishing'),
        ('packaging', 'Packaging'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='labour_tasks')
    task_type = models.CharField(max_length=20, choices=TASK_TYPES)
    task_name = models.CharField(max_length=100, blank=True)
    labour_cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=1, validators=[MinValueValidator(0.1)])
    description = models.TextField()
    sequence = models.IntegerField(default=0, help_text="Order in which this task should be performed")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sequence', 'task_type']
        verbose_name = "Labour Task"
        verbose_name_plural = "Labour Tasks"
    
    def __str__(self):
        if self.task_name:
            return f"{self.task_name} - {self.product.name}"
        return f"{self.get_task_type_display()} - {self.product.name}"
    
    def save(self, *args, **kwargs):
        if not self.task_name:
            self.task_name = self.get_task_type_display()
        super().save(*args, **kwargs)
        
        # Update product production cost
        self.product.update_production_cost()

class ProductionOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True, verbose_name="Production Order Number")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='production_orders')
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(default=1, choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    start_date = models.DateField()
    expected_completion_date = models.DateField()
    actual_completion_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_production_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Production Order"
        verbose_name_plural = "Production Orders"
    
    def __str__(self):
        return f"PROD-{self.order_number} - {self.product.name} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            last_order = ProductionOrder.objects.order_by('-id').first()
            if last_order:
                try:
                    last_num = int(last_order.order_number.split('-')[1])
                    self.order_number = f"PROD-{str(last_num + 1).zfill(5)}"
                except:
                    self.order_number = f"PROD-{str(last_order.id + 1).zfill(5)}"
            else:
                self.order_number = "PROD-00001"
        
        # Auto-generate production tasks if not exists
        if not self.pk:
            super().save(*args, **kwargs)
            self.generate_production_tasks()
        else:
            super().save(*args, **kwargs)
    
    def generate_production_tasks(self):
        """Generate production tasks based on product's labour tasks"""
        labour_tasks = self.product.labour_tasks.all()
        
        for labour_task in labour_tasks:
            ProductionTask.objects.create(
                production_order=self,
                labour_task=labour_task,
                quantity=self.quantity,
                sequence=labour_task.sequence
            )
    
    def calculate_material_requirements(self):
        """Calculate total material requirements for this production order"""
        requirements = {}
        formulas = self.product.formulas.all()
        
        for formula in formulas:
            total_required = formula.quantity_required * self.quantity
            requirements[formula.raw_material] = {
                'quantity_required': total_required,
                'unit': formula.raw_material.unit,
                'current_stock': formula.raw_material.current_stock,
                'sufficient': formula.raw_material.current_stock >= total_required
            }
        
        return requirements
    
    def check_material_availability(self):
        """Check if enough materials are available for production"""
        requirements = self.calculate_material_requirements()
        all_sufficient = True
        insufficient_materials = []
        
        for material, data in requirements.items():
            if not data['sufficient']:
                all_sufficient = False
                shortage = data['quantity_required'] - data['current_stock']
                insufficient_materials.append({
                    'material': material,
                    'required': data['quantity_required'],
                    'available': data['current_stock'],
                    'shortage': shortage,
                    'unit': data['unit']
                })
        
        return all_sufficient, insufficient_materials
    
    def start_production(self):
        """Start production - consume materials and create inventory transactions"""
        if self.status != 'planned':
            return False
        
        # Check material availability
        sufficient, insufficient = self.check_material_availability()
        if not sufficient:
            return False
        
        # Consume materials
        requirements = self.calculate_material_requirements()
        for material, data in requirements.items():
            # Create inventory transaction for material usage
            from inventory.models import InventoryTransaction
            InventoryTransaction.objects.create(
                raw_material=material,
                transaction_type='production_usage',
                quantity=data['quantity_required'],
                reference=self.order_number,
                notes=f'Used for production order {self.order_number}',
                created_by=self.created_by
            )
        
        # Update status
        self.status = 'in_progress'
        self.save()
        return True
    
    def complete_production(self):
        """Mark production as complete"""
        if self.status != 'in_progress':
            return False
        
        # Check if all tasks are completed
        incomplete_tasks = self.tasks.filter(status__in=['pending', 'in_progress', 'assigned'])
        if incomplete_tasks.exists():
            return False
        
        self.status = 'completed'
        self.actual_completion_date = timezone.now().date()
        self.save()
        return True
    
    @property
    def total_labour_cost(self):
        tasks = self.product.labour_tasks.all()
        return sum(task.labour_cost for task in tasks) * self.quantity
    
    @property
    def total_material_cost(self):
        total = Decimal('0')
        for formula in self.product.formulas.all():
            total += formula.quantity_required * formula.raw_material.unit_price * self.quantity
        return total
    
    @property
    def total_production_cost(self):
        return self.total_material_cost + self.total_labour_cost
    
    @property
    def progress_percentage(self):
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0
        
        completed_tasks = self.tasks.filter(status='completed').count()
        return int((completed_tasks / total_tasks) * 100)

class ProductionTask(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
        ('cancelled', 'Cancelled'),
    ]
    
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, related_name='tasks')
    labour_task = models.ForeignKey(LabourTask, on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    quantity = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sequence = models.IntegerField(default=0)
    start_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_tasks')
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sequence', 'created_at']
        verbose_name = "Production Task"
        verbose_name_plural = "Production Tasks"
    
    def __str__(self):
        return f"{self.labour_task.task_name} - {self.production_order.order_number}"
    
    @property
    def task_name(self):
        return self.labour_task.task_name or self.labour_task.get_task_type_display()
    
    @property
    def labour_cost(self):
        return self.labour_task.labour_cost * self.quantity
    
    def assign_to_worker(self, worker_user):
        """Assign task to a worker"""
        if worker_user.role != 'fundi':
            return False, "User is not a fundi/worker"
        
        if self.status not in ['pending', 'assigned']:
            return False, f"Task is already {self.get_status_display()}"
        
        self.assigned_to = worker_user
        self.status = 'assigned'
        if not self.start_date:
            self.start_date = timezone.now()
        self.save()
        
        # Send notification to worker
        # TODO: Implement notification system
        
        return True, "Task assigned successfully"
    
    def start_work(self, worker_user):
        """Worker starts working on the task"""
        if self.assigned_to != worker_user:
            return False, "Task not assigned to you"
        
        if self.status not in ['assigned', 'pending']:
            return False, f"Task is {self.get_status_display()}, cannot start"
        
        if not self.can_start():
            return False, "Previous tasks are not completed"
        
        self.status = 'in_progress'
        if not self.start_date:
            self.start_date = timezone.now()
        self.save()
        
        return True, "Task started successfully"
    
    def mark_complete(self, worker_user):
        """Worker marks task as complete"""
        if self.assigned_to != worker_user:
            return False, "Task not assigned to you"
        
        if self.status != 'in_progress':
            return False, f"Task is {self.get_status_display()}, cannot complete"
        
        self.status = 'completed'
        self.completed_date = timezone.now()
        self.save()
        
        return True, "Task marked as complete"
    
    def verify_completion(self, supervisor_user):
        """Supervisor verifies completed task"""
        if self.status != 'completed':
            return False, "Task is not completed"
        
        # Check if user has permission to verify
        if supervisor_user.role not in ['supervisor', 'production_manager', 'owner']:
            return False, "You don't have permission to verify tasks"
        
        self.status = 'verified'
        self.verified_by = supervisor_user
        self.verified_at = timezone.now()
        self.save()
        
        # Create work log for payment (handle via signal or separate view)
        self._create_work_log()
        
        # Check if all tasks are completed to auto-complete production order
        incomplete_tasks = self.production_order.tasks.exclude(status='verified')
        if not incomplete_tasks.exists():
            self.production_order.complete_production()
        
        return True, "Task verified successfully"
    
    def _create_work_log(self):
        """Create work log for this task (called after verification)"""
        try:
            # Import inside method to avoid circular imports
            from hr.models import WorkLog
            
            # Check if user has employee record
            if not hasattr(self.assigned_to, 'employee'):
                print(f"No employee record for user {self.assigned_to.username}")
                return False
            
            # Check if work log already exists for this task
            if WorkLog.objects.filter(production_task=self).exists():
                print(f"Work log already exists for task {self.id}")
                return False
            
            # Create work log
            WorkLog.objects.create(
                employee=self.assigned_to.employee,
                production_task=self,
                date=self.completed_date.date() if self.completed_date else timezone.now().date(),
                hours_worked=self.labour_task.estimated_hours * self.quantity,
                amount_earned=self.labour_cost,
                task_description=f"{self.task_name} - {self.production_order.order_number}",
                notes=f"Verified by {self.verified_by.get_full_name() if self.verified_by else 'Supervisor'}"
            )
            
            return True
            
        except ImportError:
            print("HR app not available for work log creation")
            return False
        except Exception as e:
            print(f"Error creating work log: {e}")
            return False
    
    def can_start(self):
        """Check if task can be started (previous tasks are completed)"""
        # If no sequence or first task, can start
        if self.sequence <= 1:
            return True
        
        previous_tasks = ProductionTask.objects.filter(
            production_order=self.production_order,
            sequence__lt=self.sequence
        ).exclude(id=self.id)
        
        if not previous_tasks.exists():
            return True
        
        # Check if all previous tasks are verified
        return all(task.status == 'verified' for task in previous_tasks)
    
    def get_status_color(self):
        """Return Bootstrap color class for status"""
        status_colors = {
            'pending': 'secondary',
            'assigned': 'info',
            'in_progress': 'primary',
            'completed': 'warning',
            'verified': 'success',
            'cancelled': 'danger',
        }
        return status_colors.get(self.status, 'secondary')
    
    @property
    def is_assigned(self):
        return self.assigned_to is not None
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def is_verified(self):
        return self.status == 'verified'
    
    @property
    def worker_name(self):
        return self.assigned_to.get_full_name() if self.assigned_to else "Not assigned"
    
    @property
    def production_order_number(self):
        return self.production_order.order_number
    
    @property
    def product_name(self):
        return self.production_order.product.name
      

class WorkStation(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Work Station"
        verbose_name_plural = "Work Stations"
    
    def __str__(self):
        return self.name

class ProductionLine(models.Model):
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, related_name='lines')
    workstation = models.ForeignKey(WorkStation, on_delete=models.CASCADE)
    task = models.ForeignKey(ProductionTask, on_delete=models.CASCADE, null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ProductionTask.STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['start_time']
        verbose_name = "Production Line"
        verbose_name_plural = "Production Lines"
    
    def __str__(self):
        return f"{self.workstation.name} - {self.production_order.order_number}"