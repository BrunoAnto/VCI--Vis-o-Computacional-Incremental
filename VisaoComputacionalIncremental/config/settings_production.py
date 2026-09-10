"""
Configurações de produção — Docker + AuthService + PostgreSQL.
Todas as variáveis sensíveis vêm de variáveis de ambiente (.env).
"""
import os
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

os.environ.setdefault("PGCLIENTENCODING", "UTF8")
os.environ.setdefault("LC_ALL", "pt_BR.UTF-8")
os.environ.setdefault("LANG", "pt_BR.UTF-8")

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost', cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_yasg",
    "corsheaders",
    "app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "app.api.middleware.APIExceptionMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # TODO: altere o nome do banco em .env (POSTGRES_DB)
        "NAME": config('POSTGRES_DB', default='meu_servico'),
        "USER": config('POSTGRES_USER', default='postgres'),
        "PASSWORD": config('POSTGRES_PASSWORD', default='postgres'),
        "HOST": config('POSTGRES_HOST', default='db'),
        "PORT": config('POSTGRES_PORT', default='5432'),
        "OPTIONS": {"client_encoding": "UTF8"},
    }
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# Subpath (proxy reverso Nginx)
# TODO: configure FORCE_SCRIPT_NAME no .env com o prefixo do seu serviço, ex: /meu-servico
FORCE_SCRIPT_NAME = config('FORCE_SCRIPT_NAME', default=None) or None
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Isolamento de cookies por subpath — evita conflito entre apps no mesmo domínio
if FORCE_SCRIPT_NAME:
    _suffix = FORCE_SCRIPT_NAME.strip('/').replace('/', '_')
    SESSION_COOKIE_NAME = f'sessionid_{_suffix}'
    CSRF_COOKIE_NAME    = f'csrftoken_{_suffix}'
    SESSION_COOKIE_PATH = FORCE_SCRIPT_NAME.rstrip('/') + '/'
    CSRF_COOKIE_PATH    = FORCE_SCRIPT_NAME.rstrip('/') + '/'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'app' / 'static'] if (BASE_DIR / 'app' / 'static').exists() else []

if FORCE_SCRIPT_NAME:
    STATICFILES_STORAGE = 'config.storage.SubpathStaticFilesStorage'
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

# ─── AuthService ──────────────────────────────────────────────────────────────
# URL interna do container AuthService na rede Docker
AUTHSERVICE_URL = config('AUTHSERVICE_URL', default='http://authservice_app:8010')

# Grupo obrigatório para acessar este serviço (definido no AuthService admin).
# TODO: defina o nome do grupo no .env, ex: REQUIRED_GROUP=MeuServico
# Deixe vazio para permitir qualquer usuário autenticado no AuthService.
# Superusuários sempre têm acesso.
REQUIRED_GROUP = config('REQUIRED_GROUP', default='') or None

AUTHENTICATION_BACKENDS = [
    'app.backends.AuthServiceBackend',
]

# ─── JWT RS256 (chave pública do AuthService) ─────────────────────────────────
_jwt_public_key_path = config('JWT_PUBLIC_KEY_PATH', default=None)

SIMPLE_JWT = {
    'ALGORITHM': 'RS256',
    'SIGNING_KEY': None,
    'VERIFYING_KEY': open(_jwt_public_key_path).read() if _jwt_public_key_path else None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('JWT_ACCESS_TOKEN_MINUTES', default=60, cast=int)),
}

# ─── REST Framework ───────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'app.api.authentication.ApiKeyAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'app.api.middleware.api_exception_handler',
}

# Metadados opcionais na resposta da API dinâmica
API_INCLUDE_META = config('API_INCLUDE_META', default=False, cast=bool)

# ─── API Key (comunicação entre serviços) ─────────────────────────────────────
# Gere com: python -c "import secrets; print(secrets.token_hex(32))"
API_KEY = config('API_KEY', default='')

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())

# ─── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False},
        'app': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
    },
}
