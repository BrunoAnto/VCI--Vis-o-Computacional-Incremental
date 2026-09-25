from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied


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


class DynamicModelPermission(BasePermission):
    """
    Controla permissões na API Dinâmica:
    1. Verifica autenticação (ou API Key).
    2. Valida permissões de grupo Django (view_*, add_*, change_*, delete_*).
    3. Protege contra IDOR: apenas o dono ou Gerente/Superuser pode alterar/excluir
       recursos pessoais (Projeto, Dataset, Inferencia, EstrategiaComposicao).
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated or request.auth is not None):
            return False

        # Requisição autenticada por API Key de serviço externo tem acesso total
        if getattr(request, 'auth', None) is not None and not getattr(request.user, 'is_authenticated', False):
            return True

        user = request.user
        if user.is_superuser or user.groups.filter(name='VisaoComputacionalIncremental_Gerente').exists():
            return True

        if not hasattr(view, 'get_model'):
            return user.is_authenticated

        try:
            model = view.get_model()
        except Exception:
            return user.is_authenticated

        app_label = model._meta.app_label
        model_name = model._meta.model_name

        if request.method in SAFE_METHODS:
            return user.has_perm(f'{app_label}.view_{model_name}')
        elif request.method == 'POST':
            return user.has_perm(f'{app_label}.add_{model_name}')
        elif request.method in ('PUT', 'PATCH'):
            return user.has_perm(f'{app_label}.change_{model_name}')
        elif request.method == 'DELETE':
            return user.has_perm(f'{app_label}.delete_{model_name}')

        return False

    def has_object_permission(self, request, view, obj):
        # Leitura é permitida para todos os usuários autenticados com permissão view_*
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if user.is_superuser or user.groups.filter(name='VisaoComputacionalIncremental_Gerente').exists():
            return True

        # Recursos pessoais: checa se o usuário logado é o dono
        if hasattr(obj, 'usuario'):
            if obj.usuario != user:
                raise PermissionDenied("Você não tem permissão para alterar ou excluir um projeto de outro usuário.")
            return True

        if hasattr(obj, 'projeto'):
            if obj.projeto and obj.projeto.usuario != user:
                raise PermissionDenied("Você não tem permissão para alterar ou excluir recursos de um projeto de outro usuário.")
            return True

        # Para catálogo geral (Classe, Modelo, etc.), valida se tem permissão de alteração/exclusão
        app_label = obj._meta.app_label
        model_name = obj._meta.model_name
        perm_action = 'change' if request.method in ('PUT', 'PATCH') else 'delete'
        return user.has_perm(f'{app_label}.{perm_action}_{model_name}')

