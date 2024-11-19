# admin.py
from django.contrib import admin
from .models import Producto



from django.contrib import admin
from .models import Producto

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'stock', 'tipo_producto', 'peso', 'valor_declarado')  # Campos a mostrar en la lista
    search_fields = ('nombre', 'tipo_producto', 'descripcion')  # Campos de búsqueda
    list_filter = ('tipo_producto', 'stock')  # Filtros por tipo de producto y stock
    ordering = ('nombre',)  # Ordenar por nombre de producto ascendente
    readonly_fields = ('valor_declarado',)  # Campo de solo lectura si no es editable
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'imagen', 'precio', 'descripcion', 'tipo_producto')
        }),
        ('Dimensiones y Peso', {
            'fields': ('peso', 'altura', 'ancho', 'largo')
        }),
        ('Otros Detalles', {
            'fields': ('stock', 'valor_declarado')
        }),
    )

    def imagen_preview(self, obj):
        """
        Muestra una vista previa de la imagen si es un campo URL.
        """
        return f'<img src="{obj.imagen}" width="100" height="100" />' if obj.imagen else "Sin imagen"
    imagen_preview.short_description = 'Vista previa'
    imagen_preview.allow_tags = True


from django.contrib import admin
from .models import Pedido, PedidoProducto

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'numero_orden', 'cliente', 'total', 'fecha_creacion', 'estado_pedido')  # Campos visibles en la lista
    search_fields = ('numero_orden', 'cliente__username', 'cliente__email')  # Permite búsqueda por número de orden y cliente
    list_filter = ('fecha_creacion',)  # Filtros para la lista
    ordering = ('-fecha_creacion',)  # Orden descendente por fecha de creación
    readonly_fields = ('id', 'fecha_creacion')  # Campos que no se pueden editar directamente
    fieldsets = (
        ('Información del Pedido', {
            'fields': ('id', 'numero_orden', 'cliente', 'total', 'fecha_creacion')
        }),
        ('Productos en el Pedido', {
            'fields': ('productos',),  # Mostrar productos relacionados
        }),
    )

    def productos(self, obj):
        """
        Muestra los productos relacionados con el pedido.
        """
        return ", ".join([str(pp.producto) for pp in obj.detalles.all()])
    productos.short_description = 'Productos en el Pedido'

@admin.register(PedidoProducto)
class PedidoProductoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'producto', 'cantidad', 'precio_unitario')  # Campos visibles
    search_fields = ('pedido__numero_orden', 'producto__nombre')  # Búsqueda por pedido y producto
    list_filter = ('pedido',)  # Filtros
