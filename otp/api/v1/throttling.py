from rest_framework.throttling import SimpleRateThrottle

class OTPStatusThrottle(SimpleRateThrottle):
    """Límite de peticiones por IP para consultar el estado del OTP."""
    scope = 'otp_status'

    def get_cache_key(self, request, view):
        # Utiliza la IP del cliente como clave en la memoria caché
        return self.get_ident(request)


class OTPVerifyThrottle(SimpleRateThrottle):
    """Límite estricto por IP para la verificación del código OTP."""
    scope = 'otp_verify'

    def get_cache_key(self, request, view):
        return self.get_ident(request)


class OTPGenerateThrottle(SimpleRateThrottle):
    """Límite por IP para solicitar nuevos códigos OTP."""
    scope = 'otp_generate'

    def get_cache_key(self, request, view):
        return self.get_ident(request)