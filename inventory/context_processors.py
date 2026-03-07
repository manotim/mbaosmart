# inventory/context_processors.py
from .models import StockAlert

def stock_alert_count(request):
    """Add stock alert count to all templates"""
    if request.user.is_authenticated:
        count = StockAlert.objects.filter(is_active=True).count()
        return {'stock_alert_count': count}
    return {'stock_alert_count': 0}