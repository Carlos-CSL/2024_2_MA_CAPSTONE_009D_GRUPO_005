import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from .models import Producto, Perfil
from django.utils.translation import gettext_lazy as _

class RegistroForm(UserCreationForm):
    nombre = forms.CharField(max_length=30, required=True, help_text='Nombre',widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellido = forms.CharField(max_length=30, required=True, help_text='Apellido',widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(max_length=254, required=True, help_text='Correo electrónico',widget=forms.TextInput(attrs={'class': 'form-control'}))
    rut = forms.CharField(max_length=12, required=True, help_text='RUT en formato XX.XXX.XXX-Y',widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'Formato 00.000.000-0'}))
    numero_telefono = forms.CharField(max_length=15, required=True, help_text='Número de Teléfono',widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'Formato 9 0000 0000' }))
    password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label='Confirmar Contraseña',widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('username', 'nombre', 'apellido', 'email', 'rut', 'numero_telefono', 'password1', 'password2',)

        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'username': 'Nombre de usuario'
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return email

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if Perfil.objects.filter(rut=rut).exists():
            raise ValidationError("Este RUT ya está registrado.")
        return rut

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'nombre', 'imagen', 'precio', 'descripcion', 'peso',
            'altura', 'ancho', 'largo', 'tipo_producto', 'valor_declarado', 'stock'
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
            'tipo_producto': 'Tipo de Producto:',
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
            'tipo_producto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el tipo de producto',
                'id': 'tipo_producto',
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


def validate_rut(value):
    # Validar formato del RUT
    if not re.match(r'^\d{7,8}-[0-9Kk]$', value):
        raise ValidationError('El RUT debe tener el formato 12345678-9 o 12345678-K')

    # Validar dígito verificador
    rut, dv = value.split('-')
    rut = int(rut)
    dv = dv.upper()
    s = 1
    m = 0
    while rut > 0:
        s = (s + rut % 10 * (9 - m % 6)) % 11
        rut //= 10
        m += 1
    if (s > 0 and chr(s + 47) != dv) and (s == 0 and dv != 'K'):
        raise ValidationError('El RUT ingresado no es válido')


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Nombre'
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primer Apellido'}),
        label='Apellido'
    )
    email = forms.EmailField(
        required=True, 
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label='Correo Electrónico'
    )
    rut = forms.CharField(
        max_length=10, 
        required=True, 
        validators=[validate_rut],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sin puntos y con guion (Ej.: 21543567-1)'}),
        label='RUT'
    )
    celular = forms.CharField(
        max_length=9, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej.: 9 1234 5431', 'type': 'number'}),
        label='Número de celular'
    )
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'rut', 'celular', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'})
        }
        labels = {
            'username': 'Nombre de usuario'
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if UserProfile.objects.filter(rut=rut).exists():
            raise forms.ValidationError("Este RUT ya está registrado.")
        return rut

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        user_profile = UserProfile.objects.create(
            user=user,
            rut=self.cleaned_data['rut'],
            celular=self.cleaned_data['celular']
        )
        return user



