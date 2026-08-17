from rest_framework.permissions import BasePermission
from ...models import AuthorizedSystem

class IsAuthorizedSystem(BasePermission):
    """
    Verifica que el request pertenezca a un sistema autorizado activo.
    """
    def has_permission(self, request, view):
        return isinstance(request.user, AuthorizedSystem) and request.user.is_active