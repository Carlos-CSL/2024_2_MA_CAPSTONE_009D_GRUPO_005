from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db.models.signals import post_save
from django.dispatch import receiver

 
class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    imagen = models.ImageField(upload_to="productos", null=False)  # Cambiado si usas imágenes estáticas
    precio = models.DecimalField(max_digits=10, decimal_places=2)  # Añade este campo si no existe
    descripcion = models.TextField()
    peso = models.DecimalField(max_digits=5, decimal_places=2, help_text="Peso en kg")
    altura = models.IntegerField(help_text="Altura en cm")
    ancho = models.IntegerField(help_text="Ancho en cm")
    largo = models.IntegerField(help_text="Largo en cm")
    tipo_producto = models.CharField(max_length=100, default= 3)
    valor_declarado = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    stock = models.PositiveIntegerField(default=0)



    def precio_formateado(self):
        return "${:,.0f}".format(self.precio).replace(",", ".")  # Reemplaza la coma con un punto

    def __str__(self):
        return self.nombre

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rut = models.CharField(
        max_length=12,
        unique=True,
        verbose_name="RUT",
        validators=[
            RegexValidator(
                regex=r'^\d{1,2}\.\d{3}\.\d{3}-[0-9Kk]$',
                message='El RUT debe tener el formato XX.XXX.XXX-Y'
            )
        ]
    )
    numero_telefono = models.CharField(
        max_length=15,
        verbose_name="Número de Teléfono",
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='El número de teléfono debe tener entre 9 y 15 dígitos.'
            )
        ]
    )

    def __str__(self):
        return f"Perfil de {self.user.username}"
    
class Comentario(models.Model):
    usuario = models.CharField(max_length=100, default="Usuario Anónimo")
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, related_name="comentarios")
    visible = models.BooleanField(default=True)  # Campo para visibilidad

    def __str__(self):
        return f"Comentario de {self.usuario} en {self.producto}"



from django.contrib.auth.models import User  # Si usas autenticación de usuarios
import uuid
from django.contrib.auth.models import User
import uuid
from django.contrib.auth.models import User
from django.utils import timezone



class Pedido(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_orden = models.CharField(max_length=20, unique=True, blank=True)
    cliente = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado_pedido = models.CharField(max_length=40, default= "En Preparación")

    def save(self, *args, **kwargs):
        # Asegurar que fecha_creacion tenga un valor válido
        if not self.fecha_creacion:
            self.fecha_creacion = timezone.now()

        # Generar el número de orden si no existe
        if not self.numero_orden:
            fecha_formato = self.fecha_creacion.strftime('%Y%m%d')
            self.numero_orden = f"ORD-{fecha_formato}-{Pedido.objects.count() + 1:04d}"
        super().save(*args, **kwargs)


    def actualizar_stock_productos(self):
        """
        Reduce el stock de los productos asociados al pedido.
        """
        for pedido_producto in self.pedido_productos.all():
            producto = pedido_producto.producto
            if producto.stock >= pedido_producto.cantidad:
                producto.stock -= pedido_producto.cantidad
                producto.save()
            else:
                raise ValueError(f"Stock insuficiente para {producto.nombre}.")


class PedidoProducto(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)  # Precio por unidad del producto

    def __str__(self):
        return f"{self.producto} - {self.cantidad} unidades"



class Pago(models.Model):
    id_pago = models.CharField(max_length=100, unique=True)
    estado = models.CharField(max_length=50)
    detalle_estado = models.CharField(max_length=200, blank=True, null=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    pedido = models.OneToOneField(Pedido, on_delete=models.SET_NULL, null=True, blank=True)  # Relación con Pedido
    referencia_externa = models.CharField(max_length=255, blank=True, null=True)  # Nuevo campo
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.id_pago} - Estado {self.estado}"


from django.contrib.auth.models import User

from django.contrib.auth.models import User
from django.db import models
from django.db import models
from django.contrib.auth.models import User

class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    rut = models.CharField(max_length=12, null=True, blank=True)  # RUT es opcional
    email = models.EmailField()
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre} - {self.rut or 'Sin RUT'}"

    def get_info(self):
        return {
            "rut": self.rut,
            "nombre": self.nombre,
            "email": self.email,
            "user_id": self.user.id if self.user else None
        }


from naturalworld_d.models import Pedido
from uuid import uuid4

