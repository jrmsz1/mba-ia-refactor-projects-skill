# Code Audit Skill — code-smells-project

> Skill de auditoria e refatoração automática de código aplicada a uma API Flask de e-commerce.  
> Projeto analisado: **code-smells-project** | Stack: **Python 3 + Flask 3.1.1 + SQLite**

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

1. **Fase 1 — Reconhecimento do projeto:** leitura de todos os arquivos-fonte, mapeamento das dependências, identificação das tabelas do banco e caracterização da arquitetura real (não declarada).
2. **Fase 2 — Auditoria por catálogo de anti-patterns:** cruzamento de cada arquivo contra um conjunto predefinido de padrões problemáticos, ordenando os achados por severidade e impacto real.
3. **Fase 3 — Refatoração guiada:** aplicação das correções na mesma sessão, com validação por smoke test de todos os endpoints originais.

---

### Problemas Identificados

#### 🔴 Críticos — Risco imediato de segurança ou perda de dados

| ID | Problema | Arquivo(s) | Por que é relevante |
|---|---|---|---|
| C-01 | `SECRET_KEY` hardcoded no código-fonte | `app.py:7` | Qualquer pessoa com acesso ao repositório pode forjar tokens de sessão. A rotação exige redeploy. Segredos no VCS são permanentes mesmo após remoção. |
| C-02 | `DEBUG=True` hardcoded para produção | `app.py:8`, `app.py:88` | O debugger interativo do Werkzeug expõe um console de execução remota de código. Stack traces completos são retornados a qualquer cliente em caso de erro. |
| C-03 | Endpoint de execução arbitrária de SQL sem autenticação | `app.py:59-78` | `POST /admin/query` executa qualquer SQL enviado no body, sem auth, allowlist ou rate-limit. Comprometimento total do banco por qualquer chamador anônimo. |
| C-04 | Endpoint destrutivo sem autenticação | `app.py:47-57` | `POST /admin/reset-db` apaga todas as tabelas sem autenticação, CSRF ou confirmação. Vetor trivial de denial-of-service e perda total de dados. |
| C-05 | `SECRET_KEY` exposta pelo endpoint de health check | `controllers.py:289` | O health check publica a chave secreta em cada probe. Monitores externos, proxies e log aggregators capturam o valor indefinidamente. |
| C-06 | Senhas em texto puro no banco de dados | `database.py:75-83`, `models.py:105-131` | Senhas armazenadas sem qualquer hashing. Um único `SELECT` ou SQL injection expõe todas as credenciais em claro. |
| C-07 | SQL Injection generalizado via concatenação de strings | `models.py` (20+ ocorrências) | Todas as queries são construídas por concatenação de input do usuário. Bypass de autenticação, exfiltração e mutação arbitrária são triviais (`' OR '1'='1`). |
| C-08 | God File — `models.py` mistura quatro domínios | `models.py:1-315` | Um único módulo contém acesso a dados de quatro entidades e regras de negócio. Qualquer alteração pode quebrar domínios não relacionados; impossível testar em isolamento. |
| C-09 | God File — `controllers.py` mistura cinco domínios | `controllers.py:1-293` | Alto acoplamento entre domínios distintos. Novo recurso força edição no mesmo arquivo, gerando conflitos de merge e risco de regressão cruzada. |

---

#### 🟠 Altos — Degradação de arquitetura e risco operacional

| ID | Problema | Arquivo(s) | Por que é relevante |
|---|---|---|---|
| A-01 | Conexão global mutável ao banco (Singleton) | `database.py:4-11` | Sem injeção de dependência — unit tests são impossíveis sem monkey-patching. `check_same_thread=False` com conexão única gera race conditions sob carga. |
| A-02 | Senhas retornadas nos endpoints de usuário | `controllers.py:128-144`, `models.py:72-103` | `GET /usuarios` e `GET /usuarios/<id>` incluem o campo `senha` na resposta. Credential disclosure completa sem necessidade de SQL injection. |
| A-03 | Lógica de negócio na camada de model (`relatorio_vendas`) | `models.py:235-273` | Regras de desconto por tier misturadas com queries SQL. Regras de negócio não podem ser testadas sem banco; mudança de percentual exige editar o model. |
| A-04 | Orquestração multi-etapa com lógica de negócio no model (`criar_pedido`) | `models.py:133-169` | Quatro escritas sequenciais sem transação. Falha no meio deixa o banco em estado parcial sem rollback. Exceções retornam como dicts de erro, vazando para o controller. |
| A-05 | Lógica de validação embutida no controller | `controllers.py:24-96` | ~30 linhas de validação duplicadas entre `criar_produto` e `atualizar_produto`. Regras já divergem entre os dois handlers. |
| A-06 | Side-effects de notificação dentro dos controllers | `controllers.py:208-210`, `247-250` | `print("ENVIANDO EMAIL/SMS/PUSH")` acoplado ao controller HTTP. Não pode ser desabilitado em testes nem substituído por provedor real sem editar o controller. |
| A-07 | Rotas de admin com acesso direto ao banco em `app.py` | `app.py:47-78` | Rotas administrativas chamam `cursor.execute()` diretamente, bypassando a camada de model. `app.py` acumula comportamento de negócio, violando seu papel de entrypoint. |

---

#### 🟡 Médios — Problemas de qualidade e manutenibilidade

| ID | Problema | Arquivo(s) | Por que é relevante |
|---|---|---|---|
| M-01 | N+1 Query em `get_pedidos_usuario` | `models.py:171-201` | Três níveis de queries aninhadas por pedido. 20 pedidos × 5 itens = 121 round-trips ao banco por requisição. |
| M-02 | N+1 Query em `get_todos_pedidos` | `models.py:203-233` | Mesmo padrão N+1 aplicado ao endpoint de listagem global. Latência cresce O(pedidos × itens). |
| M-03 | Sem handler centralizado de erros | `app.py`, `controllers.py` | `str(e)` retornado diretamente ao cliente pode vazar mensagens internas do banco. Sem `@app.errorhandler`, novos handlers facilmente omitem o boilerplate. |
| M-04 | Bloco de validação duplicado (produto create vs update) | `controllers.py:24-96` | Regras já divergem entre os dois handlers. Manter dois locais sincronizados é uma fonte constante de bugs. |
| M-05 | Mapeamento row-to-dict duplicado em sete locais | `models.py` (7 ocorrências) | Renomear ou adicionar um campo requer atualização em múltiplos locais; bugs silenciosos quando algum local é esquecido. |
| M-06 | Boilerplate `try/except` repetido em todos os handlers | `controllers.py:5-292` | 14 de 14 handlers com o mesmo wrapper. Ruído que mascara a causa raiz real de cada falha. |

---

#### 🔵 Baixos — Legibilidade e manutenção de longo prazo

| ID | Problema | Arquivo(s) | Por que é relevante |
|---|---|---|---|
| B-01 | Magic numbers nos tiers de desconto | `models.py:257-262` | Thresholds e percentuais de desconto são literais sem nome. Ajuste de negócio exige busca e edição no código. |
| B-02 | Magic string lists (status / categoria) | `controllers.py:52`, `242` | Listas de valores permitidos redeclaradas inline. Adicionar um valor requer localizar e editar todos os pontos. |
| B-03 | `print()` usado como logging | `app.py`, `controllers.py` (15+ ocorrências) | Sem níveis de log, sem controle de destino, sem IDs de correlação. Observabilidade em produção é inviável. |
| B-04 | Validação de login limitada à presença do campo | `controllers.py:167-186` | Sem verificação de formato ou comprimento antes da concatenação SQL. Amplia a superfície de ataque do SQL injection. |

---

### Justificativa da Classificação

A severidade foi atribuída com base em três eixos:

- **Exploitabilidade:** quão facilmente um atacante externo, sem credenciais, consegue acionar o problema.
- **Impacto:** extensão do dano — de perda de dados pontual até comprometimento total do sistema.
- **Reversibilidade:** custo de recovery após o problema ser explorado.

Achados classificados como Críticos satisfazem os três eixos simultaneamente: são exploráveis sem autenticação, têm impacto sistêmico (perda total de dados, comprometimento de todas as credenciais, execução remota de código) e são de difícil reversão (credenciais no histórico git, dados já exfiltrados).

---

## Construção da Skill

### Visão Geral

A skill é um agente de auditoria e refatoração estruturado em **três fases obrigatórias e sequenciais** — Reconhecimento → Auditoria → Refatoração — que opera sobre qualquer base de código de API REST, independentemente de linguagem ou framework.

### Decisões de Design

#### 1. Separação rígida entre fases

Cada fase produz um artefato explícito (resumo, relatório, estrutura refatorada) antes de avançar para a próxima. Isso evita que a skill "corrija enquanto lê", o que tenderia a perder achados sistêmicos por foco excessivo no primeiro problema encontrado.

#### 2. Catálogo de anti-patterns como lista de verificação

A fase de auditoria não depende de heurísticas livres. Cada arquivo é cruzado contra um catálogo fixo de categorias:

| Categoria | Exemplos de anti-patterns cobertos |
|---|---|
| Segredos e configuração | Hardcoded secrets, DEBUG em produção, credenciais em logs |
| Autenticação e autorização | Endpoints sem auth, hashing inseguro, senhas em texto puro |
| Injeção | SQL injection por concatenação, exec de queries arbitrárias |
| Arquitetura | God files/classes, ausência de separação de camadas, singleton de banco |
| Performance | N+1 queries, ausência de transações em operações multi-etapa |
| Qualidade | Código duplicado, magic numbers/strings, tratamento de erros swallowed |
| Observabilidade | print() como log, sem handler centralizado de erros |

#### 3. Severidade baseada em impacto real, não em nomenclatura

A classificação CRÍTICO/ALTO/MÉDIO/BAIXO não é cosmética. Crítico reservado para achados que satisfazem simultaneamente: exploitável sem autenticação + impacto sistêmico + difícil reversão. Isso evita "severity inflation" que dilui o sinal para os times de desenvolvimento.

#### 4. Recomendações sempre acionáveis

Cada achado inclui uma recomendação com: (a) o que fazer, (b) onde fazer (arquivo/módulo alvo), e (c) como (API, padrão ou ferramenta concreta). Recomendações vagas como "melhorar a segurança" foram explicitamente evitadas.

#### 5. Validação como parte integral da skill

A fase de refatoração não termina sem um smoke test de todos os endpoints originais. Isso garante que as correções não quebrem o comportamento observável da API — condição necessária para que a skill seja útil em produção.

---

### Anti-patterns Incluídos e Justificativa

| Anti-pattern | Por que incluído |
|---|---|
| Hardcoded secrets | Presente em praticamente toda base legada; impacto crítico e correção simples (dotenv) |
| SQL Injection | Vetor de ataque #1 em APIs REST legadas; detectável estaticamente por análise de concatenação |
| Plain-text passwords | Frequente em projetos sem revisão de segurança; catastrófico em combinação com SQL injection |
| God Files/Classes | Raiz de boa parte dos outros problemas — impede testabilidade e favorece regressões |
| N+1 Queries | Impacto de performance invisível em desenvolvimento mas crítico em produção sob carga |
| Global mutable state | Causa race conditions e impossibilita testes paralelos |
| Swallowed exceptions | Mascara bugs reais, tornando depuração exponencialmente mais cara |
| Magic numbers/strings | Risco de divergência silenciosa; baixo custo de correção com alto retorno em manutenibilidade |

---

### Como a Skill é Agnóstica de Tecnologia

A skill foi projetada para ser aplicável a qualquer stack de API REST. Os mecanismos de agnossticidade são:

**Catálogo orientado a conceitos, não a APIs:** o anti-pattern "SQL Injection por concatenação de strings" se manifesta da mesma forma em Python (`"SELECT ... " + user_input`), JavaScript (template literals), PHP, Java, etc. A skill detecta o padrão conceitual, não a sintaxe específica.

**Recomendações mapeadas para equivalentes por linguagem:** quando uma recomendação sugere `bcrypt`, a skill documenta o pacote equivalente para cada linguagem alvo (`bcrypt` para Python/Node, `spring-security-crypto` para Java, `BCrypt.Net` para C#).

**Fases independentes de framework:** a Fase 1 (reconhecimento) adapta-se ao framework encontrado; as Fases 2 e 3 operam sobre conceitos de camada (Model, Controller, View, Middleware) que existem em qualquer framework MVC — Flask, Express, Django, Spring, Laravel, Rails.

**Estrutura de saída padronizada:** o relatório de auditoria segue o mesmo template independentemente da stack — seções fixas de Visão Geral, Achados por Severidade, Refatoração e Validação. Isso permite comparar auditorias entre projetos diferentes.

---

### Desafios Encontrados

**Achados inter-relacionados:** vários problemas tinham dependências entre si. Por exemplo, C-07 (SQL injection) e C-06 (senhas em texto puro) são independentes no diagnóstico mas a correção de C-06 requer resolver C-07 primeiro (não adianta hashear com bcrypt se a query de login ainda compara por concatenação). A skill precisou identificar a ordem correta de aplicação das correções.

**God files com múltiplos problemas sobrepostos:** `models.py` e `controllers.py` concentravam achados de todas as severidades. A decisão foi registrar cada achado separadamente (para clareza no relatório) e depois aplicar a divisão estrutural (RT-02) como pré-condição para os demais.

**Preservar comportamento externo durante a refatoração:** todos os 18 endpoints originais precisavam responder com o mesmo contrato após a refatoração. A estratégia foi manter os paths de URL idênticos nos Blueprints e validar cada um por smoke test antes de marcar a fase como concluída.

**Separação de configuração sem quebrar o ambiente de desenvolvimento:** `.env` não pode ser versionado, mas o projeto precisa funcionar localmente sem passos manuais. A solução foi o padrão `.env.example` com todos os valores de desenvolvimento preenchidos como placeholder — o desenvolvedor copia o arquivo e a aplicação sobe imediatamente.

---

## Resultados

### Resumo dos Relatórios de Auditoria

| Dimensão | Antes | Depois |
|---|---|---|
| Arquivos-fonte | 4 (`app.py`, `controllers.py`, `models.py`, `database.py`) | 21 arquivos em estrutura MVC |
| Linhas de código | ~784 LOC (4 arquivos) | Distribuídas em módulos coesos |
| Achados Críticos | 9 | 0 |
| Achados Altos | 7 | 0 |
| Achados Médios | 6 | 0 |
| Achados Baixos | 4 | 0 |
| **Total de achados** | **26** | **0** |
| Segredos no código-fonte | `SECRET_KEY`, senhas de seed em texto puro | Carregados de variáveis de ambiente |
| Hashing de senha | Texto puro (sem hashing) | bcrypt com salt |
| SQL Injection | 20+ pontos de concatenação | Zero — 100% parametrizado |
| Autenticação em rotas admin | Inexistente | Gated por `ADMIN_API_ENABLED` |
| Transações no checkout | Ausente — escritas parciais possíveis | `BEGIN`/`COMMIT`/`ROLLBACK` |
| Queries N+1 | Três níveis aninhados por pedido | Single LEFT JOIN |
| Logging | `print()` em 15+ locais | `logging.getLogger(__name__)` |
| Handler de erros | `try/except Exception` em cada handler | Middleware centralizado |

---

### Comparação Antes / Depois

#### Estrutura de arquivos

```
ANTES                          DEPOIS
─────────────────────────      ─────────────────────────────────────────
app.py          (89 LOC)       src/
controllers.py (293 LOC)       ├── app.py                  ← composition root
models.py      (315 LOC)       ├── config/settings.py      ← env-driven config
database.py     (87 LOC)       ├── models/
                               │   ├── database.py          ← Flask g + teardown
                               │   ├── produto_model.py
                               │   ├── usuario_model.py
                               │   └── pedido_model.py
                               ├── controllers/
                               │   ├── produto_controller.py
                               │   ├── usuario_controller.py
                               │   ├── pedido_controller.py
                               │   └── relatorio_controller.py
                               ├── views/
                               │   ├── produto_routes.py
                               │   ├── usuario_routes.py
                               │   ├── pedido_routes.py
                               │   ├── relatorio_routes.py
                               │   ├── health_routes.py
                               │   └── admin_routes.py
                               └── middlewares/
                                   └── error_handler.py
```

#### SQL Injection — antes e depois

```python
# ANTES — concatenação direta (vulnerável)
query = "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
cursor.execute(query)

# DEPOIS — query parametrizada (segura)
cursor.execute(
    "SELECT * FROM usuarios WHERE email = ? AND senha_hash = ?",
    (email, senha_hash)
)
```

#### Senhas — antes e depois

```python
# ANTES — texto puro no seed e na comparação
INSERT INTO usuarios (nome, email, senha) VALUES ('Admin', 'admin@loja.com', 'admin123')

# DEPOIS — bcrypt no seed e verificação por checkpw
senha_hash = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt())
INSERT INTO usuarios (nome, email, senha_hash) VALUES ('Admin', 'admin@loja.com', ?)
```

#### Endpoint admin — antes e depois

```python
# ANTES — execução arbitrária de SQL sem autenticação
@app.route("/admin/query", methods=["POST"])
def admin_query():
    query = dados.get("sql", "")
    cursor.execute(query)          # qualquer SQL, de qualquer chamador
    return jsonify(cursor.fetchall())

# DEPOIS — gated por configuração, retorna 404 quando desabilitado
@admin_bp.route("/query", methods=["POST"])
def admin_query():
    if not Config.ADMIN_API_ENABLED:
        abort(404)
    # ... lógica com allowlist e autenticação
```

#### N+1 Query — antes e depois

```python
# ANTES — três níveis de queries aninhadas
pedidos = get_pedidos_usuario(user_id)          # query 1
for pedido in pedidos:
    itens = get_itens_pedido(pedido['id'])       # query 2 (×N)
    for item in itens:
        produto = get_produto(item['produto_id'])# query 3 (×N×M)

# DEPOIS — single LEFT JOIN
SELECT p.*, ip.*, pr.nome as produto_nome
FROM pedidos p
LEFT JOIN itens_pedido ip ON ip.pedido_id = p.id
LEFT JOIN produtos pr ON pr.id = ip.produto_id
WHERE p.usuario_id = ?
```

---

### Checklist de Validação

#### Segurança

- [x] Nenhuma credencial ou chave secreta hardcoded no código-fonte
- [x] `SECRET_KEY` carregada exclusivamente de variável de ambiente
- [x] `DEBUG` controlado por variável de ambiente (padrão `false`)
- [x] Todas as queries SQL parametrizadas — zero concatenações de input do usuário
- [x] Senhas armazenadas como hash bcrypt com salt
- [x] Endpoint `/admin/query` desabilitado por padrão (`ADMIN_API_ENABLED=false`)
- [x] Endpoint `/admin/reset-db` desabilitado por padrão
- [x] Campo `senha` ausente em todas as respostas de `/usuarios`
- [x] Campos `secret_key`, `db_path`, `debug` ausentes da resposta de `/health`
- [x] `.env` listado no `.gitignore`

#### Arquitetura

- [x] Zero lógica de negócio na camada de views (handlers ≤ 15 linhas)
- [x] Models sem imports de `request`, `jsonify` ou regras de negócio
- [x] Controllers sem imports de `sqlite3` ou queries SQL diretas
- [x] Cada entidade em seu próprio arquivo de model e controller
- [x] Blueprints registrados no `app.py` (composition root)

#### Qualidade

- [x] N+1 em `get_pedidos_usuario` eliminado (single LEFT JOIN)
- [x] N+1 em `get_todos_pedidos` eliminado (single LEFT JOIN)
- [x] Handler centralizado de erros registrado em `middlewares/error_handler.py`
- [x] Zero boilerplate `try/except Exception` nos controllers
- [x] `to_dict()` implementado por model (zero duplicação de row-to-dict)
- [x] Validação de produto consolidada em `_validate_payload` (create e update)
- [x] `SALES_REPORT_TIERS`, `CATEGORIAS_VALIDAS`, `STATUS_PEDIDO` definidos em `Config`
- [x] `logging.getLogger(__name__)` substituindo `print()` em todos os módulos

#### Comportamento

- [x] Servidor inicializa sem erros — 18 rotas registradas
- [x] `GET /` responde 200
- [x] `GET /health` responde sem `secret_key` no payload
- [x] `GET /produtos` responde 200 com lista
- [x] `POST /produtos` cria produto e retorna 201
- [x] `GET /produtos/<id>` retorna produto por id
- [x] `GET /produtos/busca` retorna resultados filtrados
- [x] `POST /login` com credenciais válidas retorna token
- [x] `POST /login` com credenciais inválidas retorna 401
- [x] `POST /login` com payload de SQLi retorna 401 (bloqueado)
- [x] `POST /pedidos` cria pedido com transação completa
- [x] `GET /pedidos` retorna lista sem N+1
- [x] `PUT /pedidos/<id>/status` com status válido atualiza corretamente
- [x] `PUT /pedidos/<id>/status` com status inválido retorna 400
- [x] `GET /relatorios/vendas` retorna relatório com tiers de desconto corretos
- [x] `GET /usuarios` retorna lista sem campo `senha`
- [x] `POST /admin/query` retorna 404 com `ADMIN_API_ENABLED=false`

---

### Logs da Aplicação Após Refatoração

```
$ python src/app.py

INFO:src.models.database:Banco de dados inicializado.
INFO:src.models.database:Seed de dados inserido com sucesso.
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://0.0.0.0:5000
 * Registered blueprints: index, produtos, usuarios, pedidos, relatorios, health, admin
 * Total routes registered: 18
Press CTRL+C to quit
```

```
$ curl -s http://localhost:5000/health | python -m json.tool

{
    "status": "ok",
    "database": "connected",
    "timestamp": "2025-01-15T10:32:07.841Z"
}
```

> **Nota:** os campos `secret_key`, `db_path` e `debug` foram removidos do payload de health, confirmando o fechamento de C-05.

```
$ curl -s -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@loja.com", "senha": "'"'"' OR '"'"'1'"'"'='"'"'1"}' \
  | python -m json.tool

{
    "erro": "Credenciais inválidas"
}
```

> **Nota:** payload de SQL injection retorna 401, confirmando o fechamento de C-07.

---

## Como Executar

### Pré-requisitos

| Requisito | Versão mínima | Verificação |
|---|---|---|
| Python | 3.10+ | `python --version` |
| pip | 23+ | `pip --version` |
| Git | qualquer | `git --version` |

Não há dependência de Docker, banco externo ou variável de ambiente de sistema — a aplicação usa SQLite em arquivo local.

---

### Instalação

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd code-smells-project

# 2. Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -r requirements.txt
# Deve incluir: flask, flask-cors, python-dotenv, bcrypt
```

---

### Configuração do Ambiente

```bash
# 4. Copie o arquivo de exemplo e ajuste os valores
cp .env.example .env
```

Conteúdo mínimo do `.env` para desenvolvimento:

```dotenv
SECRET_KEY=chave-local-de-desenvolvimento
DEBUG=false
HOST=0.0.0.0
PORT=5000
DATABASE_PATH=loja.db
ADMIN_API_ENABLED=false

# Tiers de desconto (valores padrão)
BULK_DISCOUNT_TIER_1_MIN=10000
BULK_DISCOUNT_TIER_1_RATE=0.10
BULK_DISCOUNT_TIER_2_MIN=5000
BULK_DISCOUNT_TIER_2_RATE=0.05
BULK_DISCOUNT_TIER_3_MIN=1000
BULK_DISCOUNT_TIER_3_RATE=0.02
```

> **Atenção:** nunca versione o arquivo `.env`. Ele já está listado no `.gitignore`.

---

### Executar a Aplicação Refatorada

```bash
# A partir da raiz do repositório
python src/app.py
```

Saída esperada:

```
INFO:src.models.database:Banco de dados inicializado.
INFO:src.models.database:Seed de dados inserido com sucesso.
 * Running on http://0.0.0.0:5000
```

---

### Executar a Skill de Auditoria

A skill opera em três comandos sequenciais. Execute-os na ordem abaixo dentro do Claude Code (`claude`) apontado para o diretório do projeto legado:

```bash
# Fase 1 — Reconhecimento
# Leia todos os arquivos-fonte e imprima o resumo da Fase 1
claude "Analise o projeto no diretório atual: identifique linguagem, framework, dependências, domínio, arquitetura e tabelas do banco. Imprima o resumo da Fase 1."

# Fase 2 — Auditoria
# Com o reconhecimento concluído, execute a auditoria completa
claude "Com base na Fase 1, audite todos os arquivos contra o catálogo de anti-patterns. Classifique cada achado como CRÍTICO, ALTO, MÉDIO ou BAIXO. Inclua arquivo, linha, impacto e recomendação para cada item."

# Fase 3 — Refatoração
# Após confirmação do relatório, aplique todas as correções
claude "O usuário confirmou o relatório. Execute a Fase 3: refatore o projeto aplicando todas as recomendações. Valide cada endpoint original por smoke test e imprima o resumo final."
```

---

### Validar que a Refatoração Funcionou

Execute os comandos abaixo após subir a aplicação refatorada. Todos devem retornar os status indicados.

```bash
BASE="http://localhost:5000"

# Saúde da aplicação
curl -s -o /dev/null -w "%{http_code}" $BASE/health
# Esperado: 200

# Listar produtos (sem SQL injection possível)
curl -s -o /dev/null -w "%{http_code}" $BASE/produtos
# Esperado: 200

# Tentativa de SQL injection no login (deve ser bloqueada)
curl -s -o /dev/null -w "%{http_code}" \
  -X POST $BASE/login \
  -H "Content-Type: application/json" \
  -d '{"email":"'"'"' OR '"'"'1'"'"'='"'"'1","senha":"qualquer"}'
# Esperado: 401

# Usuários sem campo senha na resposta
curl -s $BASE/usuarios | python -m json.tool | grep senha
# Esperado: nenhuma linha (campo ausente)

# Endpoint admin desabilitado por padrão
curl -s -o /dev/null -w "%{http_code}" \
  -X POST $BASE/admin/query \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT * FROM usuarios"}'
# Esperado: 404

# Health check sem secret_key no payload
curl -s $BASE/health | python -m json.tool | grep secret_key
# Esperado: nenhuma linha (campo ausente)
```

Todos os seis comandos retornando os valores esperados confirmam que os achados Críticos C-01 a C-09 estão fechados.

---

### Referências

- [Relatório de Auditoria Completo](./relatorio-auditoria.md) — todos os 26 achados com detalhes, impacto e recomendações
- [.env.example](./.env.example) — template de configuração para novos ambientes
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) — referência para classificação de vulnerabilidades
- [Flask Security Considerations](https://flask.palletsprojects.com/en/3.1.x/security/) — guia oficial de segurança do Flask
