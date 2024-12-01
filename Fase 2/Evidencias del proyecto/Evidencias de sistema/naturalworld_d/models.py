# shipping/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import re
from django.conf import settings
from django.db import models, transaction
from decimal import Decimal
# === VALIDADORES ===

def validar_rut(value):
    """
    Valida que el RUT chileno cumpla con el formato correcto.
    """
    pattern = r'^\d{7,8}-[\dkK]$'
    if not re.match(pattern, value):
        raise ValidationError('RUT inválido')

phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Número de teléfono inválido. Debe tener entre 9 y 15 dígitos."
)

# === MODELOS ===

# === MODELO DE PRODUCTOS ===
class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    imagen = models.ImageField(upload_to="productos", null=False) 
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField()
    peso = models.DecimalField(max_digits=5, decimal_places=2, help_text="Peso en kg")
    altura = models.IntegerField(help_text="Altura en cm")
    ancho = models.IntegerField(help_text="Ancho en cm")
    largo = models.IntegerField(help_text="Largo en cm")
    
    TIPO_PRODUCTO_CHOICES = [
        ('tipo1', 'Tipo 1'),
        ('tipo2', 'Tipo 2'),
        # Agrega más opciones según sea necesario
    ]
    tipo_producto = models.CharField(max_length=100, choices=TIPO_PRODUCTO_CHOICES, default='tipo1')
    valor_declarado = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Valor declarado del producto"
    )
    stock = models.PositiveIntegerField(default=0)

    def precio_formateado(self):
        return "${:,.0f}".format(self.precio).replace(",", ".")

    def __str__(self):
        return self.nombre

# === MODELO DE CLIENTES ===
class Cliente(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cliente'
    )
    rut = models.CharField(
        max_length=12,
        null=True,
        blank=True,
        validators=[validar_rut],
        help_text="Formato: 12345678-9"
    )
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        validators=[phone_regex],
        help_text="Formato: +569XXXXXXXX"
    )

    def __str__(self):
        return f"{self.nombre} - {self.rut or 'Sin RUT'}"

    def get_info(self):
        return {
            "rut": self.rut,
            "nombre": self.nombre,
            "email": self.email,
            "telefono": self.telefono,
            "user_id": self.user.id if self.user else None
        }

    @property
    def username(self):
        return self.nombre

# === MODELO DE DIRECCIONES ===
class Direccion(models.Model):
    api_address_id = models.IntegerField(null=True, blank=True)
    county_coverage_code = models.CharField(max_length=4)  # Código de cobertura de la dirección
    street_name = models.CharField(max_length=100)         # Ajustado a 100
    street_number = models.CharField(max_length=10, null=True, blank=True)  # Ajustado a 10
    supplement = models.CharField(max_length=255, null=True, blank=True)
    comuna = models.CharField(max_length=100, default="Desconocido")
    address_type = models.CharField(max_length=4)  # `DEST` o `DEV`
    delivery_on_commercial_office = models.BooleanField(default=False)
    commercial_office_id = models.IntegerField(null=True, blank=True)
    observation = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.street_name} {self.street_number}, {self.county_coverage_code}"

# === MODELO DE CONTACTOS ===
class Contacto(models.Model):
    CONTACT_TYPE_CHOICES = [
        ('R', 'Remitente'),
        ('D', 'Destinatario'),
    ]
    name = models.CharField(max_length=100)
    phone_number = models.CharField(validators=[phone_regex], max_length=15)
    email = models.EmailField()
    contact_type = models.CharField(max_length=1, choices=CONTACT_TYPE_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.get_contact_type_display()})"

# === MODELO DE PEDIDOS ===
# naturalworld_d/models.py

from django.db import models
from django.core.exceptions import ValidationError
import uuid

class Pedido(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_orden = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, null=True, blank=True)
    direccion = models.ForeignKey(
        'Direccion', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='pedidos',
        help_text="Dirección asociada al pedido"
    )
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Campos requeridos por la API de Chilexpress
    customer_card_number = models.CharField(
        max_length=12,
        default='18578680',
        help_text="Número de Tarjeta Cliente Chilexpress (TCC). TCC pruebas = 18578680",
        verbose_name="Customer Card Number"
    )  # Obligatorio
    label_type = models.CharField(
        max_length=4,
        choices=[
            ('0', 'Solo Datos'),
            ('1', 'EPL Impresora Zebra + Datos'),
            ('2', 'Imagen en Binario + Datos'),
        ],
        default='2',
        help_text="Tipo de etiqueta; 0 = Solo Datos;1 = EPL Impresora Zebra + Datos;2 = Imagen en Binario + Datos",
        verbose_name="Label Type"
    )  # Obligatorio
    county_of_origin_coverage_code = models.CharField(
        max_length=4,
        help_text="Código de cobertura de origen obtenido por la API Consultar Coberturas",
        verbose_name="County of Origin Coverage Code",
        default='PUDA'  # Valor predeterminado
    )

    estado = models.CharField(
        max_length=20,
        default='pendiente',
    )
    estado_envio = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )
    numero_seguimiento = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )
    servicio_cotizado = models.IntegerField(null=True, blank=True)
    respuesta_envio = models.JSONField(null=True, blank=True)

    # Campos integrados de TransportOrderHeader
    certificate_number = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Número de certificado, si no se ingresa se creará uno nuevo"
    )
    marketplace_rut = models.CharField(
        max_length=15,
        default='96756430',  # Valor de prueba predeterminado
        help_text="Rut asociado al Marketplace sin puntos ni dígito verificador. RUT pruebas = 96756430",
        verbose_name="Marketplace RUT"
    )
    seller_rut = models.CharField(
        max_length=15,
        default='96756430',  # Valor de prueba predeterminado
        help_text="Rut asociado al Vendedor sin puntos ni dígito verificador. RUT pruebas = 96756430",
        verbose_name="Seller RUT"
    )

    def save(self, *args, **kwargs):
        # Asegurarse de que 'fecha_creacion' esté definida
        if not self.fecha_creacion:
            self.fecha_creacion = timezone.now()

        # Verificar si el número de orden ya está generado
        if not self.numero_orden:
            try:
                fecha_formato = self.fecha_creacion.strftime('%Y%m%d')
                ultimo_pedido = Pedido.objects.filter(
                    fecha_creacion__date=self.fecha_creacion.date()
                ).count() + 1
                self.numero_orden = f"ORD-{fecha_formato}-{ultimo_pedido:04d}"
            except Exception as e:
                raise ValueError(f"Error al generar 'numero_orden': {e}")

        super().save(*args, **kwargs)

    def clean(self):
        """
        Validaciones adicionales antes de guardar.
        """
        if not self.county_of_origin_coverage_code:
            self.county_of_origin_coverage_code = 'PUDA'  # Asignar un valor predeterminado si no lo tiene

        # Validar que los RUTs predeterminados no se usen en producción
        if self.marketplace_rut == '96756430' or self.seller_rut == '96756430':
            if not settings.DEBUG:  # Solo permitir en modo DEBUG
                raise ValidationError("Los RUTs de prueba no deben usarse en producción.")

        super().clean()

    def __str__(self):
        return f"Pedido {self.numero_orden} - Cliente {self.cliente} - Estado {self.estado}"

    @property
    def peso_total(self):
        """
        Calcula el peso total de los productos asociados al pedido.
        """
        return sum(
            detalle.cantidad * detalle.peso_unitario for detalle in self.detalles_pedido.all()
        )


from django.db import models
from decimal import Decimal

class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        'Pedido',
        on_delete=models.CASCADE,
        related_name='detalles_pedido'
    )
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    peso_unitario = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    @property
    def subtotal(self):
        """
        Calcula el subtotal del producto dentro del pedido.
        Maneja casos donde 'cantidad' o 'precio_unitario' puedan ser None.
        """
        cantidad = self.cantidad if self.cantidad is not None else 0
        precio_unitario = self.precio_unitario if self.precio_unitario is not None else Decimal('0.00')
        return cantidad * precio_unitario

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} para {self.pedido.numero_orden}"

    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para actualizar el stock del producto asociado.
        - Al crear un nuevo DetallePedido, resta la cantidad del stock.
        - Al actualizar un DetallePedido existente, ajusta el stock en base a la diferencia de cantidad.
        """
        with transaction.atomic():
            if self.pk:
                # DetallePedido existente: actualizar stock basado en la diferencia de cantidad
                original = DetallePedido.objects.select_for_update().get(pk=self.pk)
                cantidad_diff = self.cantidad - original.cantidad
            else:
                # Nuevo DetallePedido: restar la cantidad directamente
                cantidad_diff = self.cantidad

            if cantidad_diff > 0:
                # Incremento en la cantidad solicitada
                if self.producto.stock < cantidad_diff:
                    raise ValueError(
                        f"No hay suficiente stock para {self.producto.nombre}. "
                        f"Stock disponible: {self.producto.stock}, solicitado adicional: {cantidad_diff}."
                    )
                self.producto.stock -= cantidad_diff
            elif cantidad_diff < 0:
                # Reducción en la cantidad solicitada
                self.producto.stock -= cantidad_diff  # Resta un negativo = suma

            # Validar que el stock no sea negativo
            if self.producto.stock < 0:
                raise ValueError(
                    f"El stock del producto {self.producto.nombre} no puede ser negativo."
                )

            # Guardar los cambios en el producto
            self.producto.save()

            # Guardar los cambios en el DetallePedido
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Sobrescribe el método delete para restaurar el stock del producto cuando
        un DetallePedido es eliminado.
        """
        with transaction.atomic():
            # Restaurar el stock del producto
            self.producto.stock += self.cantidad
            self.producto.save()

            # Eliminar el DetallePedido
            super().delete(*args, **kwargs)



# === MODELO DE PAQUETES DE ENVÍO ===
class PaqueteEnvio(models.Model):
    pedido = models.ForeignKey(
        'Pedido', 
        on_delete=models.CASCADE, 
        related_name='paquetes_envio'
    )
    peso = models.DecimalField(max_digits=10, decimal_places=2, help_text="Peso en kg")
    altura = models.IntegerField(help_text="Altura en cm")
    ancho = models.IntegerField(help_text="Ancho en cm")
    largo = models.IntegerField(help_text="Largo en cm")
    servicio_entrega_codigo = models.IntegerField(help_text="Código del servicio de entrega")
    product_code = models.IntegerField(
        choices=[
            (1, 'Documento'),
            (3, 'Encomienda'),
        ],
        help_text="Código del tipo de producto a enviar; 1 = Documento, 3 = Encomienda"
    )
    referencia_envio = models.CharField(
        max_length=150, 
        unique=True, 
        help_text="Referencia única para el envío"
    )
    referencia_grupo = models.CharField(
        max_length=150, 
        help_text="Referencia para el grupo de envíos"
    )
    contenido_declarado = models.IntegerField(
        choices=[
            (1, 'Artículos Personales'),
            (10000331, 'Celular'),
            (2, 'Educación'),
            (4, 'Vestuario'),
            (5, 'Otros'),
            (7, 'Tecnología'),
        ],
        null=True,
        blank=True,
        help_text="Tipo de producto enviado: 1 = Artículos Personales, 10000331 = Celular, 2 = Educación, 4 = Vestuario, 5 = Otros, 7 = Tecnología"
    )
    valor_declarado = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Valor declarado del producto"
    )
    # Si `receivableAmountInDelivery` es un monto, usa DecimalField; si es booleano, usa BooleanField
    receivable_amount_in_delivery = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Monto a cobrar, en caso que el cliente tenga habilitada esta opción."
    )

    # Relaciones ManyToMany con Direccion y Contacto
    addresses = models.ManyToManyField('Direccion', related_name='paquetes_envio', blank=True)
    contacts = models.ManyToManyField('Contacto', related_name='paquetes_envio', blank=True)

    def save(self, *args, **kwargs):
        # Generar referencias únicas si no están definidas
        if not self.referencia_envio:
            self.referencia_envio = f"{self.pedido.numero_orden}-{uuid.uuid4().hex[:6]}"
        if not self.referencia_grupo:
            self.referencia_grupo = f"GRUPO-{self.pedido.numero_orden}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Paquete {self.referencia_envio} para Pedido {self.pedido.numero_orden}"

    def clean(self):
        # Validaciones adicionales
        errors = {}
        if not self.servicio_entrega_codigo:
            errors['servicio_entrega_codigo'] = 'El código del servicio de entrega es obligatorio.'
        if not self.referencia_envio:
            errors['referencia_envio'] = 'La referencia de envío es obligatoria.'
        if not self.referencia_grupo:
            errors['referencia_grupo'] = 'La referencia de grupo es obligatoria.'
        if not self.product_code:
            errors['product_code'] = 'El código del producto es obligatorio.'
        if not self.addresses.exists():
            errors['addresses'] = 'Se debe proporcionar al menos una dirección.'
        if not self.contacts.exists():
            errors['contacts'] = 'Se debe proporcionar al menos un contacto.'
        if not self.peso:
            errors['peso'] = 'El peso del paquete es obligatorio.'
        if not self.altura:
            errors['altura'] = 'La altura del paquete es obligatorio.'
        if not self.ancho:
            errors['ancho'] = 'El ancho del paquete es obligatorio.'
        if not self.largo:
            errors['largo'] = 'El largo del paquete es obligatorio.'
        
        if errors:
            raise ValidationError(errors)

# === MODELO DE ENVÍOS GENERADOS ===
class EnvioGenerado(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('generado', 'Generado'),
        # Puedes agregar más estados si los necesitas
        ('en_transito', 'En Tránsito'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    pedido = models.OneToOneField('Pedido', on_delete=models.CASCADE, related_name='envio')
    numero_seguimiento = models.CharField(
        max_length=100,
        help_text="Número de seguimiento del envío",
        db_index=True
    )
    etiqueta = models.FileField(
        upload_to='etiquetas/',
        null=True,
        blank=True,
        help_text="Etiqueta generada por Chilexpress"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
    )
    fecha_generacion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Envío {self.numero_seguimiento} - {self.get_estado_display()}"

# === MODELO DE PAGOS ===
class Pago(models.Model):
    id_pago = models.CharField(max_length=100, unique=True)
    estado = models.CharField(max_length=50)
    detalle_estado = models.CharField(max_length=200, blank=True, null=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    pedido = models.ForeignKey('Pedido', on_delete=models.CASCADE, related_name='pagos')
    referencia_externa = models.CharField(max_length=255, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.id_pago} - Estado {self.estado}"

# === MODELO DE COMENTARIOS ===
class Comentario(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    producto = models.ForeignKey(
        'Producto', on_delete=models.CASCADE, related_name="comentarios"
    )
    visible = models.BooleanField(default=True)  # Campo para visibilidad

    def __str__(self):
        return f"Comentario de {self.usuario.username if self.usuario else 'Usuario Anónimo'} en {self.producto.nombre}"

# === MODELO INTERMEDIO PARA PAQUETE Y DETALLE PEDIDO (Opcional) ===
class PaqueteDetallePedido(models.Model):
    paquete_envio = models.ForeignKey(PaqueteEnvio, on_delete=models.CASCADE)
    detalle_pedido = models.ForeignKey(DetallePedido, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.cantidad} x {self.detalle_pedido.producto.nombre} en {self.paquete_envio.referencia_envio}"

from django.db import models
from django.utils.timezone import now
class TransportOrder(models.Model):
    pedido = models.OneToOneField(
        'Pedido',
        on_delete=models.CASCADE,
        related_name='transport_order',
        help_text="Pedido asociado a esta orden de transporte"
    )
    transport_order_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Número de la Orden de Transporte generado por Chilexpress"
    )
    certificate_number = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Número del certificado asociado a la orden de transporte"
    )
    label_type = models.CharField(
        max_length=4,
        choices=[
            ('0', 'Solo Datos'),
            ('1', 'EPL Impresora Zebra + Datos'),
            ('2', 'Imagen en Binario + Datos'),
        ],
        default='2',
        help_text="Tipo de etiqueta; 0 = Solo Datos, 1 = EPL Zebra + Datos, 2 = Imagen Binaria"
    )
    estado = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente'),
            ('generado', 'Generado'),
            ('en_transito', 'En Tránsito'),
            ('entregado', 'Entregado'),
        ],
        default='pendiente',
        help_text="Estado actual de la orden de transporte"
    )
    etiqueta = models.FileField(
        upload_to='etiquetas/',
        null=True,
        blank=True,
        help_text="Etiqueta generada por Chilexpress para el envío"
    )
    respuesta_api = models.JSONField(
        null=True,
        blank=True,
        help_text="Respuesta completa de la API al generar la orden de transporte"
    )
    fecha_generacion = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha en que se generó la orden"
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        help_text="Última vez que se actualizó la información"
    )

    def __str__(self):
        return f"TransportOrder {self.transport_order_number} - Estado {self.estado}"

from django.db import models

