from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from app.api.utils import get_schema_info
from app.api.exceptions import ModelNotFoundError, OperationError

APP_LABEL = "app"


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('model', openapi.IN_QUERY, description="Nome do modelo (opcional)", type=openapi.TYPE_STRING, required=False),
        openapi.Parameter('id', openapi.IN_QUERY, description="ID do objeto específico (opcional, requer model)", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('include_related', openapi.IN_QUERY, description="Incluir modelos relacionados (parents, children, both)", type=openapi.TYPE_STRING, required=False, enum=['parents', 'children', 'both']),
        openapi.Parameter('related_depth', openapi.IN_QUERY, description="Profundidade de relacionamentos (padrão: 1, máximo: 3)", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={
        200: openapi.Response(description="Schema dos modelos em JSON"),
        400: openapi.Response(description="Erro de validação"),
        404: openapi.Response(description="Modelo ou objeto não encontrado"),
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def schema_view(request):
    """Retorna o schema dos modelos da aplicação."""
    model_name = request.query_params.get('model')
    obj_id = request.query_params.get('id')
    include_related = request.query_params.get('include_related')
    related_depth_param = request.query_params.get('related_depth', '1')

    if include_related and include_related not in ['parents', 'children', 'both']:
        return Response({"error": "O parâmetro 'include_related' deve ser 'parents', 'children' ou 'both'"}, status=400)

    related_depth = 1
    if related_depth_param:
        try:
            related_depth = int(related_depth_param)
            if related_depth < 1 or related_depth > 3:
                return Response({"error": "O parâmetro 'related_depth' deve estar entre 1 e 3"}, status=400)
        except ValueError:
            return Response({"error": "O parâmetro 'related_depth' deve ser um número inteiro válido"}, status=400)

    try:
        if obj_id:
            try:
                obj_id = int(obj_id)
            except ValueError:
                return Response({"error": "O parâmetro 'id' deve ser um número inteiro válido"}, status=400)

        schema_info = get_schema_info(
            app_name=APP_LABEL,
            model_name=model_name,
            obj_id=obj_id,
            include_related=include_related,
            related_depth=related_depth,
        )
        return Response(schema_info)
    except ModelNotFoundError as e:
        return Response({"error": str(e)}, status=404)
    except ObjectDoesNotExist as e:
        return Response({"error": str(e)}, status=404)
    except OperationError as e:
        return Response({"error": e.detail, "reason": e.reason if hasattr(e, 'reason') else None}, status=400)
    except Exception as e:
        return Response({"error": f"Erro inesperado: {str(e)}"}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info_view(request):
    """Retorna os dados do usuário autenticado extraídos do JWT."""
    user = request.user

    if hasattr(request, 'auth') and request.auth:
        token = request.auth
        payload = {
            'username': getattr(token, 'get', lambda k, d=None: d)('username') or getattr(user, 'username', None),
            'email': getattr(token, 'get', lambda k, d=None: d)('email') or getattr(user, 'email', None),
            'groups': getattr(token, 'get', lambda k, d=None: d)('groups', []),
            'is_superuser': getattr(token, 'get', lambda k, d=None: d)('is_superuser', False),
            'is_staff': getattr(token, 'get', lambda k, d=None: d)('is_staff', False),
        }
    else:
        payload = {
            'username': getattr(user, 'username', str(user)),
            'email': getattr(user, 'email', None),
            'groups': [],
            'is_superuser': getattr(user, 'is_superuser', False),
            'is_staff': getattr(user, 'is_staff', False),
        }

    return Response(payload)
