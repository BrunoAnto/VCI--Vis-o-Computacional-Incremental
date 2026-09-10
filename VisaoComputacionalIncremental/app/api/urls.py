from django.urls import path
from app.api.viewsets import DynamicModelViewSet
from app.api.views import schema_view, user_info_view

APP_LABEL = "app"

# Este prefixo aparece nas URLs: /api/vci/<model>/
_PREFIX = "vci"

urlpatterns = [
    # Rotas literais ANTES das wildcards — evita que Django capture "schema" e "me" como modelos
    path(f"api/{_PREFIX}/schema/", schema_view, name=f"api-{_PREFIX}-schema"),
    path(f"api/{_PREFIX}/me/", user_info_view, name=f"api-{_PREFIX}-me"),

    # Lista e criação: GET/POST /api/<prefix>/<model>/
    path(
        f"api/{_PREFIX}/<str:model>/",
        DynamicModelViewSet.as_view({"get": "list", "post": "create"}),
        {"app": APP_LABEL},
        name=f"api-{_PREFIX}-list",
    ),
    # Detalhe: GET/PUT/PATCH/DELETE /api/<prefix>/<model>/<pk>/
    path(
        f"api/{_PREFIX}/<str:model>/<int:pk>/",
        DynamicModelViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        {"app": APP_LABEL},
        name=f"api-{_PREFIX}-detail",
    ),
]
