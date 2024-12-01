import urllib.request
import json
import requests


API_BASE_URL = "https://testservices.wschilexpress.com/georeference/api/v1.0" 
API_KEY = "9b0dd01cf2944af9a9c179e3176f45ca"  # Asegúrate de que tu clave esté correcta

def consultar_calles(county_name, street_name, limit=10, points_of_interest_enabled=False, street_name_enabled=True, road_type=0):
    url = f"{API_BASE_URL}/streets/search"
    headers = {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
        'Ocp-Apim-Subscription-Key': API_KEY,
    }

    # Datos del cuerpo de la solicitud
    data = {
        "countyName": county_name,
        "streetName": street_name,
        "pointsOfInterestEnabled": points_of_interest_enabled,
        "streetNameEnabled": street_name_enabled,
        "roadType": road_type
    }

    # Convertir el cuerpo a JSON
    data = json.dumps(data)
    req = urllib.request.Request(url, headers=headers, data=bytes(data.encode("utf-8")))
    req.get_method = lambda: 'POST'

    try:
        response = urllib.request.urlopen(req)
        if response.getcode() == 200:
            return json.loads(response.read().decode('utf-8'))
        else:
            return {"error": "No se pudo obtener una respuesta válida"}
    except Exception as e:
        return {"error": str(e)}


API_BASE_URL_COTIZADOR = "https://testservices.wschilexpress.com/rating/api/v1.0"
API_KEY_COTIZADOR = "7479a6dfcb6d4627ad3fbf616b2e9b5b"  # Reemplaza con tu clave de suscripción

def cotizar_envio(originCountyCode, destinationCountyCode, package, productType, declaredWorth, deliveryTime=0):
    url = f"{API_BASE_URL_COTIZADOR}/rates/courier"

    headers = {
        "Ocp-Apim-Subscription-Key": API_KEY_COTIZADOR,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache"
    }
    
    # Estructura de datos para el request
    data = {
        "originCountyCode": originCountyCode,
        "destinationCountyCode": destinationCountyCode,
        "package": package,  # Diccionario con weight, height, width, length
        "productType": productType,
        "contentType": 1,  # Por defecto, puedes ajustar según sea necesario
        "declaredWorth": declaredWorth,
        "deliveryTime": deliveryTime
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al solicitar la cotización: {e}")
        return {"error": "Error al obtener la cotización"}

import requests
import requests
import logging

logger = logging.getLogger(__name__)

API_BASE_URL = "https://testservices.wschilexpress.com/georeference/api/v1.0"
API_KEY = "9b0dd01cf2944af9a9c179e3176f45ca"

def consultar_cobertura_real(region_code, tipo_cobertura):
    """
    Consulta las áreas de cobertura disponibles.
    """
    url = f"{API_BASE_URL}/coverage-areas?RegionCode={region_code}&type={tipo_cobertura}"
    headers = {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
        'Ocp-Apim-Subscription-Key': API_KEY,
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Depurar el contenido completo de la respuesta
        logger.info(f"Respuesta completa de la API: {response.text}")

        datos_cobertura = response.json()
        if datos_cobertura.get("statusCode") == 0 and datos_cobertura.get("coverageAreas"):
            return datos_cobertura["coverageAreas"]
        else:
            return {"error": "No se encontró información de cobertura para los parámetros proporcionados."}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la consulta a la API de cobertura: {str(e)}")
        return {"error": str(e)}
    except ValueError as ve:
        logger.error(f"Error al procesar la respuesta JSON: {str(ve)}")
        return {"error": "La API no devolvió un JSON válido."}



# Define estos valores según los datos de tu cuenta en Chilexpress
API_BASE_URL = "http://testservices.wschilexpress.com/georeference/api/v1.0"
API_KEY = "9b0dd01cf2944af9a9c179e3176f45ca"

def consultar_numeracion(street_name_id, street_number):
    url = f"{API_BASE_URL}/streets/{street_name_id}/numbers"
    headers = {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
        'Ocp-Apim-Subscription-Key': API_KEY,
    }
    params = {
        'streetNumber': street_number
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        if data.get("statusCode") == 0:
            return data["streetNumbers"]
        else:
            return {"error": data.get("statusDescription", "Error en la consulta de numeración")}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
    


API_BASE_URL = "http://testservices.wschilexpress.com/georeference/api/v1.0"
API_KEY = "9b0dd01cf2944af9a9c179e3176f45ca"  # Asegúrate de reemplazar con tu clave de suscripción
def georreferenciar_direccion(county_name, street_name, number):
    url = f"{API_BASE_URL}/addresses/georeference"
    headers = {
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': API_KEY
    }
    data = {
        "countyName": county_name,
        "streetName": street_name,
        "number": number
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        resultado = response.json()
        
        # Verificar si la respuesta contiene la clave "statusCode" y "data"
        if resultado.get("statusCode") == 0 and "data" in resultado:
            return resultado["data"]
        else:
            # Si no se encuentra la comuna o la cobertura
            error_message = resultado.get("statusDescription", "Error desconocido")
            return {"error": error_message}
    
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}




from django.conf import settings
import requests
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def generar_envio(pedido, customer_card_number, origin_code, destination_code, package_details, contact_details):
    """
    Genera un envío en Chilexpress usando la API de Transport Orders.

    :param pedido: Objeto Pedido con los datos del envío.
    :param customer_card_number: TCC del cliente.
    :param origin_code: Código de cobertura de origen.
    :param destination_code: Código de cobertura de destino.
    :param package_details: Diccionario con los detalles del paquete.
    :param contact_details: Diccionario con los detalles de contacto.
    :return: Respuesta de la API de Chilexpress.
    """
    # API key y URL
    API_KEY = getattr(settings, "CHILEXPRESS_API_KEY", "f3f0c3d9b9d34032a559426ab9e6cdda")  # Cambia según configuración
    API_URL = "http://testservices.wschilexpress.com/transport-orders/api/v1.0/transport-orders"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Ocp-Apim-Subscription-Key": API_KEY
    }

    # Verificar datos esenciales
    if not pedido or not pedido.direccion or not pedido.cliente:
        return {"success": False, "error": "Datos del pedido incompletos"}

    # Construcción del payload
    body = {
        "header": {
            "certificateNumber": 0,  # Número de certificado opcional
            "customerCardNumber": customer_card_number,
            "countyOfOriginCoverageCode": origin_code,
            "labelType": 2,  # Imagen Binaria + Datos
            "marketplaceRut": "96756430",  # RUT de prueba
            "sellerRut": "DEFAULT"
        },
        "details": [  # Detalles del envío
            {
                "addresses": [  # Dirección
                    {
                        "countyCoverageCode": destination_code,
                        "streetName": pedido.direccion.street_name,
                        "streetNumber": pedido.direccion.street_number or "0",
                        "supplement": pedido.direccion.supplement or "",
                        "addressType": "DEST",
                        "deliveryOnCommercialOffice": contact_details.get("deliveryOnCommercialOffice", False),
                        "observation": contact_details.get("observation", "Entrega estándar")
                    }
                ],
                "contacts": [  # Contactos
                    {
                        "name": pedido.cliente.nombre,
                        "phoneNumber": pedido.cliente.telefono or "000000000",
                        "mail": pedido.cliente.email,
                        "contactType": "D"
                    },
                    {
                        "name": "Remitente de Prueba",
                        "phoneNumber": "987654321",
                        "mail": "remitente@prueba.cl",
                        "contactType": "R"
                    }
                ],
                "packages": [  # Paquetes
                    {
                        "weight": package_details["weight"],
                        "height": package_details["height"],
                        "width": package_details["width"],
                        "length": package_details["length"],
                        "serviceDeliveryCode": package_details["serviceDeliveryCode"],
                        "productCode": package_details["productCode"],
                        "deliveryReference": f"PED-{pedido.id}",
                        "groupReference": f"GRP-{pedido.id}",
                        "declaredValue": package_details.get("declaredValue", pedido.total),
                        "declaredContent": package_details.get("declaredContent", 5)
                    }
                ]
            }
        ]
    }

    try:
        # Enviar solicitud POST
        response = requests.post(API_URL, json=body, headers=headers)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("statusCode") == 0:
            logger.info(f"Envío generado exitosamente para pedido {pedido.id}")
            return {"success": True, "data": response_data}

        error_message = response_data.get("statusDescription", "Error desconocido")
        logger.error(f"Error al generar envío para pedido {pedido.id}: {error_message}")
        return {"success": False, "error": error_message}

    except requests.RequestException as e:
        logger.error(f"Excepción al llamar a la API de Chilexpress: {e}")
        return {"success": False, "error": str(e)}


from django.conf import settings


from .carrito import Carrito

def obtener_datos_carrito(request):
    carrito = Carrito(request).carrito
    total_peso = 0
    total_largo = 0
    total_ancho = 0
    total_alto = 0
    valor_total = 0

    for item in carrito.values():
        cantidad = item['cantidad']
        peso = float(item['peso'])
        largo = float(item['largo'])
        ancho = float(item['ancho'])
        alto = float(item['alto'])
        precio = float(item['precio'])

        total_peso += peso * cantidad
        # Dependiendo de cómo empaquetas los productos, puedes ajustar estas sumas
        total_largo += largo * cantidad  # Por ejemplo, sumamos los largos
        total_ancho = max(total_ancho, ancho)  # Tomamos el ancho máximo
        total_alto = max(total_alto, alto)     # Tomamos el alto máximo
        valor_total += precio * cantidad

    return {
        'peso': total_peso,
        'largo': total_largo,
        'ancho': total_ancho,
        'alto': total_alto,
        'valor': valor_total,
    }


