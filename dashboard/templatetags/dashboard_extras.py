from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to access a dictionary value by key.
    
    Usage:
        {{ dict_value|get_item:key }}
    """
    return dictionary.get(key, 0) 