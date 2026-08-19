import pyotp
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny

from .authentication import SystemTokenAuthentication
from .throttling import OTPGenerateThrottle, OTPVerifyThrottle, OTPStatusThrottle
from ...models import UserOTP, OTPLog
from ...services import EmailService

OTP_INTERVAL = 300  # 5 minutos

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class GenerateOTPView(APIView):
    """
    Endpoint para generar y enviar un código de verificación OTP por correo electrónico.
    """
    authentication_classes = [SystemTokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [OTPGenerateThrottle]

    def post(self, request):
        email = request.data.get('email')
        recipient_name = request.data.get('nombre', 'Usuario')
        system = request.user  # Instancia del sistema autorizado validado por el token
        client_ip = get_client_ip(request)

        # 1. Validación de campos obligatorios
        if not email:
            return Response(
                {'error': 'El parámetro "email" es requerido.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Verificar si el usuario se encuentra actualmente bloqueado
        blocked_otp = UserOTP.objects.filter(
            email=email, 
            system_name=system.name,
            status=UserOTP.OTPStatus.BLOCKED
        ).first()

        if blocked_otp and blocked_otp.is_currently_blocked():
            remaining_seconds = blocked_otp.get_remaining_block_time_seconds()
            remaining_minutes = (remaining_seconds // 60) + 1

            # Log de auditoría: intento de generación bloqueado
            OTPLog.objects.create(
                email=email,
                system_name=system.name,
                otp_code='BLOCKED',
                status='GENERATE_ATTEMPT_BLOCKED',
                ip_address=client_ip
            )

            return Response({
                'error': f'El correo está temporalmente bloqueado por {remaining_minutes} minuto(s) más.',
                'status': blocked_otp.status,
                'retry_after_seconds': remaining_seconds
            }, status=status.HTTP_403_FORBIDDEN)

        # 3. Obtener o crear el registro unificado del usuario en UserOTP
        user_otp, _ = UserOTP.objects.get_or_create(
            email=email, 
            system_name=system.name
        )

        # Expirar solicitudes pendientes previas para este correo y sistema
        UserOTP.objects.filter(
            email=email,
            system_name=system.name,
            status=UserOTP.OTPStatus.PENDING
        ).exclude(id=user_otp.id).update(status=UserOTP.OTPStatus.EXPIRED)

        # 4. Actualizar las credenciales y estado del OTP
        user_otp.secret_key = pyotp.random_base32()
        user_otp.status = UserOTP.OTPStatus.PENDING
        user_otp.failed_attempts = 0
        user_otp.blocked_until = None
        user_otp.save()

        # 5. Generar el código TOTP de 6 dígitos (válido por 5 minutos)
        totp = pyotp.TOTP(user_otp.secret_key, interval=300)
        otp_code = totp.now()

        # 6. Registrar evento en la tabla de auditoría (OTPLog)
        OTPLog.objects.create(
            email=email,
            system_name=system.name,
            otp_code=otp_code,
            status='GENERATED',
            ip_address=client_ip
        )

        # 7. Enviar la notificación al microservicio de correo
        email_sent = EmailService.send_otp_email(
            recipient_email=email,
            otp_code=otp_code,
            system_name=system.name,
            recipient_name=recipient_name,
            expiration_minutes="5"
        )

        if not email_sent:
            return Response(
                {'error': 'No se pudo enviar el correo de verificación OTP. Intente nuevamente.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 8. Respuesta exitosa
        return Response({
            'message': 'Código OTP generado y enviado con éxito.',
            'system_name': system.name,
            'status': user_otp.status
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    authentication_classes = [SystemTokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp')
        system = request.user
        client_ip = get_client_ip(request)

        if not email or not otp_code:
            return Response({'error': 'El email y el código OTP son requeridos.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_otp = UserOTP.objects.get(email=email, system_name=system.name)
        except UserOTP.DoesNotExist:
            return Response({'error': 'No existe una solicitud activa para este sistema.'}, status=status.HTTP_404_NOT_FOUND)

        # 1. Intento cuando el usuario ya se encuentra bloqueado
        if user_otp.is_currently_blocked():
            remaining_seconds = user_otp.get_remaining_block_time_seconds()
            remaining_minutes = (remaining_seconds // 60) + 1

            # Log de auditoría: intento en estado bloqueado
            OTPLog.objects.create(
                email=email,
                system_name=system.name,
                otp_code=otp_code,
                status='VERIFY_ATTEMPT_BLOCKED',
                ip_address=client_ip
            )

            return Response({
                'error': f'El correo está bloqueado. Intente nuevamente en {remaining_minutes} minuto(s).',
                'status': user_otp.status,
                'retry_after_seconds': remaining_seconds
            }, status=status.HTTP_403_FORBIDDEN)

        # Restablecer si el tiempo de bloqueo venció
        if user_otp.status == UserOTP.OTPStatus.BLOCKED and not user_otp.is_currently_blocked():
            user_otp.status = UserOTP.OTPStatus.PENDING
            user_otp.failed_attempts = 0
            user_otp.blocked_until = None
            user_otp.save()

        if user_otp.status == UserOTP.OTPStatus.VERIFIED:
            return Response({'error': 'Este código OTP ya fue utilizado.'}, status=status.HTTP_400_BAD_REQUEST)

        totp = pyotp.TOTP(user_otp.secret_key, interval=300)

        # 2. VERIFICACIÓN EXITOSA
        if totp.verify(otp_code):
            user_otp.status = UserOTP.OTPStatus.VERIFIED
            user_otp.failed_attempts = 0
            user_otp.blocked_until = None
            user_otp.save()

            # 🔹 Log de auditoría: Éxito
            OTPLog.objects.create(
                email=email,
                system_name=system.name,
                otp_code=otp_code,
                status='VERIFIED_SUCCESS',
                ip_address=client_ip
            )

            return Response({
                'message': 'Código OTP verificado correctamente.',
                'status': user_otp.status
            }, status=status.HTTP_200_OK)

        # 3. VERIFICACIÓN FALLIDA (Código incorrecto)
        user_otp.failed_attempts += 1

        if user_otp.failed_attempts >= UserOTP.MAX_FAILED_ATTEMPTS:
            from datetime import timedelta
            from django.utils import timezone

            unblock_time = timezone.now() + timedelta(minutes=UserOTP.BLOCK_DURATION_MINUTES)
            user_otp.status = UserOTP.OTPStatus.BLOCKED
            user_otp.blocked_until = unblock_time
            user_otp.save()

            # Expirar solicitudes pendientes previas
            UserOTP.objects.filter(
                email=email, 
                status=UserOTP.OTPStatus.PENDING
            ).update(status=UserOTP.OTPStatus.EXPIRED)

            # 🔹 Log de auditoría: Fallo que detonó el bloqueo
            OTPLog.objects.create(
                email=email,
                system_name=system.name,
                otp_code=otp_code,
                status='VERIFY_FAILED_BLOCKED',
                ip_address=client_ip
            )

            return Response({
                'error': f'Ha superado los {UserOTP.MAX_FAILED_ATTEMPTS} intentos fallidos. Su correo ha sido bloqueado por {UserOTP.BLOCK_DURATION_MINUTES} minutos.',
                'status': user_otp.status,
                'retry_after_seconds': UserOTP.BLOCK_DURATION_MINUTES * 60
            }, status=status.HTTP_403_FORBIDDEN)

        else:
            user_otp.save()
            attempts_left = UserOTP.MAX_FAILED_ATTEMPTS - user_otp.failed_attempts

            # 🔹 Log de auditoría: Fallo con intentos restantes
            OTPLog.objects.create(
                email=email,
                system_name=system.name,
                otp_code=otp_code,
                status='VERIFY_FAILED',
                ip_address=client_ip
            )

            return Response({
                'error': f'Código inválido. Le quedan {attempts_left} intento(s).',
                'status': user_otp.status,
                'failed_attempts': user_otp.failed_attempts
            }, status=status.HTTP_400_BAD_REQUEST)

class OTPStatusView(APIView):
    authentication_classes = [SystemTokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [OTPStatusThrottle]

    def get(self, request):
        email = request.query_params.get('email')
        system = request.user

        if not email:
            return Response(
                {'error': 'El parámetro "email" es requerido.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_otp = UserOTP.objects.get(email=email,system_name=system.name)
        except UserOTP.DoesNotExist:
            return Response(
                {'error': 'No existe registro para este email y sistema.'}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Si el tiempo de bloqueo de 5 minutos ya venció, restablecemos el estado
        if user_otp.status == UserOTP.OTPStatus.BLOCKED and not user_otp.is_currently_blocked():
            user_otp.status = UserOTP.OTPStatus.PENDING
            user_otp.failed_attempts = 0
            user_otp.blocked_until = None
            user_otp.save()

        # Construcción de la respuesta base
        data = {
            'email': user_otp.email,
            'system_name': system.name,
            'status': user_otp.status,
            'failed_attempts': user_otp.failed_attempts,
            'created_at': user_otp.created_at,
            'updated_at': user_otp.updated_at,
            'retry_after_seconds': 0
        }

        # Si continúa activamente bloqueado, incluimos los segundos restantes
        if user_otp.is_currently_blocked():
            data['retry_after_seconds'] = user_otp.get_remaining_block_time_seconds()

        return Response(data, status=status.HTTP_200_OK)

class HealthCheckView(APIView):
    """
    Endpoint público de monitoreo (Healthcheck) para verificar el estado de la aplicación
    y la conectividad con la base de datos PostgreSQL.
    """
    authentication_classes = []  # Exento de autenticación
    permission_classes = [AllowAny]

    def get(self, request):
        db_healthy = True
        db_error = None

        # Verificar conectividad con PostgreSQL realizando una consulta mínima
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
        except Exception as e:
            db_healthy = False
            db_error = str(e)

        payload = {
            'status': 'healthy' if db_healthy else 'unhealthy',
            'components': {
                'database': {
                    'status': 'up' if db_healthy else 'down',
                    'engine': 'PostgreSQL'
                }
            }
        }

        if not db_healthy:
            payload['components']['database']['error'] = db_error
            return Response(payload, status=status.HTTP_531_SERVICE_UNAVAILABLE if hasattr(status, 'HTTP_531_SERVICE_UNAVAILABLE') else status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(payload, status=status.HTTP_200_OK)