from django.shortcuts import render, get_object_or_404, redirect
from .models import Producto, Comentario
from django import template
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json
import mercadopago
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .utils import consultar_calles
from .utils import georreferenciar_direccion
from .utils import consultar_cobertura_real, cotizar_envio
from .utils import consultar_cobertura_real
from .models import  Pedido, Producto  # Importa los modelos necesarios
from .forms import ProductoForm, LoginForm, RegisterForm
from django.contrib.auth import authenticate, login
from django.views.decorators.cache import never_cache
from django.contrib.auth import views as auth_views


def pag_productos(request):
    productos = Producto.objects.all()  # Obtener todos los productos
    return render(request, 'productos.html', {'productos': productos})

def buscar_producto(request):
    query = request.GET.get('query', '')
    resultados = Producto.objects.filter(nombre__icontains=query) if query else []
    return render(request, 'resultados_busqueda.html', {'productos': resultados, 'query': query})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')  # Redirigir a la página principal u otra después del login
            else:
                messages.error(request, 'Correo o contraseña incorrectos.')
        else:
            messages.error(request, 'Información inválida.')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()  # Guarda el nuevo usuario
            # Especifica el backend de autenticación aquí
            login(request, user, backend='naturalworld_d.backends.EmailBackend')
            messages.success(request, 'Tu cuenta ha sido creada exitosamente.')
            return redirect('index')  # Redirige a la página principal o a la deseada
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = RegisterForm()
    return render(request, 'registration/registro.html', {'form': form})

@login_required
def mis_pedidos(request):
    """
    Vista para que el usuario autenticado pueda ver sus propios pedidos filtrados por email.
    """
    user_email = request.user.email  # Obtener el correo electrónico del usuario autenticado

    # Filtrar pedidos donde el correo electrónico del cliente coincide con el del usuario
    pedidos = Pedido.objects.filter(cliente__email=user_email).order_by('-fecha_creacion').prefetch_related('detalles_pedido__producto', 'paquetes_envio__addresses')

    context = {
        'pedidos': pedidos
    }

    return render(request, 'mis_pedidos.html', context)

@login_required
def admin_productos(request):
    producto = Producto.objects.all()
    datos = {
        'producto': producto
    }
    return render(request, 'admin_productos.html', datos)

@login_required
def admin_add_producto(request):                             
    if request.method == 'POST':
        producto_form = ProductoForm(request.POST, request.FILES)

        if producto_form.is_valid():
            producto_form.save()
            return redirect ('admin_productos')

    else:
        producto_form = ProductoForm()
    return render(request, 'admin_add_producto.html' ,{'producto_form': producto_form })

def delete_producto(request,id):
    producto = Producto.objects.get(id=id)
    producto.delete()
    return redirect('admin_productos')

@login_required
def admin_mod_producto(request, id):
    producto = Producto.objects.get(id=id)
    datos = {
        'form': ProductoForm(instance = producto)
    }
    if request.method=='POST':
        formulario = ProductoForm(data=request.POST, instance = producto)
        if formulario.is_valid():
            formulario.save()
            return redirect ('admin_productos')
        
    return render(request, 'admin_mod_producto.html', datos)

@login_required
def admin_pedidos(request):
    pedidos = Pedido.objects.all().order_by('-fecha_creacion') 
    datos = {
        'pedidos': pedidos 
    }
    return render(request, 'admin_pedidos.html', datos) 


def actualizar_estado_pedido(request, pedido_id):
    # Obtener el pedido o redirigir si no existe
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == "POST":
        nuevo_estado = request.POST.get('estado')

        # Validar que el nuevo estado es uno de los permitidos
        estados_validos = ['Pendiente', 'En Preparacion', 'Enviado', 'Cancelado', 'Pagado']
        if nuevo_estado not in estados_validos:
            messages.error(request, "Estado de pedido no válido.")
            return redirect('actualizar_estado_pedido', pedido_id=pedido_id)

        # Actualizar el estado del pedido
        pedido.estado = nuevo_estado
        pedido.save()
        messages.success(request, "Estado del pedido actualizado correctamente.")
        return redirect('admin_pedidos')  # Asegúrate de que 'admin_pedidos' está correctamente configurado

    return render(request, 'admin_pedidos.html', {'pedido': pedido})

# Registro de filtro para formateo de moneda en templates
register = template.Library()

@register.filter
def format_clp(value):
    try:
        return "${:,.0f} CLP".format(value)
    except ValueError:
        return value

# Vista principal de índice
def index(request):
    productos = Producto.objects.all()  # Obtener todos los productos
    return render(request, 'index.html', {'productos': productos})

# Vista de detalles del producto
def producto_detalle(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    comentarios = producto.comentarios.filter(visible=True)  # Mostrar solo comentarios visibles al usuario
    context = {
        'producto': producto,
        'comentarios': comentarios,
        'is_product_detail': True  # Variable para indicar que es la página de detalle del producto
    }
    return render(request, 'producto_detalle.html', context)

# Agregar un comentario
@require_POST
def agregar_comentario(request, producto_id):
    data = json.loads(request.body)
    texto = data.get("texto", "").strip()
    producto = get_object_or_404(Producto, id=producto_id)

    # Verificar que el texto no esté vacío
    if not texto:
        return JsonResponse({"success": False, "error": "El comentario no puede estar vacío."}, status=400)

    # Crear nuevo comentario
    nuevo_comentario = Comentario.objects.create(
        producto=producto,
        texto=texto,
        usuario=request.user.username if request.user.is_authenticated else "Usuario Anónimo"
    )
    return JsonResponse({
        "id": nuevo_comentario.id,
        "usuario": nuevo_comentario.usuario,
        "texto": nuevo_comentario.texto,
        "fecha": nuevo_comentario.fecha.strftime("%Y-%m-%d %H:%M:%S"),
        "success": True
    })

# Ocultar un comentario (solo para administradores)
@require_POST
@login_required
def eliminar_comentario(request, comentario_id):
    if request.user.is_staff:  # Solo permite ocultar a los administradores
        comentario = get_object_or_404(Comentario, id=comentario_id)
        comentario.visible = False  # Cambia la visibilidad en lugar de eliminar
        comentario.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Permisos insuficientes"})


#MERCADO PAGO APIIIIIIIIIIIIIII

import mercadopago
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Producto

# naturalworld_d/views.py

from django.shortcuts import render, get_object_or_404
from .models import Producto
import json
from django.http import JsonResponse
from .carrito import Carrito
import mercadopago

# views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import mercadopago
import json
from .carrito import Carrito

import mercadopago
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .carrito import Carrito  # Asegúrate de tener el módulo Carrito configurado

from django.shortcuts import get_object_or_404
from .models import Pedido
from django.shortcuts import get_object_or_404

from django.shortcuts import get_object_or_404


import uuid
from django.shortcuts import get_object_or_404
# Asegúrate de que no hay errores antes de esta línea
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Producto, Pedido, Pago
from .carrito import Carrito  # Asegúrate de que el archivo `carrito.py` esté en el mismo directorio
import json  # Correcto
import uuid  # Correcto
def crear_preferencia(request):
    if request.method == 'POST':
        sdk = mercadopago.SDK("APP_USR-7989794511721795-103003-30ce8ee651d7e12a6f9180d1369215df-2065223385")
        carrito = Carrito(request)

        # Verificar si ya existe un pedido único para esta sesión o cliente
        pedido_id = request.session.get('pedido_id')
        cliente = request.user if request.user.is_authenticated else None

        if pedido_id:
            try:
                pedido = Pedido.objects.get(id=pedido_id)
            except Pedido.DoesNotExist:
                pedido = None
        else:
            pedido = Pedido.objects.filter(cliente=cliente, total=0.0).first()

        if not pedido:
            pedido = Pedido.objects.create(cliente=cliente, total=0.0)
            request.session['pedido_id'] = str(pedido.id)

        try:
            data = json.loads(request.body)
            costo_envio = float(data.get('costo_envio', 0))
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({"error": "Costo de envío no válido"}, status=400)

        # Actualizar el total del pedido
        pedido.total = carrito.total() + costo_envio
        pedido.save()

        # Asociar todos los productos del carrito al mismo pedido
        for item in carrito.carrito.values():
            try:
                producto = Producto.objects.get(id=item['producto_id'])
                detalle_pedido, creado = DetallePedido.objects.get_or_create(
                    pedido=pedido,
                    producto=producto,
                    defaults={
                        'cantidad': item['cantidad'],
                        'precio_unitario': float(item['precio']),
                        'peso_unitario': float(producto.peso),
                    }
                )
                if not creado:
                    detalle_pedido.cantidad += item['cantidad']
                    detalle_pedido.save()
            except Producto.DoesNotExist:
                return JsonResponse({"error": f"Producto con ID {item['producto_id']} no encontrado"}, status=400)

        # Configurar preferencia de pago
        items = [
            {
                "title": item['nombre'],
                "quantity": item['cantidad'],
                "unit_price": float(item['precio'])
            }
            for item in carrito.carrito.values()
        ]

        if costo_envio > 0:
            items.append({
                "title": "Costo de Envío",
                "quantity": 1,
                "unit_price": costo_envio
            })

        preference_data = {
            "items": items,
            "back_urls": {
                "success": "https://f4a4-181-43-149-87.ngrok-free.app/confirmacion/",
                "failure": "https://f4a4-181-43-149-87.ngrok-free.app/failure/",
                "pending": "https://f4a4-181-43-149-87.ngrok-free.app/pending/"
            },
            "auto_return": "approved",
            "notification_url": "https://f4a4-181-43-149-87.ngrok-free.app/webhook/",
            "external_reference": f"pedido-{pedido.id}",
        }

        preference_response = sdk.preference().create(preference_data)
        if "response" in preference_response and "id" in preference_response["response"]:
            carrito.limpiar()
            return JsonResponse({"preference_id": preference_response["response"]["id"]})
        else:
            print("Error en la respuesta de Mercado Pago:", preference_response)
            return JsonResponse({"error": "Error al crear la preferencia"}, status=500)

    return JsonResponse({"error": "Método no permitido"}, status=405)

   

from .utils import consultar_calles, cotizar_envio

def buscar_calle(request):
    if request.method == 'POST':
        county_name = request.POST.get('countyName')
        street_name = request.POST.get('streetName')
        resultado = consultar_calles(county_name, street_name)

        if "error" in resultado:
            return render(request, 'template_a_mostrar.html', {'error': resultado["error"]})
        
        calles = resultado.get("streets", [])
        return render(request, 'consultar_calles.html', {'calles': calles})
    
    return render(request, 'consultar_calles.html')


def cotizar_envio_view(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        # Obtener comuna de destino ingresada por el usuario
        dest_county_name = request.POST.get('destCountyName')

        # Código de región y tipo de cobertura para la consulta de cobertura real
        region_code = 'RM'  # Región Metropolitana
        tipo_cobertura = 1   # Tipo de cobertura (1 para comunas)

        # Obtener el código de cobertura para el origen (comuna de "El Monte")
        resultado_cobertura_real_origen = consultar_cobertura_real(region_code, tipo_cobertura)
        origin_code = next(
            (area['countyCode'] for area in resultado_cobertura_real_origen if area['countyName'].upper() == "EL MONTE"),
            None
        )

        if not origin_code:
            return render(request, 'cotizar_envio.html', {
                'producto': producto,
                'error': "No se encontró el código de cobertura para la comuna de origen proporcionada."
            })

        # Obtener el código de cobertura para la comuna de destino
        resultado_cobertura_real_destino = consultar_cobertura_real(region_code, tipo_cobertura)
        destination_code = next(
            (area['countyCode'] for area in resultado_cobertura_real_destino if area['countyName'].upper() == dest_county_name.upper()),
            None
        )

        if not destination_code:
            return render(request, 'cotizar_envio.html', {
                'producto': producto,
                'error': "No se encontró el código de cobertura para la comuna de destino proporcionada."
            })

        # Preparar el paquete con valores predeterminados o los del producto
        package = {
            "weight": float(producto.peso) if producto.peso else 1.0,
            "height": int(producto.altura) if producto.altura else 1,
            "width": int(producto.ancho) if producto.ancho else 1,
            "length": int(producto.largo) if producto.largo else 1
        }
        product_type = int(producto.tipo_producto) if producto.tipo_producto else 3  # Encomienda por defecto
        declared_worth = int(producto.valor_declarado) if producto.valor_declarado else 0

        # Llamada a la API de Cotizador con solo los datos de cobertura y paquete
        resultado = cotizar_envio(origin_code, destination_code, package, product_type, declared_worth)
        resultado_cotizacion = resultado.get("data", {}).get("courierServiceOptions", [])

        # Filtrar solo las opciones "PRIORITARIO" y "EXPRESS"
        resultado_cotizacion_filtrado = [
            option for option in resultado_cotizacion 
            if option.get("serviceDescription") in ["PRIORITARIO", "EXPRESS"]
        ]

        if not resultado_cotizacion_filtrado:
            return render(request, 'cotizar_envio.html', {
                'producto': producto,
                'error': "No se encontraron opciones de envío disponibles para 'PRIORITARIO' o 'EXPRESS'."
            })

        # Mostrar resultados
        return render(request, 'cotizar_envio.html', {
            'producto': producto,
            'resultado_cotizacion': resultado_cotizacion_filtrado,
            'error': resultado.get("errors")
        })

    # Vista inicial sin cálculo
    return render(request, 'cotizar_envio.html', {'producto': producto})


from django.shortcuts import render
from .utils import consultar_cobertura_real

def cobertura_real_view(request):
    cobertura_areas = []  # Inicializa la lista vacía
    error = None  # Inicializa la variable de error

    # Verifica si el formulario se ha enviado
    if request.GET:
        region_code = request.GET.get('region_code', 'RM')  # Valor por defecto
        tipo_cobertura = request.GET.get('type', 0)         # Tipo de cobertura (0, 1 o 2)

        # Llamada a la función para consultar coberturas
        resultado = consultar_cobertura_real(region_code, tipo_cobertura)
        
        if "error" in resultado:
            # Si hay un error en el resultado
            error = resultado["error"]
        else:
            # Se asume que 'resultado' es una lista de áreas de cobertura
            cobertura_areas = resultado

    return render(request, 'consultar_cobertura.html', {
        'cobertura_areas': cobertura_areas,
        'error': error
    })


from django.shortcuts import render
from .utils import consultar_calles, consultar_numeracion

def consultar_calle_numeracion_view(request):
    resultado_numeracion = None
    error = None

    if request.method == 'POST':
        # Obtener los datos del formulario
        county_name = request.POST.get('countyName')
        street_name = request.POST.get('streetName')
        street_number = request.POST.get('streetNumber')  # Opcional

        # Paso 1: Llamada a la API de Consultar Calle para obtener el streetNameId
        calles_response = consultar_calles(county_name, street_name)

        # Validar y extraer el streetNameId de la respuesta de la API de Consultar Calle
        if "error" in calles_response:
            error = calles_response["error"]
        elif isinstance(calles_response, dict) and "streets" in calles_response:
            try:
                # Extraer el streetNameId de la primera calle encontrada
                street_name_id = calles_response["streets"][0]["streetId"]

                # Paso 2: Llamada a la API de Consultar Numeración usando el streetNameId y streetNumber
                numeracion_response = consultar_numeracion(street_name_id, street_number)

                # Verificar si la respuesta de numeración es una lista
                if isinstance(numeracion_response, list):
                    resultado_numeracion = numeracion_response  # Es una lista de numeraciones
                elif "error" in numeracion_response:
                    error = numeracion_response["error"]
                else:
                    error = "Formato inesperado en la respuesta de la API de Consultar Numeración."
            except (IndexError, KeyError):
                error = "No se encontró el streetNameId para la comuna y nombre de calle proporcionados."
        else:
            error = "Respuesta inesperada de la API de Consultar Calle."

    return render(request, 'consultar_calle_numeracion.html', {
        'resultado_numeracion': resultado_numeracion,
        'error': error
    })


from django.shortcuts import render
from .utils import georreferenciar_direccion

from .utils import consultar_cobertura_real, georreferenciar_direccion
from .utils import consultar_cobertura_real, georreferenciar_direccion
import logging

logger = logging.getLogger(__name__)

def buscar_county_coverage_code(cobertura, county_name):
    """
    Busca el countyCoverageCode para una comuna específica.
    
    Parámetros:
        cobertura (list): Lista de áreas de cobertura.
        county_name (str): Nombre de la comuna a buscar.

    Retorna:
        str: Código de cobertura si se encuentra, de lo contrario None.
    """
    county_name_normalized = county_name.lower().capitalize()
    for area in cobertura:
        if area["countyName"].lower() == county_name_normalized.lower():
            return area["countyCode"]
    return None

def georreferenciar_direccion_view(request):
    if request.method == 'POST':
        county_name = request.POST.get('countyName')
        street_name = request.POST.get('streetName')
        number = request.POST.get('streetNumber')

        resultado = georreferenciar_direccion(county_name, street_name, number)
        if "error" in resultado:
            return render(request, 'georreferenciar_direccion.html', {'error': resultado["error"]})

        latitude = resultado.get("latitude")
        longitude = resultado.get("longitude")
        address_id = resultado.get("addressId")
        county_coverage_code = resultado.get("countyCoverageCode")

        if not county_coverage_code:
            cobertura = consultar_cobertura_real(region_code="RM", tipo_cobertura=1)

            # Validar si la API devolvió correctamente datos de cobertura
            if isinstance(cobertura, dict) and "error" in cobertura:
                return render(request, 'georreferenciar_direccion.html', {'error': cobertura["error"]})

            if not isinstance(cobertura, list):
                logger.error(f"Formato inesperado en cobertura: {cobertura}")
                return render(request, 'georreferenciar_direccion.html', {
                    'error': "Error al procesar la respuesta de cobertura."
                })

            # Buscar el código de cobertura correspondiente a la comuna
            county_coverage_code = buscar_county_coverage_code(cobertura, county_name)

        if not county_coverage_code:
            return render(request, 'georreferenciar_direccion.html', {
                'error': f"No se encontró cobertura para la comuna {county_name}."
            })

        try:
            direccion = Direccion.objects.create(
                api_address_id=address_id,
                county_coverage_code=county_coverage_code,
                street_name=street_name,
                street_number=number,
                comuna=county_name,
                address_type="DEST",
                observation=f"Georreferenciado automáticamente con lat: {latitude}, long: {longitude}"
            )
        except Exception as e:
            logger.error(f"Error al guardar en la base de datos: {str(e)}")
            return render(request, 'georreferenciar_direccion.html', {
                'error': f"Error al guardar en la base de datos: {e}"
            })

        return render(request, 'georreferenciar_direccion.html', {
            'latitude': latitude,
            'longitude': longitude,
            'addressId': address_id,
            'countyCoverageCode': county_coverage_code,
            'message': "Dirección guardada exitosamente en la base de datos."
        })

    return render(request, 'georreferenciar_direccion.html')


def seleccionar_direccion(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    context = {
        'producto': producto,
    }
    return render(request, 'seleccionar_direccion.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from .models import Producto
from .utils import cotizar_envio, consultar_cobertura_real

def calcular_envio(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        comuna = request.POST.get('comuna')
        direccion = request.POST.get('direccion')
        calle = request.POST.get('calle')
        numero = request.POST.get('numero')

        if not comuna or not direccion or not calle or not numero:
            return render(request, 'seleccionar_direccion.html', {
                'producto': producto,
                'error': "Todos los campos son obligatorios."
            })

        region_code = 'RM'
        tipo_cobertura = 1

        resultado_cobertura_real_origen = consultar_cobertura_real(region_code, tipo_cobertura)
        origin_code = next(
            (area['countyCode'] for area in resultado_cobertura_real_origen if area['countyName'].upper() == "EL MONTE"),
            None
        )

        if not origin_code:
            return render(request, 'seleccionar_direccion.html', {
                'producto': producto,
                'error': "No se encontró el código de cobertura para la comuna de origen proporcionada."
            })

        resultado_cobertura_real_destino = consultar_cobertura_real(region_code, tipo_cobertura)
        destination_code = next(
            (area['countyCode'] for area in resultado_cobertura_real_destino if area['countyName'].upper() == comuna.upper()),
            None
        )

        if not destination_code:
            return render(request, 'seleccionar_direccion.html', {
                'producto': producto,
                'error': "No se encontró el código de cobertura para la comuna de destino proporcionada."
            })

        package = {
            "weight": float(producto.peso) if producto.peso else 1.0,
            "height": int(producto.altura) if producto.altura else 1,
            "width": int(producto.ancho) if producto.ancho else 1,
            "length": int(producto.largo) if producto.largo else 1
        }
        product_type = int(producto.tipo_producto) if producto.tipo_producto else 3
        declared_worth = int(producto.valor_declarado) if producto.valor_declarado else 0

        resultado = cotizar_envio(origin_code, destination_code, package, product_type, declared_worth)
        resultado_cotizacion = resultado.get("data", {}).get("courierServiceOptions", [])

        # Seleccionar la opción "EXPRESS" en lugar de "PRIORITARIO"
        resultado_cotizacion_filtrado = [
            option for option in resultado_cotizacion 
            if option.get("serviceDescription") == "EXPRESS"
        ]

        if not resultado_cotizacion_filtrado:
            return render(request, 'seleccionar_direccion.html', {
                'producto': producto,
                'error': "No se encontraron opciones de envío disponibles para 'EXPRESS'."
            })

        # Convertir el costo de envío a un tipo numérico
        costo_envio = float(resultado_cotizacion_filtrado[0]['serviceValue'])
        
        # Convertir el precio del producto a un tipo float
        precio_producto_float = float(producto.precio)
        
        # Calcular el costo total
        costo_total = precio_producto_float + costo_envio

        # Redirigir a la vista de pago con los parámetros correctos
        return redirect('pago', producto_id=producto.id, costo_envio=int(costo_envio), costo_total=int(costo_total))

    return redirect('seleccionar_direccion', producto_id=producto.id)


from django.shortcuts import render, get_object_or_404
from .models import Producto


def pago(request):
    carrito = Carrito(request)
    if not carrito.carrito:
        return redirect('ver_carrito')

    if request.method == 'POST':
        # Procesar el pago...
        # Si el pago es exitoso:
        with transaction.atomic():
            for item in carrito.carrito.values():
                producto = Producto.objects.select_for_update().get(id=item['producto_id'])
                cantidad_comprada = item['cantidad']
                if producto.stock >= cantidad_comprada:
                    producto.stock -= cantidad_comprada
                    producto.save()
                else:
                    # Manejar el caso donde el stock es insuficiente
                    return render(request, 'error.html', {'mensaje': f"No hay suficiente stock para {producto.nombre}."})

            # Crear el pedido en la base de datos
            # Limpiar el carrito y la sesión
            carrito.clear()
            # Redirigir a una página de confirmación
            return render(request, 'confirmacion.html', {'mensaje': 'Pago realizado con éxito.'})
    else:
        # Mostrar resumen del pedido
        pass
# views.py

from django.db import transaction
from .carrito import Carrito

# Vista para realizar el pago

def pago(request, producto_id, costo_envio):
    producto = get_object_or_404(Producto, id=producto_id)
    carrito = request.session.get('carrito', {})  # Obtén el carrito desde la sesión

    context = {
        'producto': producto,
        'carrito': carrito,
        'costo_envio': costo_envio,
        'total_pagar': producto.precio + costo_envio  # Calcula el total a pagar
    }
    return render(request, 'pago.html', context)


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
def webhook(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # Registra los datos para solucionar problemas
            print("Datos del webhook recibidos:", data)
            return JsonResponse({"status": "received"})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Formato JSON inválido"}, status=400)
    return JsonResponse({"error": "Solicitud inválida"}, status=400)





from django.contrib import messages
from .models import Producto
from .carrito import Carrito


from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Producto
from .carrito import Carrito
from django.http import JsonResponse, HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from .models import Producto
from .carrito import Carrito

@csrf_exempt
def agregar_al_carrito(request, producto_id):
    # Verifica si la solicitud es AJAX
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Responde con JSON indicando que la solicitud debe ser AJAX
        return JsonResponse({'success': False, 'message': 'Esta vista solo acepta solicitudes AJAX.'}, status=400)

    # Obtiene el producto y el carrito
    producto = get_object_or_404(Producto, id=producto_id)
    carrito = Carrito(request)

    try:
        # Intenta añadir el producto al carrito
        if carrito.add(producto):
            # Calcula el total de productos en el carrito
            total_items = sum(item['cantidad'] for item in carrito.carrito.values())
            return JsonResponse({'success': True, 'cart_total_items': total_items})
        else:
            # Responde con un mensaje de error si no hay suficiente stock
            return JsonResponse({'success': False, 'message': 'No hay suficiente stock disponible.'})
    except Exception as e:
        # Captura cualquier excepción y envía un mensaje de error
        print("Error al añadir producto al carrito:", e)
        return JsonResponse({'success': False, 'message': 'Error interno al procesar la solicitud.'})

def agregar_al_carrito_2(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    carrito = Carrito(request)

    try:
        if carrito.add(producto):
            messages.success(request, f"{producto.nombre} ha sido agregado al carrito.")
        else:
            messages.error(request, "No hay suficiente stock disponible.")
    except Exception as e:
        print("Error al añadir producto al carrito:", e)
        messages.error(request, "Error interno al procesar la solicitud.")
    
    return redirect('ver_carrito')

def ver_carrito(request):
    carrito = Carrito(request)
    
    # Calcular el total del carrito
    total_carrito = sum(float(item['cantidad']) * float(item['precio']) for item in carrito.carrito.values())
    
    # Pasar 'carrito' y 'total_carrito' al contexto
    return render(request, 'ver_carrito.html', {
        'carrito': carrito.carrito,
        'total_carrito': total_carrito
    })


def eliminar_del_carrito(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    carrito = Carrito(request)
    carrito.remove(producto)
    messages.success(request, f"{producto.nombre} se ha eliminado del carrito.")
    return redirect('ver_carrito')

def restar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    carrito = Carrito(request)
    carrito.decrement(producto)
    messages.success(request, f"Se ha disminuido la cantidad de {producto.nombre} en el carrito.")
    return redirect('ver_carrito')

def limpiar_carrito(request):
    carrito = Carrito(request)
    carrito.clear()
    messages.success(request, "El carrito se ha vaciado.")
    return redirect('ver_carrito')

# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .carrito import Carrito
from .utils import cotizar_envio, consultar_cobertura_real, obtener_datos_carrito  # Asegúrate de importar la función
from .models import Producto

from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Producto
from .utils import consultar_cobertura_real, cotizar_envio, obtener_datos_carrito
from .carrito import Carrito

# Vista para el checkout
from django.shortcuts import render, redirect, get_object_or_404
from .carrito import Carrito
from .utils import cotizar_envio, consultar_cobertura_real, obtener_datos_carrito, georreferenciar_direccion  # Asegúrate de importar la función
from .models import Producto
from .models import Cliente


import logging
import json

logger = logging.getLogger(__name__)

# views.py

from django.shortcuts import render, redirect
from .models import Pedido, Cliente, Producto
from .utils import cotizar_envio, georreferenciar_direccion, obtener_datos_carrito, consultar_cobertura_real
import logging
import json
from .utils import georreferenciar_direccion

from .utils import georreferenciar_direccion
from .models import Direccion

from .utils import georreferenciar_direccion

from django.shortcuts import render, redirect
from .models import Cliente, Direccion, Pedido, Producto, Contacto
from .utils import georreferenciar_direccion, obtener_datos_carrito, cotizar_envio
from django.contrib.auth.models import User
import json


from .utils import georreferenciar_direccion, obtener_datos_carrito, cotizar_envio

from django.shortcuts import render, redirect
from .models import Direccion, Pedido, Producto,  Contacto
from .carrito import Carrito
from .utils import georreferenciar_direccion, cotizar_envio

from django.shortcuts import render, redirect
from .models import Pedido,  Contacto, Direccion, Cliente, Producto
from .utils import georreferenciar_direccion, cotizar_envio, consultar_cobertura_real
from .carrito import Carrito
# views.py

# naturalworld_d/views.py

from django.shortcuts import render, get_object_or_404, redirect
from .models import Producto
from .carrito import Carrito

def listar_productos(request):
    """
    Vista para listar todos los productos.
    """
    productos = Producto.objects.all()
    return render(request, 'listar_productos.html', {'productos': productos})

from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.utils import timezone
from .carrito import Carrito
from .utils import (
    cotizar_envio,
    consultar_cobertura_real,
    obtener_datos_carrito,
    georreferenciar_direccion,
    generar_envio
)
from .models import (
    Producto,
    Cliente,
    Direccion,
    Contacto,
    Pedido,
    DetallePedido,
    PaqueteEnvio,
    EnvioGenerado,
    
)
import logging
import json
import uuid

logger = logging.getLogger(__name__)

# naturalworld_d/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.utils import timezone
from .carrito import Carrito
from .utils import (
    cotizar_envio,
    consultar_cobertura_real,
    obtener_datos_carrito,
    georreferenciar_direccion,
    generar_envio
)
from .models import (
    Producto,
    Cliente,
    Direccion,
    Contacto,
    Pedido,
    DetallePedido,
    PaqueteEnvio,
    EnvioGenerado,
    
)
import logging
import uuid

logger = logging.getLogger(__name__)

# naturalworld_d/views.py

import uuid
import logging
from django.shortcuts import render, redirect
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from .models import Cliente, Contacto, Direccion, Pedido, DetallePedido, PaqueteEnvio, EnvioGenerado, Producto
from .utils import generar_envio, georreferenciar_direccion, cotizar_envio, obtener_datos_carrito

logger = logging.getLogger(__name__)
# naturalworld_d/views.py

import uuid
import logging
from django.shortcuts import render, redirect
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from .models import (
    Cliente, Contacto, Direccion, Pedido, DetallePedido,
    PaqueteEnvio, EnvioGenerado, Producto
)
from .utils import (
    generar_envio, georreferenciar_direccion,
    cotizar_envio, obtener_datos_carrito, consultar_cobertura_real
)

logger = logging.getLogger(__name__)
from django.shortcuts import render, redirect
from django.db import transaction
from .models import Cliente, Contacto, Direccion, Pedido, DetallePedido, EnvioGenerado, Producto
from .utils import consultar_cobertura_real, obtener_datos_carrito, georreferenciar_direccion, cotizar_envio, generar_envio
from .carrito import Carrito
from django.utils import timezone

from django.shortcuts import render, redirect
from django.db import transaction
from .utils import generar_envio, georreferenciar_direccion, cotizar_envio, obtener_datos_carrito
from .models import Cliente, Contacto, Direccion, Pedido, DetallePedido, EnvioGenerado, Producto

from django.shortcuts import render, redirect
from django.db import transaction
from django.utils import timezone
from .models import Cliente, Contacto, Direccion, Pedido, DetallePedido, EnvioGenerado
from .utils import consultar_cobertura_real, cotizar_envio, georreferenciar_direccion, obtener_datos_carrito

from django.shortcuts import render, redirect
from django.db import transaction
from .models import Cliente, Contacto, Direccion, Pedido, DetallePedido, Producto
from .carrito import Carrito
from .utils import consultar_cobertura_real, cotizar_envio, georreferenciar_direccion, obtener_datos_carrito
from django.db import IntegrityError  # Importa IntegrityError
from django.db import IntegrityError
from django.shortcuts import render, redirect
import json
from .models import Cliente, Direccion, Pedido
from .carrito import Carrito
from .utils import georreferenciar_direccion, obtener_datos_carrito, consultar_cobertura_real, cotizar_envio
from .utils import georreferenciar_direccion

from .utils import georreferenciar_direccion
from .utils import consultar_cobertura_real, georreferenciar_direccion
import logging
from .utils import consultar_cobertura_real, georreferenciar_direccion
import logging




# naturalworld_d/views.py

# naturalworld_d/views.py
# naturalworld_d/views.py
from .carrito import Carrito

from django.shortcuts import render, redirect
from django.db import IntegrityError, transaction
from django.contrib import messages
from .models import (
    Pedido,
    PaqueteEnvio,
    Direccion,
    Cliente,
    Contacto,
    DetallePedido
)
from .utils import (
    georreferenciar_direccion,
    consultar_cobertura_real,
    cotizar_envio,
    obtener_datos_carrito
)
import logging
import uuid

logger = logging.getLogger(__name__)
# naturalworld_d/views.py

from django.shortcuts import render, redirect
from django.db import IntegrityError, transaction
from django.contrib import messages
from .carrito import Carrito
from .models import (
    Pedido,
    PaqueteEnvio,
    Direccion,
    Cliente,
    Contacto,
    DetallePedido
)
from .utils import (
    georreferenciar_direccion,
    consultar_cobertura_real,
    cotizar_envio,
    obtener_datos_carrito
)
import logging
import uuid

logger = logging.getLogger(__name__)
def buscar_county_coverage_code(cobertura, county_name):
    """
    Busca el countyCoverageCode para una comuna específica.
    """
    county_name_normalized = county_name.lower().capitalize()
    for area in cobertura:
        if area["countyName"].lower() == county_name_normalized.lower():
            return area["countyCode"]
    return None
import logging

# Configura el logger
logger = logging.getLogger(__name__)

from django.shortcuts import render, redirect
from django.db import IntegrityError, transaction
from django.contrib import messages
from .carrito import Carrito
from .models import (
    Pedido,
    PaqueteEnvio,
    Direccion,
    Cliente,
    Contacto,
    DetallePedido
)
from .utils import (
    georreferenciar_direccion,
    consultar_cobertura_real,
    cotizar_envio,
    obtener_datos_carrito
)
import logging
import uuid
from django.shortcuts import render, redirect
from django.db import IntegrityError, transaction
from django.contrib import messages
from .carrito import Carrito
from .models import (
    Pedido,
    PaqueteEnvio,
    Direccion,
    Cliente,
    Contacto,
    DetallePedido
)
from .utils import (
    georreferenciar_direccion,
    consultar_cobertura_real,
    cotizar_envio,
    obtener_datos_carrito
)
import logging
import uuid
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Cliente, Direccion, Pedido, DetallePedido, PaqueteEnvio, Producto

logger = logging.getLogger(__name__)
def buscar_county_coverage_code(cobertura, county_name):
    """
    Busca el countyCoverageCode para una comuna específica.
    """
    county_name_normalized = county_name.lower().capitalize()
    for area in cobertura:
        if area["countyName"].lower() == county_name_normalized.lower():
            return area["countyCode"]
    return None

def checkout(request):
    logger.info("Iniciando el proceso de checkout.")
    
    carrito = Carrito(request)
    if not carrito.carrito:
        logger.warning("El carrito está vacío. Redirigiendo al carrito.")
        return redirect('ver_carrito')


    if request.method == 'POST':
        logger.debug("Datos POST recibidos: %s", request.POST)

        # Capturar datos del cliente y la dirección
        rut = request.POST.get('rut', '').strip()
        email = request.POST.get('mail_cliente', '').strip()
        comuna = request.POST.get('comuna', '').strip()
        calle = request.POST.get('calle', '').strip()
        numero = request.POST.get('numero', '').strip()
        nombre_cliente = request.POST.get('nombre_cliente', 'Cliente Sin Nombre').strip()
        telefono = request.POST.get('telefono', '000000000').strip()

        logger.info("Datos capturados: rut=%s, email=%s, nombre=%s, teléfono=%s, comuna=%s, calle=%s, número=%s",
                    rut, email, nombre_cliente, telefono, comuna, calle, numero)

        # Verificar que todos los campos requeridos están llenos
        if not all([rut, comuna, calle, numero, email, nombre_cliente, telefono]):
            logger.error("Campos obligatorios faltantes.")
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'checkout.html')

        # Validar el RUT
        if len(rut) < 7 or not rut.replace(".", "").replace("-", "").isdigit():
            logger.error("RUT inválido: %s", rut)
            messages.error(request, "El RUT ingresado no es válido.")
            return render(request, 'checkout.html')

        try:
            # Crear o actualizar el cliente
            cliente, created = Cliente.objects.get_or_create(
                rut=rut,
                defaults={'email': email, 'nombre': nombre_cliente, 'telefono': telefono}
            )
            if not created:
                cliente.email = email
                cliente.nombre = nombre_cliente
                cliente.telefono = telefono
                cliente.save()
        except IntegrityError as e:
            logger.error("Error al crear/actualizar el cliente: %s", str(e))
            messages.error(request, "El email ingresado ya está registrado con otro cliente.")
            return render(request, 'checkout.html')

        # Georreferenciar la dirección
        try:
            georef = georreferenciar_direccion(comuna, calle, numero)
            if "error" in georef:
                raise ValueError(georef['error'])
        except Exception as e:
            logger.error("Error al georreferenciar la dirección: %s", str(e))
            messages.error(request, f"Error al georeferenciar la dirección: {str(e)}")
            return render(request, 'checkout.html')

        latitude = georef.get("latitude")
        longitude = georef.get("longitude")
        address_id = georef.get("addressId")
        county_coverage_code = georef.get("countyCoverageCode")

        if not county_coverage_code:
            cobertura = consultar_cobertura_real(region_code="RM", tipo_cobertura=1)
            county_coverage_code = buscar_county_coverage_code(cobertura, comuna)
            if not county_coverage_code:
                messages.error(request, f"No se encontró cobertura para la comuna {comuna}.")
                return render(request, 'checkout.html')

        # Guardar la dirección
        direccion = Direccion.objects.create(
            api_address_id=address_id,
            county_coverage_code=county_coverage_code,
            street_name=calle,
            street_number=numero,
            comuna=comuna,
            address_type="DEST",
            observation=f"Georreferenciado automáticamente con lat: {latitude}, long: {longitude}"
        )

        # Obtener datos del carrito
        datos_paquete = obtener_datos_carrito(request)
        if not datos_paquete or not all(k in datos_paquete for k in ('peso', 'alto', 'ancho', 'largo', 'valor')):
            messages.error(request, "Datos del carrito incompletos o inválidos.")
            return render(request, 'checkout.html')

        # Cotizar envío
        package = {
            "weight": datos_paquete['peso'],
            "height": datos_paquete['alto'],
            "width": datos_paquete['ancho'],
            "length": datos_paquete['largo']
        }
        declared_worth = datos_paquete['valor']
        product_type = 3  # Encomienda
        resultado = cotizar_envio(county_coverage_code, county_coverage_code, package, product_type, declared_worth)
        opciones_envio = [opt for opt in resultado.get("data", {}).get("courierServiceOptions", []) if opt.get("serviceDescription") == "EXPRESS"]

        if not opciones_envio:
            messages.error(request, "No se encontraron opciones de envío disponibles para 'EXPRESS'.")
            return render(request, 'checkout.html')

        costo_envio = float(opciones_envio[0].get('serviceValue', 0))
        total_pagar = sum(
            float(item.get('cantidad', 0)) * float(item.get('precio', 0))
            for item in carrito.carrito.values()
        ) + costo_envio

        try:
            with transaction.atomic():
                # Crear pedido si no existe uno en progreso para evitar duplicación
                pedido, created = Pedido.objects.get_or_create(
                    cliente=cliente,
                    estado='pendiente',
                    defaults={
                        'direccion': direccion,
                        'total': total_pagar
                    }
                )
                if not created:
                    pedido.direccion = direccion
                    pedido.total = total_pagar
                    pedido.save()

                for item_id, item_data in carrito.carrito.items():
                    producto = Producto.objects.get(id=item_id)
                    # Crear o actualizar el detalle del pedido
                    detalle, detalle_created = DetallePedido.objects.get_or_create(
                        pedido=pedido,
                        producto=producto,
                        defaults={
                            'cantidad': item_data.get('cantidad', 1),
                            'precio_unitario': producto.precio,
                            'peso_unitario': producto.peso
                        }
                    )
                    if not detalle_created:
                        detalle.cantidad += item_data.get('cantidad', 1)
                        detalle.save()

                PaqueteEnvio.objects.create(
                    pedido=pedido,
                    peso=datos_paquete['peso'],
                    altura=datos_paquete['alto'],
                    ancho=datos_paquete['ancho'],
                    largo=datos_paquete['largo'],
                    servicio_entrega_codigo=3,
                    product_code=product_type,
                    referencia_envio=f"{pedido.numero_orden}-{uuid.uuid4().hex[:6].upper()}",
                    referencia_grupo=f"GRUPO-{pedido.numero_orden}",
                    contenido_declarado=1,
                    valor_declarado=declared_worth
                )

        except Exception as e:
            logger.error("Error al crear el pedido o los detalles: %s", str(e))
            messages.error(request, f"Error al procesar el pedido: {str(e)}")
            return render(request, 'checkout.html')

        request.session['pedido_id'] = str(pedido.id)
        request.session['cliente_rut'] = cliente.rut
        request.session['cliente_email'] = cliente.email
        request.session['costo_envio'] = costo_envio
        request.session['total_pagar'] = total_pagar
        request.session['direccion'] = {'comuna': comuna, 'calle': calle, 'numero': numero}

        logger.info("Checkout completado. Redirigiendo al pago.")
        return redirect('pago')

    return render(request, 'checkout.html')

from django.shortcuts import render
from django.http import JsonResponse
from .carrito import Carrito  # Asegúrate de que esto esté configurado correctamente

def pago(request):
    # Inicializa el carrito
    carrito = Carrito(request)
    costo_envio = request.session.get('costo_envio')
    total_pagar = request.session.get('total_pagar')
    direccion = request.session.get('direccion')  # Asegúrate de guardar la dirección previamente en checkout

    # Validaciones
    if not carrito.carrito:
        return JsonResponse({"error": "El carrito está vacío"}, status=400)
    if costo_envio is None or total_pagar is None:
        return JsonResponse({"error": "Faltan datos del costo de envío o total a pagar"}, status=400)
    if not direccion:
        return JsonResponse({"error": "No se ha proporcionado la dirección de envío"}, status=400)

    # Asegúrate de que los elementos del carrito tengan las claves necesarias
    for key, item in carrito.carrito.items():
        if not all(k in item for k in ('nombre', 'precio', 'cantidad')):
            return JsonResponse({"error": f"El item {key} no contiene los campos necesarios"}, status=400)

    # Renderiza la plantilla con los datos necesarios
    return render(request, 'pago.html', {
        'carrito': list(carrito.carrito.values()),  # Pasamos una lista de los valores del carrito
        'costo_envio': costo_envio,
        'total_pagar': total_pagar,
        'direccion': direccion,
    })


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import mercadopago
from .models import Pago  # Asegúrate de tener el modelo Pago configurado correctamente
from .models import Pedido, Producto, Pago  # Asegúrate de incluir todos los modelos necesarios
import json
import logging
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from .models import Pedido, Pago
import mercadopago
from .utils import generar_envio     

import json
import logging
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from .models import Pedido, Pago
from .utils import generar_envio # Asumiendo que generar_envio está en utils.py
import json
import logging
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from .models import Pedido, Pago
from .utils import generar_envio
import mercadopago

import logging
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Pedido, Pago
from .utils import generar_envio
from mercadopago import SDK



from .models import Pedido
from .utils import generar_envio      

from django.views.decorators.csrf import csrf_exempt
import mercadopago

from django.views.decorators.csrf import csrf_exempt
import logging
import json

logger = logging.getLogger(__name__)

@csrf_exempt
def recibir_pago(request):
    if request.method == "POST":
        try:
            # Registrar los datos de la solicitud
            logger.debug(f"Headers: {dict(request.headers)}")
            logger.debug(f"Body: {request.body.decode('utf-8')}")

            # Procesar parámetros GET
            payment_id = request.GET.get('id')
            topic = request.GET.get('topic')

            # Registrar parámetros GET
            logger.debug(f"GET Params: payment_id={payment_id}, topic={topic}")

            # Validar los datos
            if not payment_id or not topic:
                return JsonResponse({"error": "Datos insuficientes en la solicitud"}, status=400)

            # Procesar según el tipo de notificación
            if topic == "payment":
                logger.debug(f"Procesando pago con ID: {payment_id}")
                # Lógica de procesamiento del pago
                return JsonResponse({"message": "Pago procesado exitosamente"}, status=200)
            elif topic == "merchant_order":
                logger.debug(f"Procesando orden de comercio con ID: {payment_id}")
                # Lógica para manejar merchant_order
                return JsonResponse({"message": "Merchant order manejada"}, status=200)
            else:
                return JsonResponse({"error": "Tipo de notificación no manejada"}, status=400)

        except Exception as e:
            logger.error(f"Error al procesar el webhook: {str(e)}")
            return JsonResponse({"error": "Error interno del servidor"}, status=500)

    return JsonResponse({"error": "Método no permitido"}, status=405)

# views.py
from django.conf import settings
# views.py
from django.conf import settings
from .utils import generar_envio

def confirmar_envio(request):
    # Asegúrate de que esta vista se llama después de un pago exitoso
    pedido_id = request.session.get('pedido_id')
    if not pedido_id:
        return JsonResponse({"error": "No se encontró el pedido en la sesión"}, status=400)

    try:
        pedido = Pedido.objects.get(id=pedido_id)
    except Pedido.DoesNotExist:
        return JsonResponse({"error": "El pedido no existe"}, status=404)

    # Datos del paquete (puedes ajustar esto según tu lógica)
    package_details = {
        "weight": pedido.peso_total,
        "height": 10,  # Altura de ejemplo
        "width": 10,   # Ancho de ejemplo
        "length": 20,  # Largo de ejemplo
        "serviceDeliveryCode": 3,  # Código de servicio (puedes obtenerlo de la cotización previa)
        "productCode": 3,  # Encomienda
        "declaredValue": pedido.total,
        "declaredContent": 5  # "Otros" según la API
    }

    # Detalles de contacto adicionales (opcional)
    contact_details = {
        "deliveryOnCommercialOffice": False,
        "observation": "Entrega estándar"
    }

    # Código de cobertura (puedes haberlo obtenido previamente)
    origin_code = "PUDA"  # Código de cobertura de origen (ejemplo)
    destination_code = pedido.direccion.county_coverage_code

    # Llamar a la función para generar el envío
    resultado_envio = generar_envio(
        pedido=pedido,
        customer_card_number=settings.CHILEXPRESS_CUSTOMER_CARD_NUMBER,
        origin_code=origin_code,
        destination_code=destination_code,
        package_details=package_details,
        contact_details=contact_details
    )

    if resultado_envio.get("success"):
        # Guardar detalles del envío en el pedido o base de datos
        pedido.estado_envio = "generado"
        pedido.numero_seguimiento = resultado_envio["data"]["data"]["detail"][0]["transportOrderNumber"]
        pedido.save()

        return JsonResponse({
            "message": "Envío generado exitosamente",
            "tracking_number": pedido.numero_seguimiento,
            "detalle_envio": resultado_envio["data"]
        })
    else:
        return JsonResponse({
            "error": "No se pudo generar el envío",
            "detalle": resultado_envio.get("error")
        }, status=400)



import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from mercadopago import SDK
from .models import Pedido, Pago

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging

# Configuración de logging
logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from mercadopago import SDK
import logging

# Configura el logger
logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from mercadopago import SDK
import logging

# Configura el logger
logger = logging.getLogger(__name__)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from mercadopago import SDK
from .models import Pedido, Pago

logger = logging.getLogger(__name__)


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from mercadopago import SDK
from .models import Pedido, Pago

logger = logging.getLogger(__name__)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from mercadopago import SDK
from .models import Pedido, Pago

logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from mercadopago import SDK
from .models import Pedido, Pago
from .utils import generar_envio  # Importa la función que implementaste
import json
import logging
import requests
from datetime import datetime  # Importar datetime aquí
from django.http import JsonResponse
from .models import Pedido, Contacto, Direccion, Pago
from .utils import generar_envio  # Asumiendo que generas la función en otro archivo como utils.py


logger = logging.getLogger(__name__)
from .utils import generar_envio

from django.http import JsonResponse
import json
from mercadopago import SDK
from naturalworld_d.models import Pedido, Pago
import logging

logger = logging.getLogger(__name__)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from mercadopago import SDK
from .models import Pedido, Pago
import logging

# Configura un logger para depuración
logger = logging.getLogger(__name__)


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from mercadopago import SDK
from .models import Pedido, Pago
import logging

# Configura un logger para depuración
logger = logging.getLogger(__name__)

import json
from django.http import JsonResponse
import logging
from mercadopago import SDK
from .models import Pedido, Pago

logger = logging.getLogger(__name__)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from mercadopago import SDK
from .models import Pedido, Pago
import logging

# Configuración del logger para depuración
logger = logging.getLogger(__name__)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from mercadopago import SDK
from .models import Pedido, Pago
import logging

# Configura un logger para depuración
logger = logging.getLogger(__name__)


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from mercadopago import SDK
from .models import Pedido, Pago
import logging

# Configurar logger para depuración
logger = logging.getLogger(__name__)

from django.utils import timezone  # Asegúrate de importar timezone si no lo has hecho
from django.utils import timezone  # Asegúrate de importar timezone si no lo has hecho
from django.http import JsonResponse
import json
import logging
from mercadopago import SDK  # Asegúrate de importar el SDK de Mercado Pago
from .models import Pedido, Pago, TransportOrder  # Importa tus modelos

logger = logging.getLogger(__name__)
import json
import logging
from django.http import JsonResponse
from django.utils import timezone
from mercadopago import SDK
from .models import Pedido, Pago, EnvioGenerado, TransportOrder  # Asegúrate de importar tus modelos
from .utils import generar_envio  # Importa la función generar_envio si está en otro módulo

logger = logging.getLogger(__name__)
@csrf_exempt
def webhook(request):
    """
    Webhook simplificado para registrar pagos en la base de datos y generar envío.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        # Intentar cargar los datos del webhook
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"JSON inválido recibido: {e}")
            return JsonResponse({"error": "JSON inválido en el cuerpo de la solicitud"}, status=400)

        # Extraer información del webhook
        resource_id = data.get("data", {}).get("id") or data.get("id")
        topic = data.get("type") or request.GET.get("topic")

        if topic != "payment" or not resource_id:
            logger.warning(f"Evento no manejado o ID faltante. Topic: {topic}, ID: {resource_id}")
            return JsonResponse({"error": "Evento no manejado o ID faltante"}, status=400)

        logger.info(f"Recibiendo evento con topic '{topic}' y resource ID: {resource_id}")

        # Inicializar SDK de Mercado Pago
        sdk = SDK("APP_USR-7989794511721795-103003-30ce8ee651d7e12a6f9180d1369215df-2065223385")  # Reemplaza con tu access token real

        # Obtener información del pago
        try:
            payment_response = sdk.payment().get(resource_id)
            if "response" not in payment_response:
                logger.error(f"Respuesta inválida del SDK: {payment_response}")
                return JsonResponse({"error": "No se pudo obtener información del pago desde Mercado Pago"}, status=500)
            payment_data = payment_response.get("response", {})
            logger.info(f"Detalles del pago recibido: {payment_data}")
        except Exception as e:
            logger.error(f"Error obteniendo detalles del pago: {e}")
            return JsonResponse({"error": "No se pudo obtener información del pago"}, status=500)

        # Extraer datos del pago
        external_reference = payment_data.get("external_reference")
        payment_id = payment_data.get("id")
        status = payment_data.get("status")
        transaction_amount = payment_data.get("transaction_amount")
        status_detail = payment_data.get("status_detail")

        # Validar datos esenciales
        if not external_reference or not payment_id:
            logger.error("Faltan datos clave: external_reference o payment_id")
            return JsonResponse({"error": "Datos del pago incompletos"}, status=400)
        if not status or transaction_amount is None:
            logger.error(f"Faltan datos en el pago: Status: {status}, Monto: {transaction_amount}")
            return JsonResponse({"error": "Faltan datos en el pago recibido"}, status=400)

        # Obtener pedido asociado
        pedido_id = external_reference.replace("pedido-", "")
        try:
            pedido = Pedido.objects.get(id=pedido_id)
        except Pedido.DoesNotExist:
            logger.error(f"Pedido con ID {pedido_id} no encontrado.")
            return JsonResponse({"error": f"Pedido {pedido_id} no encontrado"}, status=404)

        # Registrar o actualizar el pago en la base de datos
        try:
            pago, created = Pago.objects.update_or_create(
                id_pago=payment_id,
                defaults={
                    "estado": status,
                    "detalle_estado": status_detail,
                    "monto": transaction_amount,
                    "pedido": pedido,
                    "referencia_externa": external_reference,
                },
            )
            if created:
                logger.info(f"Pago creado exitosamente en la base de datos: {pago}")
            else:
                logger.info(f"Pago actualizado exitosamente en la base de datos: {pago}")

            # Actualizar estado del pedido si el pago fue aprobado
            if status == "approved":
                pedido.estado = "pagado"
                pedido.save()
                logger.info(f"Estado del pedido {pedido_id} actualizado a 'pagado'.")

                # Generar el envío
                envio_response = generar_envio(pedido)
                if envio_response.get("success"):
                    logger.info(f"Envío generado exitosamente para el pedido {pedido_id}.")

                    # Intentar obtener el número de seguimiento
                    try:
                        detail = envio_response.get('data', {}).get('detail', [])[0]
                        tracking_id = detail.get('transportOrderNumber')
                        if not tracking_id:
                            raise ValueError("No se recibió 'transportOrderNumber' en la respuesta de 'generar_envio'.")

                        # Actualizar estado del pedido si es necesario
                        pedido.estado_envio = 'generado'
                        pedido.numero_seguimiento = tracking_id
                        pedido.save()

                        # Si necesitas acceder a la instancia de EnvioGenerado
                        envio_generado = EnvioGenerado.objects.get(pedido=pedido)
                        logger.info(f"EnvioGenerado creado: {envio_generado}")

                        # Si necesitas acceder a la instancia de TransportOrder
                        transport_order = TransportOrder.objects.get(pedido=pedido)
                        logger.info(f"TransportOrder creada: {transport_order}")

                    except Exception as e:
                        logger.error(f"Error al procesar la respuesta de 'generar_envio': {e}")
                        # Manejar el error según tus necesidades

                else:
                    logger.error(f"Error generando el envío para el pedido {pedido_id}: {envio_response.get('error')}")
                    # Opcional: actualizar el estado de TransportOrder a 'error'
                    transport_order = TransportOrder.objects.filter(pedido=pedido).first()
                    if transport_order:
                        transport_order.estado = 'error'
                        transport_order.save()
            else:
                logger.info(f"Pago con estado {status} para el pedido {pedido_id}. No se genera envío.")

            return JsonResponse({"success": True, "message": "Pago registrado y envío procesado exitosamente"}, status=200)

        except Exception as e:
            logger.error(f"Error registrando el pago en la base de datos: {e}")
            return JsonResponse({"error": "Error al registrar el pago en la base de datos"}, status=500)

    except Exception as e:
        logger.error(f"Error procesando el webhook: {e}")
        return JsonResponse({"error": str(e)}, status=500)




from datetime import datetime  # Importar datetime aquí
import logging
from datetime import datetime
import requests
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
import requests
import logging
from django.utils import timezone
from .models import Pedido, EnvioGenerado, Pago

# Configurar el logger
logger = logging.getLogger(__name__)

from .models import Pedido, EnvioGenerado  # Asegúrate de importar lo necesario
import requests
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)
import requests
from django.utils import timezone
import logging
from .models import  EnvioGenerado

logger = logging.getLogger(__name__)

import requests
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

import requests
from django.utils import timezone
import logging
from .models import EnvioGenerado

# Configuración de logging
logger = logging.getLogger(__name__)

import requests
import os
import base64
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import EnvioGenerado, TransportOrder  # Asegúrate de importar TransportOrder

import requests
import os
import base64
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import EnvioGenerado, TransportOrder  # Asegúrate de importar TransportOrder
import logging
import pprint

logger = logging.getLogger(__name__)

import requests
import os
import base64
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import EnvioGenerado, TransportOrder  # Asegúrate de importar EnvioGenerado y TransportOrder
import logging
import pprint

logger = logging.getLogger(__name__)
from django.core.mail import send_mail
from django.http import JsonResponse
from django.utils import timezone
import base64
import os
import json
import requests
import logging
from .models import Pedido, TransportOrder, EnvioGenerado
from django.conf import settings

logger = logging.getLogger(__name__)
def generar_envio(pedido, request=None):
    """
    Genera un envío utilizando la API de Chilexpress y envía un correo de confirmación si el envío es exitoso.
    """
    CHILEXPRESS_SUBSCRIPTION_KEY = "f3f0c3d9b9d34032a559426ab9e6cdda"  # Cambia por tu clave real

    try:
        direccion = pedido.direccion
        cliente = pedido.cliente

        if not direccion or not cliente:
            logger.error(f"El pedido {pedido.id} no tiene dirección o cliente asociado.")
            return {"success": False, "error": "Datos de cliente o dirección incompletos."}

        # Dirección fija del remitente (puedes ajustarla según la configuración que desees)
        direccion_remitente = {
            "addressId": 0,  # Si no se tiene un ID de dirección, pon un valor por defecto
            "countyCoverageCode": "PUDA",  # Código de cobertura
            "streetName": "Alfredo Silva Carvallo",  # Calle del remitente
            "streetNumber": "1939",  # Número de calle
            "supplement": "",  # Complemento si se tiene
            "addressType": "DEV",  # Dirección de devolución (DEV)
            "deliveryOnCommercialOffice": False,  # Si se entrega en oficina comercial
            "commercialOfficeId": 0,  # ID de la oficina comercial si es el caso
            "observation": "Remitente fijo"  # Observaciones si es necesario
        }

        # Validar campos necesarios
        if not direccion.county_coverage_code:
            logger.error(f"El pedido {pedido.id} tiene un código de cobertura inválido.")
            return {"success": False, "error": "Código de cobertura inválido."}

        # Preparar el payload
        detalles = []
        paquetes = pedido.paquetes_envio.all()
        if not paquetes:
            logger.error(f"El pedido {pedido.id} no tiene paquetes asociados.")
            return {"success": False, "error": "No hay paquetes para enviar."}

        for paquete in paquetes:
            detalle = {
                "addresses": [
                    # Dirección de destino
                    {
                        "addressId": direccion.api_address_id or 0,
                        "countyCoverageCode": direccion.county_coverage_code,
                        "streetName": direccion.street_name,
                        "streetNumber": direccion.street_number or "",
                        "supplement": direccion.supplement or "",
                        "addressType": "DEST",
                        "deliveryOnCommercialOffice": direccion.delivery_on_commercial_office or False,
                        "commercialOfficeId": direccion.commercial_office_id or 0,
                        "observation": direccion.observation or ""
                    },
                    # Dirección del remitente (usando la dirección fija)
                    direccion_remitente
                ],
                "contacts": [
                    {"name": cliente.nombre, "phoneNumber": cliente.telefono or "", "mail": cliente.email, "contactType": "D"},
                    {"name": "Remitente Fijo", "phoneNumber": "+56987654321", "mail": "remitente@correo.com", "contactType": "R"}
                ],
                "packages": [{
                    "weight": str(paquete.peso),
                    "height": str(paquete.altura),
                    "width": str(paquete.ancho),
                    "length": str(paquete.largo),  # Aseguramos que 'length' esté correctamente escrito
                    "serviceDeliveryCode": str(paquete.servicio_entrega_codigo),
                    "productCode": str(paquete.product_code),
                    "deliveryReference": f"pedido-{pedido.numero_orden}",
                    "groupReference": f"grupo-{pedido.numero_orden}",
                    "declaredValue": str(paquete.valor_declarado) if paquete.valor_declarado else "",
                    "declaredContent": str(paquete.contenido_declarado) if paquete.contenido_declarado else "",
                    # Omitir 'receivableAmountInDelivery' si es cero o None
                    **({"receivableAmountInDelivery": paquete.receivable_amount_in_delivery} if paquete.receivable_amount_in_delivery else {})
                }]
            }
            detalles.append(detalle)

        payload = {
            "header": {
                "customerCardNumber": pedido.customer_card_number,
                "countyOfOriginCoverageCode": direccion.county_coverage_code,
                "labelType": int(pedido.label_type)
            },
            "details": detalles
        }

        headers = {
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": CHILEXPRESS_SUBSCRIPTION_KEY
        }

        # Enviar solicitud a la API de Chilexpress
        url = "http://testservices.wschilexpress.com/transport-orders/api/v1.0/transport-orders"
        logger.debug(f"Enviando payload:\n{pprint.pformat(payload)}")
        response = requests.post(url, json=payload, headers=headers)
        logger.debug(f"Respuesta de la API: {response.status_code} - {response.text}")

        if response.status_code == 200:
            response_data = response.json()
            detail = response_data.get("data", {}).get("detail", [{}])[0]
            tracking_number = detail.get("transportOrderNumber")
            barcode = detail.get("barcode")
            service_description = detail.get("serviceDescriptionFull")
            label_data_base64 = detail.get("label", {}).get("labelData", "")

            # Procesar y guardar la etiqueta
            if label_data_base64:
                label_binary = base64.b64decode(label_data_base64)
                etiqueta_dir = os.path.join(settings.MEDIA_ROOT, 'etiquetas')
                os.makedirs(etiqueta_dir, exist_ok=True)
                etiqueta_filename = f"etiqueta_{pedido.numero_orden}.pdf"
                etiqueta_path = os.path.join(etiqueta_dir, etiqueta_filename)
                with open(etiqueta_path, 'wb') as etiqueta_file:
                    etiqueta_file.write(label_binary)
                etiqueta_rel_path = f"etiquetas/{etiqueta_filename}"
            else:
                etiqueta_rel_path = ""

            # Actualizar o crear TransportOrder
            transport_order, created = TransportOrder.objects.update_or_create(
                pedido=pedido,
                defaults={
                    "transport_order_number": tracking_number,
                    "certificate_number": response_data.get("data", {}).get("header", {}).get("certificateNumber"),
                    "label_type": pedido.label_type,
                    "estado": 'generado',
                    "etiqueta": etiqueta_rel_path,
                    "respuesta_api": response_data,
                }
            )

            # Actualizar el estado del pedido
            pedido.estado_envio = "generado"
            pedido.numero_seguimiento = tracking_number
            pedido.respuesta_envio = response_data
            pedido.save()

            # Crear EnvioGenerado con estado 'generado'
            EnvioGenerado.objects.create(
                pedido=pedido,
                numero_seguimiento=tracking_number,
                estado='generado',
                fecha_generacion=timezone.now(),
                etiqueta=etiqueta_rel_path
            )

            # Enviar correo de confirmación
            if request is None:
                from django.test import RequestFactory
                request = RequestFactory().get("/")

            resultado_correo = enviar_correo_confirmacion(
                request=request,
                cliente_email=cliente.email,
                cliente_nombre=cliente.nombre,
                numero_orden=pedido.numero_orden,
                tracking_number=tracking_number,
            )

            if not resultado_correo["success"]:
                logger.error(f"Error al enviar el correo: {resultado_correo['error']}")

            return {"success": True, "data": response_data}
        else:
            error_response = response.json()
            return {"success": False, "error": error_response.get("errors", ["Error desconocido"])[0]}

    except Exception as e:
        logger.error(f"Error general: {e}")
        return {"success": False, "error": str(e)}


import requests
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from naturalworld_d.models import Pedido
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from naturalworld_d.models import Pedido
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from naturalworld_d.models import Pedido
import requests  # Asegúrate de importar 'requests' para la API de MailerSend
from django.urls import reverse
import requests
import requests  # Asegúrate de importar 'requests' para la API de MailerSend
from django.urls import reverse
import requests
from django.conf import settings  # Agregar import settings para usar SITE_URL si no hay request

def enviar_correo_confirmacion(request, cliente_email, cliente_nombre, numero_orden, tracking_number):
    """
    Función para enviar el correo de confirmación de pedido y envío, utilizando la API de MailerSend.
    """
    api_url = "https://api.mailersend.com/v1/email"
    api_token = "mlsn.af9921bb60b889fddf5527336115a9c3db2497bec3ba3a1738d12270941b29fc"  # Tu API Token aquí directamente

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    # Aquí utilizamos directamente la URL fija de ngrok para la consulta de envío
    consultar_envio_url = "https://f4a4-181-43-149-87.ngrok-free.app/consulta-envio/"

    # Construir la URL del pedido. Si existe un request real, lo usamos, sino usamos SITE_URL
    if request is not None:
        base_url = f"{request.scheme}://{request.get_host()}"
    else:
        base_url = settings.SITE_URL

    pedido_url = f"{base_url}/pedido/{numero_orden}/"

    asunto = f"Confirmación de Pago para su pedido {numero_orden}"
    cuerpo_texto = (
        f"Hola {cliente_nombre},\n\n"
        f"Su pedido {numero_orden} ha sido procesado correctamente.\n"
        f"El número de seguimiento es: {tracking_number}.\n\n"
        f"Puede consultar su pedido aquí: {pedido_url}\n\n"
        f"También puede consultar el estado de su envío aquí: {consultar_envio_url}\n\n"
        "Gracias por su compra.\nEl equipo de The World of Natural Medicine."
    )
    cuerpo_html = (
        f"<p>Hola {cliente_nombre},</p>"
        f"<p>Su pedido <strong>{numero_orden}</strong> ha sido procesado correctamente.</p>"
        f"<p>El número de seguimiento es: <strong>{tracking_number}</strong>.</p>"
        f"<p>También puede consultar el estado de su envío aquí y ver su pedido: <a href='{consultar_envio_url}'>Consultar Envío</a></p>"
        f"<p>Gracias por su compra.<br>El Equipo de The World of Natural Medicine.</p>"
    )

    payload = {
        "from": {
            "email": "remitente@trial-z3m5jgrwzr0ldpyo.mlsender.net",  # Cambia por el correo remitente configurado en MailerSend
            "name": "The World of Natural Medicine"
        },
        "to": [{"email": cliente_email}],
        "subject": asunto,
        "text": cuerpo_texto,
        "html": cuerpo_html,
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        return {"success": True, "message": "Correo enviado correctamente"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
    
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Pedido
import requests

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from .models import Pedido
import requests

# API Key definida al inicio
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from .models import Pedido
import requests
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Pedido
import requests

from django.shortcuts import render
from django.http import JsonResponse
import requests

from django.shortcuts import render
from django.http import JsonResponse
import requests
from django.shortcuts import render
from .models import Pedido, DetallePedido, EnvioGenerado

import requests
from django.shortcuts import render
from .models import Pedido, DetallePedido, EnvioGenerado

API_KEY = "f3f0c3d9b9d34032a559426ab9e6cdda"  # Clave de la API

def consulta_individual_envio(transportOrderNumber, reference, showTrackingEvents=1):
    """
    Realiza una consulta individual al estado del envío en la API de Chilexpress.
    """
    url = "http://testservices.wschilexpress.com/transport-orders/api/v1.0/tracking"
    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": API_KEY
    }

    payload = {
        "transportOrderNumber": transportOrderNumber,
        "reference": reference,
        "rut": "96756430",  # RUT fijo proporcionado por Chilexpress
        "showTrackingEvents": showTrackingEvents
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def consultar_envio(request):
    if request.method == "POST":
        numero_orden = request.POST.get("numero_orden")

        # Verificar que se haya proporcionado un número de orden
        if not numero_orden:
            return render(request, "consulta_envio.html", {"error": "Debe proporcionar el número de orden del pedido."})

        # Buscar el pedido en la base de datos usando el número de orden
        try:
            pedido = Pedido.objects.get(numero_orden=numero_orden)
            transport_order = pedido.transport_order  # Relación con la tabla TransportOrder
            transportOrderNumber = transport_order.transport_order_number
            reference = pedido.numero_orden
        except Pedido.DoesNotExist:
            return render(request, "consulta_envio.html", {"error": "No se encontró el pedido con el número de orden proporcionado."})
        except AttributeError:
            return render(request, "consulta_envio.html", {"error": "El pedido no tiene una orden de transporte asociada."})

        # Consultar estado del envío con la API de Chilexpress
        resultado = consulta_individual_envio(transportOrderNumber, reference)

        if "error" in resultado:
            return render(request, "consulta_envio.html", {
                "error": resultado.get("error", "Error desconocido.")
            })

        # Procesar datos relevantes de la API
        data = resultado.get("data", {})
        transport_order_data = data.get("transportOrderData", {})
        address_data = data.get("addressData", {})
        tracking_events = data.get("trackingEvents", [])

        # Obtener detalles del pedido local
        try:
            envio_generado = pedido.envio  # Relación con el modelo EnvioGenerado
            fecha_generacion = envio_generado.fecha_generacion
            pedido_estado = envio_generado.estado

            # Detalles del pedido (productos comprados)
            detalles = DetallePedido.objects.filter(pedido=pedido)
            detalles_list = [
                {
                    'producto': d.producto.nombre,
                    'cantidad': d.cantidad,
                    'precio_unitario': d.precio_unitario,
                    'subtotal': d.cantidad * d.precio_unitario
                } for d in detalles
            ]

        except (Pedido.DoesNotExist, AttributeError):
            fecha_generacion = None
            pedido_estado = None
            detalles_list = None

        context = {
            "estado": transport_order_data.get("status"),
            "referencia": transport_order_data.get("reference"),
            "servicio": transport_order_data.get("service"),
            "peso": transport_order_data.get("weight"),
            "dimensiones": transport_order_data.get("dimensions"),
            "ubicacion": transport_order_data.get("locationStatus"),
            "direccion_destino": address_data.get("address"),
            "fecha_generacion": fecha_generacion,
            "pedido_estado": pedido_estado,
            "eventos": tracking_events,
            "detalles": detalles_list,
        }

        return render(request, "consulta_envio.html", context)

    return render(request, "consulta_envio.html")



def confirmacion(request):
    contexto = {
        'mensaje': 'Tu pedido se ha procesado correctamente.'
    }
    return render(request, 'confirmacion.html', contexto)




import requests
import base64
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image

import requests
import base64
import os
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image

# API Key global, se reutiliza para todas las funciones
import requests  # Asegúrate de importar requests si no está ya importado

# Clave API
import requests
import base64
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image
from django.core.files.base import ContentFile
from naturalworld_d.models import TransportOrder

import os
import base64
import requests
import logging
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image
from django.core.files.base import ContentFile
from django.conf import settings

# Clave de la API de Chilexpress (obligatoria)
import os
import base64
import requests
import logging
from django.utils import timezone
from django.conf import settings
from .models import TransportOrder

logger = logging.getLogger(__name__)

def reimprimir_etiqueta(pedido, request=None):
    """
    Reimprime la etiqueta de una Orden de Transporte existente con labelType=2 (Imagen en Binario + Datos).
    """
    CHILEXPRESS_SUBSCRIPTION_KEY = os.getenv('CHILEXPRESS_SUBSCRIPTION_KEY', 'f3f0c3d9b9d34032a559426ab9e6cdda')  # Usar variable de entorno
    label_type = 2  # Forzamos labelType a 2
    url = os.getenv('CHILEXPRESS_API_URL', 'http://testservices.wschilexpress.com/transport-orders/api/v1.0/transport-orders-labels')

    try:
        # Validar que el pedido tenga un número de seguimiento
        if not pedido.numero_seguimiento:
            logger.error(f"El pedido {pedido.id} no tiene un número de seguimiento asociado. No se puede reimprimir etiqueta.")
            return {"success": False, "error": "No hay número de seguimiento para reimprimir etiqueta."}

        # Preparar el payload
        payload = {
            "transportOrderNumber": str(pedido.numero_seguimiento),  # Cambiado a str para evitar problemas de tipo
            "labelType": label_type
        }

        headers = {
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": CHILEXPRESS_SUBSCRIPTION_KEY
        }

        logger.debug(f"Enviando payload de reimpresión:\n{payload}")
        response = requests.post(url, json=payload, headers=headers)
        logger.debug(f"Respuesta de la API reimpresión: {response.status_code} - {response.text}")

        if response.status_code == 200:
            response_data = response.json()
            detail = response_data.get("data", {}).get("detail", [{}])[0]
            label_data_base64 = detail.get("label", {}).get("labelData", "")

            etiqueta_rel_path = ""
            if label_data_base64:
                label_binary = base64.b64decode(label_data_base64)
                
                # Crear directorio si no existe
                etiqueta_dir = os.path.join(settings.MEDIA_ROOT, 'etiquetas')
                os.makedirs(etiqueta_dir, exist_ok=True)
                
                # Guardar la etiqueta como PDF
                etiqueta_filename = f"etiqueta_reimp_{pedido.numero_seguimiento}.pdf"
                etiqueta_path = os.path.join(etiqueta_dir, etiqueta_filename)
                
                with open(etiqueta_path, 'wb') as etiqueta_file:
                    etiqueta_file.write(label_binary)
                
                etiqueta_rel_path = f"etiquetas/{etiqueta_filename}"

            # Actualizar o crear TransportOrder con la nueva etiqueta
            transport_order, created = TransportOrder.objects.update_or_create(
                pedido=pedido,
                defaults={
                    'transport_order_number': str(pedido.numero_seguimiento),
                    'certificate_number': response_data.get("data", {}).get("header", {}).get("certificateNumber"),
                    'label_type': str(label_type),
                    'estado': 'generado',
                    'etiqueta': etiqueta_rel_path,
                    'respuesta_api': response_data,
                    'fecha_actualizacion': timezone.now()
                }
            )

            if created:
                logger.info(f"TransportOrder creada exitosamente para el pedido {pedido.id}")
            else:
                logger.info(f"TransportOrder actualizada para el pedido {pedido.id}")

            return {"success": True, "data": response_data}

        else:
            try:
                error_response = response.json()
                error_msg = error_response.get("errors", ["Error desconocido"])[0]
            except Exception as e:
                logger.error(f"Error al decodificar la respuesta de la API: {e}")
                error_msg = "Error desconocido"

            logger.error(f"Error en la reimpresión de la etiqueta: {error_msg}")
            return {"success": False, "error": error_msg}

    except Exception as e:
        logger.error(f"Error general en reimpresión de etiqueta: {e}")
        return {"success": False, "error": str(e)}
