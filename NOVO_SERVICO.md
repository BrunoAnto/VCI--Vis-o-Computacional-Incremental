### VisaoComputacionalIncremental

**Descrição:** Plataforma de criação e evolução de detectores de objetos personalizados: verifica reuso de modelos já treinados (Model Registry via dicionário de sinônimos), aplica fallback de vocabulário aberto, treina (fine-tuning) apenas as classes sem cobertura e compõe o detector final por ensemble em tempo de inferência.
**URL Base:** `/vci/`
**Porta interna:** `8060` — **PROVISÓRIA, a confirmar com o dev antes da Sprint 1** (não há CLAUDE.md acessível neste ambiente para checar conflito com outros serviços PCI).
**Status:** 🔧 Planejado

---

#### Problema que resolve

Hoje, criar um detector de objetos para um conjunto de classes exige treinar do zero, mesmo quando parte das classes já é coberta por modelos existentes. A plataforma automatiza a decisão por classe — reusar modelo exato, reusar modelo parcial (multi-classe) filtrando a saída, cair para um modelo de vocabulário aberto, ou treinar (fine-tuning) a partir de dataset fornecido pelo usuário — e compõe o resultado final via ensemble em tempo de inferência (execução paralela dos modelos envolvidos + NMS), sem fundir pesos nem exigir retreino de um modelo único.

---

#### Requisitos Funcionais

- **RF-01:** O sistema deve permitir que o usuário informe uma lista de classes desejadas para detecção.
- **RF-02:** O sistema deve normalizar os nomes de classes informados usando um dicionário de sinônimos fixo.
- **RF-03:** O sistema deve consultar o Model Registry para verificar, por classe, se existe modelo exato, parcial ou nenhum modelo disponível.
- **RF-04:** O sistema deve reutilizar diretamente um modelo quando houver correspondência exata de classe.
- **RF-05:** O sistema deve reutilizar um modelo multi-classe filtrando sua saída para a classe de interesse, quando houver correspondência parcial.
- **RF-06:** O sistema deve aplicar um modelo de vocabulário aberto como fallback para classes sem modelo cadastrado.
- **RF-07:** O sistema deve permitir que o usuário faça upload de um dataset anotado para classes sem modelo reutilizável adequado.
- **RF-08:** O sistema deve validar o dataset enviado (formato de anotação, quantidade mínima de imagens por classe).
- **RF-09:** O sistema deve treinar (fine-tuning) um modelo a partir de um modelo-base pré-treinado, usando o dataset validado.
- **RF-10:** O sistema deve cadastrar automaticamente, no Model Registry, todo modelo resultante de treinamento realizado pela plataforma.
- **RF-11:** O sistema deve compor um detector personalizado combinando, via ensemble, os modelos reutilizados e treinados relevantes para as classes solicitadas.
- **RF-12:** O sistema deve aplicar supressão de não-máximos (NMS) ou técnica equivalente para consolidar detecções sobrepostas entre modelos do ensemble.
- **RF-13:** O sistema deve permitir que o usuário envie imagens para inferência usando o detector personalizado composto.
- **RF-14:** O sistema deve exibir ao usuário, para cada classe solicitada, qual estratégia foi usada (reuso exato, reuso parcial, vocabulário aberto ou treino).
- **RF-15:** O sistema deve permitir que um administrador cadastre manualmente um modelo no Model Registry, associando-o a uma ou mais classes.
- **RF-16:** O sistema deve permitir que um administrador edite o dicionário de sinônimos usado na normalização de classes.
- **RF-17:** O sistema deve registrar, para cada classe processada em um projeto, a estratégia de composição utilizada (reuso exato, reuso parcial, vocabulário aberto ou treino) e o(s) modelo(s) envolvido(s), de forma persistente.

---

#### Modelos de Dados

| Model | Campos principais | Descrição |
|---|---|---|
| `Projeto` | `nome`, `usuario`, `classes_desejadas`, `status` | Projeto de detector criado por um usuário; agrega classes, datasets e resultado final. RF01, RF14 |
| `Classe` | `nome_canonico` | Classe canônica de objeto reconhecida pela plataforma (curadoria admin). RF02 |
| `SinonimoClasse` | `classe` (FK Classe), `termo_sinonimo` | Entrada do dicionário de sinônimos fixo usado na normalização (ex.: "capacete" = "helmet"). RF02, RF16 |
| `Dataset` | `nome`, `projeto` (FK), `quantidade_imagens`, `anotacoes`, `split`, `classes_cobertas` (M2M Classe) | Dataset anotado enviado pelo usuário para classes sem modelo reutilizável. RF07, RF08 |
| `Modelo` | `nome`, `origem` (reutilizado/treinado), `classes_suportadas` (M2M Classe), `acuracia_geral` | Entrada do Model Registry — modelo cadastrado manualmente (admin) ou gerado por treinamento. RF03, RF04, RF05, RF10, RF15 |
| `Treinamento` | `dataset` (FK), `modelo_base`, `status`, `epocas`, `batch_size`, `modelo_resultante` (FK Modelo, nulo até concluir) | Execução de fine-tuning a partir de um dataset validado. RF09 |
| `EstrategiaComposicao` | `projeto` (FK), `classe` (FK), `estrategia` (reuso_exato/reuso_parcial/vocabulario_aberto/treino), `modelos_envolvidos` (M2M Modelo) | Log imutável de qual estratégia foi usada por classe/projeto — alimenta RF14 e a rastreabilidade (RNF06). RF14, RF17, RNF06 |
| `Inferencia` | `projeto` (FK), `imagem_entrada`, `modelos_usados` (M2M Modelo), `caixas_detectadas` (JSON), `confianca_media` | Execução de inferência via ensemble sobre uma imagem; guarda quais modelos participaram. RF11, RF12, RF13 |
| `Metrica` | `escopo` (modelo/execucao), `tipo` (mAP/precisao/recall), `valor`, `modelo` (FK Modelo, nulo), `treinamento` (FK Treinamento, nulo) | Métrica de avaliação associada a um modelo ou a uma execução de treinamento (ainda a formalizar segundo o PRD). — |

> **Nota para a Sprint 3:** `classes_desejadas` (Projeto), `anotacoes` (Dataset) e `caixas_detectadas` (Inferência) têm formato de dado não totalmente especificado no documento de requisitos (lista simples? M2M? JSON estruturado?). Isso deve ser esclarecido com o dev antes de codificar `models.py`, conforme regra de "parar e perguntar" do plano.

---

#### Grupos e Permissões

| Grupo | Permissões |
|---|---|
| `VisaoComputacionalIncremental_Gerente` | Todas (`'all'`) — inclui cadastro/curadoria de `Modelo` e `SinonimoClasse` (Administrador, UC08/UC09) |
| `VisaoComputacionalIncremental_Usuario` | Criar/editar/ver seus próprios `Projeto`, `Dataset`, `Inferencia`; ver `Modelo`, `Classe`, `Treinamento`, `EstrategiaComposicao` (somente leitura) |
| `VisaoComputacionalIncremental_Visualizador` | Ver `Projeto`, `Modelo`, `Classe`, `EstrategiaComposicao`, `Inferencia` — sem criar/editar |

---

#### Dependências com outros serviços

| Serviço | Tipo | Motivo |
|---|---|---|
| AuthService | Consome (AuthServiceBackend) | Login e sincronização de grupos/permissões |

> **Observação sobre `Transito`:** o serviço `Transito` já existente no ecossistema PCI possui entidades com nomes semelhantes (`Modelo`, `Dataset`, `Arquitetura`, `Treinamento`), mas é uma aplicação de domínio específico (trânsito). Decisão do dev: manter models locais nesta plataforma (que é o Model Registry/motor genérico), sem consumir a API do `Transito`. Revisitar no futuro a possibilidade de o `Transito` migrar para consumir esta plataforma.
