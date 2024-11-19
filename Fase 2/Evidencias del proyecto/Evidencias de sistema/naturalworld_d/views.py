from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django import template
import json
import mercadopago
from .models import Producto, Comentario, PedidoProducto, Pedido, Perfil
from .forms import LoginForm, RegistroForm, ProductoForm
from .utils import consultar_calles, georreferenciar_direccion, consultar_cobertura_real, cotizar_envio
import locale


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
def admin_pedidos(request):
    pedido = Pedido.objects.all()
    datos = {
        'pedido': pedido
    }
    return render(request, 'admin_pedidos.html', datos)

def actualizar_estado_pedido(request, pedido_id):
    # Verificamos que el pedido_id es un UUID válido
    try:
        pedido = Pedido.objects.get(id=pedido_id)  # Aquí Django convertirá automáticamente el UUID en el filtro
    except Pedido.DoesNotExist:
        # Redirige si no se encuentra el pedido
        return redirect('admin_pedidos')  

    if request.method == "POST":
        # Obtén el nuevo estado del formulario
        nuevo_estado = request.POST.get('estado_pedido')
        # Actualiza el estado del pedido
        pedido.estado_pedido = nuevo_estado
        pedido.save()  # Guarda el pedido con el nuevo estado
        return redirect('admin_pedidos')  # Redirige después de actualizar el estado

    # Si la petición es GET, muestra el pedido con su estado actual (opcional, dependiendo de tu implementación)
    return render(request, 'admin_pedidos.html', {'pedido': pedido})

def seguimiento(request):
    pedido = None
    error = None
    if request.method == "POST":
        # Obtener el número de orden desde el formulario
        numero_orden = request.POST.get('numero_orden')

        try:
            # Buscar el pedido por el número de orden
            pedido = Pedido.objects.get(numero_orden=numero_orden)
            messages.success(request, "Estado del pedido actualizado")
        except Pedido.DoesNotExist:
            # Si no se encuentra el pedido, mostrar un mensaje de error
            error = "No se encontró un pedido con ese número de orden."

    return render(request, 'seguimiento.html', {'pedido': pedido, 'error': error})

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



@csrf_exempt
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
            producto = Producto.objects.get(id=item['producto_id'])
            pedido_producto, creado = PedidoProducto.objects.get_or_create(
                pedido=pedido,
                producto=producto,
                defaults={
                    'cantidad': item['cantidad'],
                    'precio_unitario': float(item['precio'])
                }
            )
            if not creado:
                pedido_producto.cantidad += item['cantidad']
                pedido_producto.save()

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
                "success": "https://6730-181-43-124-153.ngrok-free.app/success/",
                "failure": "https://6730-181-43-124-153.ngrok-free.app/failure/",
                "pending": "https://6730-181-43-124-153.ngrok-free.app/pending/"
            },
            "auto_return": "approved",
            "notification_url": "https://6730-181-43-124-153.ngrok-free.app/producto/recibir-pago/",
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
from .models import Pedido, Cliente, Producto, PedidoProducto
from .utils import cotizar_envio, georreferenciar_direccion, obtener_datos_carrito, consultar_cobertura_real
import logging
import json

def checkout(request):
    carrito = Carrito(request)
    if not carrito.carrito:
        return redirect('ver_carrito')

    if request.method == 'POST':
        # Capturar el RUT junto con los otros datos
        rut = request.POST.get('rut')
        email = request.POST.get('mail_cliente')  # Capturar el email del cliente
        comuna = request.POST.get('comuna')
        direccion = request.POST.get('direccion')
        calle = request.POST.get('calle')
        numero = request.POST.get('numero')

        # Verificar que todos los campos sean válidos
        if not rut or not comuna or not direccion or not calle or not numero:
            return render(request, 'checkout.html', {'error': "Todos los campos son obligatorios."})

        # Validación básica del RUT (puedes mejorarla según tus reglas de validación)
        if len(rut) < 7 or not rut.replace(".", "").replace("-", "").isdigit():
            return render(request, 'checkout.html', {'error': "El RUT ingresado no es válido."})

        # Crear o actualizar cliente en la base de datos
        cliente, created = Cliente.objects.get_or_create(
            rut=rut,
            defaults={'email': email, 'nombre': 'Cliente Nuevo'}  # Cambia según lo necesario
        )
        if not created:
            cliente.email = email  # Actualizar email si ya existe el cliente
            cliente.save()

        # Asociar cliente con un usuario registrado si existe
        user = cliente.user if cliente.user else None

        # Georreferenciar la dirección
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

        # Código de cobertura para la comuna de origen
        resultado_cobertura_real_origen = consultar_cobertura_real('RM', 1)  # Región Metropolitana
        logger.debug(f"resultado_cobertura_real_origen: {resultado_cobertura_real_origen}")

        origin_code = next(
            (area['countyCode'] for area in resultado_cobertura_real_origen
             if isinstance(area, dict) and area.get('countyName', '').upper() == "EL MONTE"),
            None
        )

        if not origin_code:
            logger.error("No se encontró el código de cobertura para la comuna de origen.")
            return render(request, 'checkout.html', {'error': "No se encontró el código de cobertura para la comuna de origen."})

        # Código de cobertura para la comuna de destino
        resultado_cobertura_real_destino = consultar_cobertura_real('RM', 1)
        logger.debug(f"resultado_cobertura_real_destino: {resultado_cobertura_real_destino}")

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

        resultado_cotizacion_filtrado = [
            option for option in resultado.get("data", {}).get("courierServiceOptions", [])
            if isinstance(option, dict) and option.get("serviceDescription") == "EXPRESS"
        ]

        if not resultado_cotizacion_filtrado:
            logger.error("No se encontraron opciones de envío disponibles para 'EXPRESS'.")
            return render(request, 'checkout.html', {'error': "No se encontraron opciones de envío disponibles para 'EXPRESS'."})

        costo_envio = float(resultado_cotizacion_filtrado[0].get('serviceValue', 0))
        total_pagar = sum(
            float(item.get('cantidad', 0)) * float(item.get('precio', 0))
            for item in carrito.carrito.values()
        ) + costo_envio

        # Crear el pedido
        pedido = Pedido.objects.create(
            cliente=user,  # Asigna el usuario si está registrado
            total=total_pagar
        )

        # Añadir productos al pedido
        for item in carrito.carrito.values():
            producto = Producto.objects.get(id=item['producto_id'])  # Ajusta según tu modelo
            PedidoProducto.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=item['cantidad'],
                precio_unitario=item['precio']  # Cambiado a precio_unitario
            )

        # Guardar los datos necesarios en la sesión, incluyendo el cliente
        request.session['cliente_rut'] = cliente.rut
        request.session['cliente_email'] = cliente.email
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

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import mercadopago
from .models import Pago  # Asegúrate de tener el modelo Pago configurado correctamente
from .models import Pedido, Producto, Pago  # Asegúrate de incluir todos los modelos necesarios

@csrf_exempt
@csrf_exempt
@csrf_exempt

def recibir_pago(request):
    if request.method == "POST":
        try:
            # Leer el cuerpo de la solicitud
            data = json.loads(request.body)
            event_type = data.get("type", "")
            data_payload = data.get("data", {})
            payment_id = data_payload.get("id")

            if event_type == "payment" and payment_id:
                sdk = mercadopago.SDK("APP_USR-7989794511721795-103003-30ce8ee651d7e12a6f9180d1369215df-2065223385")
                payment_info = sdk.payment().get(payment_id)

                status = payment_info["response"].get("status", "")
                status_detail = payment_info["response"].get("status_detail", "")
                external_reference = payment_info["response"].get("external_reference", "")
                monto = payment_info["response"].get("transaction_amount")

                print(f"Pago ID={payment_id}, Estado={status}, Detalle={status_detail}, Referencia={external_reference}")

                # Validar referencia externa
                if external_reference.startswith("pedido-"):
                    pedido_id = external_reference.replace("pedido-", "")
                else:
                    raise ValueError("Referencia externa inválida")

                # Validar que el pedido_id es un UUID válido
                try:
                    uuid.UUID(pedido_id)
                except ValueError:
                    raise ValueError(f"'{pedido_id}' no es un UUID válido.")

                # Obtener el pedido
                pedido = Pedido.objects.get(id=pedido_id)

                if status == "approved":
                    pedido.estado = "pagado"
                    pedido.save()

                    # Actualizar el stock basado en los productos relacionados al pedido
                    productos_pedido = PedidoProducto.objects.filter(pedido=pedido)
                    for pp in productos_pedido:
                        producto = pp.producto
                        cantidad = pp.cantidad
                        if producto.stock >= cantidad:
                            producto.stock -= cantidad
                            producto.save()
                            print(f"Stock actualizado para {producto.nombre}: {producto.stock} unidades restantes.")
                        else:
                            print(f"Stock insuficiente para {producto.nombre}.")
                            raise ValueError(f"Stock insuficiente para {producto.nombre}. Pedido no puede completarse.")

                    print("Pedido procesado y stock actualizado correctamente.")

                elif status == "pending":
                    pedido.estado = "pendiente"
                    pedido.save()
                elif status == "rejected":
                    pedido.estado = "cancelado"
                    pedido.save()

                # Crear o actualizar el registro de pago
                Pago.objects.update_or_create(
                    pedido=pedido,
                    defaults={
                        "id_pago": payment_id,
                        "estado": status,
                        "detalle_estado": status_detail,
                        "monto": monto,
                    }
                )

            return JsonResponse({"status": "success"}, status=200)

        except Exception as e:
            print(f"Error procesando el Webhook: {e}")
            return JsonResponse({"error": "Error interno del servidor"}, status=500)

    return JsonResponse({"error": "Método no permitido"}, status=405)
