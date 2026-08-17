from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from ...models import AuthorizedSystem

class SystemTokenAuthentication(BaseAuthentication):
    """
    Autentica la petición mediante la cabecera 'X-System-Token'.
    """
    def authenticate(self, request):
        token = request.headers.get('X-System-Token')

        if not token:
            raise AuthenticationFailed('Cabecera "X-System-Token" no proporcionada.')

        try:
            authorized_system = AuthorizedSystem.objects.get(api_key=token, is_active=True)
        except AuthorizedSystem.DoesNotExist:
            raise AuthenticationFailed('Token de sistema inválido o inactivo.')

        # Retorna el objeto del sistema en request.user y None para la credencial
        return (authorized_system, None)