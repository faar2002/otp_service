import os
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Servicio encargado de abstraer y gestionar la comunicación HTTP 
    con el Email Microservice independiente.
    """

    @staticmethod
    def send_otp_email(recipient_email: str, otp_code: str, system_name: str = 'default') -> bool:
        """
        Envía una petición POST al microservicio de correo con los datos del OTP.
        
        :param recipient_email: Dirección de correo del destinatario.
        :param otp_code: Código OTP de 6 dígitos generado.
        :return: True si el microservicio aceptó la solicitud, False en caso de error.
        """
        # 1. Obtener la configuración cargada desde los archivos .env
        service_url = getattr(settings, 'EMAIL_SERVICE_URL', None)
        api_key = getattr(settings, 'EMAIL_SERVICE_API_KEY', None)

        if not service_url or not api_key:
            logger.error("Error de configuración: EMAIL_SERVICE_URL o EMAIL_SERVICE_API_KEY no están definidos.")
            return False

        # 2. Construir el contrato/payload JSON esperado por el microservicio
        payload = {
            "to": recipient_email,
            "system_name": system_name,  # Identificador del sistema solicitante
            "template": "otp_verification",
            "data": {
                "code": otp_code,
                "system": system_name,
                "expiration_minutes": 5
            }
        }

        # 3. Cabeceras con token de autenticación inter-servicio
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Django-OTP-Service/1.0"
        }

        # 4. Envío de la petición HTTP con control de excepciones y timeout
        try:
            response = requests.post(
                service_url,
                json=payload,
                headers=headers,
                timeout=5  # Timeout estricto de 5s para no congelar la petición del usuario
            )

            # Aceptamos códigos 200 OK, 201 Created o 202 Accepted (cola asíncrona)
            if response.status_code in [200, 201, 202]:
                logger.info(f"Correo OTP enviado con éxito a {recipient_email} vía Email Microservice.")
                return True

            logger.error(
                f"El Email Microservice devolvió un error: {response.status_code} - {response.text}"
            )
            return False

        except requests.exceptions.Timeout:
            logger.error(f"Timeout al conectar con el Email Microservice en {service_url}.")
            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Fallo de red al intentar conectar con el Email Microservice: {e}")
            return False