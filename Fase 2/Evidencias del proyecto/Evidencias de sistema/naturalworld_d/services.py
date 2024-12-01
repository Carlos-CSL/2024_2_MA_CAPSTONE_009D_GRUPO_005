import requests
from datetime import datetime

def generar_envio(pedido):
    """
    Genera un envío en la API de Chilexpress usando los datos del pedido.
    """
    try:
        # Validar que el pedido tenga los datos necesarios
        if not pedido.direccion or not pedido.contacto_destinatario or not pedido.paquetes.exists():
            return {"success": False, "error": "Faltan datos requeridos en el pedido."}

        # Construir el payload para la solicitud
        payload = {
            "header": {
                "certificateNumber": 0,
                "customerCardNumber": "18578680",  # Número de cliente
                "countyOfOriginCoverageCode": pedido.direccion.county_coverage_code,
                "labelType": 2,
                "marketplaceRut": "96756430",
                "sellerRut": "DEFAULT"
            },
            "details": [{
                "addresses": [{
                    "addressId": pedido.direccion.api_address_id or 0,
                    "countyCoverageCode": pedido.direccion.county_coverage_code,
                    "streetName": pedido.direccion.street_name,
                    "streetNumber": pedido.direccion.street_number,
                    "supplement": pedido.direccion.supplement or "",
                    "addressType": "DEST",
                    "deliveryOnCommercialOffice": False,
                    "commercialOfficeId": pedido.direccion.commercial_office_id or 0,
                    "observation": pedido.direccion.observation or ""
                }],
                "contacts": [
                    {
                        "name": pedido.cliente.nombre,
                        "phoneNumber": pedido.cliente.telefono or "000000000",
                        "mail": pedido.cliente.email,
                        "contactType": "R"  # Remitente
                    },
                    {
                        "name": pedido.contacto_destinatario.name,
                        "phoneNumber": pedido.contacto_destinatario.phone_number,
                        "mail": pedido.contacto_destinatario.email,
                        "contactType": "D"  # Destinatario
                    }
                ],
                "packages": [
                    {
                        "weight": paquete.peso,
                        "height": paquete.altura,
                        "width": paquete.ancho,
                        "length": paquete.largo,
                        "serviceDeliveryCode": 3,  # Código de entrega
                        "productCode": 3,  # Encomienda
                        "deliveryReference": f"PED-{pedido.numero_orden}",
                        "groupReference": f"GRP-{datetime.now().strftime('%Y%m%d')}",
                        "declaredValue": paquete.valor_declarado or pedido.total,
                        "declaredContent": "Otros"
                    } for paquete in pedido.paquetes.all()
                ]
            }]
        }

        # Configurar los headers
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Ocp-Apim-Subscription-Key": "TU_CLAVE_DE_SUSCRIPCION"
        }

        # Realizar la solicitud
        url = "https://testservices.wschilexpress.com/transport-orders/api/v1.0/transport-orders"
        response = requests.post(url, json=payload, headers=headers)

        # Procesar la respuesta
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "certificate_number": data["header"]["certificateNumber"],
                "tracking_number": data["details"][0]["transportOrderNumber"]
            }
        else:
            return {
                "success": False,
                "error": response.json().get("message", "Error desconocido")
            }

    except Exception as e:
        return {"success": False, "error": str(e)}
