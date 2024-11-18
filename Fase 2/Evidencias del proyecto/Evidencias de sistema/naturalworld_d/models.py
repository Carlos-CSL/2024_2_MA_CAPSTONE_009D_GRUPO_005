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
    
class Comentario(models.Model):
    usuario = models.CharField(max_length=100, default="Usuario Anónimo")
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, related_name="comentarios")
    visible = models.BooleanField(default=True)  # Campo para visibilidad

    def __str__(self):
        return f"Comentario de {self.usuario} en {self.producto}"


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



