from django import template
from datetime import timedelta


register = template.Library()

@register.filter
def add_days(value, days):
    return value + timedelta(days=days)

@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0
