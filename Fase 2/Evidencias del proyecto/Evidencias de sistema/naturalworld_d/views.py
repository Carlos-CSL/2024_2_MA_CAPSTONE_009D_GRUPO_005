from django.shortcuts import render, get_object_or_404, redirect
from .models import Producto, Comentario, Perfil
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
from .forms import LoginForm, RegistroForm, ProductoForm
from django.contrib.auth import authenticate, login


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

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data.get('nombre')
            user.last_name = form.cleaned_data.get('apellido')
            user.email = form.cleaned_data.get('email')
            user.save()
            
            # Crear perfil asociado
            Perfil.objects.create(
                user=user,
                rut=form.cleaned_data.get('rut'),
                numero_telefono=form.cleaned_data.get('numero_telefono')
            )
            
            # Autenticar y loguear al usuario
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')  # Cambia 'inicio' por la URL de inicio de tu sitio
        else:
            messages.error(request, "Por favor, corrige los errores a continuación.")
    else:
        form = RegistroForm()
    
    return render(request, 'registration/registro.html', {'form': form})

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

def crear_preferencia(request):
    if request.method == 'POST':
        sdk = mercadopago.SDK("APP_USR-7989794511721795-103003-30ce8ee651d7e12a6f9180d1369215df-2065223385")

        carrito = Carrito(request)

        # Obtener y verificar el costo de envío desde el JSON del cuerpo de la solicitud
        try:
            data = json.loads(request.body)
            costo_envio = float(data.get('costo_envio', 0))
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({"error": "Costo de envío no válido"}, status=400)

        # Construir los items en base a cada producto en el carrito, agregando el costo de envío como un item separado
        items = [
            {
                "title": item['nombre'],
                "quantity": item['cantidad'],
                "unit_price": float(item['precio'])
            }
            for item in carrito.carrito.values()
        ]

        # Agregar el costo de envío como un item adicional
        if costo_envio > 0:
            items.append({
                "title": "Costo de Envío",
                "quantity": 1,
                "unit_price": costo_envio
            })

        # Configura la preferencia de pago
        preference_data = {
            "items": items,
            "back_urls": {
                "success": "https://yourdomain.com/success/",
                "failure": "https://yourdomain.com/failure/",
                "pending": "https://yourdomain.com/pending/"
            },
            "auto_return": "approved",
            "notification_url": "https://yourdomain.com/producto/webhook/",
            "external_reference": f"carrito-{request.session.session_key}"
        }

        # Crear la preferencia en Mercado Pago
        preference_response = sdk.preference().create(preference_data)
        if "response" in preference_response and "id" in preference_response["response"]:
            return JsonResponse({"preference_id": preference_response["response"]["id"]})
        else:
            print("Error en la respuesta de Mercado Pago:", preference_response)
            return JsonResponse({"error": "Error al crear la preferencia"}, status=500)

    return JsonResponse({"error": "Método no permitido"}, status=405)



#def buscar_calle(request):
    if request.method == 'POST':
        county_name = request.POST.get('countyName')
        street_name = request.POST.get('streetName')
        resultado = consultar_calles(county_name, street_name)

        # Procesa y pasa los resultados al template
        if "error" in resultado:
            return render(request, 'template_a_mostrar.html', {'error': resultado["error"]})
        
        calles = resultado.get("streets", [])  # Asegúrate de extraer la lista de calles
        return render(request, 'consultar_calles.html', {'calles': calles})
    
    return render(request, 'consultar_calles.html')

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

def georreferenciar_direccion_view(request):
    if request.method == 'POST':
        county_name = request.POST.get('countyName')
        street_name = request.POST.get('streetName')
        number = request.POST.get('streetNumber')
        
        resultado = georreferenciar_direccion(county_name, street_name, number)
        
        if "error" in resultado:
            return render(request, 'georreferenciar_direccion.html', {'error': resultado["error"]})
        
        return render(request, 'georreferenciar_direccion.html', {
            'latitude': resultado["latitude"],
            'longitude': resultado["longitude"],
            'addressId': resultado["addressId"]
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


from .utils import generar_envio

def generar_envio_view(request, producto_id):
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

        try:
            resultado_envio = generar_envio(origin_code, destination_code, package, product_type, declared_worth)
            return render(request, 'confirmacion_envio.html', {
                'producto': producto,
                'resultado_envio': resultado_envio,
            })
        except Exception as e:
            return render(request, 'seleccionar_direccion.html', {
                'producto': producto,
                'error': str(e)
            })

    return redirect('seleccionar_direccion', producto_id=producto.id)


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

def ver_carrito(request):
    carrito = Carrito(request)
    return render(request, 'ver_carrito.html', {'carrito': carrito.carrito})



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

import logging
import json

logger = logging.getLogger(__name__)

# views.py

def checkout(request):
    carrito = Carrito(request)
    if not carrito.carrito:
        return redirect('ver_carrito')

    if request.method == 'POST':
        comuna = request.POST.get('comuna')
        direccion = request.POST.get('direccion')
        calle = request.POST.get('calle')
        numero = request.POST.get('numero')

        if not comuna or not direccion or not calle or not numero:
            return render(request, 'checkout.html', {'error': "Todos los campos son obligatorios."})

        # Georeferenciar la dirección
        georef = georreferenciar_direccion(comuna, calle, numero)
        logger.debug(f"Resultado de georreferenciar_direccion: {georef}")

        if 'error' in georef:
            logger.error(f"Error en georeferenciación: {georef['error']}")
            return render(request, 'checkout.html', {'error': f"Error al georeferenciar la dirección: {georef['error']}"})

        # Obtener datos del paquete a partir del carrito
        datos_paquete = obtener_datos_carrito(request)
        logger.debug(f"datos_paquete: {datos_paquete}")

        if isinstance(datos_paquete, str):
            try:
                datos_paquete = json.loads(datos_paquete)
                logger.debug("datos_paquete parseado correctamente.")
            except json.JSONDecodeError:
                logger.error("Error al parsear datos_paquete desde JSON.")
                return render(request, 'checkout.html', {'error': "Error en los datos del carrito."})

        # Verificar que datos_paquete es un diccionario y contiene las claves necesarias
        if not isinstance(datos_paquete, dict):
            logger.error("datos_paquete no es un diccionario después del parseo.")
            return render(request, 'checkout.html', {'error': "Datos del carrito inválidos."})

        claves_esperadas = {'peso', 'alto', 'ancho', 'largo', 'valor'}
        if not claves_esperadas.issubset(datos_paquete.keys()):
            logger.error(f"datos_paquete faltan claves esperadas. Claves recibidas: {datos_paquete.keys()}")
            return render(request, 'checkout.html', {'error': "Datos del carrito incompletos."})

        # Integrar las APIs de Chilexpress
        region_code = 'RM'  # Región Metropolitana
        tipo_cobertura = 1   # Tipo de cobertura (1 para comunas)

        # Código de cobertura para la comuna de origen
        resultado_cobertura_real_origen = consultar_cobertura_real(region_code, tipo_cobertura)
        logger.debug(f"resultado_cobertura_real_origen: {resultado_cobertura_real_origen}")

        if not isinstance(resultado_cobertura_real_origen, list):
            logger.error("resultado_cobertura_real_origen no es una lista.")
            return render(request, 'checkout.html', {'error': "Error al obtener cobertura de origen."})

        # Asegurarse de que cada elemento en la lista es un diccionario
        origin_code = next(
            (area['countyCode'] for area in resultado_cobertura_real_origen 
             if isinstance(area, dict) and area.get('countyName', '').upper() == "EL MONTE"),
            None
        )

        if not origin_code:
            logger.error("No se encontró el código de cobertura para la comuna de origen.")
            return render(request, 'checkout.html', {'error': "No se encontró el código de cobertura para la comuna de origen."})

        # Código de cobertura para la comuna de destino
        resultado_cobertura_real_destino = consultar_cobertura_real(region_code, tipo_cobertura)
        logger.debug(f"resultado_cobertura_real_destino: {resultado_cobertura_real_destino}")

        if not isinstance(resultado_cobertura_real_destino, list):
            logger.error("resultado_cobertura_real_destino no es una lista.")
            return render(request, 'checkout.html', {'error': "Error al obtener cobertura de destino."})

        destination_code = next(
            (area['countyCode'] for area in resultado_cobertura_real_destino 
             if isinstance(area, dict) and area.get('countyName', '').upper() == comuna.upper()),
            None
        )

        if not destination_code:
            logger.error("No se encontró el código de cobertura para la comuna de destino.")
            return render(request, 'checkout.html', {'error': "No se encontró el código de cobertura para la comuna de destino."})

        # Preparar el paquete para cotizar el envío
        package = {
            "weight": datos_paquete.get('peso'),
            "height": datos_paquete.get('alto'),
            "width": datos_paquete.get('ancho'),
            "length": datos_paquete.get('largo')
        }
        product_type = 3  # Encomienda por defecto
        declared_worth = datos_paquete.get('valor')

        logger.debug(f"Paquete preparado para cotización: {package}")

        # Llamada a la API de Cotizador
        resultado = cotizar_envio(origin_code, destination_code, package, product_type, declared_worth)
        logger.debug(f"resultado de cotizar_envio: {resultado}")

        if not isinstance(resultado, dict):
            logger.error("resultado de cotizar_envio no es un diccionario.")
            return render(request, 'checkout.html', {'error': "Error al cotizar el envío."})

        resultado_cotizacion = resultado.get("data", {}).get("courierServiceOptions", [])
        logger.debug(f"resultado_cotizacion: {resultado_cotizacion}")

        if not isinstance(resultado_cotizacion, list):
            logger.error("courierServiceOptions no es una lista.")
            resultado_cotizacion = []

        # Seleccionar la opción "EXPRESS"
        resultado_cotizacion_filtrado = [
            option for option in resultado_cotizacion
            if isinstance(option, dict) and option.get("serviceDescription") == "EXPRESS"
        ]

        logger.debug(f"resultado_cotizacion_filtrado: {resultado_cotizacion_filtrado}")

        if not resultado_cotizacion_filtrado:
            logger.error("No se encontraron opciones de envío disponibles para 'EXPRESS'.")
            return render(request, 'checkout.html', {'error': "No se encontraron opciones de envío disponibles para 'EXPRESS'."})

        try:
            costo_envio = float(resultado_cotizacion_filtrado[0]['serviceValue'])
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error al obtener serviceValue: {e}")
            return render(request, 'checkout.html', {'error': "Error al obtener el costo de envío."})

        # Cálculo total_pagar
        total_pagar = 0
        for item in carrito.carrito.values():
            if isinstance(item, dict) and 'cantidad' in item and 'precio' in item:
                try:
                    cantidad = float(item['cantidad'])
                    precio = float(item['precio'])
                    total_pagar += cantidad * precio
                except (ValueError, TypeError) as e:
                    logger.error(f"Error al convertir cantidad/precio: {e} en item: {item}")
            else:
                logger.warning(f"Item inválido en el carrito: {item}")
        total_pagar += costo_envio

        logger.debug(f"total_pagar calculado: {total_pagar}")

        # Guardar los datos necesarios en la sesión
        request.session['costo_envio'] = costo_envio
        request.session['total_pagar'] = total_pagar
        request.session['direccion'] = {
            'comuna': comuna,
            'direccion': direccion,
            'calle': calle,
            'numero': numero,
            'georeferencia': georef  # Guardar la georeferencia en la sesión
        }

        # Redirigir a la página de pago sin argumentos
        return redirect('pago')

    else:
        return render(request, 'checkout.html')


# views.py

from django.shortcuts import render, get_object_or_404
from .models import Producto

def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, 'producto_detalle.html', {'producto': producto})



def listar_productos(request):
    productos = Producto.objects.all()
    return render(request, 'listar_productos.html', {'productos': productos})

# naturalworld_d/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from .models import Producto
from .carrito import Carrito


# naturalworld_d/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from .models import Producto
from .carrito import Carrito

# views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from .carrito import Carrito
from .utils import cotizar_envio, consultar_cobertura_real, obtener_datos_carrito, georreferenciar_direccion
from .models import Producto

import logging
import json

logger = logging.getLogger(__name__)


# views.py

def pago(request):
    carrito = Carrito(request)
    if not carrito.carrito:
        return redirect('ver_carrito')

    if request.method == 'POST':
        # Aquí debes integrar la lógica para procesar el pago con Mercado Pago u otro método
        # Por ejemplo, crear una preferencia de pago y redirigir al usuario al flujo de pago

        # Supongamos que el pago es exitoso:
        with transaction.atomic():
            for item in carrito.carrito.values():
                producto = get_object_or_404(Producto, id=item['producto_id'])
                cantidad_comprada = item['cantidad']
                if producto.stock >= cantidad_comprada:
                    producto.stock -= cantidad_comprada
                    producto.save()
                else:
                    # Manejar el caso donde el stock es insuficiente
                    return render(request, 'error.html', {'mensaje': f"No hay suficiente stock para {producto.nombre}."})

            # Aquí podrías agregar lógica para crear un objeto Pedido si tienes un modelo para ello

            # Limpiar el carrito y la sesión
            carrito.clear()
            request.session.pop('costo_envio', None)
            request.session.pop('direccion', None)
            request.session.pop('total_pagar', None)

            # Redirigir a una página de confirmación
            return render(request, 'confirmacion.html', {'mensaje': 'Pago realizado con éxito.'})
    else:
        # Mostrar resumen del pedido
        costo_envio = request.session.get('costo_envio')
        direccion = request.session.get('direccion')
        total_pagar = request.session.get('total_pagar')

        if not costo_envio or not direccion or not total_pagar:
            logger.error("Faltan datos en la sesión para procesar el pago.")
            return redirect('checkout')

        contexto = {
            'carrito': carrito.carrito.values(),  # Asumiendo que es un diccionario de ítems
            'costo_envio': costo_envio,
            'total_pagar': total_pagar,
            'direccion': direccion,
        }
        return render(request, 'pago.html', contexto)
