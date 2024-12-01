# naturalworld_d/admin.py
from django.contrib import admin
from .models import (
    Producto,
    Cliente,
    Direccion,
    Contacto,
    Pedido,
    DetallePedido,
    PaqueteEnvio,
    EnvioGenerado,
    Pago,
    Comentario,
    PaqueteDetallePedido,
    TransportOrder,  # Incluyendo TransportOrder
)

# === Inlines ===

class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 1
    readonly_fields = ('subtotal',)  # Muestra 'subtotal' como campo de solo lectura

class PaqueteDetallePedidoInline(admin.TabularInline):
    model = PaqueteDetallePedido
    extra = 1

class PaqueteEnvioInline(admin.TabularInline):
    model = PaqueteEnvio
    extra = 0
    show_change_link = True

# === Admin Models ===

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('numero_orden', 'cliente', 'total', 'estado', 'estado_envio', 'numero_seguimiento')
    search_fields = ('numero_orden', 'cliente__nombre', 'cliente__email')
    list_filter = ('estado', 'estado_envio', 'fecha_creacion')
    readonly_fields = ('peso_total', 'fecha_creacion', 'numero_seguimiento', 'respuesta_envio')  # Agregados campos adicionales como solo lectura
    date_hierarchy = 'fecha_creacion'  # Para facilitar la navegación por fechas en el administrador

    inlines = [DetallePedidoInline, PaqueteEnvioInline]

    fieldsets = (
        (None, {
            'fields': ('numero_orden', 'cliente', 'total', 'fecha_creacion')
        }),
        ('Información de Envío', {
            'fields': (
                'customer_card_number',
                'label_type',
                'county_of_origin_coverage_code',
                'certificate_number',
                'marketplace_rut',
                'seller_rut',
                'estado',
                'estado_envio',
                'numero_seguimiento',
                'servicio_cotizado',
                'respuesta_envio',
                'peso_total',
            )
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Asegura que ciertos campos sean de solo lectura dependiendo del estado del objeto.
        """
        readonly_fields = list(self.readonly_fields)
        if obj and obj.estado_envio == 'generado':
            readonly_fields += ['estado', 'estado_envio', 'numero_seguimiento']
        return readonly_fields

@admin.register(PaqueteEnvio)
class PaqueteEnvioAdmin(admin.ModelAdmin):
    list_display = ('referencia_envio', 'pedido', 'servicio_entrega_codigo', 'product_code', 'get_estado_envio')
    search_fields = ('referencia_envio', 'pedido__numero_orden', 'numero_seguimiento')
    list_filter = ('servicio_entrega_codigo', 'product_code')
    inlines = [PaqueteDetallePedidoInline]
    filter_horizontal = ('addresses', 'contacts')
    fieldsets = (
        (None, {
            'fields': ('pedido', 'referencia_envio', 'referencia_grupo')
        }),
        ('Dimensiones y Peso', {
            'fields': ('peso', 'altura', 'ancho', 'largo')
        }),
        ('Información del Servicio', {
            'fields': ('servicio_entrega_codigo', 'product_code', 'contenido_declarado', 'valor_declarado', 'receivable_amount_in_delivery')
        }),
        ('Relaciones', {
            'fields': ('addresses', 'contacts')
        }),
    )

    def get_estado_envio(self, obj):
        return obj.pedido.estado_envio if obj.pedido else 'N/A'
    get_estado_envio.short_description = 'Estado de Envío'

@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'producto', 'cantidad', 'precio_unitario', 'peso_unitario', 'display_subtotal')
    search_fields = ('pedido__numero_orden', 'producto__nombre')
    list_filter = ('pedido', 'producto')
    readonly_fields = ('subtotal',)

    def display_subtotal(self, obj):
        return obj.subtotal
    display_subtotal.short_description = 'Subtotal'

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'stock', 'tipo_producto')
    search_fields = ('nombre', 'descripcion')
    list_filter = ('tipo_producto',)

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'email', 'rut', 'telefono')
    search_fields = ('nombre', 'email', 'rut')
    list_filter = ('nombre',)

@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ('street_name', 'street_number', 'county_coverage_code', 'address_type')
    search_fields = ('street_name', 'street_number', 'county_coverage_code')
    list_filter = ('address_type', 'county_coverage_code')

@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'email', 'contact_type')
    search_fields = ('name', 'email', 'phone_number')
    list_filter = ('contact_type',)

@admin.register(EnvioGenerado)
class EnvioGeneradoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'numero_seguimiento', 'estado', 'fecha_generacion')
    search_fields = ('pedido__numero_orden', 'numero_seguimiento')
    list_filter = ('estado', 'fecha_generacion')

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id_pago', 'pedido', 'estado', 'monto', 'fecha_creacion')
    search_fields = ('id_pago', 'pedido__numero_orden', 'estado')
    list_filter = ('estado',)

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('producto', 'usuario', 'fecha', 'visible')
    search_fields = ('producto__nombre', 'usuario__username', 'texto')
    list_filter = ('visible', 'fecha')

@admin.register(PaqueteDetallePedido)
class PaqueteDetallePedidoAdmin(admin.ModelAdmin):
    list_display = ('paquete_envio', 'detalle_pedido', 'cantidad')
    search_fields = ('paquete_envio__referencia_envio', 'detalle_pedido__producto__nombre')
    list_filter = ('paquete_envio',)

# === TransportOrder ===

@admin.register(TransportOrder)
class TransportOrderAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'transport_order_number', 'certificate_number', 'estado', 'label_type', 'fecha_generacion')
    search_fields = ('pedido__numero_orden', 'transport_order_number')
    list_filter = ('estado', 'label_type', 'fecha_generacion')
    readonly_fields = ('fecha_generacion', 'fecha_actualizacion', 'respuesta_api')
    fieldsets = (
        (None, {
            'fields': ('pedido', 'transport_order_number', 'certificate_number', 'label_type')
        }),
        ('Información de Estado', {
            'fields': ('estado', 'fecha_generacion', 'fecha_actualizacion')
        }),
        ('Detalles de la API', {
            'fields': ('respuesta_api',)
        }),
    )

