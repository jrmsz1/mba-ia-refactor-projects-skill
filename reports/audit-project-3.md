# Relatório de Auditoria de Código
**Projeto:** task-manager-api  
**Stack:** Python 3.x + Flask 3.0.0 + Flask-SQLAlchemy 3.1.1  
**Data:** 2025  
**Arquivos analisados:** 11 (`app.py`, `database.py`, `seed.py`, 3 models, 3 routes, 1 service, 1 utils) — ~900 LOC

---

## 1. Visão Geral do Projeto

| Atributo | Detalhe |
|---|---|
| Linguagem | Python 3.x |
| Framework | Flask 3.0.0 + Flask-SQLAlchemy 3.1.1 |
| Dependências | flask, flask-sqlalchemy, flask-cors, marshmallow, requests, python-dotenv |
| Domínio | API de gerenciamento de tarefas (tasks, users, categories, reports, login) |
| Tabelas do banco | `tasks`, `users`, `categories` |

### Arquitetura atual

O projeto adota uma arquitetura **parcialmente em camadas**: existem as pastas `models/`, `routes/`, `services/` e `utils/`, mas a separação é sistematicamente violada. Rotas contêm lógica de negócio, validação e padrões N+1; models contêm métodos de validação; segredos estão hardcoded em `app.py` e nos services. A pasta `utils/` define constantes e helpers que nunca são importados pelo restante do código.

---

## 2. Resumo dos Achados

| Severidade | Quantidade |
|---|---|
| 🔴 CRÍTICO | 4 |
| 🟠 ALTO | 6 |
| 🟡 MÉDIO | 5 |
| 🔵 BAIXO | 5 |
| **Total** | **20** |

---

## 3. Achados Detalhados

### 🔴 Críticos

---

#### C-01 — Credenciais e Segredos Hardcoded no Código-Fonte
**Arquivo:** `app.py:11-13`

A URI do banco de dados e a chave secreta do Flask estão escritas diretamente no código-fonte: `app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'` e `app.config['SECRET_KEY'] = 'super-secret-key-123'`.

**Impacto:** Qualquer desenvolvedor com acesso ao repositório pode forjar tokens de sessão; os segredos são versionados no VCS e não podem ser rotacionados por ambiente sem alterar o código.

**Recomendação:** Extrair para `src/config/settings.py` e carregar via `os.environ.get(...)` com `python-dotenv` (já presente no `requirements.txt`). Criar `.env` (gitignored) e `.env.example` com placeholders.

---

#### C-02 — Credenciais SMTP Hardcoded no Service
**Arquivo:** `services/notification_service.py:7-10`

Host de email, porta, endereço de remetente e senha em texto puro (`self.email_password = 'senha123'`) estão hardcoded dentro do método `NotificationService.__init__`.

**Impacto:** Credenciais SMTP versionadas no repositório — qualquer leitor pode enviar emails como a identidade da aplicação; rotacionar a senha exige alteração de código.

**Recomendação:** Mover as configurações SMTP para `src/config/settings.py` e lê-las de variáveis de ambiente; injetá-las no service.

---

#### C-03 — Hashing de Senha Inseguro (MD5)
**Arquivo:** `models/user.py:27-32`

`set_password` e `check_password` utilizam `hashlib.md5(pwd.encode()).hexdigest()` — MD5 é criptograficamente quebrado e inadequado para armazenamento de senhas (rápido, sem salt, suscetível a rainbow tables e ataques de colisão).

**Impacto:** Senhas de usuários são efetivamente recuperáveis a partir do banco de dados; uma violação de dados expõe todas as credenciais.

**Recomendação:** Substituir por `bcrypt` ou `argon2-cffi`; armazenar o hash resultante (com salt) na coluna `password`. Atualizar `seed.py` e adicionar `bcrypt>=4.0.0` ao `requirements.txt`.

---

#### C-04 — Senha Retornada nas Respostas da API
**Arquivo:** `models/user.py:16-25`

`User.to_dict()` retorna o campo `password` (hash). Esse dicionário é então retornado ao cliente em `GET /users/:id`, `POST /users`, `PUT /users/:id` e `POST /login` (`user_routes.py:33`, `86`, `129`, `209`).

**Impacto:** O hash da senha é vazado pela API, acelerando ataques de cracking offline — efeito particularmente devastador combinado com o hashing MD5.

**Recomendação:** Remover `password` de `to_dict()`; expor apenas campos seguros. Endpoints de autenticação nunca devem ecoar o hash.

---

### 🟠 Altos

---

#### A-01 — Lógica de Negócio e Queries SQL no Handler de Rota — Listagem de Tarefas
**Arquivo:** `routes/task_routes.py:11-63` (`get_tasks`)

Handler de 53 linhas que lê todas as tarefas, executa `User.query.get(t.user_id)` e `Category.query.get(t.category_id)` dentro de um loop por tarefa, recalcula o flag de vencimento inline e monta dicts de resposta manualmente — misturando acesso a dados, regras de negócio e apresentação.

**Impacto:** Não pode ser testado sem inicializar Flask + SQLAlchemy; duplica lógica que já existe em `Task.is_overdue()` e `Task.to_dict()`.

**Recomendação:** Mover a orquestração para `controllers/task_controller.py::list_tasks()`; a rota passa a ser uma chamada fina ao controller.

---

#### A-02 — Lógica de Negócio no Handler de Rota — Criação e Atualização de Tarefas
**Arquivo:** `routes/task_routes.py:85-223` (`create_task`, `update_task`)

Cada handler tem ~70 linhas combinando parsing de JSON, validação campo a campo (comprimento do título, enum de status, faixa de prioridade, verificações de existência de usuário/categoria), parsing de datas, persistência e logging via `print()`.

**Impacto:** Impossível testar as regras de validação de forma isolada; as mesmas regras já existem parcialmente em `utils/helpers.py::process_task_data` e no model — três fontes de verdade.

**Recomendação:** Extrair `TaskController.create_task(payload)` / `update_task(task_id, payload)` que delegam para o `TaskModel`; consolidar as regras de validação em um único lugar (controller ou schema).

---

#### A-03 — Lógica de Negócio no Handler de Rota — Relatórios
**Arquivo:** `routes/report_routes.py:12-155` (`summary_report`, `user_report`)

`summary_report` tem ~90 linhas calculando contagens por status, por prioridade, atividade recente, lista de vencidos e produtividade por usuário com queries N+1 (linha 56: `Task.query.filter_by(user_id=u.id).all()` dentro de um loop sobre todos os usuários). `user_report` calcula estatísticas inline de forma similar (~50 linhas).

**Impacto:** Relatórios não podem ser testados ou reutilizados; o plano de query cresce linearmente com o número de usuários.

**Recomendação:** Mover a lógica de agregação para `controllers/report_controller.py`; expor métodos de model como `TaskModel.count_by_status()`, `TaskModel.list_overdue()`, etc.

---

#### A-04 — Lógica de Negócio no Handler de Rota — CRUD de Usuários e Login
**Arquivo:** `routes/user_routes.py:42-211`

`create_user` (~50 linhas), `update_user` (~40 linhas), `delete_user` (cascade delete manual de tarefas relacionadas nas linhas 140-145) e `login` (~30 linhas) misturam HTTP, validação, persistência e regras de negócio ad-hoc (ex.: whitelist de roles, regex de email, construção de fake-token).

**Impacto:** A lógica de autenticação não está isolada da camada HTTP, tornando testes e endurecimento futuro (rate limiting, JWT real) trabalhosos. O cascade delete manual duplica o que deveria ser uma configuração de relacionamento ORM.

**Recomendação:** Extrair `UserController` cobrindo `create_user`, `update_user`, `delete_user`, `authenticate`; mover regex de email e regras de senha para controller/config; configurar `cascade='all, delete-orphan'` no relacionamento `User.tasks`.

---

#### A-05 — Sem Handler Centralizado de Erros
**Arquivo:** `app.py:1-35`

Nenhum `@app.errorhandler` é registrado em nenhum lugar. Cada rota trata erros localmente com blocos `except:` / `except Exception as e:` nus que engolam a exceção subjacente e retornam 500s genéricos (ex.: `routes/task_routes.py:62-63`, `152-154`, `221-223`, `235-238`).

**Impacto:** Respostas de erro inconsistentes; causas reais ocultas da observabilidade; `except:` nu mascara bugs de programação.

**Recomendação:** Adicionar `src/middlewares/error_handler.py::register_error_handlers(app)` cobrindo 400/404/422/500/Exception com JSON estruturado; remover os wrappers `try/except` ad-hoc que apenas reemitem uma mensagem genérica.

---

#### A-06 — Lógica de Validação Duplicada em Três Camadas
**Arquivo:** `routes/task_routes.py:110-114`, `167-184`; `utils/helpers.py:57-108`; `models/task.py:38-48`

A whitelist de status `['pending','in_progress','done','cancelled']`, a faixa de prioridade 1-5 e as regras de comprimento do título são repetidas verbatim nos handlers de rota, em `utils/helpers.py::process_task_data` e no próprio model `Task` — mas `process_task_data` nunca é chamada.

**Impacto:** Qualquer mudança de regra exige editar três locais; o helper não utilizado se deteriora silenciosamente e pode divergir das regras reais.

**Recomendação:** Definir as regras uma única vez (constantes em `config/settings.py` ou no controller); deletar a função morta `process_task_data` ou utilizá-la como fonte única de verdade.

---

### 🟡 Médios

---

#### M-01 — N+1 Query — Listagem de Tarefas com Lookups de Usuário/Categoria
**Arquivo:** `routes/task_routes.py:41-57`

Para cada tarefa no resultado, `get_tasks` executa um `User.query.get(t.user_id)` e um `Category.query.get(t.category_id)` separados (linhas 42 e 51). 100 tarefas resultam em até 201 round-trips ao banco.

**Impacto:** Latência de listagem cresce linearmente com o número de tarefas; os relacionamentos (`User`/`Category`) já estão declarados no model e poderiam ser carregados de forma eager.

**Recomendação:** Usar `Task.query.options(db.joinedload(Task.user), db.joinedload(Task.category)).all()` na camada de model, ou incluir `user_name`/`category_name` em `Task.to_dict()` via o relacionamento existente.

---

#### M-02 — N+1 Query — Seção de Produtividade por Usuário no Relatório Resumido
**Arquivo:** `routes/report_routes.py:53-68`

`for u in users:` executa `Task.query.filter_by(user_id=u.id).all()` por usuário (linha 56), depois itera novamente para contar tarefas concluídas. O mesmo ocorre com as contagens por prioridade, usando cinco queries `COUNT` separadas (linhas 24-28).

**Impacto:** Latência do relatório cresce linearmente com o número de usuários; poderia ser resolvido com uma única query `GROUP BY`.

**Recomendação:** Substituir por uma query agregada: `db.session.query(Task.user_id, Task.status, func.count()).group_by(Task.user_id, Task.status).all()` e pivotar em Python; agregar contagens de prioridade da mesma forma.

---

#### M-03 — Cláusulas `except:` Nuas Engolam Erros
**Arquivo:** `routes/task_routes.py:62`, `137`, `204`, `236`; `routes/user_routes.py:130`, `149`; `routes/report_routes.py:187`, `207`, `222`; `utils/helpers.py:46`, `49`, `88`

Aproximadamente 12 blocos `except:` ou `except Exception:` nus que ou retornam um 500 genérico ou silenciosamente definem um valor como `None`, sem logar a exceção real.

**Impacto:** Bugs reais (typos, incompatibilidades de schema, problemas de encoding) tornam-se 500s invisíveis sem stack trace; depuração requer reprodução local.

**Recomendação:** Substituir por tipos de exceção específicos (`ValueError`, `SQLAlchemyError`) e centralizar no handler de erros; logar exceções via `logger.exception()`.

---

#### M-04 — Cascade Delete Manual (Deveria Ser Relacionamento ORM)
**Arquivo:** `routes/user_routes.py:140-145`

Antes de deletar um usuário, a rota busca manualmente todas as suas tarefas e as deleta uma a uma em Python.

**Impacto:** Race condition entre as duas transações; o loop emite N+1 instruções `DELETE` que uma declaração de `cascade` trataria em uma única operação.

**Recomendação:** Declarar `cascade='all, delete-orphan'` no backref `User.tasks` (ou `ON DELETE CASCADE` no nível da FK) e remover o loop manual.

---

#### M-05 — `db.create_all()` Executado em Tempo de Importação
**Arquivo:** `app.py:30-31`

A criação do schema é executada incondicionalmente dentro de `with app.app_context():` no nível do módulo, toda vez que `app` é importado (inclusive pelo `seed.py`).

**Impacto:** Side-effect em tempo de importação é problemático para testes e migrações; conflitará com o Alembic se for adicionado futuramente.

**Recomendação:** Mover para uma factory `create_app()` ou um comando CLI `flask init-db`; chamar apenas no entrypoint da aplicação.

---

### 🔵 Baixos

---

#### B-01 — Magic Strings — Whitelists de Status e Role
**Arquivo:** `routes/task_routes.py:110`, `177`; `routes/user_routes.py:71`, `120`; `models/task.py:39`

As listas literais `['pending','in_progress','done','cancelled']` e `['user','admin','manager']` aparecem inline em cinco locais diferentes; o mesmo ocorre com a cor padrão `'#000000'` (`models/category.py:10`, `utils/helpers.py:116`).

**Impacto:** Adicionar um novo status ou role exige editar cinco arquivos; fácil deixar algum passar e criar uma divergência silenciosa.

**Recomendação:** Definir `TaskStatus`, `UserRole` (enum ou tupla) em `config/settings.py` e referenciar em todos os lugares.

---

#### B-02 — Magic Numbers — Limites de Validação e Defaults
**Arquivo:** `routes/task_routes.py:96`, `99`, `113`, `167`, `169`, `182`; `routes/user_routes.py:64`, `115`; `models/task.py:12`, `46`

Limites de comprimento do título (3/200), faixa de prioridade (1/5), comprimento mínimo de senha (4) e prioridade padrão (3) aparecem como inteiros brutos ao longo do código. `utils/helpers.py:110-116` já define constantes para esses valores, mas ninguém as importa.

**Impacto:** Mesmo risco das magic strings — divergência fácil; as constantes existentes provam a intenção mas são código morto.

**Recomendação:** Importar `MIN_TITLE_LENGTH`, `MAX_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, etc., de um módulo compartilhado (mover para `config/settings.py`) e usá-las em todos os lugares.

---

#### B-03 — `print()` Usado para Logging
**Arquivo:** `routes/task_routes.py:149`, `153`, `219`, `234`; `routes/user_routes.py:83`, `89`, `147`; `services/notification_service.py:21`, `24`; `utils/helpers.py:39-41`

Aproximadamente 10 chamadas `print(...)` usadas para logar criações, deleções e erros; nenhuma configuração de `logging` em nenhum lugar.

**Impacto:** Output não pode ser filtrado por nível, enviado para um arquivo ou formatado para produção; impacto de performance sob carga.

**Recomendação:** Substituir por `logging.getLogger(__name__).info(...)`/`.exception(...)` e configurar um logger básico em `app.py` (ou `src/config/logging.py`).

---

#### B-04 — Nomenclatura Ruim e Estilo Inconsistente
**Arquivo:** `models/task.py:45` (`validate_priority(self, p)`); `routes/task_routes.py:268` (`for t in results`); `routes/user_routes.py:14` (`for u in users`); `routes/report_routes.py:24-28` (`p1, p2, p3, p4, p5`)

Variáveis de uma letra fora de corpos de loop estreitos; parâmetro de método não descritivo `p`; contadores `p1..p5` em vez de níveis de prioridade nomeados.

**Impacto:** Legibilidade prejudicada; a intenção precisa ser inferida do contexto.

**Recomendação:** Renomear para `priority`, `task`, `user`, e usar um dict indexado por label de prioridade (`counts_by_priority['critical']`).

---

#### B-05 — Imports Não Utilizados
**Arquivo:** `app.py:7` (`os, sys, json, datetime` — apenas `datetime` usado); `routes/task_routes.py:7` (`json, os, sys, time` — nenhum usado); `routes/user_routes.py:6` (`hashlib, json` — nenhum usado); `routes/report_routes.py:7-8` (`format_date`, `calculate_percentage`, `json` — nenhum usado); `utils/helpers.py:3-7` (`os, sys, math, hashlib` — nenhum usado)

Múltiplos módulos carregam imports que nunca são referenciados.

**Impacto:** Ruído; risco leve de confundir futuros leitores sobre dependências reais.

**Recomendação:** Remover imports não utilizados; em `app.py:7` manter apenas `datetime`.

---

## 4. Refatoração Aplicada (Fase 3)

Todos os 20 achados foram endereçados em uma refatoração completa para arquitetura MVC com factory pattern.

### Nova Estrutura do Projeto

```
task-manager-api/
├── .env.example
├── .gitignore
├── README.md
├── app.py                       # Composition root (factory create_app)
├── requirements.txt             # + bcrypt
├── seed.py
├── config/
│   ├── __init__.py
│   └── settings.py              # Config + constantes de status/role/regex
├── controllers/
│   ├── __init__.py
│   ├── task_controller.py       # ValidationError / NotFoundError + TaskController
│   ├── user_controller.py       # AuthenticationError + UserController
│   ├── category_controller.py
│   └── report_controller.py
├── middlewares/
│   ├── __init__.py
│   └── error_handler.py         # register_error_handlers(app)
├── models/
│   ├── __init__.py
│   ├── database.py              # db = SQLAlchemy()
│   ├── user.py                  # bcrypt hashing, password removido de to_dict
│   ├── task.py                  # lista eager-loaded, stats agregados
│   └── category.py
├── services/
│   └── notification_service.py  # config SMTP injetada de settings
└── views/
    ├── __init__.py
    ├── task_routes.py
    ├── user_routes.py
    ├── category_routes.py
    └── report_routes.py
```

### Transformações Aplicadas

| ID | Descrição |
|---|---|
| RT-01 | Credenciais hardcoded → `config/settings.py` + `.env` / `.env.example` (`SECRET_KEY`, `DATABASE_URL`, `SMTP_*`) + `.gitignore` |
| RT-02 | `routes/report_routes.py` dividido em `views/category_routes.py` + `views/report_routes.py` (uma entidade por arquivo) |
| RT-04 | Lógica de negócio extraída: `routes/` → `controllers/` (task/user/category/report); views agora com handlers de ≤ 10 linhas |
| RT-05 | N+1 corrigidos: `Task.get_all_with_relations()` usa `joinedload(user, category)`; relatórios usam `GROUP BY` (`count_by_status`, `count_by_priority`, `stats_by_user`) |
| RT-06 | Tratamento de erros centralizado via `middlewares/error_handler.py` para `ValidationError`, `NotFoundError`, `AuthenticationError`, 400/404/405/500/Exception; `except:` nus removidos |
| RT-07 | Validação consolidada: `utils/helpers.py::process_task_data` deletado; regras definidas uma única vez em `task_controller` / `user_controller` |
| RT-08 | Magic numbers substituídos por `Config.*` de `settings.py` (limites de título/prioridade/senha, `RECENT_ACTIVITY_DAYS`); listas de status/role → `VALID_TASK_STATUSES` / `VALID_USER_ROLES` / `TERMINAL_TASK_STATUSES` |
| RT-10 | MD5 substituído por bcrypt em `User.set_password`/`check_password`; campo `password` removido de `User.to_dict`; `cascade='all, delete-orphan'` configurado em `User.tasks` e `ondelete='CASCADE'` na FK; loop de cascade delete manual removido |
| — | `print()` substituído por `logging.getLogger` via `basicConfig` em `create_app` |
| — | `database.py` raiz obsoleto, `routes/` e `utils/` legados removidos |
| — | App migrado para factory pattern `create_app()` |

### Validação Final

- ✅ Aplicação inicializa sem erros
- ✅ Todos os endpoints respondem corretamente:

| Grupo | Endpoints |
|---|---|
| Sistema | `/health`, `/` |
| Tarefas | `GET/POST/PUT/DELETE /tasks`, `/tasks/search`, `/tasks/stats` |
| Usuários | `GET/POST/PUT/DELETE /users`, `/users/<id>/tasks`, `/login` |
| Categorias | `GET/POST/PUT/DELETE /categories` |
| Relatórios | `/reports/summary`, `/reports/user/<id>` |
| Erros | Fluxos 404, 400 e 401 verificados |

- ✅ Zero credenciais hardcoded restantes (verificado via grep)
- ✅ Zero lógica de negócio na camada de views (todos os handlers com ≤ 10 linhas, chamando o controller)
- ✅ Models abstraem todo acesso a dados (controllers chamam class methods, nunca tocam `db.session` diretamente)

---

## 5. Conclusão

O projeto apresentava **4 vulnerabilidades críticas de segurança**, incluindo segredos e credenciais SMTP hardcoded no código-fonte, hashing de senha com MD5 — algoritmo criptograficamente quebrado — e vazamento do hash de senha em todas as respostas da API de usuários. A combinação de MD5 sem salt com a exposição do hash representa risco imediato de comprometimento de todas as credenciais em caso de acesso ao banco de dados.

A refatoração para arquitetura MVC com factory pattern endereçou todos os 20 achados: regras de validação foram consolidadas de três fontes de verdade para uma; queries N+1 foram eliminadas com `joinedload` e `GROUP BY`; o tratamento de erros foi centralizado; e toda a lógica de negócio foi removida da camada de rotas, que passou a ter handlers de no máximo 10 linhas cada.
