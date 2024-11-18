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


API_BASE_URL = "https://testservices.wschilexpress.com/georeference/api/v1.0"
API_KEY = "9b0dd01cf2944af9a9c179e3176f45ca"  # Coloca tu clave de API correcta

def consultar_cobertura_real(region_code, tipo_cobertura):
    url = f"{API_BASE_URL}/coverage-areas?RegionCode={region_code}&type={tipo_cobertura}"
    headers = {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
        'Ocp-Apim-Subscription-Key': API_KEY,
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Verificar si la respuesta contiene datos de cobertura
        datos_cobertura = response.json()
        if datos_cobertura.get("statusCode") == 0 and datos_cobertura.get("coverageAreas"):
            return datos_cobertura["coverageAreas"]
        else:
            return {"error": "No se encontró información de cobertura para los parámetros proporcionados."}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}





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
        
        if resultado.get("statusCode") == 0 and "data" in resultado:
            return resultado["data"]
        else:
            return {"error": resultado.get("statusDescription", "Error desconocido")}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}



from django.conf import settings

def obtener_token():
    url = "https://api.wschilexpress.com/oauth2/token"
    payload = {
        'grant_type': 'client_credentials',
        'client_id': settings.WS_CHILE_EXPRESS_PRIMARY_KEY,
        'client_secret': settings.WS_CHILE_EXPRESS_SECONDARY_KEY,
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    return response.json().get('access_token')
def obtener_token():
    url = "https://api.wschilexpress.com/oauth2/token"
    payload = {
        'grant_type': 'client_credentials',
        'client_id': settings.WS_CHILE_EXPRESS_PRIMARY_KEY,
        'client_secret': settings.WS_CHILE_EXPRESS_SECONDARY_KEY,
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    return response.json().get('access_token')


def generar_envio(origin_code, destination_code, package, product_type, declared_worth):
    url = "https://api.wschilexpress.com/rest/transport-orders-api/v1/shipments"
    headers = {
        'Authorization': f'Bearer {obtener_token()}',
        'Content-Type': 'application/json',
    }
    data = {
        "originCountyCode": origin_code,
        "destinationCountyCode": destination_code,
        "package": package,
        "productType": product_type,
        "declaredWorth": declared_worth,
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

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
