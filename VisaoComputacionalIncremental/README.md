# pci-service-template

Template base para novos serviços do ecossistema **PCI – Campus Inteligente IFSulDeMinas**.

Inclui: Django 4.2 + DRF + API dinâmica + autenticação via AuthService (JWT RS256) + Docker + CI/CD GitHub Actions.

---

## O que já vem pronto

| O que | Onde |
|---|---|
| AuthServiceBackend completo | `app/backends.py` |
| API dinâmica (CRUD genérico) | `app/api/` |
| Isolamento de cookies por subpath | `config/settings_production.py` |
| Templates base (navbar, login, home) | `app/templates/app/` |
| Dockerfile + docker-compose + entrypoint | raiz |
| CI/CD (build GHCR + deploy SSH) | `.github/workflows/ci-cd.yml` |
| `.env.example` documentado | raiz |

---

## Pré-requisitos

- Docker e Docker Compose instalados no servidor
- Acesso SSH ao servidor de produção
- Chave pública RSA do AuthService (`public.pem`)
- Rede Docker `nginx_default` já existente no servidor (`docker network create nginx_default`)

---

## Checklist de criação de um novo serviço

### 1. Renomear — o que trocar

Faça uma busca global por `meuservico` / `MeuServico` / `meu-servico` / `meu_servico` e substitua pelo nome do seu serviço:

| Arquivo | O que trocar |
|---|---|
| `Dockerfile` | `EXPOSE 800X` e `--bind 0.0.0.0:800X` → porta real (ex: 8036) |
| `docker-compose.yml` | `container_name` de `app` e `db` → nomes do seu serviço |
| `.env.example` + `.env` | `FORCE_SCRIPT_NAME`, `POSTGRES_DB`, `REQUIRED_GROUP` |
| `app/api/urls.py` | `_PREFIX = "meuservico"` → prefixo da sua API |
| `config/urls.py` | Título e descrição do Swagger |
| `app/backends.py` | `DEFAULT_GROUP_PERMISSIONS` com grupos e permissões reais |
| `app/templates/app/base.html` | Nome e ícone do serviço na navbar |
| `.github/workflows/ci-cd.yml` | `IMAGE_NAME`, URL de produção, caminho do deploy |
| `entrypoint.sh` | Nome do serviço na mensagem de log |

### 2. Copiar a chave pública do AuthService

```bash
# Na raiz do projeto PCI, execute:
./copy-public-key.sh

# Ou manualmente:
cp /caminho/do/authservice/app/keys/public.pem ./app/keys/public.pem
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite .env com os valores reais
```

### 4. Configurar Secrets do GitHub

No repositório GitHub → Settings → Secrets and variables → Actions:

| Secret | Valor |
|---|---|
| `SSH_PRIVATE_KEY` | Chave privada SSH do servidor de produção |
| `VPS_HOST` | IP ou hostname do servidor |
| `VPS_USER` | Usuário SSH (ex: `deploy`) |

### 5. Criar pasta no servidor

```bash
ssh -p 33333 usuario@servidor
mkdir -p /conteineres/app_separadas/MeuServico
cd /conteineres/app_separadas/MeuServico
git clone https://github.com/seu-org/seu-repo.git .
cp /caminho/do/authservice/keys/public.pem ./app/keys/public.pem
cp .env.example .env && nano .env
docker compose up -d
```

### 6. Cadastrar no GestaoNginx

Acesse `/nginx/` e cadastre o novo serviço com:
- **Nome:** nome do serviço
- **Upstream:** `meu_servico_app:800X`
- **URL base:** `/meu-servico/`
- **Categoria:** `django_app`

Clique em **Aplicar configuração**.

---

## Desenvolvimento local

```bash
# Instalar dependências
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Criar banco SQLite local e rodar
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

> Em desenvolvimento (`settings.py`), o AuthService não é necessário — o Django usa autenticação local padrão.

---

## API dinâmica

Todos os models do `app` ficam disponíveis automaticamente:

```
GET  /api/meuservico/schema/            → schema de todos os models
GET  /api/meuservico/<model>/           → listar (suporta ?filter_campo=valor, ?depth=1, ?fields=id,nome)
POST /api/meuservico/<model>/           → criar
GET  /api/meuservico/<model>/<pk>/      → detalhe
PUT  /api/meuservico/<model>/<pk>/      → atualizar
DEL  /api/meuservico/<model>/<pk>/      → excluir
GET  /api/meuservico/me/                → dados do usuário autenticado
```

Documentação interativa disponível em `/swagger/` e `/redoc/`.

---

## Estrutura de arquivos

```
pci-service-template/
├── .github/workflows/ci-cd.yml     # CI/CD
├── config/
│   ├── settings.py                 # Dev (SQLite, sem AuthService)
│   ├── settings_production.py      # Produção (PostgreSQL + AuthService)
│   ├── storage.py                  # Static files com subpath
│   └── urls.py                     # Rotas + Swagger
├── app/
│   ├── backends.py                 # AuthServiceBackend
│   ├── models.py                   # Modelo de exemplo (substitua)
│   ├── views.py                    # login, logout, home
│   ├── api/                        # API dinâmica (não modificar)
│   │   ├── urls.py                 # TODO: alterar _PREFIX
│   │   ├── viewsets.py
│   │   ├── serializers.py
│   │   ├── utils.py
│   │   ├── views.py
│   │   ├── exceptions.py
│   │   ├── middleware.py
│   │   ├── authentication.py       # ApiKeyAuthentication
│   │   └── permissions.py
│   ├── keys/                       # Coloque public.pem aqui (ignorado pelo git)
│   ├── static/app/                 # CSS e JS base
│   └── templates/app/              # base.html, login.html, home.html
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh
├── manage.py
└── requirements.txt
```
