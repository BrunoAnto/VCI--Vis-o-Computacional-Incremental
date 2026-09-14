# VisaoComputacionalIncremental — Plano de Implementação

> **Para agentes:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para implementar este plano task-by-task. Steps usam sintaxe checkbox (`- [ ]`) para rastreamento.

**Goal:** Criar o serviço VisaoComputacionalIncremental (`/vci/`) seguindo os padrões do PCI — microsserviço Django com autenticação JWT RS256, API Dinâmica e Docker.

**Architecture:** Microsserviço Django + PostgreSQL isolado, autenticação via AuthServiceBackend (JWT RS256), API Dinâmica copiada de pci-service-template/app/api/, exposto via Nginx gateway na porta 8060. Domínio: plataforma de criação de detectores de objetos por reuso de modelos (Model Registry + dicionário de sinônimos), fallback de vocabulário aberto, treino condicional (fine-tuning) e composição por ensemble em tempo de inferência.

**Tech Stack:** Python 3.x, Django 3.2+, Django REST Framework, drf-yasg, djangorestframework-simplejwt, PostgreSQL 15.3, Docker, Nginx, GitHub Actions

---

## 📍 Status da implementação (atualizado em 2026-09-14)

**Concluído — Sprints 0 a 5, e parte da 6 e 7, na branch `dev`:**

| Commit | Sprint | Descrição |
|---|---|---|
| `d5af0ac` | 0 + 1 | Estrutura base copiada de `pci-service-template`, nomes/porta (8060) ajustados |
| `8fcd412` | 2 | Grupos reais em `AuthServiceBackend` (`Gerente`/`Usuario`/`Visualizador`) |
| `149bf79` | 3 | Models, migration inicial e admin |
| `f5aaaba` | 4 | API Dinâmica (`/api/vci/`) e Swagger/ReDoc |
| `946149f` | 5 | Views e templates (dashboard com contadores reais) |
| `c80926c` | 6 (parcial) | Workflow de CI/CD ajustado (nome da imagem, path de deploy, URLs) |
| `4e16d96` | 7, Passos 1 e 3 | `CLAUDE.md` do serviço + registro em `documentação/APLICACOES.md` |
| `2145f85` | 7, Passo 4 | `/simplify` (4 agentes: reuse/simplification/efficiency/altitude) aplicado a `backends.py`, `views.py`, `login.html`, `base.html` |

As 3 dúvidas de modelagem bloqueantes da Sprint 3 foram confirmadas com o dev e aplicadas exatamente como propostas no plano: `classes_desejadas` = M2M(Classe), `anotacoes` = FileField único (zip), `caixas_detectadas` = lista de `{x, y, w, h, classe, confianca, modelo_origem}`.

**Desvio do plano:** `Dockerfile` tinha placeholder `800X` não previsto no plano original — corrigido para `8060` junto com o resto da Sprint 1. `requirements.txt` ganhou `Pillow` (necessário para o `ImageField` de `Inferencia`, ausente no template base).

**Como foi validado:** este ambiente **não tem Docker instalado** (`docker`/`docker compose` não encontrados). Toda a validação das Sprints 1–5 e dos ajustes de `/simplify` foi feita localmente com `config.settings` (SQLite, sem Docker/Postgres/AuthService) via `.venv`: `manage.py check`, `makemigrations`, `migrate`, e smoke tests de `/swagger/`, `/redoc/`, `/login/`, `/admin/`, `/api/vci/schema/` e da home autenticada (Django test client). O passo "verificar que o container sobe" das Sprints 1, 4 e 5 **não foi executado com Docker real** — recomenda-se rodar `docker compose up --build` em um ambiente com Docker antes de dar como definitivamente verificado.

**`/security-review` da Sprint 7 (Passo 5) rodou e encontrou 3 vulnerabilidades reais, ainda NÃO corrigidas — bloqueante para produção:**
1. **[HIGH] IDOR na API Dinâmica** (`app/api/viewsets.py:35`, `get_queryset`) — não filtra por dono do recurso; qualquer autenticado lê/altera/apaga `Projeto`/`Dataset`/`Inferencia`/`EstrategiaComposicao` de outros usuários via `/api/vci/<model>/<pk>/`.
2. **[HIGH] Permissões de grupo não aplicadas** (`config/settings_production.py:150`) — `DEFAULT_PERMISSION_CLASSES` é só `IsAuthenticated`; `DynamicModelViewSet` nunca checa `has_perm()`, então o grupo `Visualizador` (deveria ser somente leitura) consegue `POST/PUT/DELETE`.
3. **[MEDIUM] Vazamento de PII via `?depth=`** (`app/api/serializers.py:21`) — `Meta.depth` controlado pelo cliente serializa a FK `Projeto.usuario` como objeto `User` completo (email, is_staff, is_superuser, etc.).

A correção da vulnerabilidade 1 (IDOR) depende de uma decisão de escopo — nem todo model do serviço é "de um usuário só" (`Classe`/`Modelo`/`Treinamento`/`Metrica` são catálogo compartilhado; `Projeto`/`Dataset`/`Inferencia`/`EstrategiaComposicao` são pessoais, direto ou via `projeto.usuario`) — perguntada ao dev e ainda sem resposta aplicada; dev pediu para commitar/pushar o que já estava pronto e retomar a correção depois. As vulnerabilidades 2 e 3 são mecânicas (sem decisão de negócio nova) e podem ser corrigidas na próxima sessão sem nova pergunta.

**Pendente — bloqueado por infraestrutura indisponível neste ambiente:**
- [ ] Confirmar porta `8060` não colide com outro serviço PCI (Sprint 6, Passo 0 — bloqueante)
- [ ] Registrar o serviço no GestaoNginx (`/nginx/`) — precisa do Nginx gateway rodando
- [ ] Distribuir a chave pública JWT via `./copy-public-key.sh` — precisa do AuthService rodando
- [ ] Verificar autenticação com a chave pública distribuída

**Pendente — Sprint 7 (não bloqueado por infra, retomar direto):**
- [ ] Corrigir as 3 vulnerabilidades do `/security-review` acima (Passo 5 — refazer a checagem depois de corrigir)
- [ ] Commitar os ajustes de segurança (Passo 6)
- [ ] Finalizar branch / abrir PR (Passos 7-8)

**Para retomar:** primeiro decidir com o dev o escopo de ownership da vulnerabilidade IDOR (pergunta em aberto acima) e aplicar as 3 correções de segurança. Em paralelo/depois, com Docker, Nginx gateway e AuthService disponíveis (ambiente real/VPS), seguir a partir do Passo 0 da Sprint 6 abaixo. `.env` local de teste (`cp .env.example .env`, gitignorado) e um `.venv/` já existem em `VisaoComputacionalIncremental/` para conferência rápida sem Docker, se necessário.

---

## Regras do agente executor

> Estas regras se aplicam a todo agente que implementar este plano.

### Dúvidas durante a implementação

**Se em qualquer momento surgir uma dúvida — PARE e pergunte ao dev antes de continuar.**

Situações que exigem pergunta obrigatória:
- Tipo de campo de um model não está claro no `NOVO_SERVICO.md` (ex: `CharField` vs `TextField`, tamanho máximo, nullable)
- Relação entre models é ambígua (ex: ForeignKey vs ManyToMany)
- Nome de variável, rota ou grupo não está especificado
- Comportamento de negócio não descrito (ex: o que acontece quando X é deletado?)
- Qualquer decisão que afete a estrutura do banco de dados ou a API pública

Formato da pergunta:
```
⏸️ DÚVIDA — preciso de clarificação antes de continuar:

[Descreva a dúvida com contexto suficiente para o dev responder]

Opções:
  A) [opção A]
  B) [opção B]
  C) Outro (descreva)
```

Nunca assuma, nunca invente. A implementação errada custa mais que a pergunta.

**Dúvidas já sinalizadas em `NOVO_SERVICO.md` que a Sprint 3 DEVE confirmar antes de codificar `models.py`:**
- `Projeto.classes_desejadas`: `ManyToManyField(Classe)` (proposto) ou lista simples de texto?
- `Dataset.anotacoes`: `FileField` com upload de um arquivo compactado (proposto), ou múltiplos arquivos/anotações por imagem?
- `Inferencia.caixas_detectadas`: estrutura do JSON (proposto: lista de `{x, y, w, h, classe, confianca, modelo_origem}`) — confirmar formato exato.

### Monitoramento de contexto

Após o commit de cada sprint, avalie o volume da conversa atual. Se a conversa estiver longa (muitas mensagens, muito código gerado, muitos arquivos lidos), emita o aviso abaixo **antes de iniciar a próxima sprint**:

```
⚠️ AVISO DE CONTEXTO — A conversa está crescendo.
Recomendo rodar /compact agora para liberar contexto antes de continuar.
Após o /compact, retome a partir da Sprint [X].
```

Sinais de que o contexto está pesado (qualquer um é suficiente para avisar):
- Mais de 6 sprints concluídas na mesma sessão
- Muitos arquivos grandes foram lidos (models.py, settings, templates)
- Respostas do agente estão ficando mais lentas ou truncadas

---

### Sprint 0: Setup — Branch isolada e estrutura de diretório

**REQUIRED SUB-SKILL:** Use superpowers:using-git-worktrees para criar workspace isolado.

**Files:**
- Create: `VisaoComputacionalIncremental/` (diretório raiz do serviço)

- [x] **Passo 1: Invocar using-git-worktrees**

Anuncie: "Estou usando superpowers:using-git-worktrees para criar workspace isolado."
Use a skill `superpowers:using-git-worktrees` para criar um worktree ou verificar que já existe um isolado.

- [x] **Passo 2: Criar branch de feature**

```bash
git checkout -b feat/visao-computacional-incremental
# Se a branch já existir: git checkout feat/visao-computacional-incremental
```

- [x] **Passo 3: Criar diretório do serviço**

```bash
mkdir -p VisaoComputacionalIncremental
```

- [x] **Commit**

```bash
git add VisaoComputacionalIncremental/
git commit -m "chore(VisaoComputacionalIncremental): init service directory"
```

> 🔍 **Checkpoint de contexto:** avalie o volume da conversa. Se estiver pesado, avise o dev antes de continuar para a Sprint 1.

---

### Sprint 1: Estrutura base — Copiar template e configurar

**Files:**
- Copy: `pci-service-template/` → `VisaoComputacionalIncremental/`
- Modify: `VisaoComputacionalIncremental/entrypoint.sh`
- Modify: `VisaoComputacionalIncremental/docker-compose.yml`
- Modify: `VisaoComputacionalIncremental/.env.example`

- [x] **Passo 1: Copiar pci-service-template**

```bash
cp -r pci-service-template/. VisaoComputacionalIncremental/
```

Remove arquivos desnecessários:

```bash
rm -f VisaoComputacionalIncremental/db.sqlite3
rm -rf VisaoComputacionalIncremental/.git
```

- [x] **Passo 2: Atualizar entrypoint.sh com o nome do serviço**

Em `VisaoComputacionalIncremental/entrypoint.sh`, substitua a mensagem do serviço na linha `echo`:

```bash
echo "=== VisaoComputacionalIncremental Entrypoint ==="
```

> **Nota:** `settings_production.py` já está configurado com `FORCE_SCRIPT_NAME`, `SIMPLE_JWT`, `AUTHENTICATION_BACKENDS`, `AUTHSERVICE_URL`, `REQUIRED_GROUP` e isolamento de cookies — não é necessário modificar. O Docker usa este arquivo via `DJANGO_SETTINGS_MODULE=config.settings_production` definido no `entrypoint.sh`.

- [x] **Passo 3: Atualizar docker-compose.yml**

Em `VisaoComputacionalIncremental/docker-compose.yml`, substitua os nomes de serviço/container e a porta:

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: vci_app
    restart: always
    env_file:
      - .env
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - ./app/keys:/app/app/keys:ro
    depends_on:
      - db
    networks:
      - internal_network
      - nginx_network

  db:
    image: postgres:15.3
    container_name: vci_db
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-vci}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - internal_network

volumes:
  postgres_data:
  static_volume:
  media_volume:

networks:
  internal_network:
    driver: bridge
  nginx_network:
    external: true
    name: nginx_default
```

- [x] **Passo 4: Atualizar .env.example**

```
# ─── Django ───────────────────────────────────────────────────────────────────
DEBUG=False
SECRET_KEY=sua-chave-secreta-aqui-gere-uma-nova
ALLOWED_HOSTS=localhost,127.0.0.1,campusinteligente.ifsuldeminas.edu.br
CSRF_TRUSTED_ORIGINS=http://localhost,https://campusinteligente.ifsuldeminas.edu.br

# ─── Subpath (proxy reverso Nginx) ───────────────────────────────────────────
FORCE_SCRIPT_NAME=/vci
DJANGO_SETTINGS_MODULE=config.settings_production

# ─── AuthService ──────────────────────────────────────────────────────────────
AUTHSERVICE_URL=http://authservice_app:8010
JWT_PUBLIC_KEY_PATH=/app/app/keys/public.pem
REQUIRED_GROUP=VisaoComputacionalIncremental_Gerente

# ─── Banco de dados ───────────────────────────────────────────────────────────
POSTGRES_DB=vci
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

# ─── API inter-serviços ───────────────────────────────────────────────────────
API_KEY=
CORS_ALLOWED_ORIGINS=https://campusinteligente.ifsuldeminas.edu.br

# ─── Logging ──────────────────────────────────────────────────────────────────
DJANGO_LOG_LEVEL=INFO

# ─── API Dinâmica ─────────────────────────────────────────────────────────────
API_INCLUDE_META=False
```

> ⚠️ **Porta 8060 é provisória.** Confirme com o dev que não colide com outro serviço PCI (não havia `CLAUDE.md` acessível no momento do planejamento para checar automaticamente) antes de registrar no Nginx (Sprint 6).

- [x] **Passo 5: Verificar que o container sobe**

```bash
cd VisaoComputacionalIncremental
cp .env.example .env
# Preencha POSTGRES_PASSWORD no .env com valor local
docker compose up --build -d
docker compose logs app
```

Esperado: sem erros críticos (warning de chave pública é esperado neste ponto).

- [x] **Commit**

```bash
cd ..
git add VisaoComputacionalIncremental/
git commit -m "feat(VisaoComputacionalIncremental): add base Django structure from template"
```

> 🔍 **Checkpoint de contexto:** avalie o volume da conversa. Se estiver pesado, avise o dev antes de continuar para a Sprint 2.

---

### Sprint 2: Autenticação — AuthServiceBackend e JWT

**Files:**
- Modify: `VisaoComputacionalIncremental/app/backends.py`

- [x] **Passo 1: Atualizar backends.py com grupos reais**

Em `VisaoComputacionalIncremental/app/backends.py`, localize o dict `DEFAULT_GROUP_PERMISSIONS` (já existe no template) e substitua apenas seu conteúdo com os grupos reais do serviço:

```python
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
```

> **Nota:** `settings_production.py` já tem `AUTHENTICATION_BACKENDS`, `AUTHSERVICE_URL`, `REQUIRED_GROUP`, `SIMPLE_JWT` e isolamento de cookies configurados. Nenhuma modificação necessária em settings.

- [x] **Commit**

```bash
git add VisaoComputacionalIncremental/app/backends.py
git commit -m "feat(VisaoComputacionalIncremental): configure AuthServiceBackend groups"
```

> 🔍 **Checkpoint de contexto:** avalie o volume da conversa. Se estiver pesado, avise o dev antes de continuar para a Sprint 3.

---

### Sprint 3: Modelos — models.py, migrations, admin.py

**Files:**
- Modify: `VisaoComputacionalIncremental/app/models.py`
- Create: `VisaoComputacionalIncremental/app/migrations/0001_initial.py` (via makemigrations)
- Modify: `VisaoComputacionalIncremental/app/admin.py`

- [x] **Passo 0 (bloqueante): Confirmar as 3 dúvidas de campo listadas em "Regras do agente executor"**

Antes de escrever `models.py`, pare e confirme com o dev:
1. `Projeto.classes_desejadas` — `ManyToManyField(Classe)` ou texto livre?
2. `Dataset.anotacoes` — um `FileField` único (zip com imagens+anotações) ou estrutura diferente?
3. `Inferencia.caixas_detectadas` — schema exato do JSON de caixas detectadas.

O código abaixo assume as respostas mais prováveis (M2M, FileField único, lista de dicts) — ajuste conforme a resposta real do dev.

- [x] **Passo 1: Escrever models.py com os models do serviço**

Em `VisaoComputacionalIncremental/app/models.py`:

```python
from django.conf import settings
from django.db import models


class Classe(models.Model):
    nome_canonico = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['nome_canonico']
        verbose_name = 'Classe'
        verbose_name_plural = 'Classes'

    def __str__(self):
        return self.nome_canonico


class SinonimoClasse(models.Model):
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='sinonimos')
    termo_sinonimo = models.CharField(max_length=100, unique=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Sinônimo de Classe'
        verbose_name_plural = 'Dicionário de Sinônimos'

    def __str__(self):
        return f'{self.termo_sinonimo} → {self.classe.nome_canonico}'


class Projeto(models.Model):
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('verificando', 'Verificando conhecimento'),
        ('aguardando_dataset', 'Aguardando dataset'),
        ('treinando', 'Treinando'),
        ('pronto', 'Pronto'),
    ]

    nome = models.CharField(max_length=200)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='projetos')
    classes_desejadas = models.ManyToManyField(Classe, related_name='projetos')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='rascunho')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'

    def __str__(self):
        return self.nome


class Dataset(models.Model):
    SPLIT_CHOICES = [
        ('train', 'Train'),
        ('valid', 'Valid'),
        ('test', 'Test'),
    ]

    nome = models.CharField(max_length=200)
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='datasets')
    quantidade_imagens = models.PositiveIntegerField(default=0)
    anotacoes = models.FileField(upload_to='datasets/anotacoes/')
    split = models.CharField(max_length=10, choices=SPLIT_CHOICES, default='train')
    classes_cobertas = models.ManyToManyField(Classe, related_name='datasets')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Dataset'
        verbose_name_plural = 'Datasets'

    def __str__(self):
        return self.nome


class Modelo(models.Model):
    ORIGEM_CHOICES = [
        ('reutilizado', 'Reutilizado'),
        ('treinado', 'Treinado'),
    ]

    nome = models.CharField(max_length=200)
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES)
    classes_suportadas = models.ManyToManyField(Classe, related_name='modelos')
    acuracia_geral = models.FloatField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Modelo'
        verbose_name_plural = 'Modelos (Registry)'

    def __str__(self):
        return self.nome


class Treinamento(models.Model):
    STATUS_CHOICES = [
        ('em_andamento', 'Em andamento'),
        ('concluido', 'Concluído'),
        ('falhou', 'Falhou'),
    ]

    dataset = models.ForeignKey(Dataset, on_delete=models.PROTECT, related_name='treinamentos')
    modelo_base = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='em_andamento')
    epocas = models.PositiveIntegerField()
    batch_size = models.PositiveIntegerField()
    modelo_resultante = models.ForeignKey(
        Modelo, on_delete=models.SET_NULL, null=True, blank=True, related_name='treinamento_origem'
    )
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Treinamento'
        verbose_name_plural = 'Treinamentos'

    def __str__(self):
        return f'Treinamento #{self.pk} ({self.status})'


class EstrategiaComposicao(models.Model):
    ESTRATEGIA_CHOICES = [
        ('reuso_exato', 'Reuso exato'),
        ('reuso_parcial', 'Reuso parcial'),
        ('vocabulario_aberto', 'Vocabulário aberto'),
        ('treino', 'Treino'),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='estrategias')
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, related_name='estrategias')
    estrategia = models.CharField(max_length=30, choices=ESTRATEGIA_CHOICES)
    modelos_envolvidos = models.ManyToManyField(Modelo, related_name='estrategias', blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Estratégia de Composição'
        verbose_name_plural = 'Estratégias de Composição'

    def __str__(self):
        return f'{self.classe.nome_canonico} → {self.estrategia}'


class Inferencia(models.Model):
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='inferencias')
    imagem_entrada = models.ImageField(upload_to='inferencias/entrada/')
    modelos_usados = models.ManyToManyField(Modelo, related_name='inferencias')
    caixas_detectadas = models.JSONField(default=list)
    confianca_media = models.FloatField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Inferência'
        verbose_name_plural = 'Inferências'

    def __str__(self):
        return f'Inferência #{self.pk} ({self.projeto.nome})'


class Metrica(models.Model):
    ESCOPO_CHOICES = [
        ('modelo', 'Modelo'),
        ('execucao', 'Execução'),
    ]

    escopo = models.CharField(max_length=20, choices=ESCOPO_CHOICES)
    tipo = models.CharField(max_length=50)
    valor = models.FloatField()
    modelo = models.ForeignKey(Modelo, on_delete=models.CASCADE, null=True, blank=True, related_name='metricas')
    treinamento = models.ForeignKey(
        Treinamento, on_delete=models.CASCADE, null=True, blank=True, related_name='metricas'
    )
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Métrica'
        verbose_name_plural = 'Métricas'

    def __str__(self):
        return f'{self.tipo} = {self.valor}'
```

Regras obrigatórias:
- Todo model principal deve ter `data_cadastro` e `data_atualizacao`
- Ordenação padrão: `-data_cadastro`
- Models referenciados por outros: `on_delete=models.PROTECT` (`Dataset` referenciado por `Treinamento`, `Classe` referenciada por `EstrategiaComposicao`); `EstrategiaComposicao` e `Inferencia` usam `CASCADE` a partir de `Projeto` por serem dados derivados do projeto.

- [x] **Passo 2: Executar makemigrations**

```bash
cd VisaoComputacionalIncremental
docker compose exec app python manage.py makemigrations
```

Esperado: `Migrations for 'app': app/migrations/0001_initial.py`

- [x] **Passo 3: Executar migrate**

```bash
docker compose exec app python manage.py migrate
```

Esperado: `Applying app.0001_initial... OK`

- [x] **Passo 4: Registrar models no admin.py**

Em `VisaoComputacionalIncremental/app/admin.py`:

```python
from django.contrib import admin
from .models import (
    Classe, SinonimoClasse, Projeto, Dataset, Modelo,
    Treinamento, EstrategiaComposicao, Inferencia, Metrica,
)


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ['id', 'nome_canonico']
    search_fields = ['nome_canonico']


@admin.register(SinonimoClasse)
class SinonimoClasseAdmin(admin.ModelAdmin):
    list_display = ['id', 'termo_sinonimo', 'classe', 'data_cadastro']
    search_fields = ['termo_sinonimo', 'classe__nome_canonico']
    list_filter = ['classe']


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ['id', 'nome', 'usuario', 'status', 'data_cadastro']
    search_fields = ['nome']
    list_filter = ['status']


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ['id', 'nome', 'projeto', 'split', 'quantidade_imagens', 'data_cadastro']
    search_fields = ['nome']
    list_filter = ['split']


@admin.register(Modelo)
class ModeloAdmin(admin.ModelAdmin):
    list_display = ['id', 'nome', 'origem', 'acuracia_geral', 'data_cadastro']
    search_fields = ['nome']
    list_filter = ['origem']


@admin.register(Treinamento)
class TreinamentoAdmin(admin.ModelAdmin):
    list_display = ['id', 'dataset', 'status', 'epocas', 'batch_size', 'data_cadastro']
    list_filter = ['status']


@admin.register(EstrategiaComposicao)
class EstrategiaComposicaoAdmin(admin.ModelAdmin):
    list_display = ['id', 'projeto', 'classe', 'estrategia', 'data_cadastro']
    list_filter = ['estrategia']
    search_fields = ['projeto__nome', 'classe__nome_canonico']


@admin.register(Inferencia)
class InferenciaAdmin(admin.ModelAdmin):
    list_display = ['id', 'projeto', 'confianca_media', 'data_cadastro']
    search_fields = ['projeto__nome']


@admin.register(Metrica)
class MetricaAdmin(admin.ModelAdmin):
    list_display = ['id', 'escopo', 'tipo', 'valor', 'modelo', 'treinamento']
    list_filter = ['escopo', 'tipo']
```

- [x] **Commit**

```bash
cd ..
git add VisaoComputacionalIncremental/app/models.py VisaoComputacionalIncremental/app/migrations/ VisaoComputacionalIncremental/app/admin.py
git commit -m "feat(VisaoComputacionalIncremental): add data models and migrations"
```

> 🔍 **Checkpoint de contexto:** avalie o volume da conversa. Se estiver pesado, avise o dev antes de continuar para a Sprint 4.

> **Nota sobre dependências externas:** nenhum model deste serviço foi identificado como duplicata de outro serviço já existente no `APLICACOES.md`. O serviço `Transito` tem entidades com nomes parecidos (`Modelo`, `Dataset`, `Treinamento`), mas é uma aplicação de domínio específico (trânsito) — decisão do dev registrada em `NOVO_SERVICO.md`: manter models locais nesta plataforma, sem consumir a API do `Transito`.

---

### Sprint 4: API Dinâmica — Rotas, Swagger, ReDoc

**Files:**
- Verify: `VisaoComputacionalIncremental/app/api/` (já copiada do template — verificar integridade)
- Modify: `VisaoComputacionalIncremental/app/api/urls.py`
- Modify: `VisaoComputacionalIncremental/config/urls.py`

- [x] **Passo 1: Verificar que app/api/ está completa**

Verifique que a pasta `VisaoComputacionalIncremental/app/api/` existe. Ela foi copiada automaticamente de `pci-service-template/` no Sprint 1. Se estiver faltando algum arquivo, copie de `pci-service-template/app/api/`.

- [x] **Passo 2: Atualizar _PREFIX em app/api/urls.py**

Em `VisaoComputacionalIncremental/app/api/urls.py`, substitua o valor de `_PREFIX` na linha 9:

```python
_PREFIX = "vci"
```

Este prefixo define as URLs da API: `/api/vci/<model>/` e `/api/vci/<model>/<pk>/`.

- [x] **Passo 3: Atualizar config/urls.py com rotas da API Dinâmica**

Em `VisaoComputacionalIncremental/config/urls.py`:

```python
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
    path('', include('app.api.urls')),
    path("", include("app.urls")),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
```

- [x] **Passo 4: Verificar Swagger**

```bash
cd VisaoComputacionalIncremental
docker compose restart app
```

Acesse: `http://localhost:8060/vci/swagger/`
Esperado: página do Swagger carregada com endpoints da API Dinâmica visíveis.

- [x] **Commit**

```bash
cd ..
git add VisaoComputacionalIncremental/config/urls.py VisaoComputacionalIncremental/app/api/
git commit -m "feat(VisaoComputacionalIncremental): add dynamic API and Swagger"
```

> 🔍 **Checkpoint de contexto:** avalie o volume da conversa. Se estiver pesado, avise o dev antes de continuar para a Sprint 5.

---

### Sprint 5: Views e Templates — Interface web base

**Files:**
- Modify: `VisaoComputacionalIncremental/app/views.py`
- Modify: `VisaoComputacionalIncremental/app/urls.py`
- Modify: `VisaoComputacionalIncremental/app/templates/app/base.html`
- Modify: `VisaoComputacionalIncremental/app/templates/app/home.html`

- [x] **Passo 1: Atualizar views.py com home view autenticada**

Em `VisaoComputacionalIncremental/app/views.py`, o template já tem `home` e `logout_view`. Substitua `'VisaoComputacionalIncremental'` no contexto do `home` view:

```python
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.contrib import messages


@login_required
def home(request):
    return render(request, 'app/home.html', {
        'user': request.user,
        'service_name': 'VisaoComputacionalIncremental',
    })


def logout_view(request):
    auth_logout(request)
    messages.success(request, "Você saiu com sucesso.")
    return redirect('login')
```

- [x] **Passo 2: Atualizar app/urls.py**

Em `VisaoComputacionalIncremental/app/urls.py`:

```python
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="app/login.html"), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.home, name="home"),
]
```

- [x] **Passo 3: Atualizar base.html com nome do serviço**

Em `VisaoComputacionalIncremental/app/templates/app/base.html`, substitua o título e nome exibido:

```html
<title>VisaoComputacionalIncremental — Campus Inteligente</title>
```

e no navbar/header:

```html
<span class="service-name">VisaoComputacionalIncremental</span>
```

- [x] **Passo 4: Atualizar home.html com dashboard básico**

Em `VisaoComputacionalIncremental/app/templates/app/home.html`, adicione um bloco de boas-vindas com o nome do serviço e um resumo dos projetos do usuário:

```html
{% extends 'app/base.html' %}
{% block content %}
<h1>Bem-vindo ao VisaoComputacionalIncremental</h1>
<p>Olá, {{ user.username }}.</p>
<!-- Adicionar cards/links para Projeto, Dataset, Modelo (Registry) e Inferência conforme a UI evoluir -->
{% endblock %}
```

- [x] **Passo 5: Verificar login e home**

```bash
cd VisaoComputacionalIncremental
docker compose restart app
```

Acesse `http://localhost:8060/vci/login/` — deve exibir o formulário de login.
Faça login com credenciais do AuthService — deve redirecionar para home.

- [x] **Commit**

```bash
cd ..
git add VisaoComputacionalIncremental/app/views.py VisaoComputacionalIncremental/app/urls.py VisaoComputacionalIncremental/app/templates/
git commit -m "feat(VisaoComputacionalIncremental): add base views and templates"
```

> 🔍 **Checkpoint de contexto:** avalie o volume da conversa. Se estiver pesado, avise o dev antes de continuar para a Sprint 6.

---

### Sprint 6: Infraestrutura — Nginx, chave JWT, CI/CD

**Files:**
- Create: `VisaoComputacionalIncremental/app/keys/public.pem` (via copy-public-key.sh)
- Create: `VisaoComputacionalIncremental/.github/workflows/ci-cd.yml`

- [ ] **Passo 0 (bloqueante): Confirmar a porta 8060 com o dev**

Antes de registrar no Nginx, confirme que a porta `8060` não colide com nenhum outro serviço PCI já em produção. Se colidir, ajuste `docker-compose.yml` e `.env.example` (Sprint 1) antes de prosseguir.

- [ ] **Passo 1: Registrar serviço no GestaoNginx**

Acesse `/nginx/` no ambiente de desenvolvimento.
Cadastre o novo serviço com:
- Nome: `VisaoComputacionalIncremental`
- Upstream: `vci_app:8060`
- URL: `/vci/`
- Categoria: `django_app`

Clique em "Aplicar configuração" — deve executar `nginx -t` e `nginx -s reload` com sucesso.

- [ ] **Passo 2: Distribuir chave pública JWT**

```bash
./copy-public-key.sh
```

Verifique que o arquivo foi criado:

```bash
ls VisaoComputacionalIncremental/app/keys/public.pem
```

Esperado: arquivo existe e não está vazio.

- [ ] **Passo 3: Verificar autenticação com chave pública**

```bash
cd VisaoComputacionalIncremental
docker compose restart app
docker compose logs app
```

Esperado: sem erros de `JWT_PUBLIC_KEY_PATH`.

- [x] **Passo 4: Configurar CI/CD**

Copie o workflow do template:

```bash
mkdir -p VisaoComputacionalIncremental/.github/workflows
cp pci-service-template/.github/workflows/ci-cd.yml VisaoComputacionalIncremental/.github/workflows/ci-cd.yml
```

Edite `VisaoComputacionalIncremental/.github/workflows/ci-cd.yml` e ajuste:
- `IMAGE_NAME`: `ghcr.io/<org>/visao-computacional-incremental`
- `CONTAINER_NAME`: `vci_app`
- Secrets necessários: `GHCR_TOKEN`, `SSH_HOST`, `SSH_USER`, `SSH_KEY`

- [ ] **Commit**

```bash
cd ..
git add VisaoComputacionalIncremental/.github/
git commit -m "feat(VisaoComputacionalIncremental): add infrastructure config (nginx, jwt key, ci-cd)"
```

> 🔍 **Checkpoint de contexto:** Sprint 6 concluída — este é o ponto mais comum de contexto pesado. Avise o dev e recomende fortemente `/compact` antes de iniciar a Sprint 7.

> Nota: nunca commitar `public.pem` diretamente se o `.gitignore` não a excluir — verificar antes.

---

### Sprint 7: Qualidade e PR — Init, Simplify, Security Review, PR

- [ ] **Passo 1: Gerar CLAUDE.md do serviço**

Com o Claude Code aberto na pasta `VisaoComputacionalIncremental/`:

```
/init
```

Verifique que `VisaoComputacionalIncremental/CLAUDE.md` foi gerado com contexto específico do serviço.

- [ ] **Passo 2: Atualizar CLAUDE.md com o novo serviço**

Em `CLAUDE.md` (raiz do PCI, se/quando este serviço for integrado ao monorepo principal), localize o bloco `## Arquitetura` e insira uma nova linha para o serviço na lista de rotas do Nginx, seguindo o padrão de formatação existente:

```
  ├── /vci/       → VisaoComputacionalIncremental    (8060)
```

Insira em ordem alfabética pelo prefixo entre as linhas existentes. Não altere nenhuma outra parte do arquivo.

> **Nota:** este repositório não possuía `CLAUDE.md` acessível no momento do planejamento — se o serviço for movido para o monorepo principal do PCI, aplicar este passo lá.

- [ ] **Passo 3: Atualizar APLICACOES.md com os endpoints do novo serviço**

Em `APLICACOES.md` (`documentação/APLICACOES.md` neste repositório), adicione uma nova seção para o serviço em ordem alfabética entre as seções existentes:

```markdown
## VisaoComputacionalIncremental
- GET `/admin/`
- GET `/api/vci/schema/`
- GET `/api/vci/me/`
- GET `/api/vci/<model>/`
- POST `/api/vci/<model>/`
- GET `/api/vci/<model>/<pk>/`
- PUT `/api/vci/<model>/<pk>/`
- PATCH `/api/vci/<model>/<pk>/`
- DELETE `/api/vci/<model>/<pk>/`
- GET `/swagger/`
- GET `/redoc/`
- GET `/swagger.json`
- GET `/login/`
- GET `/logout/`
- GET `/`
```

Se o serviço tiver views customizadas (além das padrão — ex.: rota específica para disparar treinamento ou rodar inferência via upload de imagem), adicione-as também com base no `app/urls.py` gerado.

- [ ] **Commit das atualizações de documentação**

```bash
git add CLAUDE.md documentação/APLICACOES.md
git commit -m "docs: register VisaoComputacionalIncremental in architecture map and endpoint catalog"
```

- [ ] **Passo 4: Revisar e simplificar código**

```
/simplify
```

Aplique as sugestões de simplificação: elimine abstrações desnecessárias, código duplicado e padrões fora do estilo do projeto.

- [ ] **Passo 5: Revisão de segurança**

```
/security-review
```

Verifique especialmente:
- JWT configurado com RS256 e chave pública (não HMAC)
- `set_unusable_password()` sendo chamado no backends.py
- Sem `SECRET_KEY` ou senha hardcoded
- `CORS_ALLOWED_ORIGINS` sem wildcard
- `CSRF_TRUSTED_ORIGINS` configurado
- Upload de dataset e de imagem para inferência (RF07, RF13) validam tipo/tamanho de arquivo antes de gravar em disco

Corrija qualquer vulnerabilidade antes de continuar.

- [ ] **Passo 6: Commitar ajustes de qualidade**

```bash
git add VisaoComputacionalIncremental/
git commit -m "refactor(VisaoComputacionalIncremental): apply simplify and security review fixes"
```

- [ ] **Passo 7: Finalizar branch de desenvolvimento**

Anuncie: "Estou usando superpowers:finishing-a-development-branch para finalizar."

Use a skill `superpowers:finishing-a-development-branch` — ela verificará o estado da branch e apresentará as opções de merge/PR.

- [ ] **Passo 8: Revisar Pull Request**

Após o PR ser aberto:

```
/review
```

Aplique o feedback antes do merge na `main`.
