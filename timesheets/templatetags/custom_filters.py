from django import template
from datetime import timedelta
from django.utils.safestring import SafeString


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
        if css_classes:
            css_classes = f"{css_classes} {arg}"
        else:
            css_classes = arg
        return value.as_widget(attrs={'class': css_classes})