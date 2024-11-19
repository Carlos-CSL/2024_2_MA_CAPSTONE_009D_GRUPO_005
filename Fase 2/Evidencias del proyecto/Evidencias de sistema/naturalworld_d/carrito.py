class Carrito:
    def __init__(self, request):
        self.request = request
        self.session = request.session

        # Verifica si el carrito existe en la sesión
        carrito = self.session.get('carrito')

        if not carrito:
            carrito = self.session['carrito'] = {}
        self.carrito = carrito

    def add(self, producto):
        producto_id = str(producto.id)
        cantidad_actual = self.carrito.get(producto_id, {}).get('cantidad', 0)

        # Depuración: muestra el stock y cantidad actual en el carrito
        print(f"Intentando añadir producto {producto.nombre} - ID: {producto_id}")
        print(f"Stock disponible: {producto.stock}, Cantidad en carrito: {cantidad_actual}")

        # Verifica si hay suficiente stock para añadir el producto
        if producto.stock >= cantidad_actual + 1:
            if producto_id not in self.carrito:
                self.carrito[producto_id] = {
                    'producto_id': producto.id,
                    'nombre': producto.nombre,
                    'precio': str(producto.precio),
                    'cantidad': 1,
                    'peso': str(producto.peso),
                    'largo': str(producto.largo),
                    'ancho': str(producto.ancho),
                    'alto': str(producto.altura),
                }
            else:
                # Incrementa la cantidad si el producto ya está en el carrito
                self.carrito[producto_id]['cantidad'] += 1
            self.save()
            print(f"Producto {producto.nombre} añadido correctamente al carrito.")
            return True
        else:
            print(f"No se pudo añadir el producto {producto.nombre}: Stock insuficiente.")
            return False

    def remove(self, producto):
        producto_id = str(producto.id)
        if producto_id in self.carrito:
            del self.carrito[producto_id]
            self.save()

    def decrement(self, producto):
        producto_id = str(producto.id)
        if producto_id in self.carrito:
            self.carrito[producto_id]['cantidad'] -= 1
            if self.carrito[producto_id]['cantidad'] <= 0:
                self.remove(producto)
            else:
                self.save()

    def clear(self):
        self.session['carrito'] = {}
        self.save()

    def save(self):
        self.session.modified = True

    def total(self):
        """
        Calcula el total del carrito sumando los precios multiplicados por las cantidades.
        """
        total = 0
        for item in self.carrito.values():
            total += float(item['precio']) * item['cantidad']
        return total

    def total_items(self):
        """
        Devuelve el número total de artículos en el carrito.
        """
        total_items = 0
        for item in self.carrito.values():
            total_items += item['cantidad']
        return total_items

    def limpiar(self):
        """
        Limpia el carrito, eliminando todos los productos.
        """
        self.session['carrito'] = {}
        self.session.modified = True
