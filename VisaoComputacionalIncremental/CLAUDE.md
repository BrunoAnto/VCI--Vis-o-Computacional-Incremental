# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é este serviço

`VisaoComputacionalIncremental` (prefixo de URL/API: `vci`) é um microsserviço Django do ecossistema **PCI — Campus Inteligente IFSulDeMinas**. É uma plataforma para criação de detectores de objetos por reuso de modelos: um Model Registry com dicionário de sinônimos de classes, fallback de vocabulário aberto, treino condicional (fine-tuning) quando não há modelo reutilizável, e composição por ensemble em tempo de inferência.

Foi gerado a partir do `pci-service-template` (ver `README.md` nesta pasta para o que o template traz pronto) e segue as convenções do PCI: Django + DRF, autenticação delegada a um AuthService central via JWT RS256, API Dinâmica genérica sobre os models do app, e deploy via Docker atrás de um gateway Nginx compartilhado entre serviços.

## Comandos de desenvolvimento

Não há suíte de testes neste serviço ainda (`app/tests.py` não existe) nem lint configurado — o CI (`.github/workflows/ci-cd.yml`) só faz build da imagem e deploy por SSH quando há push em `main`/`master`.

Ambiente local (SQLite, sem Docker/Postgres/AuthService — usa `config.settings`):
```bash
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Ambiente via Docker (Postgres + `config.settings_production`, precisa da rede `nginx_default` e da chave pública do AuthService):
```bash
cp .env.example .env   # preencher valores reais
docker compose up --build -d
docker compose logs app
docker compose exec app python manage.py makemigrations
docker compose exec app python manage.py migrate
```

Verificações rápidas sem depender de nenhum serviço externo:
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

## Arquitetura

**Duas configurações de settings, uma única `ROOT_URLCONF`:**
- `config.settings` — desenvolvimento local: SQLite, `AUTH_USER_MODEL` padrão do Django, sem `AuthServiceBackend` nem JWT. Usada quando `DJANGO_SETTINGS_MODULE` não é definido.
- `config.settings_production` — produção via Docker: PostgreSQL, `AuthServiceBackend` como único `AUTHENTICATION_BACKENDS`, JWT RS256 verificado com a chave pública em `app/keys/public.pem` (`JWT_PUBLIC_KEY_PATH`), `FORCE_SCRIPT_NAME=/vci` (o serviço roda atrás do Nginx num subpath) com isolamento de cookies de sessão/CSRF por subpath (`config/settings.py` faz o sufixo a partir do próprio `FORCE_SCRIPT_NAME`). `entrypoint.sh` fixa esse módulo como padrão no container.

**Autenticação é 100% delegada ao AuthService** (`app/backends.py`, `AuthServiceBackend`): não há senha local. No login, o backend faz `POST {AUTHSERVICE_URL}/api/token/`, decodifica o JWT retornado (sem verificar assinatura aqui — a verificação RS256 real acontece via `SIMPLE_JWT.VERIFYING_KEY` quando a API é chamada com `Authorization: Bearer`), confere `REQUIRED_GROUP` contra os `groups` do payload (superusuário sempre passa), e cria/atualiza o `User` local com `set_unusable_password()`. Grupos vindos do token são sincronizados como `django.contrib.auth.models.Group` locais; **na primeira vez que um grupo é criado**, `DEFAULT_GROUP_PERMISSIONS` (dict no topo de `backends.py`) aplica automaticamente as permissões daquele grupo — depois disso as permissões do grupo já existente não são reaplicadas, só sincronizadas por associação usuário↔grupo. Os três grupos deste serviço são `VisaoComputacionalIncremental_{Gerente,Usuario,Visualizador}`.

**API Dinâmica (`app/api/`) é genérica sobre os models do app `app` — não é código a modificar por feature.** `DynamicModelViewSet` (`app/api/viewsets.py`) resolve o model pelo nome vindo da URL (`get_model_from_names` em `app/api/utils.py`), monta um `DynamicSerializer` (`app/api/serializers.py`) sob medida por request suportando `?depth=N` (serializa relações aninhadas), `?fields=a,b,c` (subconjunto de campos) e `?filter_<campo>=valor` (filtro genérico via queryset). `list` também aceita `?group_by=campo1,campo2` para agregação com `Count`. `create`/`update` aceitam campos `<algo>_set` no payload para criar/substituir objetos relacionados numa mesma transação, resolvendo FKs por PK bruta. O prefixo de rota vem de `_PREFIX = "vci"` em `app/api/urls.py`, incluído em `config/urls.py` — para adicionar um novo model à API não se mexe em `app/api/`, só em `app/models.py` (e migrations); o CRUD aparece automaticamente em `/api/vci/<model>/`.

**Domínio (`app/models.py`) é o registro central do produto**, não CRUD isolado:
- `Classe` + `SinonimoClasse` formam o dicionário de sinônimos que resolve nomes de classe informados pelo usuário para uma classe canônica.
- `Projeto.classes_desejadas` (M2M para `Classe`) é o que o usuário quer detectar; `Projeto.status` modela o fluxo (`rascunho` → `verificando` → `aguardando_dataset` → `treinando` → `pronto`).
- `Modelo` é o Model Registry (`origem`: `reutilizado` ou `treinado`); `Treinamento` liga um `Dataset` a um `Modelo` resultante (fine-tuning); `EstrategiaComposicao` registra, por classe dentro de um projeto, qual estratégia foi usada (`reuso_exato`, `reuso_parcial`, `vocabulario_aberto`, `treino`) e quais `Modelo`s entraram no ensemble.
- `Inferencia.caixas_detectadas` é um `JSONField` com lista de `{x, y, w, h, classe, confianca, modelo_origem}` — schema fixo, decidido com o dev, não inferido do código.
- `Dataset.anotacoes` é um único `FileField` (upload compactado com imagens + anotações), não múltiplos arquivos por imagem — também decisão explícita do dev, ver histórico de commits da Sprint 3.
- Convenção obrigatória neste serviço: todo model principal tem `data_cadastro`/`data_atualizacao` e `ordering = ['-data_cadastro']`; `on_delete=PROTECT` quando o model é referenciado por outro que não deve sobreviver à perda da referência (ex.: `Dataset` em `Treinamento`, `Classe` em `EstrategiaComposicao`), `CASCADE` quando o dado é derivado do `Projeto` pai (`EstrategiaComposicao`, `Inferencia`).

**Deploy é multi-serviço, não isolado:** este container (`vci_app`, porta 8060) espera uma rede Docker externa `nginx_default` já criada e um gateway Nginx compartilhado registrado via GestaoNginx (upstream `vci_app:8060`, URL base `/vci/`) — nenhuma dessas peças faz parte deste repositório. `copy-public-key.sh` (fora deste repositório, na raiz do monorepo PCI) é o que popula `app/keys/public.pem` a partir do AuthService antes do primeiro `docker compose up`.

## Estado da implementação

Ver `PLANO_IMPLEMENTACAO.md` nesta pasta para o histórico sprint-a-sprint (o que já foi commitado, decisões de modelagem confirmadas com o dev, e o que segue bloqueado por depender de infraestrutura — Nginx/AuthService/verificação de porta — que não existe neste ambiente isolado).
