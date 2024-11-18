from django.urls import path
from . import views
from .views import pag_productos, login_view, admin_productos, admin_add_producto, admin_mod_producto, delete_producto
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', views.index, name='index'),
    path('producto/<int:producto_id>/', views.producto_detalle, name='producto_detalle'),
    path('producto/<int:producto_id>/crear-preferencia/', views.crear_preferencia, name="crear_preferencia"),
    path('producto/webhook/', views.webhook, name='webhook'),
    path('producto/<int:producto_id>/comentar/', views.agregar_comentario, name="agregar_comentario"),
    path('comentario/<int:comentario_id>/eliminar/', views.eliminar_comentario, name="eliminar_comentario"),
    path('consultar-calles/', views.buscar_calle, name='buscar_calle'),
    path('cotizar-envio/<int:producto_id>/', views.cotizar_envio_view, name='cotizar_envio'),
    path('cobertura-real/', views.cobertura_real_view, name='cobertura_real'),
    path('consultar-calle-numeracion/', views.consultar_calle_numeracion_view, name='consultar_calle_numeracion'),
    path('georreferenciar-direccion/', views.georreferenciar_direccion_view, name='georreferenciar_direccion'),
    path('producto/<int:producto_id>/seleccionar-direccion/', views.seleccionar_direccion, name='seleccionar_direccion'),
    path('producto/<int:producto_id>/calcular-envio/', views.calcular_envio, name='calcular_envio'),
    path('producto/<int:producto_id>/pago/<int:costo_envio>/<int:costo_total>/', views.pago, name='pago'),
    path('producto/<int:producto_id>/crear-preferencia/', views.crear_preferencia, name='crear_preferencia'),
    path('producto/<int:producto_id>/generar-envio/', views.generar_envio_view, name='generar_envio'),
    path('producto/webhook/', views.webhook, name='webhook'),
    path('crear_preferencia/', views.crear_preferencia, name='crear_preferencia'),
    path('agregar_al_carrito/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('ver_carrito/', views.ver_carrito, name='ver_carrito'),
    path('eliminar_del_carrito/<int:producto_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('restar_producto/<int:producto_id>/', views.restar_producto, name='restar_producto'),
    path('limpiar_carrito/', views.limpiar_carrito, name='limpiar_carrito'),
    path('checkout/', views.checkout, name='checkout'),
    path('productos/', views.listar_productos, name='listar_productos'),
    path('pago/', views.pago, name='pago'),
    path('pag_productos/', views.pag_productos, name='pag_productos'),
    path('buscar/', views.buscar_producto, name='buscar_producto'),
    path('login/', login_view, name='login'),
    path('admin_productos/', admin_productos, name='admin_productos'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('admin_add_producto/', admin_add_producto, name='admin_add_producto'),
    path('delete_producto/<id>', delete_producto, name="delete_producto"),
    path('admin_mod_producto/<id>', admin_mod_producto, name="admin_mod_producto"),
    path('registro/', views.registro, name='registro'),

]

