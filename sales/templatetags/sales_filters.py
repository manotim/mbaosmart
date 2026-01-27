# sales/templatetags/sales_filters.py
from django import template

register = template.Library()

@register.filter
def list_sum(queryset, field):
    """Sum a field in a queryset"""
    return sum(getattr(item, field) for item in queryset)

@register.filter
def filter_stock_status(queryset, status):
    """Filter queryset by stock status"""
    return [item for item in queryset if item.stock_status == status]

@register.filter
def div(value, arg):
    """Divide value by arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except ValueError:
        return 0