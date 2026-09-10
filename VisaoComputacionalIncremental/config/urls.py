from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

_script_name = getattr(settings, 'FORCE_SCRIPT_NAME', None) or ''

schema_view = get_schema_view(
    openapi.Info(
        title="VisaoComputacionalIncremental API",
        default_version='v1',
        description=(
            "API dinâmica do serviço VisaoComputacionalIncremental.\n\n"
            "**Autenticação JWT:**\n"
            "1. Obtenha o token: `POST /login/api/token/`\n"
            "2. Use no header: `Authorization: Bearer <token>`\n\n"
            "**Endpoints:**\n"
            "- `GET/POST /api/vci/<model>/` — listar / criar\n"
            "- `GET/PUT/PATCH/DELETE /api/vci/<model>/<pk>/` — detalhe / atualizar / excluir\n"
            "- `GET /api/vci/schema/` — schema dos modelos\n"
            "- `GET /api/vci/me/` — dados do usuário autenticado"
        ),
        contact=openapi.Contact(email="contato@ifsuldeminas.edu.br"),
        license=openapi.License(name="MIT License"),
    ),
    url=f"https://campusinteligente.ifsuldeminas.edu.br{_script_name}" if _script_name else None,
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # API dinâmica com JWT
    path('', include('app.api.urls')),

    # Frontend
    path("", include("app.urls")),

    # Documentação (Swagger / ReDoc)
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
