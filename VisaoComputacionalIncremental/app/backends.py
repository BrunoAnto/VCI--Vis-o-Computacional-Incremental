import logging
import jwt as pyjwt
import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group, Permission
from django.conf import settings

logger = logging.getLogger(__name__)

User = get_user_model()

_APP_LABEL = 'app'

# Sessão HTTP reaproveitada entre chamadas ao AuthService (pool de conexões/keep-alive).
_session = requests.Session()

# =============================================================================
# Mapeamento de permissões por grupo
# =============================================================================
# TODO: substitua pelos grupos e permissões do seu serviço.
#
# Convenção de nomenclatura: <NomeServico>_<Papel>
#   ex: MeuServico_Gerente, MeuServico_Operador, MeuServico_Visualizador
#
# Valor 'all'  → todas as permissões do app_label definido em _APP_LABEL
# Valor lista  → codenames específicos (add_X, change_X, delete_X, view_X)
#
# Grupos não listados aqui ficam sem permissões automáticas e devem ser
# configurados manualmente via Django Admin.
# =============================================================================

DEFAULT_GROUP_PERMISSIONS = {
    'VisaoComputacionalIncremental_Gerente': 'all',

    'VisaoComputacionalIncremental_Usuario': [
        'add_projeto', 'change_projeto', 'view_projeto', 'delete_projeto',
        'add_dataset', 'change_dataset', 'view_dataset', 'delete_dataset',
        'add_inferencia', 'view_inferencia',
        'view_modelo', 'view_classe', 'view_treinamento', 'view_estrategiacomposicao',
    ],

    'VisaoComputacionalIncremental_Visualizador': [
        'view_projeto', 'view_modelo', 'view_classe',
        'view_estrategiacomposicao', 'view_inferencia',
    ],
}


def _aplicar_permissoes_grupo(group, group_name):
    """
    Aplica permissões padrão a um grupo recém-criado.
    Lê GROUP_PERMISSIONS do settings (se definido) ou usa DEFAULT_GROUP_PERMISSIONS.
    """
    mapa = getattr(settings, 'GROUP_PERMISSIONS', DEFAULT_GROUP_PERMISSIONS)

    if group_name not in mapa:
        logger.debug(
            "Grupo '%s' criado sem mapeamento de permissões — configure via admin.",
            group_name,
        )
        return

    cfg = mapa[group_name]

    if cfg == 'all':
        perms = Permission.objects.filter(content_type__app_label=_APP_LABEL)
    else:
        perms = Permission.objects.filter(
            content_type__app_label=_APP_LABEL,
            codename__in=cfg,
        )

    group.permissions.set(perms)
    logger.info(
        "Grupo '%s' criado: %d permissões aplicadas automaticamente.",
        group_name,
        perms.count(),
    )


class AuthServiceBackend(ModelBackend):
    """
    Autentica o usuário delegando ao AuthService centralizado.

    Fluxo:
    1. POST para {AUTHSERVICE_URL}/api/token/ com username + password
    2. Decodifica o JWT retornado para extrair claims
    3. Verifica REQUIRED_GROUP (superusuários sempre passam)
    4. Cria/atualiza o User local; define set_unusable_password()
    5. Sincroniza grupos Django locais, aplicando DEFAULT_GROUP_PERMISSIONS
       na primeira criação de cada grupo

    Herda de ModelBackend só para reaproveitar get_user()/has_perm()/
    get_all_permissions() (permissões locais via grupos sincronizados) —
    authenticate() é totalmente reimplementado abaixo.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        authservice_url = getattr(settings, 'AUTHSERVICE_URL', None)
        if not authservice_url:
            logger.error("AUTHSERVICE_URL não configurado.")
            return None

        try:
            response = _session.post(
                f"{authservice_url}/api/token/",
                json={"username": username, "password": password},
                headers={"Host": "localhost"},
                timeout=10,
            )
        except requests.exceptions.ConnectionError:
            logger.error("Não foi possível conectar ao AuthService em %s", authservice_url)
            return None
        except requests.exceptions.Timeout:
            logger.error("Timeout ao conectar ao AuthService.")
            return None

        if response.status_code != 200:
            logger.warning(
                "AuthService retornou %s para usuário '%s'",
                response.status_code,
                username,
            )
            return None

        data = response.json()
        access_token = data.get("access")
        if not access_token:
            logger.error("AuthService não retornou 'access' token. Resposta: %s", data)
            return None

        try:
            payload = pyjwt.decode(
                access_token,
                options={"verify_signature": False},
                algorithms=["RS256"],
            )
        except Exception as e:
            logger.error("Erro ao decodificar JWT: %s", e)
            return None

        user_id  = payload.get("user_id")
        email    = payload.get("email", "")
        groups   = payload.get("groups", [])
        is_super = payload.get("is_superuser", False)
        is_staff = payload.get("is_staff", False)

        if not user_id:
            return None

        required_group = getattr(settings, 'REQUIRED_GROUP', None)
        if required_group and not is_super:
            if required_group not in groups:
                logger.warning(
                    "Usuário '%s' não tem o grupo '%s'. Grupos: %s",
                    username, required_group, groups,
                )
                return None

        user, created = User.objects.get_or_create(username=username)
        changed = False

        if user.email != email:
            user.email = email
            changed = True
        if user.is_superuser != is_super:
            user.is_superuser = is_super
            changed = True
        if user.is_staff != is_staff:
            user.is_staff = is_staff
            changed = True
        if user.has_usable_password():
            user.set_unusable_password()
            changed = True

        if changed or created:
            user.save()

        existentes = {g.name: g for g in Group.objects.filter(name__in=groups)}
        for group_name in groups:
            if group_name in existentes:
                continue
            group, grp_created = Group.objects.get_or_create(name=group_name)
            if grp_created:
                _aplicar_permissoes_grupo(group, group_name)
            existentes[group_name] = group
        user.groups.set(existentes.values())

        return user
