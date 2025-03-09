from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Returns the value from a dictionary for the given key.
    Usage: {{ my_dict|get_item:key_variable }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key) 