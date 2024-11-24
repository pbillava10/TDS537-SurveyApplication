from django import template

register = template.Library()

@register.filter
def dict_get(dictionary, key):
    """
    Custom filter to safely access dictionary values in Django templates.
    Usage: {{ dictionary|dict_get:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, "")
    return ""
