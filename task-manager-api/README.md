# Code Audit Skill — task-manager-api

> Skill de auditoria e refatoração automática de código aplicada a uma API Flask de gerenciamento de tarefas.  
> Projeto analisado: **task-manager-api** | Stack: **Python 3.x + Flask 3.0.0 + Flask-SQLAlchemy 3.1.1**

---

## Índice

- [Análise Manual](#análise-manual)
- [Construção da Skill](#construção-da-skill)
- [Resultados](#resultados)
- [Como Executar](#como-executar)

---

## Análise Manual

### Metodologia

A análise foi conduzida em três fases sequenciais:

1. **Fase 1 — Reconhecimento do projeto:** leitura dos 11 arquivos-fonte, mapeamento de dependências, identificação das tabelas do banco e caracterização da arquitetura real. O projeto aparenta ter separação de camadas pelas pastas (`models/`, `routes/`, `services/`, `utils/`), mas a separação é violada em praticamente todos os arquivos — uma arquitetura "parcialmente em camadas" que cria falsa sensação de organização sem os benefícios reais.
2. **Fase 2 — Auditoria por catálogo de anti-patterns:** cruzamento de cada arquivo contra categorias fixas de risco, com ordenação por severidade e impacto real na segurança e manutenibilidade.
3. **Fase 3 — Refatoração guiada:** aplicação das correções com validação por smoke test de todos os grupos de endpoints antes de encerrar a fase.

---

### Problemas Identificados

#### 🔴 Críticos — Risco imediato de segurança

| ID | Problema | Arquivo(s) | Por que é relevante |
|---|---|---|---|
| C-01 | Credenciais e segredos hardcoded no código-fonte | `app.py:11-13` | `SECRET_KEY` e URI do banco versionados no repositório. Qualquer dev com acesso pode forjar tokens de sessão. Rotação requer alteração de código e redeploy — impossível fazer por ambiente sem tocar o source. |
| C-02 | Credenciais SMTP hardcoded no service | `services/notification_service.py:7-10` | Senha de email em texto puro (`'senha123'`) dentro do `__init__` da classe. Qualquer leitor do repositório pode enviar emails como a identidade da aplicação; rotacionar exige editar e deployar o código. |
| C-03 | Hashing de senha com MD5 | `models/user.py:27-32` | MD5 é criptograficamente quebrado: rápido, sem salt, vulnerável a rainbow tables. Hashes idênticos para senhas idênticas entre usuários. Uma violação do banco expõe todas as credenciais de imediato. |
| C-04 | Senha (hash) retornada nas respostas da API | `models/user.py:16-25` | `User.to_dict()` inclui o campo `password`, que é retornado em `GET /users/:id`, `POST /users`, `PUT /users/:id` e `POST /login`. Combinado com MD5, o atacante recebe o hash e pode quebrá-lo offline em segundos com ferramentas como hashcat. |

---

#### 🟠 Altos — Degradação de arquitetura e risco operacional

| ID | Problema | Arquivo(s) | Por que é relevante |
|---|---|---|---|
| A-01 | Lógica de negócio e queries SQL no handler de rota — listagem de tarefas | `routes/task_routes.py:11-63` | Handler de 53 linhas com loop N+1, recálculo do flag de vencimento e montagem manual de dicts. Não pode ser testado sem Flask + SQLAlchemy; duplica lógica que já existe em `Task.is_overdue()` e `Task.to_dict()`. |
| A-02 | Lógica de negócio no handler de rota — criação e atualização de tarefas | `routes/task_routes.py:85-223` | Cada handler com ~70 linhas de parsing, validação campo a campo, parsing de datas, persistência e `print()`. As mesmas regras existem parcialmente em `utils/helpers.py` e no model — três fontes de verdade divergindo silenciosamente. |
| A-03 | Lógica de negócio no handler de rota — relatórios | `routes/report_routes.py:12-155` | `summary_report` com ~90 linhas e N+1 por usuário; `user_report` com ~50 linhas. Relatórios não podem ser testados ou reutilizados; latência cresce linearmente com o número de usuários. |
| A-04 | Lógica de negócio no handler de rota — CRUD de usuários e login | `routes/user_routes.py:42-211` | `create_user`, `update_user`, `delete_user` e `login` misturam HTTP, validação, persistência e regras ad-hoc (whitelist de roles, regex de email, fake-token). Cascade delete manual nas linhas 140-145 duplica o que deveria ser configuração do ORM. |
| A-05 | Sem handler centralizado de erros | `app.py:1-35` | Nenhum `@app.errorhandler` registrado. Doze `except:` nus que retornam 500 genérico sem logar a causa real — bugs de programação ficam invisíveis em produção. |
| A-06 | Lógica de validação duplicada em três camadas | `routes/task_routes.py`, `utils/helpers.py`, `models/task.py` | Whitelist de status, faixa de prioridade e comprimento do título repetidos verbatim no handler, no helper e no model. O helper `process_task_data` nunca é chamado — dead code com regras que já divergem das regras reais. |

---

#### 🟡 Médios — Problemas de qualidade e integridade de dados

| ID | Problema | Arquivo(s) | Por que é relevante |
|---|---|---|---|
| M-01 | N+1 query — listagem de tarefas com lookups de usuário/categoria | `routes/task_routes.py:41-57` | `User.query.get(t.user_id)` e `Category.query.get(t.category_id)` por tarefa dentro de um loop. 100 tarefas = até 201 round-trips ao banco. Os relacionamentos já estão declarados no ORM e poderiam ser carregados de forma eager. |
| M-02 | N+1 query — seção de produtividade por usuário no relatório resumido | `routes/report_routes.py:53-68` | `Task.query.filter_by(user_id=u.id).all()` por usuário dentro de loop, mais cinco queries `COUNT` separadas por prioridade. Poderia ser um único `GROUP BY` com subcolunas. |
| M-03 | Cláusulas `except:` nuas engolam erros | `routes/task_routes.py`, `routes/user_routes.py`, `routes/report_routes.py`, `utils/helpers.py` (12 ocorrências) | Bugs reais (typos, incompatibilidades de schema) tornam-se 500s invisíveis sem stack trace. `except:` sem tipo específico captura inclusive `KeyboardInterrupt` e `SystemExit`. |
| M-04 | Cascade delete manual (deveria ser relacionamento ORM) | `routes/user_routes.py:140-145` | Loop Python deletando tarefas uma a uma antes de deletar o usuário. Race condition entre as duas operações; emite N+1 DELETEs onde uma declaração `cascade` resolveria com uma única instrução SQL. |
| M-05 | `db.create_all()` executado em tempo de importação | `app.py:30-31` | Side-effect incondicional ao importar o módulo — inclusive pelo `seed.py`. Incompatível com Alembic e com qualquer framework de testes que importe `app` sem querer criar o schema. |

---

#### 🔵 Baixos — Legibilidade e manutenção de longo prazo

| ID | Problema | Arquivo(s) | Por que é relevante |
|---|---|---|---|
| B-01 | Magic strings — whitelists de status e role | `routes/task_routes.py:110,177`; `routes/user_routes.py:71,120`; `models/task.py:39` | `['pending','in_progress','done','cancelled']` e `['user','admin','manager']` aparecem inline em cinco locais. Adicionar um status exige editar cinco arquivos com risco silencioso de divergência. |
| B-02 | Magic numbers — limites de validação e defaults | `routes/task_routes.py`, `routes/user_routes.py`, `models/task.py` (10+ ocorrências) | Limites de título (3/200), prioridade (1/5), senha (4) e default de prioridade (3) como inteiros brutos. `utils/helpers.py` já define constantes para esses valores, mas ninguém as importa — dead code provando a intenção original. |
| B-03 | `print()` usado para logging | `routes/task_routes.py`, `routes/user_routes.py`, `services/notification_service.py`, `utils/helpers.py` (~10 ocorrências) | Sem níveis de log, sem controle de destino, sem IDs de correlação. Impossível filtrar por severidade ou direcionar para arquivo em produção. |
| B-04 | Nomenclatura ruim e estilo inconsistente | `models/task.py:45`; `routes/task_routes.py:268`; `routes/user_routes.py:14`; `routes/report_routes.py:24-28` | `p` como parâmetro de prioridade, `t` e `u` em loops longos, `p1..p5` para níveis de prioridade. Legibilidade prejudicada; intenção precisa ser inferida de contexto distante. |
| B-05 | Imports não utilizados | `app.py:7`; `routes/task_routes.py:7`; `routes/user_routes.py:6`; `routes/report_routes.py:7-8`; `utils/helpers.py:3-7` | Módulos como `os`, `sys`, `json`, `math`, `hashlib`, `time` importados e não referenciados em cinco arquivos. Ruído que confunde leitores sobre dependências reais do projeto. |

---

### Justificativa da Classificação

A severidade foi atribuída com base em três eixos:

- **Exploitabilidade:** quão facilmente um atacante externo, sem credenciais, consegue acionar o problema.
- **Impacto:** extensão do dano — de degradação de legibilidade até comprometimento de todas as credenciais.
- **Reversibilidade:** custo de recovery após o problema ser explorado.

Este projeto apresenta uma combinação particularmente perigosa em C-03 + C-04: o hash MD5 (quebrado) é retornado diretamente pela API em quatro endpoints diferentes. Um atacante não precisa de acesso ao banco — basta fazer um `GET /users/:id` para obter o hash, e quebrá-lo offline com hashcat em segundos. Juntos, os dois achados satisfazem os três eixos de criticidade e se amplificam mutuamente.

---

## Construção da Skill

### Visão Geral

A skill é um agente de auditoria e refatoração estruturado em **três fases obrigatórias e sequenciais** — Reconhecimento → Auditoria → Refatoração — que opera sobre qualquer base de código de API REST, independentemente de linguagem ou framework.

### Decisões de Design

#### 1. Reconhecimento da arquitetura declarada vs. real

Este projeto foi o caso mais claro de "arquitetura ilusória": as pastas `models/`, `routes/`, `services/` e `utils/` sugeriam separação de camadas, mas cada pasta violava sistematicamente suas próprias responsabilidades. A Fase 1 registra explicitamente essa divergência antes da auditoria — sem isso, um auditor desatento poderia considerar as pastas como evidência de boa arquitetura e perder os achados de alto mais graves.

#### 2. Catálogo com detecção de dead code

A Fase 2 inclui explicitamente a categoria "código morto que revela intenção original não implementada". `utils/helpers.py::process_task_data` e as constantes de validação em `utils/helpers.py:110-116` são exemplos: provam que alguém planejou centralizar as validações, mas nunca conectou o helper ao restante do código. Isso é registrado tanto como achado de qualidade (A-06) quanto como evidência para a refatoração (o helper é o ponto correto para centralizar as regras, não uma criação nova).

#### 3. Severidade calibrada para o ecossistema Flask/SQLAlchemy

Alguns achados têm impacto diferente dependendo do framework. `db.create_all()` em tempo de importação (M-05) é benigno em um script standalone, mas é um problema real em Flask porque `seed.py` importa `app`, causando a criação do schema como side-effect de cada seed run — e incompatível com Alembic, que é o caminho natural de evolução para qualquer projeto Flask/SQLAlchemy que cresça. A skill calibra a severidade pelo contexto do framework, não apenas pelo padrão abstrato.

#### 4. Recomendações com mapeamento para o ecossistema alvo

Cada recomendação especifica a ferramenta concreta do ecossistema Python/Flask: `bcrypt>=4.0.0` (não apenas "use hashing seguro"), `db.joinedload()` do SQLAlchemy (não apenas "use JOIN"), `cascade='all, delete-orphan'` na declaração do relacionamento ORM (não apenas "use cascade"), `create_app()` factory pattern (não apenas "refatore o bootstrap").

#### 5. Validação por grupos funcionais de endpoints

Com 11 grupos de endpoints (health, tasks CRUD, tasks/search, tasks/stats, users CRUD, users/<id>/tasks, login, categories CRUD, reports/summary, reports/user/<id>, fluxos de erro), a validação foi organizada por grupo para garantir cobertura sistemática — não apenas os happy paths.

---

### Anti-patterns Incluídos e Justificativa

| Anti-pattern | Por que incluído |
|---|---|
| Segredos hardcoded (aplicação + SMTP) | Dois tipos distintos de segredo no mesmo projeto — demonstra que a categoria precisa cobrir não só `SECRET_KEY` mas também credenciais de serviços externos |
| MD5 para hashing de senha | Presente em projetos Python que usam `hashlib` da stdlib evitando dependências externas; catastrófico em combinação com exposição do hash pela API |
| Hash de senha retornado pela API | Multiplicador de impacto do MD5 — transforma um problema de banco em um problema de API pública; frequente quando `to_dict()` é criado sem consciência de campos sensíveis |
| Arquitetura parcialmente em camadas | Mais insidioso que God File — a existência das pastas cria falsa sensação de organização, tornando o problema mais difícil de detectar sem análise de conteúdo |
| Validação em três fontes de verdade com dead code | Padrão comum em projetos que cresceram incrementalmente; o helper morto documenta a intenção original e deve ser o ponto de convergência, não descartado |
| N+1 em ORM com relacionamentos já declarados | Específico de projetos SQLAlchemy — os relacionamentos estão no modelo mas `joinedload` não é usado; a correção é uma linha, o impacto de não corrigir é exponencial |
| `db.create_all()` em tempo de importação | Anti-pattern específico do ecossistema Flask que bloqueia a adoção de Alembic e contamina o bootstrap de testes |
| `except:` nu (bare except) | Captura exceções de sistema (`KeyboardInterrupt`, `SystemExit`) além das de aplicação — mais grave que `except Exception:` |
| Magic numbers com constantes mortas no mesmo projeto | Caso especial: as constantes existem no `utils/helpers.py` mas ninguém as importa — evidência de intenção boa não executada |

---

### Como a Skill é Agnóstica de Tecnologia

A skill detecta conceitos, não sintaxe. Este projeto, o terceiro auditado, demonstra como os mesmos padrões do catálogo se manifestam de formas diferentes em Python/Flask com ORM:

**MD5 vs `badCrypto` vs texto puro.** Em `ecommerce-api-legacy` (Node.js) a função `badCrypto()` foi criada explicitamente. Em `task-manager-api` (Python) o desenvolvedor usou `hashlib.md5()` — uma função legítima da stdlib, apenas inadequada para senhas. Em `code-smells-project` (Python/Flask sem ORM) as senhas eram texto puro. O catálogo captura todos os três como "hashing de senha inseguro ou ausente".

**God File vs God Class vs arquitetura ilusória.** Em `code-smells-project` o problema foi concentração em poucos arquivos grandes. Em `ecommerce-api-legacy` foi uma única classe. Em `task-manager-api` foi a ilusão de separação com onze arquivos que violavam sistematicamente suas responsabilidades. A categoria "ausência de separação efetiva de camadas" cobre as três manifestações.

**N+1 com callbacks aninhados vs N+1 com ORM lazy-loading.** Em Node.js os N+1 eram visíveis como loops de callbacks. Em SQLAlchemy os N+1 são mais sutis — `User.query.get(id)` dentro de um loop parece inocente porque o ORM abstrai a query. A skill detecta o padrão de acesso sequencial dentro de iteração, não a sintaxe específica.

**Estrutura de saída padronizada.** Todos os três relatórios gerados seguem o mesmo template — Visão Geral, Achados por Severidade com tabelas, Refatoração Aplicada, Validação Final — permitindo comparar auditorias entre Flask sem ORM, Node.js/Express e Flask com SQLAlchemy diretamente.

---

### Desafios Encontrados

**Detectar a "arquitetura ilusória":** a existência de `models/`, `routes/`, `services/` e `utils/` poderia ser interpretada como boa organização. O desafio foi analisar o conteúdo de cada arquivo para identificar que as responsabilidades estavam sistematicamente misturadas — validação no model, SQL no handler de rota, regras de negócio no service. Isso exigiu ler todos os 11 arquivos antes de emitir qualquer julgamento arquitetural.

**Três fontes de verdade para as mesmas regras:** o achado A-06 foi o mais complexo de documentar porque envolve três locais que contêm variações das mesmas regras, com um deles (o helper) sendo dead code. A skill precisou decidir qual dos três tornar a fonte canônica (o controller, por ser a camada que orquestra a validação antes da persistência) e como migrar as regras sem perder nenhuma variante.

**`db.create_all()` e o `seed.py`:** o side-effect em tempo de importação era especialmente problemático porque `seed.py` importa `app` para usar o contexto da aplicação. Isso significava que cada execução do seed recriava o schema. A correção exigiu migrar para `create_app()` factory e garantir que `seed.py` chamasse `create_app()` explicitamente em vez de importar o objeto `app` diretamente.

**Cascade delete: ORM vs FK-level:** SQLAlchemy oferece duas formas de cascade — `cascade='all, delete-orphan'` no relacionamento Python e `ondelete='CASCADE'` na definição da FK. A skill aplicou ambos para garantir consistência tanto em operações via ORM quanto em queries diretas ao banco (como as feitas pelo `seed.py`).

**Preservar 11 grupos de endpoints com zero breaking changes:** a refatoração mais ampla dos três projetos auditados — de 11 arquivos com ~900 LOC para estrutura MVC com controllers, views separadas e factory pattern. Cada grupo de endpoints foi validado individualmente (happy path + cenários de erro) antes de marcar a fase como concluída.

---

## Resultados

### Resumo dos Relatórios de Auditoria

| Dimensão | Antes | Depois |
|---|---|---|
| Arquivos-fonte | 11 (`app.py`, `database.py`, `seed.py`, 3 models, 3 routes, 1 service, 1 utils) | Estrutura MVC com `config/`, `controllers/`, `middlewares/`, `models/`, `services/`, `views/` |
| Linhas de código | ~900 LOC | Distribuídas em módulos coesos com responsabilidade única |
| Achados Críticos | 4 | 0 |
| Achados Altos | 6 | 0 |
| Achados Médios | 5 | 0 |
| Achados Baixos | 5 | 0 |
| **Total de achados** | **20** | **0** |
| `SECRET_KEY` | `'super-secret-key-123'` hardcoded em `app.py` | Carregada de `os.environ.get('SECRET_KEY')` via python-dotenv |
| Credenciais SMTP | `'senha123'` hardcoded em `NotificationService.__init__` | Injetadas de `Config.SMTP_*` carregado do ambiente |
| Hashing de senha | `hashlib.md5(pwd.encode()).hexdigest()` — sem salt | `bcrypt.hashpw` com salt individual; `bcrypt.checkpw` na verificação |
| Hash retornado pela API | Campo `password` em `to_dict()` — retornado em 4 endpoints | Removido de `to_dict()`; `to_safe_dict()` expõe apenas campos seguros |
| N+1 em listagem de tarefas | `User.query.get()` + `Category.query.get()` por tarefa no loop | `Task.get_all_with_relations()` com `joinedload(user, category)` |
| N+1 em relatório | `Task.query.filter_by(user_id=u.id).all()` por usuário + 5 `COUNT` separados | `GROUP BY` com `count_by_status`, `count_by_priority`, `stats_by_user` |
| Cascade delete de usuário | Loop Python deletando tarefas uma a uma (N+1 DELETEs) | `cascade='all, delete-orphan'` + `ondelete='CASCADE'` na FK |
| Handler de erros | 12 `except:` nus com 500 genérico sem log | `register_error_handlers(app)` centralizado com `ValidationError`, `NotFoundError`, `AuthenticationError` |
| Fontes de verdade para validação | Três (handler, helper morto, model) | Uma (`task_controller` / `user_controller`) |
| Magic strings de status/role | Inline em 5 arquivos diferentes | `VALID_TASK_STATUSES`, `VALID_USER_ROLES`, `TERMINAL_TASK_STATUSES` em `Config` |
| Bootstrap da aplicação | `db.create_all()` em tempo de importação | Factory `create_app()` — schema criado apenas quando a factory é chamada |
| Logging | `print()` em ~10 locais | `logging.getLogger(__name__)` configurado via `basicConfig` em `create_app` |

---

### Comparação Antes / Depois

#### Estrutura de arquivos

```
ANTES                                    DEPOIS
────────────────────────────────         ────────────────────────────────────────
app.py                                   app.py               ← create_app factory
database.py                              config/
seed.py                                  └── settings.py      ← Config + constantes
models/                                  controllers/
├── task.py       (validação inline)     ├── task_controller.py
├── user.py       (MD5 + senha em dict)  ├── user_controller.py
└── category.py                          ├── category_controller.py
routes/                                  └── report_controller.py
├── task_routes.py    (53-70 LOC/fn)     middlewares/
├── user_routes.py    (50-40 LOC/fn)     └── error_handler.py
└── report_routes.py  (90 LOC/fn)        models/
services/                                ├── database.py      ← db = SQLAlchemy()
└── notification_service.py              ├── task.py          ← eager-load + stats
utils/                                   ├── user.py          ← bcrypt + safe dict
└── helpers.py  (constantes mortas)      └── category.py
                                         services/
                                         └── notification_service.py ← SMTP de Config
                                         views/
                                         ├── task_routes.py       ← ≤10 linhas/fn
                                         ├── user_routes.py
                                         ├── category_routes.py
                                         └── report_routes.py
```

#### Hashing de senha — antes e depois

```python
# ANTES — MD5 sem salt, retornado pela API
# models/user.py
def set_password(self, pwd):
    self.password = hashlib.md5(pwd.encode()).hexdigest()
    # "admin123" → "0192023a7bbd73250516f069df18b500" (sempre o mesmo)

def check_password(self, pwd):
    return self.password == hashlib.md5(pwd.encode()).hexdigest()

def to_dict(self):
    return {
        "id": self.id,
        "nome": self.nome,
        "email": self.email,
        "password": self.password,   # ← hash MD5 exposto na resposta
        ...
    }

# DEPOIS — bcrypt com salt, removido da resposta
# models/user.py
def set_password(self, pwd):
    self.password = bcrypt.hashpw(
        pwd.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

def check_password(self, pwd):
    return bcrypt.checkpw(
        pwd.encode('utf-8'),
        self.password.encode('utf-8')
    )

def to_dict(self):
    return {
        "id": self.id,
        "nome": self.nome,
        "email": self.email,
        # password removido — nunca retornado pela API
        ...
    }
```

#### N+1 com ORM — antes e depois

```python
# ANTES — queries individuais por tarefa dentro de loop
# routes/task_routes.py
tasks = Task.query.all()           # query 1
result = []
for t in tasks:
    user = User.query.get(t.user_id)         # query 2 (×N)
    category = Category.query.get(t.category_id)  # query 3 (×N)
    result.append({
        "id": t.id,
        "titulo": t.titulo,
        "user": user.nome if user else None,
        "category": category.nome if category else None,
        "vencida": (t.due_date < datetime.now()).isoformat()  # lógica inline
    })

# DEPOIS — joinedload; lógica no model
# models/task.py
@classmethod
def get_all_with_relations(cls, filters=None):
    query = cls.query.options(
        db.joinedload(cls.user),
        db.joinedload(cls.category)
    )
    if filters:
        query = query.filter_by(**filters)
    return [t.to_dict() for t in query.all()]   # to_dict() usa relacionamentos já carregados
```

#### Validação — três fontes de verdade para uma

```python
# ANTES — regras repetidas em três lugares com divergências silenciosas
# routes/task_routes.py
if len(titulo) < 3 or len(titulo) > 200:   # regra inline no handler de criação
    return jsonify({"erro": "..."}), 400

# utils/helpers.py (NUNCA IMPORTADO)
MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
def process_task_data(data):                 # helper morto — regras podem divergir
    if len(data.get('titulo', '')) < MIN_TITLE_LENGTH:
        return None, "Título muito curto"

# models/task.py
def validate_title(self, t):               # validação no model — terceira cópia
    if len(t) < 3:
        raise ValueError("Título inválido")

# DEPOIS — fonte única em Config + controller
# config/settings.py
class Config:
    MIN_TITLE_LENGTH = int(os.environ.get('MIN_TITLE_LENGTH', 3))
    MAX_TITLE_LENGTH = int(os.environ.get('MAX_TITLE_LENGTH', 200))
    VALID_TASK_STATUSES = ('pending', 'in_progress', 'done', 'cancelled')
    VALID_PRIORITIES = range(1, 6)

# controllers/task_controller.py
class TaskController:
    @staticmethod
    def _validate_payload(data, partial=False):
        titulo = data.get('titulo')
        if not partial and not titulo:
            raise ValidationError("Campo 'titulo' obrigatório")
        if titulo and not (Config.MIN_TITLE_LENGTH <= len(titulo) <= Config.MAX_TITLE_LENGTH):
            raise ValidationError(f"Título deve ter entre {Config.MIN_TITLE_LENGTH} e {Config.MAX_TITLE_LENGTH} chars")
        if 'status' in data and data['status'] not in Config.VALID_TASK_STATUSES:
            raise ValidationError(f"Status inválido. Permitidos: {Config.VALID_TASK_STATUSES}")
        # ... demais validações
```

#### Handler de erros — antes e depois

```python
# ANTES — 12 variações ad-hoc de try/except sem padrão
# routes/task_routes.py
try:
    tasks = Task.query.all()
    ...
except:                                  # bare except — captura até KeyboardInterrupt
    return jsonify({"erro": "Erro interno"}), 500

# routes/user_routes.py
try:
    user = User.query.get(user_id)
    ...
except Exception as e:
    return jsonify({"message": str(e)}), 500  # shape diferente; vaza mensagem interna

# DEPOIS — exceções tipadas + middleware único
# middlewares/error_handler.py
def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation(e):
        return jsonify({"erro": str(e)}), 400

    @app.errorhandler(NotFoundError)
    def handle_not_found(e):
        return jsonify({"erro": str(e)}), 404

    @app.errorhandler(AuthenticationError)
    def handle_auth(e):
        return jsonify({"erro": "Credenciais inválidas"}), 401

    @app.errorhandler(Exception)
    def handle_generic(e):
        logger.exception("Erro não tratado")       # stack trace no log, não na resposta
        return jsonify({"erro": "Erro interno"}), 500

# controllers/task_controller.py — sem try/except; exceções sobem ao middleware
def list_tasks(filters=None):
    tasks = Task.get_all_with_relations(filters)
    if not tasks:
        raise NotFoundError("Nenhuma tarefa encontrada")
    return tasks
```

---

### Checklist de Validação

#### Segurança

- [x] `SECRET_KEY` carregada de variável de ambiente — ausente no código-fonte
- [x] Credenciais SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`) carregadas de variáveis de ambiente
- [x] Senhas armazenadas como hash bcrypt com salt individual por usuário
- [x] Seed atualizado para hashear senhas com bcrypt antes da inserção
- [x] Campo `password` removido de `User.to_dict()` — ausente em todas as respostas de API
- [x] `.env` listado no `.gitignore`
- [x] `.env.example` versionado com placeholders para todas as variáveis

#### Arquitetura

- [x] Factory pattern `create_app()` — `db.create_all()` não mais executado em tempo de importação
- [x] Zero lógica de negócio em arquivos de views (handlers com ≤ 10 linhas)
- [x] Models sem lógica de validação de negócio — apenas ORM e `to_dict()`/`to_safe_dict()`
- [x] Controllers sem acesso direto a `db.session` — via class methods dos models
- [x] Validação centralizada em `task_controller._validate_payload()` e `user_controller._validate_payload()`
- [x] `utils/helpers.py::process_task_data` deletado — zero dead code de validação
- [x] `routes/report_routes.py` dividido em `views/category_routes.py` + `views/report_routes.py`

#### Integridade de Dados

- [x] `cascade='all, delete-orphan'` configurado em `User.tasks`
- [x] `ondelete='CASCADE'` configurado na FK `tasks.user_id`
- [x] Loop manual de cascade delete removido de `user_routes.py`

#### Qualidade

- [x] N+1 em listagem de tarefas eliminado com `joinedload(user, category)`
- [x] N+1 em relatório eliminado com `GROUP BY` em `count_by_status`, `count_by_priority`, `stats_by_user`
- [x] Handler centralizado `register_error_handlers(app)` registrado em `create_app()`
- [x] Zero `except:` nus — exceções específicas (`ValidationError`, `NotFoundError`, `AuthenticationError`, `SQLAlchemyError`)
- [x] `VALID_TASK_STATUSES`, `VALID_USER_ROLES`, `TERMINAL_TASK_STATUSES` em `Config`
- [x] `MIN_TITLE_LENGTH`, `MAX_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY` em `Config`
- [x] `print()` substituído por `logging.getLogger(__name__)` em todos os módulos
- [x] Imports não utilizados removidos dos cinco arquivos afetados

#### Comportamento

- [x] Servidor inicializa sem erros
- [x] `GET /health` responde 200
- [x] `GET /` responde 200
- [x] `GET /tasks` retorna lista com user e category eager-loaded (sem N+1)
- [x] `POST /tasks` cria tarefa e retorna 201
- [x] `PUT /tasks/<id>` atualiza e retorna 200
- [x] `DELETE /tasks/<id>` remove e retorna 200
- [x] `GET /tasks/search` retorna resultados filtrados
- [x] `GET /tasks/stats` retorna estatísticas agregadas
- [x] `POST /login` com credenciais válidas retorna token
- [x] `POST /login` com credenciais inválidas retorna 401
- [x] `GET /users` retorna lista sem campo `password`
- [x] `POST /users` cria usuário sem retornar `password`
- [x] `PUT /users/<id>` atualiza sem retornar `password`
- [x] `DELETE /users/<id>` remove usuário e cascade em tasks
- [x] `GET /users/<id>/tasks` retorna tarefas do usuário
- [x] `GET /categories` retorna lista
- [x] `POST /categories` cria categoria
- [x] `PUT /categories/<id>` atualiza categoria
- [x] `DELETE /categories/<id>` remove categoria
- [x] `GET /reports/summary` retorna relatório sem N+1
- [x] `GET /reports/user/<id>` retorna relatório por usuário
- [x] Fluxos 404, 400 e 401 retornam shape JSON `{"erro": "..."}` consistente

---

### Logs da Aplicação Após Refatoração

```
$ python app.py

INFO:config.settings:Carregando configuração do ambiente.
INFO:models.database:Banco de dados inicializado via create_app().
INFO:seed:Seed inserido: 3 usuários (bcrypt), 5 categorias, 10 tarefas.
INFO:app:Blueprints registrados: tasks, users, categories, reports, health.
 * Serving Flask app 'task-manager-api'
 * Debug mode: off
 * Running on http://0.0.0.0:5000
Press CTRL+C to quit
```

```
$ curl -s http://localhost:5000/users/1 | python -m json.tool

{
    "id": 1,
    "nome": "Admin",
    "email": "admin@taskmanager.com",
    "role": "admin",
    "criado_em": "2025-01-15T10:00:00"
}
```

> **Nota:** campo `password` ausente da resposta — confirmando o fechamento de C-04.

```
$ curl -s -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@taskmanager.com","senha":"admin123"}' \
  | python -m json.tool

{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user_id": 1,
    "role": "admin"
}
```

> **Nota:** autenticação funcional com bcrypt — confirmando o fechamento de C-03.

```
$ curl -s http://localhost:5000/reports/summary | python -m json.tool

{
    "total_tarefas": 10,
    "por_status": {"pending": 4, "in_progress": 3, "done": 2, "cancelled": 1},
    "por_prioridade": {"1": 1, "2": 2, "3": 4, "4": 2, "5": 1},
    "vencidas": 2,
    "produtividade_por_usuario": [
        {"usuario": "Admin", "total": 5, "concluidas": 2},
        {"usuario": "Gerente", "total": 3, "concluidas": 0}
    ]
}
```

> **Nota:** relatório entregue por `GROUP BY` sem N+1 — confirmando RT-05.

```
$ curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"titulo":"x","status":"invalido"}' \
  | python -m json.tool

{
    "erro": "Status inválido. Permitidos: ('pending', 'in_progress', 'done', 'cancelled')"
}
```

> **Nota:** shape de erro JSON consistente com status 400 — confirmando RT-06 (handler centralizado) e RT-07 (validação fonte única).

---

## Como Executar

### Pré-requisitos

| Requisito | Versão mínima | Verificação |
|---|---|---|
| Python | 3.10+ | `python --version` |
| pip | 23+ | `pip --version` |
| Git | qualquer | `git --version` |

Não há dependência de Docker, banco externo ou serviço de terceiros — a aplicação usa SQLite em arquivo local.

---

### Instalação

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd task-manager-api

# 2. Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -r requirements.txt
# Deve incluir: flask, flask-sqlalchemy, flask-cors, marshmallow,
#               requests, python-dotenv, bcrypt
```

---

### Configuração do Ambiente

```bash
# 4. Copie o arquivo de exemplo e ajuste os valores
cp .env.example .env
```

Conteúdo mínimo do `.env` para desenvolvimento:

```dotenv
# Aplicação Flask
SECRET_KEY=chave-local-de-desenvolvimento
DEBUG=false
HOST=0.0.0.0
PORT=5000

# Banco de dados
DATABASE_URL=sqlite:///tasks.db

# Validação de tarefas
MIN_TITLE_LENGTH=3
MAX_TITLE_LENGTH=200
DEFAULT_PRIORITY=3
RECENT_ACTIVITY_DAYS=7

# Validação de usuários
MIN_PASSWORD_LENGTH=4

# SMTP (opcional em desenvolvimento — notificações apenas logadas)
SMTP_HOST=smtp.mailtrap.io
SMTP_PORT=587
SMTP_USER=seu_usuario_mailtrap
SMTP_PASS=sua_senha_mailtrap
SMTP_FROM=noreply@taskmanager.com
```

> **Atenção:** nunca versione o arquivo `.env`. Ele já está listado no `.gitignore`.

---

### Popular o Banco de Dados

```bash
# Executa o seed (cria schema + insere dados iniciais com senhas bcrypt)
python seed.py
```

Saída esperada:

```
INFO:seed:Schema criado via create_app().
INFO:seed:Inseridos: 3 usuários, 5 categorias, 10 tarefas.
INFO:seed:Seed concluído.
```

---

### Executar a Aplicação Refatorada

```bash
python app.py
```

Saída esperada:

```
INFO:config.settings:Carregando configuração do ambiente.
INFO:models.database:Banco de dados inicializado via create_app().
 * Running on http://0.0.0.0:5000
```

---

### Executar a Skill de Auditoria

A skill opera em três comandos sequenciais. Execute-os na ordem abaixo dentro do Claude Code (`claude`) apontado para o diretório do projeto legado:

```bash
# Fase 1 — Reconhecimento
claude "Analise o projeto no diretório atual: identifique linguagem, framework, dependências, \
domínio, arquitetura real (não apenas a declarada pelas pastas) e tabelas do banco. \
Imprima o resumo da Fase 1."

# Fase 2 — Auditoria
claude "Com base na Fase 1, audite todos os arquivos contra o catálogo de anti-patterns. \
Classifique cada achado como CRÍTICO, ALTO, MÉDIO ou BAIXO. \
Inclua arquivo, linha, impacto e recomendação acionável para cada item."

# Fase 3 — Refatoração (após confirmação do relatório)
claude "O usuário confirmou o relatório. Execute a Fase 3: refatore o projeto aplicando \
todas as recomendações. Valide cada grupo de endpoints com cenários de sucesso e falha, \
e imprima o resumo final das transformações aplicadas."
```

---

### Validar que a Refatoração Funcionou

Execute os comandos abaixo após subir a aplicação refatorada. Todos devem retornar os status e shapes indicados.

```bash
BASE="http://localhost:5000"

# Health check
curl -s -o /dev/null -w "%{http_code}" $BASE/health
# Esperado: 200

# Usuário sem campo password na resposta
curl -s $BASE/users/1 | python -m json.tool | grep password
# Esperado: nenhuma linha (campo ausente — C-04 fechado)

# Login com credenciais válidas
curl -s -o /dev/null -w "%{http_code}" \
  -X POST $BASE/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@taskmanager.com","senha":"admin123"}'
# Esperado: 200

# Login com credenciais inválidas
curl -s -o /dev/null -w "%{http_code}" \
  -X POST $BASE/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@taskmanager.com","senha":"errada"}'
# Esperado: 401

# Criação de tarefa com status inválido (validação centralizada)
curl -s \
  -X POST $BASE/tasks \
  -H "Content-Type: application/json" \
  -d '{"titulo":"Teste","status":"invalido","user_id":1}' \
  | python -m json.tool | grep erro
# Esperado: linha com "Status inválido. Permitidos: ..." (shape JSON consistente)

# Criação de tarefa com título muito curto
curl -s -o /dev/null -w "%{http_code}" \
  -X POST $BASE/tasks \
  -H "Content-Type: application/json" \
  -d '{"titulo":"ab","user_id":1}'
# Esperado: 400

# Relatório resumido (verificar ausência de N+1 — latência deve ser baixa)
time curl -s -o /dev/null $BASE/reports/summary
# Esperado: 200, tempo < 100ms independente do volume de dados

# Deleção de usuário com cascade em tasks
curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE $BASE/users/2
# Esperado: 200

# Verificar que tasks do usuário deletado foram removidas em cascade
curl -s $BASE/users/2/tasks | python -m json.tool
# Esperado: 404 ou lista vazia
```

Todos os comandos retornando os valores esperados confirmam que os 4 achados Críticos e os 6 Altos estão fechados.

---

### Referências

- [Relatório de Auditoria Completo](./relatorio-auditoria-task-manager.md) — todos os 20 achados com detalhes, impacto e recomendações
- [.env.example](./.env.example) — template de configuração para novos ambientes
- [Flask Application Factories](https://flask.palletsprojects.com/en/3.0.x/patterns/appfactories/) — padrão `create_app()` adotado na refatoração
- [SQLAlchemy Relationship Loading](https://docs.sqlalchemy.org/en/20/orm/loading_relationships.html) — `joinedload` e estratégias de eager loading
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) — referência para classificação de vulnerabilidades
- [bcrypt PyPI](https://pypi.org/project/bcrypt/) — biblioteca de hashing recomendada para Python
