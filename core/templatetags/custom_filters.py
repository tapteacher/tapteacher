from django import template

register = template.Library()

@register.filter(name='first_name')
def first_name(full_name):
    """Extract the first name from a full name string."""
    if not full_name:
        return ''
    return full_name.split()[0] if full_name.strip() else ''
