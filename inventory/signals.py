# inventory/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import InventoryTransaction, StockAdjustment

@receiver(post_save, sender=InventoryTransaction)
def update_stock_on_transaction(sender, instance, created, **kwargs):
    if created:
        # Stock update logic moved from save() method
        pass

@receiver(post_save, sender=StockAdjustment)
def create_transaction_on_adjustment(sender, instance, created, **kwargs):
    if created:
        # Transaction creation logic moved from save() method
        pass