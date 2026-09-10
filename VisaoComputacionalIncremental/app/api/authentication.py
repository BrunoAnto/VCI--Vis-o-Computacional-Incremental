from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ApiKeyAuthentication(BaseAuthentication):
    """Autenticação via header X-API-KEY para comunicação entre serviços (machine-to-machine)."""

    def authenticate(self, request):
        key = request.headers.get("X-API-KEY")
        if not key:
            return None
        api_key = getattr(settings, "API_KEY", "")
        if not api_key or key != api_key:
            raise AuthenticationFailed("API key inválida.")
        return (None, key)

    def authenticate_header(self, request):
        return "X-API-KEY"
