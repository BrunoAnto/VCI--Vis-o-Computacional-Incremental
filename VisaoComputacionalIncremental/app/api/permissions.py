from rest_framework.permissions import BasePermission


class IsAuthenticatedOrHasApiKey(BasePermission):
    """
    Permite acesso se o usuário está autenticado via JWT
    ou se a requisição passou pela autenticação via API Key.
    """

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return True
        if request.auth is not None:
            return True
        return False
