# Relatório de Auditoria de Código
**Projeto:** code-smells-project  
**Stack:** Python 3 + Flask 3.1.1  
**Data:** 2025  
**Arquivos analisados:** 4 (`app.py`, `controllers.py`, `models.py`, `database.py`) — ~784 LOC

---

## 1. Visão Geral do Projeto

| Atributo | Detalhe |
|---|---|
| Linguagem | Python 3 |
| Framework | Flask 3.1.1 + flask-cors 5.0.1 |
| Dependências | flask, flask-cors, sqlite3 (stdlib) |
| Domínio | API de e-commerce (produtos, usuários, pedidos, login, relatórios de vendas) |
| Tabelas do banco | `produtos`, `usuarios`, `pedidos`, `itens_pedido` |

### Arquitetura atual

O projeto adota uma arquitetura **parcialmente em camadas**: os arquivos são separados por nome (`app.py` / `controllers.py` / `models.py` / `database.py`), mas a separação é violada em múltiplos pontos:

- SQL com concatenação de strings diretamente nos models;
- Lógica de validação misturada nos controllers;
- Rotas administrativas com acesso direto ao banco em `app.py`;
- Conexão global mutável ao banco de dados utilizada como estado compartilhado.

---

## 2. Resumo dos Achados

| Severidade | Quantidade |
|---|---|
| 🔴 CRÍTICO | 9 |
| 🟠 ALTO | 7 |
| 🟡 MÉDIO | 6 |
| 🔵 BAIXO | 4 |
| **Total** | **26** |

---

## 3. Achados Detalhados

### 🔴 Críticos

---

#### C-01 — `SECRET_KEY` Hardcoded no Código-Fonte
**Arquivo:** `app.py:7`

A chave secreta da aplicação (`"minha-chave-super-secreta-123"`) está escrita diretamente no código-fonte e versionada no repositório.

**Impacto:** Qualquer pessoa com acesso ao repositório pode forjar sessões e tokens. A rotação da chave exige alteração de código e redeploy.

**Recomendação:** Mover para `config/settings.py` e carregar via `os.environ.get("SECRET_KEY")`; documentar em `.env.example`.

---

#### C-02 — `DEBUG=True` Hardcoded para Produção
**Arquivo:** `app.py:8`, `app.py:88`

`app.config["DEBUG"] = True` e `app.run(..., debug=True)` são definidos de forma fixa, ativando o debugger interativo do Werkzeug.

**Impacto:** Em produção, expõe um console de execução remota de código via PIN do debugger; além disso, stack traces completos são retornados aos clientes em qualquer erro.

**Recomendação:** Controlar via `Config.DEBUG = os.environ.get("DEBUG", "false").lower() == "true"`.

---

#### C-03 — Endpoint de Execução Arbitrária de SQL sem Autenticação
**Arquivo:** `app.py:59-78`

`POST /admin/query` lê o campo `sql` do corpo da requisição e executa o valor diretamente via `cursor.execute(query)`, retornando todas as linhas. Sem autenticação, allowlist ou rate-limit.

**Impacto:** Qualquer cliente não autenticado pode ler, modificar ou destruir todas as tabelas — comprometimento total do banco de dados.

**Recomendação:** Remover este endpoint completamente. Caso uma ferramenta de manutenção seja necessária, implementar com role de administrador autenticado, conjunto de comandos parametrizados e allowlisted.

---

#### C-04 — Endpoint Destrutivo sem Autenticação
**Arquivo:** `app.py:47-57`

`POST /admin/reset-db` deleta todas as linhas de `itens_pedido`, `pedidos`, `produtos` e `usuarios` sem autenticação, proteção CSRF ou confirmação.

**Impacto:** Negação de serviço trivial e perda total de dados por qualquer chamador anônimo.

**Recomendação:** Remover o endpoint ou protegê-lo com middleware de role de administrador; expor apenas em blueprint exclusivo para ambiente de desenvolvimento (`DEBUG=true`).

---

#### C-05 — `SECRET_KEY` Exposta pelo Endpoint de Health Check
**Arquivo:** `controllers.py:289`

`health_check()` retorna `"secret_key": "minha-chave-super-secreta-123"` no corpo JSON da resposta. O segredo está duplicado no código-fonte e é publicado a cada probe de saúde.

**Impacto:** Mesmo que a chave seja rotacionada no código, o endpoint continuará publicando o valor; qualquer monitor externo, proxy ou agregador de logs captura a chave.

**Recomendação:** Remover os campos `secret_key`, `db_path` e `debug` da resposta de health; nunca retornar valores de configuração em respostas de API.

---

#### C-06 — Senhas Armazenadas e Comparadas em Texto Puro
**Arquivo:** `database.py:75-83`, `models.py:105-120`, `models.py:122-131`

Usuários de seed são inseridos com senhas como `"admin123"`, `"123456"` e `"senha123"` diretamente na coluna `senha`. O login compara o valor bruto via `WHERE email = '...' AND senha = '...'`. Nenhum tipo de hashing é aplicado.

**Impacto:** Um único `SELECT` (ou o vetor de SQL injection descrito abaixo) expõe todas as credenciais em texto claro.

**Recomendação:** Aplicar `bcrypt` na criação (`bcrypt.hashpw`) e verificação (`bcrypt.checkpw`). Adicionar `bcrypt>=4.0` ao `requirements.txt` e re-gerar os fixtures de desenvolvimento com hashes.

---

#### C-07 — SQL Injection via Concatenação de Strings em Toda a Camada de Models
**Arquivo:** `models.py:28`, `47-50`, `57-60`, `68`, `92`, `109-110`, `126-129`, `140`, `148-150`, `155`, `157-160`, `163-166`, `174`, `188`, `192`, `220`, `224`, `280-281`, `289-297`

Todas as queries são construídas com concatenação direta de valores controlados pelo usuário. Exemplos:
- `"SELECT * FROM produtos WHERE id = " + str(id)`
- `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`
- Builder de busca que concatena `termo`, `categoria`, `preco_min`, `preco_max`.

**Impacto:** Bypass de autenticação no `/login` (ex.: `' OR '1'='1`), exfiltração de dados e mutações arbitrárias são triviais.

**Recomendação:** Substituir toda interpolação por placeholders parametrizados: `cursor.execute("SELECT ... WHERE id = ?", (id,))`. Centralizar por entidade em classes de model.

---

#### C-08 — God File: `models.py` Mistura Quatro Domínios e Regras de Negócio
**Arquivo:** `models.py:1-315`

Um único módulo de 315 linhas contém acesso a dados de `produtos`, `usuarios`, `pedidos` e `itens_pedido`, além de regras de negócio (tiers de desconto em `relatorio_vendas`, validação de estoque e cálculo de totais em `criar_pedido`).

**Impacto:** Qualquer alteração pode quebrar domínios não relacionados; impossível testar uma entidade isoladamente.

**Recomendação:** Dividir em `models/produto_model.py`, `models/usuario_model.py`, `models/pedido_model.py`, `models/item_pedido_model.py`. Mover regras de desconto e checkout para os controllers.

---

#### C-09 — God File: `controllers.py` Mistura Cinco Domínios
**Arquivo:** `controllers.py:1-293`

Único arquivo de 293 linhas com handlers de produtos, usuários, login, pedidos, relatórios e health. Validação, orquestração de negócio e side-effects (`print "ENVIANDO EMAIL/SMS/PUSH"`) estão todos intercalados.

**Impacto:** Alto acoplamento, boilerplate repetido de `try/except`, e qualquer novo domínio força edições no mesmo arquivo — conflitos de merge e regressões acidentais entre domínios.

**Recomendação:** Dividir em `controllers/produto_controller.py`, `controllers/usuario_controller.py`, `controllers/pedido_controller.py`, etc., e parear cada um com um Blueprint em `views/<entity>_routes.py`.

---

### 🟠 Altos

---

#### A-01 — Conexão Global Mutável ao Banco (Singleton)
**Arquivo:** `database.py:4-11`

`db_connection = None` é uma variável global de módulo; `get_db()` a inicializa preguiçosamente com `check_same_thread=False` e a mantém global. Todos os callers compartilham a mesma conexão.

**Impacto:** Sem injeção de dependência — todo model/controller está acoplado ao singleton, tornando testes unitários impossíveis sem monkey-patching. `check_same_thread=False` com conexão única causa race conditions sob requisições concorrentes.

**Recomendação:** Usar o objeto `g` do Flask com `teardown_appcontext`: uma conexão por requisição. Criar uma factory `models/database.py` e injetar a conexão via `get_db()` dentro do contexto de requisição.

---

#### A-02 — Senhas Retornadas nos Endpoints de Listagem e Detalhe
**Arquivo:** `controllers.py:128-134`, `controllers.py:136-144`, `models.py:72-87`, `models.py:89-103`

`GET /usuarios` e `GET /usuarios/<id>` incluem `"senha": row["senha"]` diretamente do model na resposta serializada.

**Impacto:** Divulgação completa de credenciais sem necessidade de SQL injection; trivialmente explorável.

**Recomendação:** Remover `senha` do serializador. Definir `to_safe_dict()` expondo apenas `id`, `nome`, `email`, `tipo`, `criado_em`.

---

#### A-03 — Lógica de Negócio na Camada de Model (`relatorio_vendas`)
**Arquivo:** `models.py:235-273`

`relatorio_vendas()` executa cinco queries de contagem/soma e então aplica regras de desconto por tier (`if faturamento > 10000: desconto = faturamento * 0.1` …) e calcula `ticket_medio` — lógica de negócio pura misturada com acesso a dados.

**Impacto:** Regras de desconto não podem ser testadas sem acesso ao banco; mudanças de regra exigem editar um arquivo SQL.

**Recomendação:** Manter queries agregadas em `PedidoModel.get_sales_aggregates()`; mover cálculos de desconto e ticket médio para `PedidoController.build_sales_report()` com thresholds lidos da `config`.

---

#### A-04 — Orquestração Multi-Etapa com Lógica de Negócio no Model (`criar_pedido`)
**Arquivo:** `models.py:133-169`

O método do model realiza validação de estoque, cálculo de total, três mutações sequenciais (insert pedido, insert itens, decrement estoque) e retorna resultado ou envelope `{"erro": ...}` — regras de negócio e persistência misturadas em uma única função sem garantias de transação.

**Impacto:** Falha no meio do processo deixa escritas parciais (sem rollback); regra "estoque deve cobrir quantidade" é intestável sem banco; o formato de erro vaza para o controller.

**Recomendação:** Mover orquestração para `PedidoController.process_checkout()`; expor métodos granulares no model e envolver todo o fluxo em `with db: ...` (transação). Lançar exceções tipadas em vez de retornar dicts de erro.

---

#### A-05 — Lógica de Validação Embutida no Controller
**Arquivo:** `controllers.py:24-62`, `controllers.py:64-96`

Cada handler contém ~30 linhas de validação inline (presença, negatividade, faixa de comprimento, allowlist de categorias hardcoded) antes de chamar o model. O mesmo bloco é duplicado em `atualizar_produto`.

**Impacto:** Regras de validação divergem entre criação e atualização; não podem ser testadas separadamente da camada HTTP.

**Recomendação:** Extrair para `ProdutoController.validate_payload(data)` retornando `(cleaned, error)`. Controllers devem focar em orquestração.

---

#### A-06 — Side-Effects de Notificação Dentro dos Controllers
**Arquivo:** `controllers.py:208-210`, `controllers.py:247-250`

`criar_pedido` e `atualizar_status_pedido` emitem notificações com `print("ENVIANDO EMAIL: …")` / `print("ENVIANDO SMS: …")` diretamente no controller após a persistência.

**Impacto:** Notificações não podem ser desabilitadas em testes, agrupadas ou substituídas por um provedor real sem editar o controller. Side-effects vazam para a camada HTTP.

**Recomendação:** Extrair para `services/notification_service.py` (ou helper `_notify_order_created`), invocado a partir do controller.

---

#### A-07 — Rotas de Admin com Acesso Direto ao Banco em `app.py`
**Arquivo:** `app.py:47-78`

`/admin/reset-db` e `/admin/query` são declaradas via `@app.route` dentro da raiz de composição e chamam `cursor.execute()` diretamente — bypassando a camada de model completamente.

**Impacto:** `app.py` acumula comportamento de negócio, violando seu papel de entrypoint fino.

**Recomendação:** Remover (recomendado) ou realocar para um Blueprint protegido em `views/admin_routes.py` com chamadas a métodos de model adequados.

---

### 🟡 Médios

---

#### M-01 — N+1 Queries em `get_pedidos_usuario`
**Arquivo:** `models.py:171-201`

Um SELECT busca todos os pedidos do usuário; para cada pedido, outro SELECT carrega os itens; para cada item, um terceiro SELECT busca o nome do produto — três níveis aninhados.

**Impacto:** Um usuário com 20 pedidos e média de 5 itens cada custa 1 + 20 + 100 = 121 queries; latência cresce linearmente com o número de pedidos.

**Recomendação:** Substituir por um único LEFT JOIN entre `pedidos`, `itens_pedido` e `produtos`; agrupar as linhas em Python por `pedido_id`.

---

#### M-02 — N+1 Queries em `get_todos_pedidos`
**Arquivo:** `models.py:203-233`

Mesmo padrão N+1 descrito acima, mas aplicado a todos os pedidos do sistema.

**Impacto:** O(pedidos × itens) queries por requisição — degrada o endpoint de listagem conforme os dados crescem.

**Recomendação:** Mesma estratégia de JOIN; alternativamente, buscar itens em batch via `pedido_id IN (...)` e nomes de produto em uma segunda query IN.

---

#### M-03 — Sem Handler Centralizado de Erros
**Arquivo:** `app.py` (completo), `controllers.py:5-292`

Não há registro de `@app.errorhandler`; todos os controllers envolvem seu corpo em `try / except Exception as e: return jsonify({"erro": str(e)}), 500`. `str(e)` pode vazar detalhes internos, e inconsistências são inevitáveis.

**Impacto:** Stack traces e strings de erro do driver de banco podem chegar aos clientes; novos handlers facilmente esquecem o boilerplate, quebrando o contrato da API.

**Recomendação:** Adicionar `middlewares/error_handler.py` registrando handlers para 400/404/422/500/Exception via `register_error_handlers(app)`. Remover os `try/except Exception` por handler e deixar exceções propagar.

---

#### M-04 — Bloco de Validação Duplicado (Produto: Create vs Update)
**Arquivo:** `controllers.py:24-62`, `controllers.py:64-96`

As verificações de presença, tipo/faixa e parsing de JSON estão duplicadas quase verbatim entre `criar_produto` e `atualizar_produto`.

**Impacto:** Duas fontes de verdade para a mesma regra; as regras já divergem (create verifica `len(nome) > 200`, update não).

**Recomendação:** Extrair para `ProdutoController._validate(data, partial: bool)` retornando um payload normalizado ou lançando `ValueError`.

---

#### M-05 — Mapeamento Row-to-Dict Duplicado
**Arquivo:** `models.py:10-22`, `30-40`, `78-86`, `95-102`, `178-185`, `211-217`, `302-313`

A mesma construção `{"id": row["id"], "nome": row["nome"], ...}` é repetida em sete locais (serializadores de produtos e pedidos, com variações sutis).

**Impacto:** Adições ou renomeações de campo exigem atualização em múltiplos locais; bugs introduzidos quando algum local é esquecido.

**Recomendação:** Adicionar um único método estático `to_dict()` por classe de model.

---

#### M-06 — Boilerplate de `try/except` Repetido em Todos os Handlers
**Arquivo:** `controllers.py:5-292`

14 de 14 handlers envolvem seu corpo em `try / except Exception as e: return jsonify({"erro": str(e)}), 500`. Após adicionar o handler centralizado (M-03), todo handler pode remover o wrapper.

**Impacto:** Ruído visual e uma única classe de tratamento de erros que oculta causas raiz.

**Recomendação:** Deletar os wrappers após registrar os handlers globais; deixar exceções subir ao middleware.

---

### 🔵 Baixos

---

#### B-01 — Magic Numbers nos Tiers de Desconto
**Arquivo:** `models.py:257-262`

Os tiers `> 10000`, `> 5000`, `> 1000` e as taxas `0.1`, `0.05`, `0.02` são literais inline sem explicação.

**Impacto:** Regras de negócio são invisíveis para quem lê o código; ajustes exigem alteração de código.

**Recomendação:** Definir `SALES_REPORT_TIERS` (lista de tuplas) em `config/settings.py`; iterar para selecionar o tier aplicável.

---

#### B-02 — Magic String Lists (Status / Categoria)
**Arquivo:** `controllers.py:52` (categorias_validas), `controllers.py:242` (lista de status)

As categorias permitidas `["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]` e os status de pedido `["pendente", "aprovado", "enviado", "entregue", "cancelado"]` são literais inline.

**Impacto:** A lista não pode ser alterada sem edição de código; redeclarada a cada requisição.

**Recomendação:** Mover para `config/settings.py` (ou um enum); referenciar via `Config.CATEGORIAS_VALIDAS`.

---

#### B-03 — `print()` Usado como Logging da Aplicação
**Arquivo:** `app.py:56`, `84-86`; `controllers.py:8`, `11`, `57`, `61`, `106`, `161`, `179`, `182`, `208-210`, `219`, `248`, `250`

Mensagens de status e erros são escritas com `print(...)` para stdout em vez de um logger estruturado.

**Impacto:** Sem níveis de log, sem controle de destino, sem IDs de correlação; observabilidade em produção é precária.

**Recomendação:** Usar `logging.getLogger(__name__)` por módulo; configurar uma vez em `app.py`.

---

#### B-04 — Validação de Login Limitada à Presença do Campo
**Arquivo:** `controllers.py:167-186`

`login()` verifica apenas que `email` e `senha` são não-vazios, e então os concatena diretamente em uma string SQL no model. Sem verificações de comprimento ou formato.

**Impacto:** Combinado com o SQL injection descrito em C-07, a validação ausente amplia a superfície de ataque.

**Recomendação:** Após corrigir o SQL com placeholders, validar `email` contra uma regex simples e rejeitar valores malformados com `400`.

---

## 4. Refatoração Aplicada (Fase 3)

Todos os 26 achados foram endereçados em uma refatoração completa para arquitetura MVC.

### Nova Estrutura do Projeto

```
code-smells-project/
├── .env                     # dev only, não versionado
├── .env.example
├── README.md
├── requirements.txt          # + python-dotenv, + bcrypt
└── src/
    ├── app.py                         # composition root
    ├── config/
    │   ├── __init__.py
    │   └── settings.py                # Config carregada de variáveis de ambiente
    ├── models/
    │   ├── __init__.py
    │   ├── database.py                # Flask g + teardown; schema + seed
    │   ├── produto_model.py
    │   ├── usuario_model.py
    │   └── pedido_model.py
    ├── controllers/
    │   ├── __init__.py
    │   ├── produto_controller.py      # + ValidationError
    │   ├── usuario_controller.py      # bcrypt hash + verify
    │   ├── pedido_controller.py       # checkout, notificações
    │   └── relatorio_controller.py    # regras de relatório de vendas
    ├── views/
    │   ├── __init__.py
    │   ├── index_routes.py
    │   ├── produto_routes.py
    │   ├── usuario_routes.py          # inclui /login
    │   ├── pedido_routes.py
    │   ├── relatorio_routes.py
    │   ├── health_routes.py
    │   └── admin_routes.py            # gated por ADMIN_API_ENABLED
    └── middlewares/
        ├── __init__.py
        └── error_handler.py
```

### Transformações Aplicadas

| ID | Descrição |
|---|---|
| RT-01 | `SECRET_KEY`, `DEBUG`, `HOST/PORT`, `DATABASE_PATH` e tiers de desconto movidos para `config/settings.py` (dotenv); `.env.example` criado |
| RT-02 | God files divididos: `models.py` → models por entidade; `controllers.py` → controllers por domínio; rotas migradas para Blueprints em `views/` |
| RT-03 | Toda concatenação SQL substituída por queries parametrizadas com placeholders `?` em todos os models |
| RT-04 | Lógica de negócio extraída para controllers: validação de produto em `_validate_payload`; checkout em `process_checkout` com commit/rollback transacional; tiers de desconto em `RelatorioController` |
| RT-05 | N+1 em `get_pedidos_usuario` e `get_todos_pedidos` colapsados em um único LEFT JOIN; agrupamento feito em Python via `_fetch_with_items` |
| RT-06 | `middlewares/error_handler.py` registrando handlers para `ValidationError` (400), `HTTPException` e `Exception` (500 com stack trace logado); boilerplate `try/except` removido dos controllers |
| RT-07 | Mapeamento row-to-dict deduplicado via `to_dict()`/`to_public_dict()` por model; validação de produto deduplicada entre create e update |
| RT-08 | Magic numbers/strings extraídos: tiers de desconto (`SALES_REPORT_TIERS`), categorias permitidas, status de pedido e comprimento de nome de produto agora vivem em `Config` |
| RT-09 | Validação de input reforçada: campos de produto com checagem de tipo, login rejeita campos vazios, itens de pedido rejeitam quantidades não positivas, querystrings numéricas parseadas com `type=float` |
| RT-10 | Senhas em texto puro substituídas por bcrypt; campo `senha` removido de todas as respostas `/usuarios`; `secret_key`/`db_path`/`debug` removidos do `/health`; rotas `/admin` protegidas por `ADMIN_API_ENABLED` |
| — | `print()` substituído por `logging` em todos os módulos (notificações + logger de exceções não tratadas) |

### Validação Final

- ✅ Aplicação inicializa sem erros (`python src/app.py` — servidor ativo, 18 rotas registradas)
- ✅ Todos os endpoints respondem corretamente (smoke test: `/`, `/health`, `/produtos` GET/POST, `/produtos/busca`, `/produtos/<id>`, `/login` válido + inválido + SQLi bloqueado, `/pedidos` POST/GET, `/pedidos/<id>/status`, `/relatorios/vendas`, `/usuarios`, gate `/admin/query`)
- ✅ Zero credenciais hardcoded restantes (`SECRET_KEY` e senhas carregados do ambiente; seeds com hash bcrypt)
- ✅ Zero lógica de negócio na camada de views (views apenas parseiam request, chamam controller, jsonificam resultado)
- ✅ Models abstraem todo acesso a dados (sem `request`/`jsonify`/regras de negócio nos models; controllers não importam `sqlite3`)

---

## 5. Conclusão

O projeto apresentava **9 vulnerabilidades críticas de segurança**, incluindo SQL injection generalizado, execução arbitrária de SQL sem autenticação, senhas em texto puro e exposição de configuração sensível. Adicionalmente, a arquitetura exibia violações severas de separação de responsabilidades que comprometiam a testabilidade, manutenibilidade e escalabilidade do código.

A refatoração em arquitetura MVC endereçou todos os 26 achados, resultando em uma base de código segura, modular e alinhada com as boas práticas de desenvolvimento Flask.
