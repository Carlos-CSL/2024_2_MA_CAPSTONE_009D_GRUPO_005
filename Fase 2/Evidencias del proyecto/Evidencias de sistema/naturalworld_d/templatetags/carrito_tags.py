# carrito_tags.py

from django import template
from ..carrito import Carrito

register = template.Library()

@register.simple_tag(takes_context=True)
def total_items_carrito(context):
    request = context['request']
    total_items = 0
    carrito = Carrito(request)
    for item in carrito.carrito.values():
        total_items += item['cantidad']
    return total_items
