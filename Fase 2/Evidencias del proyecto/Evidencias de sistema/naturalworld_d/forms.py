from django import forms
from .models import Cliente, Producto
import re
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['rut', 'nombre', 'email']  # Incluye los campos que deseas

# shipping/forms.py

from django import forms
from .models import Pedido, PaqueteEnvio
from django.forms import modelformset_factory

class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['cliente', 'direccion', 'customer_card_number', 'label_type']
        # Agrega otros campos si es necesario

class PaqueteEnvioForm(forms.ModelForm):
    class Meta:
        model = PaqueteEnvio
        fields = [
            'peso', 'altura', 'ancho', 'largo',
            'servicio_entrega_codigo', 'referencia_envio',
            'referencia_grupo', 'contenido_declarado',
            'valor_declarado', 'receivable_amount_in_delivery'
        ]

PaqueteEnvioFormSet = modelformset_factory(
    PaqueteEnvio,
    form=PaqueteEnvioForm,
    extra=1,  # Número de formularios adicionales que deseas mostrar
    can_delete=True  # Permite eliminar paquetes si es necesario
)

class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}),
        label=_("Correo electrónico")
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
        label=_("Contraseña")
    )

    class Meta:
        model = User
        fields = ['username', 'password']


User = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}),
        label=_("Correo electrónico")
    )
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
        label=_("Nombre")
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
        label=_("Apellido")
    )
    password1 = forms.CharField(
        label=_("Contraseña"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
    )
    password2 = forms.CharField(
        label=_("Confirmar Contraseña"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar Contraseña'}),
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email'].lower()  # Asigna el email al username
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
        return user

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'nombre', 'imagen', 'precio', 'descripcion', 'peso',
            'altura', 'ancho', 'largo', 'valor_declarado', 'stock'
        ]
        labels = {
            'nombre': 'Nombre:',
            'imagen': 'Imagen:',
            'precio': 'Precio:',
            'descripcion': 'Descripción:',
            'peso': 'Peso (kg):',
            'altura': 'Altura (cm):',
            'ancho': 'Ancho (cm):',
            'largo': 'Largo (cm):',
            'valor_declarado': 'Valor Declarado:',
            'stock': 'Stock:',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre del producto',
                'id': 'nombre',
                'required': 'required'
            }),
            'imagen': forms.FileInput(attrs={
                'class': 'form-control',
                'id': 'imagen',
                'required': 'required'
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el precio',
                'id': 'precio',
                'min': '0',
                'step': '0.01',
                'required': 'required'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese una descripción para el producto',
                'id': 'descripcion',
                'required': 'required'
            }),
            'peso': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el peso en kg',
                'id': 'peso',
                'min': '0',
                'step': '0.01',
                'required': 'required'
            }),
            'altura': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese la altura en cm',
                'id': 'altura',
                'min': '0',
                'required': 'required'
            }),
            'ancho': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el ancho en cm',
                'id': 'ancho',
                'min': '0',
                'required': 'required'
            }),
            'largo': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el largo en cm',
                'id': 'largo',
                'min': '0',
                'required': 'required'
            }),
            'valor_declarado': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el valor declarado',
                'id': 'valor_declarado',
                'min': '0',
                'step': '0.01',
                'required': 'required'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el stock disponible',
                'id': 'stock',
                'min': '0',
                'required': 'required'
            }),
        }

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is None:
            raise forms.ValidationError("Este campo es obligatorio.")
        if precio < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")
        return precio
