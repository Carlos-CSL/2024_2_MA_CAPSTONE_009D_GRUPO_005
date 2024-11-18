# context_processors.py

from .carrito import Carrito

def importe_total_carrito(request):
    total_items = 0
    if request.user.is_authenticated or True:
        carrito = Carrito(request)
        for item in carrito.carrito.values():
            total_items += item['cantidad']
    return {'total_items_carrito': total_items}


def total_items_carrito(request):
    total_items = sum(item['cantidad'] for item in Carrito(request).carrito.values())
    return {'total_items_carrito': total_items}