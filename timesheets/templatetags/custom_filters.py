from django import template
from datetime import timedelta
from django.utils.safestring import SafeString
from decimal import Decimal

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

@register.filter(name='add_class')
def add_class(value, arg):
    if isinstance(value, SafeString):
        # If it's already rendered, wrap it in a div with the new class
        return SafeString(f'<div class="{arg}">{value}</div>')
    else:
        # If it's a form field, add the class to its widget
        css_classes = value.field.widget.attrs.get('class', '')
        if (css_classes):
            css_classes = f"{css_classes} {arg}"
        else:
            css_classes = arg
        return value.as_widget(attrs={'class': css_classes})
    
@register.filter
def get_list_item(lst, index):
    try:
        return lst[index]
    except:
        return None

@register.filter
def add(value, arg):
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return value
    
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def to_decimal(value):
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return Decimal('0')
    
@register.filter
def precise_add(value1, value2):
    try:
        dec1 = Decimal(str(value1)) if value1 != '--' else Decimal('0')
        dec2 = Decimal(str(value2)) if value2 != '--' else Decimal('0')
        return (dec1 + dec2).quantize(Decimal('0.01'))
    except:
        return Decimal('0.00')

@register.filter(name='get')
def get(dictionary, key):
    """
    Gets a value from a dictionary using the given key.
    Usage: {{ dictionary|get:key }}
    """
    return dictionary.get(key, '')

@register.filter
def format_decimal(value):
    try:
        return "{:.2f}".format(float(value))
    except (TypeError, ValueError):
        return "0.00"
    
@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary safely
    """
    try:
        return dictionary.get(key, 0)
    except (AttributeError, TypeError):
        return 0

@register.filter
def format_hours(value):
    """
    Format hours with proper decimal places and handling of zero values
    """
    try:
        float_value = float(value)
        if float_value == 0:
            return '--'
        return '{:.2f}'.format(float_value)
    except (ValueError, TypeError):
        return '--'