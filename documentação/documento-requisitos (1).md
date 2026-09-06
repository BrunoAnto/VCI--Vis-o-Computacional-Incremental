# Documento de Casos de Uso e Requisitos
## Plataforma de Criação e Evolução de Modelos Personalizados de Detecção de Objetos

---

## 1. Visão Geral

A plataforma permite que um usuário defina um conjunto de classes de objetos que deseja detectar em imagens. Antes de treinar qualquer modelo novo, o sistema verifica se já existe conhecimento reutilizável (modelos previamente treinados, cadastrados no *Model Registry*) capaz de detectar total ou parcialmente as classes solicitadas. Classes sem modelo específico são tratadas por um modelo de vocabulário aberto (fallback) ou, se necessário, por treinamento (fine-tuning) a partir de dados fornecidos pelo usuário. O resultado final é obtido por meio de um **ensemble em tempo de inferência**, combinando as saídas dos modelos reutilizados com as do modelo recém-treinado.

**Decisões de escopo (MVP):**
- Reutilização de múltiplos modelos ocorre via **ensemble em inferência** (execução paralela + combinação de detecções), não fusão/retreino de pesos em um único modelo.
- A verificação de disponibilidade de modelo para uma classe usa um **dicionário/taxonomia de sinônimos fixo** (ex.: "capacete" = "helmet" = "hard hat"), sem correspondência semântica via embeddings.
- O foco de avaliação é **engenharia de software**: arquitetura, requisitos, testes e documentação têm prioridade sobre otimização de acurácia de ML.

---

## 2. Atores

| Ator | Descrição |
|---|---|
| **Usuário** | Pessoa que deseja criar um detector personalizado; informa classes desejadas e, quando necessário, fornece dataset próprio. |
| **Sistema (Plataforma)** | Automatiza a verificação de conhecimento existente, o planejamento de treino/reuso, o treinamento e a geração do modelo/ensemble final. |
| **Administrador** | Responsável por cadastrar/curar modelos no Model Registry e manter o dicionário de sinônimos. |

---

## 3. Casos de Uso

### UC01 — Definir classes desejadas
**Ator:** Usuário
**Descrição:** O usuário informa quais objetos (classes) deseja detectar.
**Pré-condição:** Usuário autenticado na plataforma.
**Fluxo principal:**
1. Usuário acessa a tela de criação de detector.
2. Usuário digita/seleciona as classes desejadas (ex.: cão, gato, capacete).
3. Sistema registra a solicitação e avança para verificação de conhecimento (UC02).

### UC02 — Verificar conhecimento existente
**Ator:** Sistema
**Descrição:** Para cada classe solicitada, o sistema consulta o Model Registry (via dicionário de sinônimos) para verificar se existe modelo já treinado que a detecte.
**Fluxo principal:**
1. Sistema normaliza o nome de cada classe usando o dicionário de sinônimos.
2. Sistema consulta o Model Registry por classe normalizada.
3. Para cada classe, o sistema classifica o resultado como: **modelo exato disponível**, **modelo parcial disponível** (ex.: modelo multi-classe que contém a classe) ou **sem modelo disponível**.
4. Sistema encaminha o resultado ao Training Planner (UC03).

### UC03 — Planejar treinamento e reuso
**Ator:** Sistema
**Descrição:** Com base no resultado da verificação, o sistema decide, por classe, se reutiliza modelo existente, aplica fallback de vocabulário aberto, ou aciona treinamento.
**Regras de decisão:**
- Modelo exato disponível → reutilizar diretamente.
- Modelo parcial disponível (multi-classe) → reutilizar, filtrando a saída para a classe de interesse.
- Sem modelo disponível → tentar modelo de vocabulário aberto; se confiança insuficiente ou usuário exigir maior precisão, encaminhar para treinamento (UC05), condicionado à existência de dataset (UC04).

### UC04 — Fornecer dataset para classes sem modelo
**Ator:** Usuário
**Descrição:** Quando uma classe não possui modelo reutilizável adequado, o usuário fornece imagens anotadas para viabilizar o treinamento.
**Fluxo principal:**
1. Sistema notifica o usuário sobre quais classes exigem dataset.
2. Usuário faz upload de imagens anotadas (formato definido pela plataforma).
3. Sistema valida o dataset (formato, quantidade mínima de exemplos, anotações consistentes).

### UC05 — Treinar modelo para classe(s) sem cobertura
**Ator:** Sistema
**Descrição:** O sistema realiza fine-tuning de um modelo-base pré-treinado (ex.: YOLO pré-treinado) utilizando o dataset fornecido, gerando um modelo específico para a(s) classe(s) faltante(s).
**Pós-condição:** Novo modelo é cadastrado no Model Registry, disponível para reuso futuro.

### UC06 — Compor detector personalizado (ensemble)
**Ator:** Sistema
**Descrição:** O sistema combina, em tempo de inferência, os modelos reutilizados e o(s) modelo(s) recém-treinado(s) para formar o detector final.
**Fluxo principal:**
1. Sistema executa cada modelo envolvido sobre a imagem de entrada.
2. Sistema filtra as detecções pela classe de interesse de cada modelo.
3. Sistema combina as detecções (ex.: supressão de não-máximos entre caixas sobrepostas).
4. Sistema retorna o resultado consolidado.

### UC07 — Executar inferência
**Ator:** Usuário
**Descrição:** Usuário envia uma imagem (ou lote de imagens) para o detector personalizado já composto e recebe as detecções.

### UC08 — Cadastrar/curar modelo no Registry
**Ator:** Administrador
**Descrição:** Administrador cadastra manualmente um modelo pré-treinado no Model Registry, associando-o às classes que ele detecta (usando os termos do dicionário de sinônimos).

### UC09 — Manter dicionário de sinônimos
**Ator:** Administrador
**Descrição:** Administrador inclui/edita entradas do dicionário de sinônimos usado na normalização de nomes de classes.

---

## 4. Requisitos Funcionais (RF)

| ID | Descrição |
|---|---|
| RF01 | O sistema deve permitir que o usuário informe uma lista de classes desejadas para detecção. |
| RF02 | O sistema deve normalizar os nomes de classes informados usando um dicionário de sinônimos fixo. |
| RF03 | O sistema deve consultar o Model Registry para verificar, por classe, se existe modelo exato, parcial ou nenhum modelo disponível. |
| RF04 | O sistema deve reutilizar diretamente um modelo quando houver correspondência exata de classe. |
| RF05 | O sistema deve reutilizar um modelo multi-classe filtrando sua saída para a classe de interesse, quando houver correspondência parcial. |
| RF06 | O sistema deve aplicar um modelo de vocabulário aberto como fallback para classes sem modelo cadastrado. |
| RF07 | O sistema deve permitir que o usuário faça upload de um dataset anotado para classes sem modelo reutilizável adequado. |
| RF08 | O sistema deve validar o dataset enviado (formato de anotação, quantidade mínima de imagens por classe). |
| RF09 | O sistema deve treinar (fine-tuning) um modelo a partir de um modelo-base pré-treinado, usando o dataset validado. |
| RF10 | O sistema deve cadastrar automaticamente, no Model Registry, todo modelo resultante de treinamento realizado pela plataforma. |
| RF11 | O sistema deve compor um detector personalizado combinando, via ensemble, os modelos reutilizados e treinados relevantes para as classes solicitadas. |
| RF12 | O sistema deve aplicar supressão de não-máximos (NMS) ou técnica equivalente para consolidar detecções sobrepostas entre modelos do ensemble. |
| RF13 | O sistema deve permitir que o usuário envie imagens para inferência usando o detector personalizado composto. |
| RF14 | O sistema deve exibir ao usuário, para cada classe solicitada, qual estratégia foi usada (reuso exato, reuso parcial, vocabulário aberto ou treino). |
| RF15 | O sistema deve permitir que um administrador cadastre manualmente um modelo no Model Registry, associando-o a uma ou mais classes. |
| RF16 | O sistema deve permitir que um administrador edite o dicionário de sinônimos usado na normalização de classes. |
| RF17 | O sistema deve registrar, para cada classe processada em um projeto, a estratégia de composição utilizada (reuso exato, reuso parcial, vocabulário aberto ou treino) e o(s) modelo(s) envolvido(s), de forma persistente. |

---

## 5. Requisitos Não Funcionais (RNF)

| ID | Descrição |
|---|---|
| RNF01 | **Modularidade:** os componentes (Registry, Training Planner, módulo de treino, módulo de inferência/ensemble) devem ser desacoplados, comunicando-se por interfaces bem definidas, para permitir testes e evolução independentes. |
| RNF02 | **Testabilidade:** cada componente principal deve possuir cobertura de testes automatizados (unitários e, quando aplicável, de integração). |
| RNF03 | **Extensibilidade:** deve ser possível adicionar novos modelos ao Registry sem alterar código-fonte da plataforma (cadastro via configuração/API). |
| RNF04 | **Documentação:** a arquitetura, as APIs internas e as decisões de design devem estar documentadas (ex.: README, diagramas de componentes/sequência). |
| RNF05 | **Desempenho de consulta:** a verificação de disponibilidade de modelo no Registry deve responder em tempo aceitável para uso interativo (ex.: poucos segundos), mesmo com o crescimento do número de modelos cadastrados. |
| RNF06 | **Rastreabilidade:** o sistema deve manter histórico de qual estratégia (reuso/treino) foi usada para compor cada detector, possibilitando auditoria posterior. |
| RNF07 | **Usabilidade:** a interface deve comunicar claramente ao usuário, em linguagem não técnica, o que está acontecendo (ex.: "não encontramos modelo para 'gato', vamos precisar de imagens suas"). |
| RNF08 | **Portabilidade:** o ambiente de treinamento e inferência deve ser reprodutível (ex.: containerização), evitando dependência de configuração manual do ambiente. |

---

## 6. Regras de Negócio

- **RN01:** A normalização de classe é feita por busca exata no dicionário de sinônimos; termos não mapeados são tratados como classes desconhecidas (sem correspondência).
- **RN02:** Um modelo multi-classe é considerado correspondência parcial para uma classe se essa classe estiver entre as classes que o modelo suporta, segundo seu cadastro no Registry.
- **RN03:** O fallback de vocabulário aberto só é utilizado quando não há modelo exato nem parcial cadastrado para a classe.
- **RN04:** O treinamento (UC05) só é acionado se o usuário fornecer dataset válido; sem dataset, a plataforma utiliza exclusivamente o fallback de vocabulário aberto para a classe em questão.

---

## 7. Fora de Escopo (nesta versão)

- Fusão real de pesos entre modelos (aprendizado incremental / class-incremental learning) — mantido como trabalho futuro.
- Correspondência semântica de classes via embeddings — mantido como trabalho futuro.
- Poda ou especialização de um modelo multi-classe para extrair apenas uma "cabeça" de detecção.
- Aprendizado contínuo automático a partir de dados de múltiplos usuários (questões de privacidade e catastrophic forgetting não endereçadas nesta versão).

---

## 8. Matriz de Entidades (Visão de Dados / CRUD)

Complementa a visão de casos de uso com a perspectiva de dados: quais entidades o sistema gerencia e quais atributos cada uma carrega. Cada entidade referencia os RFs relacionados para rastreabilidade.

| Entidade | Operações | Atributos principais | RFs relacionados |
|---|---|---|---|
| **Projeto** | CRUD | nome, classes desejadas, datasets vinculados, status | RF01, RF14 |
| **Classe** | CRUD (admin) | nome canônico | RF02 |
| **Dicionário de Sinônimos** | CRUD (admin) | termo canônico, lista de sinônimos | RF02, RF16 |
| **Dataset** | Create / Read / Delete | nome, quantidade de imagens, anotações, split (train/valid/test), classes cobertas | RF07, RF08 |
| **Modelo (Registry)** | CRUD (curadoria admin) + criação automática pós-treino | nome, origem (reutilizado / treinado), classes suportadas, acurácia geral | RF03, RF04, RF05, RF10, RF15 |
| **Treinamento** | Create / Read | status (em andamento / concluído), dataset usado, modelo-base, épocas, batch size | RF09 |
| **Estratégia de Composição** | Create / Read (log, não editável) | classe, estratégia usada (reuso exato / reuso parcial / vocabulário aberto / treino), modelo(s) envolvido(s) | RF14, RF17, RNF06 |
| **Detecção / Inferência** | Create / Read | imagem de entrada, modelo(s)/ensemble usado, caixas detectadas, confiança por caixa | RF11, RF12, RF13 |
| **Métrica** | Create / Read | escopo (por modelo ou por execução), tipo (mAP, precisão, recall, etc.), valor | — (a formalizar) |

> **Observação:** a entidade **Estratégia de Composição** é a peça que conecta o Training Planner (UC03) à interface do usuário — é ela que alimenta a tela de "por classe, o que foi feito" sugerida no item 9 abaixo. Sem essa entidade, fica difícil implementar o RF14 e o RNF06 de forma consistente.

---

## 9. Observações sobre o rascunho de telas

- O fluxo original desenhado (Projeto → classes/imagem → consulta Registro → Reutiliza? Sim/Não → treina se não → Modelo Personalizado → Inferência → Imagem Detectada) está alinhado com UC01, UC02, UC03, UC05 e UC07, mas tratava a decisão "Reutiliza? Sim/Não" como única para o projeto inteiro.
- **Fluxo corrigido:** a decisão de reuso ocorre **por classe**, não como uma decisão única para o projeto inteiro — cada classe pode seguir um caminho diferente (reuso exato, reuso parcial, vocabulário aberto ou treino). O fluxo passa a ser: Projeto → classes/imagem → consulta Registry (por classe) → tela intermediária listando, por classe, a estratégia identificada (reuso exato / reuso parcial / vocabulário aberto / treino) → treina somente as classes sem cobertura adequada (condicionado a dataset, UC04) → composição do detector por ensemble (UC06) → Inferência → Imagem Detectada. Exemplo da tela intermediária: "capacete → modelo encontrado / gato → será treinado / cão → modelo parcial encontrado".
- **Fallback de vocabulário aberto e ensemble representados no fluxo:** o fallback de vocabulário aberto (RF06) passa a aparecer como uma das estratégias possíveis na tela intermediária por classe, e a composição por ensemble em tempo de inferência (RF11/RF12) passa a ser uma etapa explícita do fluxo, entre o treinamento condicional e a inferência, e deve ser indicada de forma simples também na tela de resultado (ex.: quais modelos participaram do ensemble para aquela imagem).

---

## 10. Próximos Passos Sugeridos

1. Validar este documento com o time e o professor/orientador da disciplina.
2. Detalhar diagramas de sequência para os casos de uso críticos (UC02, UC03, UC06).
3. Definir a arquitetura de componentes e as tecnologias (ex.: framework de detecção, formato de armazenamento do Registry).
4. Definir critérios de aceite/teste para cada RF, para uso posterior em testes automatizados.
5. Revisar o rascunho de telas incorporando a exibição por classe da estratégia usada (item 9) e refinar os wireframes para as telas de Projeto, Dataset, Treinamento e Resultado.
6. Formalizar as métricas de avaliação (mAP, precisão, recall) na entidade Métrica, hoje ainda em aberto.
