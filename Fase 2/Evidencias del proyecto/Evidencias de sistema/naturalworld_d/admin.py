# admin.py
from django.contrib import admin
from .models import Producto, Perfil

class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio')
    search_fields = ('nombre',)

admin.site.register(Producto, ProductoAdmin)

admin.site.register(Perfil)

