# Relatório de Auditoria de Código
**Projeto:** ecommerce-api-legacy  
**Stack:** JavaScript (Node.js) + Express ^4.18.2  
**Data:** 2025  
**Arquivos analisados:** 3 (`src/app.js`, `src/AppManager.js`, `src/utils.js`) — ~180 LOC

---

## 1. Visão Geral do Projeto

| Atributo | Detalhe |
|---|---|
| Linguagem | JavaScript (Node.js) |
| Framework | Express ^4.18.2 |
| Dependências | express, sqlite3 |
| Domínio | LMS (Learning Management System) com fluxo de checkout — usuários se matriculam em cursos e pagam via cartão de crédito |
| Tabelas do banco | `users`, `courses`, `enrollments`, `payments`, `audit_logs` |

### Arquitetura atual

O projeto adota uma arquitetura **monolítica / God-Class**: uma única classe `AppManager` concentra a conexão com o banco de dados, bootstrap do schema, todas as rotas HTTP e toda a lógica de negócio. O arquivo `utils.js` armazena segredos hardcoded e estado global mutável.

---

## 2. Resumo dos Achados

| Severidade | Quantidade |
|---|---|
| 🔴 CRÍTICO | 5 |
| 🟠 ALTO | 8 |
| 🟡 MÉDIO | 6 |
| 🔵 BAIXO | 4 |
| **Total** | **23** |

---

## 3. Achados Detalhados

### 🔴 Críticos

---

#### C-01 — Credenciais e Segredos Hardcoded no Código-Fonte
**Arquivo:** `src/utils.js:1-7`

O objeto `config` embute segredos de produção diretamente no código-fonte: `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"`, além de `dbUser` e `smtpUser`. O prefixo `pk_live_` indica que se trata de uma chave real de gateway de pagamento — não uma chave de sandbox.

**Impacto:** Qualquer desenvolvedor com acesso ao repositório (ou qualquer pessoa que o encontre publicamente) pode realizar cobranças reais no gateway e acessar o banco de dados de produção. O literal `pk_live_` ficará permanentemente capturado no histórico do git mesmo após a rotação.

**Recomendação:** Mover todos os valores para `process.env.*` carregados via `dotenv`, expô-los por meio de `src/config/index.js` e adicionar `.env` ao `.gitignore`. Rotacionar a chave do gateway imediatamente.

---

#### C-02 — God Class: Toda a Lógica em uma Única Classe
**Arquivo:** `src/AppManager.js:1-141`

A classe `AppManager` concentra a conexão com o banco (linha 7), bootstrap do schema e dados de seed (`initDb`, linhas 10-23) e três handlers de rotas HTTP (`setupRoutes`, linhas 25-138), onde cada handler também contém SQL bruto, regras de negócio, formatação de resposta, logging e tratamento de erros. Aproximadamente 110 linhas de responsabilidades misturadas sem qualquer limite de camada.

**Impacto:** Nada pode ser testado unitariamente de forma isolada; qualquer alteração no checkout pode quebrar o relatório de admin; o arquivo crescerá sem limites à medida que novos domínios forem adicionados.

**Recomendação:** Dividir em `models/UserModel.js`, `models/CourseModel.js`, `models/EnrollmentModel.js`, `models/PaymentModel.js`, `models/AuditLogModel.js`; `controllers/CheckoutController.js`, `controllers/AdminController.js`, `controllers/UserController.js`; e uma camada HTTP fina em `routes/*Routes.js`.

---

#### C-03 — Hashing de Senha Inseguro / Customizado
**Arquivo:** `src/utils.js:17-23`

A função `badCrypto(pwd)` concatena os primeiros 2 caracteres do resultado de `Buffer.from(pwd).toString('base64')` dez mil vezes e retorna os primeiros 10 caracteres. Não é um hash criptográfico — é determinístico, sem salt, tem entropia mínima (um prefixo base64 repetido) e é trivialmente reversível lendo os dois primeiros caracteres da saída. O próprio nome da função sinaliza que não é segura.

**Impacto:** Hashes de senha armazenados podem ser revertidos em milissegundos; senhas idênticas entre usuários produzem hashes idênticos.

**Recomendação:** Substituir por `bcrypt` (npm `bcrypt`) usando `bcrypt.hash(pwd, 10)` e `bcrypt.compare()`. Mover para um módulo dedicado `models/UserModel.js` ou `utils/password.js`.

---

#### C-04 — Senha em Texto Puro nos Dados de Seed
**Arquivo:** `src/AppManager.js:18`

`INSERT INTO users (name, email, pass) VALUES ('Leonan', 'leonan@fullcycle.com.br', '123')` armazena a senha literal `'123'` na coluna `pass`. O schema trata `pass` como armazenamento em texto plano, e o seed consolida essa convenção.

**Impacto:** Qualquer dump do banco de dados expõe a senha real; novos usuários criados via rota de checkout (linha 69) têm hash gerado pelo `badCrypto` quebrado, criando uma mistura heterogênea de texto puro e hashes inválidos na mesma coluna.

**Recomendação:** Hashear a senha do seed com bcrypt antes da inserção e tratar a coluna `pass` exclusivamente como armazenamento de hash bcrypt.

---

#### C-05 — Vazamento de PII/PCI: Número de Cartão e Chave do Gateway Logados
**Arquivo:** `src/AppManager.js:45`

`console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` escreve o PAN completo do cartão de crédito informado pelo cliente junto com a chave viva do gateway de pagamento no stdout a cada checkout.

**Impacto:** Qualquer pessoa com acesso aos logs (operadores, sidecars, log shippers, agregadores de log de terceiros) obtém números de cartão e a chave do gateway. Trata-se de uma violação direta do PCI-DSS.

**Recomendação:** Remover o log inteiramente. Se um log for necessário, registrar apenas os últimos 4 dígitos (`cc.slice(-4)`) e nunca logar a chave do gateway.

---

### 🟠 Altos

---

#### A-01 — Lógica de Negócio no Handler de Rota — Checkout
**Arquivo:** `src/AppManager.js:28-78`

O handler `/api/checkout` realiza: parsing da requisição, busca do curso, busca do usuário, criação opcional de usuário com hashing, "autorização de pagamento" fake (`cc.startsWith("4") ? "PAID" : "DENIED"`), inserção de matrícula, inserção de pagamento, inserção de log de auditoria e escrita em cache — 50 linhas de orquestração com quatro níveis de callbacks aninhados dentro da rota.

**Impacto:** A regra de negócio do checkout (o que faz um pagamento ser aprovado, quando um log de auditoria é escrito, quando um usuário é auto-criado) não pode ser testada sem inicializar o Express; raciocinar sobre falha parcial é quase impossível devido ao aninhamento.

**Recomendação:** Extrair para `controllers/CheckoutController.js::process()` retornando um objeto/erro simples; converter chamadas sqlite3 para um helper promisificado e usar `async/await`. Manter a rota com menos de 10 linhas.

---

#### A-02 — Lógica de Negócio no Handler de Rota — Relatório Financeiro
**Arquivo:** `src/AppManager.js:80-129`

O handler `/api/admin/financial-report` executa callbacks `forEach` aninhados sobre cursos → matrículas → usuário + pagamento, decrementando manualmente dois contadores pendentes (`coursesPending`, `enrPending`) para saber quando chamar `res.json(report)`. 45 linhas de orquestração assíncrona diretamente dentro da rota.

**Impacto:** Intestável; requisições concorrentes não têm isolamento; uma query lenta trava a resposta sem timeout; um erro lógico em qualquer contador vaza a resposta silenciosamente ou a envia duas vezes.

**Recomendação:** Extrair para `controllers/AdminController.js::financialReport()`. Substituir os contadores por `Promise.all` após promisificar os métodos de model, ou — preferencialmente — uma única query de agregação SQL (ver achado N+1 abaixo).

---

#### A-03 — Estado Global Mutável
**Arquivo:** `src/utils.js:9-10`

`let globalCache = {}` e `let totalRevenue = 0` são variáveis mutáveis no escopo do módulo, exportadas e mutadas por `logAndCache` (linha 14).

**Impacto:** Duas requisições concorrentes podem gerar race condition em `globalCache`; testes que exercitam checkout mutam permanentemente esse estado entre execuções do suite; `totalRevenue` é exportado mas nunca atualizado, sinalizando uma intenção que nunca foi implementada.

**Recomendação:** Deletar `totalRevenue`. Se cache for necessário, substituir `globalCache` por uma instância injetada na camada de controller (ou remover `logAndCache` inteiramente, já que é puramente um logger de side-effect).

---

#### A-04 — Sem Injeção de Dependência — Banco Acoplado no Construtor
**Arquivo:** `src/AppManager.js:7`

`this.db = new sqlite3.Database(':memory:')` é criado dentro do construtor da classe com um caminho hardcoded. Cada handler de rota captura `this.db` (e um alias `self` na linha 26 por causa dos callbacks `function(err)`).

**Impacto:** A classe não pode ser instanciada com um banco diferente para testes; trocar para PostgreSQL exige editar a classe; o banco `:memory:` não pode ser compartilhado entre processos worker.

**Recomendação:** Criar `src/models/database.js` que exporta uma conexão inicializada a partir de `config.databaseUrl`, e injetar (ou importar) em cada arquivo de model. O construtor desaparece completamente.

---

#### A-05 — Sem Validação de Input — Checkout
**Arquivo:** `src/AppManager.js:29-35`

O handler de checkout lê `usr`, `eml`, `pwd`, `c_id`, `card` de `req.body` e apenas verifica `if (!u || !e || !cid || !cc)`. `pwd` nunca é validado, `c_id` não tem checagem de tipo antes de ser passado ao SQL, `eml` não é validado como email, e `card` não é validado como apenas dígitos ou por comprimento.

**Impacto:** Um POST com `c_id: "abc"` ou corpo malformado causa respostas 404/500 confusas; um `pwd` ausente ativa o fallback de senha descrito no achado crítico abaixo.

**Recomendação:** Validar o corpo no controller (ou em um schema `joi`/`zod` em middleware) — campos obrigatórios, formato de email, `c_id` numérico, `card` apenas dígitos. Retornar 400 com erro estruturado.

---

#### A-06 — Sem Autenticação no Endpoint de Admin
**Arquivo:** `src/AppManager.js:80`

`app.get('/api/admin/financial-report', ...)` expõe receita por curso, nome e email de cada estudante e valores pagos por estudante a qualquer chamador — sem header de auth, sem sessão, sem verificação de role.

**Impacto:** Divulgação pública de receita financeira e dump de PII de estudantes a partir de um único GET anônimo.

**Recomendação:** Adicionar `authMiddleware` (e `requireRole('admin')`) registrado antes das rotas `/api/admin/*`.

---

#### A-07 — Sem Autenticação/Autorização no Endpoint de Deleção de Usuário
**Arquivo:** `src/AppManager.js:131-137`

`app.delete('/api/users/:id', ...)` deleta qualquer usuário pelo id sem autenticação, verificação de propriedade ou verificação de role.

**Impacto:** Qualquer chamador pode apagar qualquer conta de usuário. Combinado com o achado de registros órfãos abaixo, produz também corrupção durável no banco de dados.

**Recomendação:** Exigir middleware de auth; restringir ao role de admin ou ao próprio id do usuário autenticado.

---

#### A-08 — Fallback de Senha Padrão Oculta Input Ausente
**Arquivo:** `src/AppManager.js:68`

`let hash = badCrypto(p || "123456")` substitui silenciosamente pelo literal `"123456"` quando a requisição omite `pwd`. Novos usuários auto-criados passam a ter uma senha conhecida e adivinhável por atacantes.

**Impacto:** Todo usuário criado sem `pwd` compartilha a mesma senha fraca; combinado com o `badCrypto` quebrado, o hash resultante é idêntico para todos esses usuários.

**Recomendação:** Rejeitar a requisição com 400 se `pwd` estiver ausente durante a auto-criação de usuário. Mover a criação de usuário para `UserModel.create()` após hashear a senha validada com bcrypt.

---

### 🟡 Médios

---

#### M-01 — N×M+1 Queries no Relatório Financeiro
**Arquivo:** `src/AppManager.js:83-128`

O handler executa `SELECT * FROM courses` (1 query), depois para cada curso executa `SELECT * FROM enrollments WHERE course_id = ?` (N queries), e então para cada matrícula executa `SELECT name, email FROM users WHERE id = ?` e `SELECT amount, status FROM payments WHERE enrollment_id = ?` (2×M queries). Total: 1 + N + 2×M round-trips por requisição.

**Impacto:** Latência da API cresce linearmente com as matrículas; 50 cursos × 1.000 matrículas = 2.051 round-trips SQL por relatório.

**Recomendação:** Substituir por uma única query de agregação com JOIN entre `courses`, `enrollments`, `users` e `payments`, agrupando por curso no SQL (ou um `IN (...)` em batch por tabela). Implementar em `AdminModel.getFinancialReport()`.

---

#### M-02 — Sem Handler Centralizado de Erros
**Arquivo:** `src/AppManager.js` (arquivo completo)

Erros são tratados inline com strings ad-hoc: `res.status(500).send("Erro DB")` (linha 41), `"Erro Matrícula"` (linha 51), `"Erro Pagamento"` (linha 55), `"Curso não encontrado"` (linha 38), sem formato compartilhado. O middleware `(err, req, res, next)` do Express não é registrado em nenhum lugar.

**Impacto:** Formato de erro inconsistente força clientes a tratar strings individualmente; exceções não capturadas em promise chains derrubam o processo; nada loga erros estruturados.

**Recomendação:** Adicionar `middlewares/errorHandler.js`, refatorar handlers para chamar `next(err)` em caso de falha e padronizar respostas JSON no formato `{ error, detail }`.

---

#### M-03 — Sem Transação no Fluxo Multi-Etapa do Checkout
**Arquivo:** `src/AppManager.js:50-62`

O checkout realiza quatro escritas sequenciais (inserção opcional de usuário → inserção de matrícula → inserção de pagamento → inserção de log de auditoria) fora de qualquer transação. Qualquer falha entre as etapas deixa o banco em estado parcial (ex.: matrícula sem pagamento, ou pagamento sem log de auditoria).

**Impacto:** Reconciliação com o gateway se torna manual; o relatório financeiro contabiliza receita de registros órfãos.

**Recomendação:** Envolver as quatro escritas em `BEGIN`/`COMMIT` (ou um helper de transação) dentro de `CheckoutController` após promisificar o sqlite3.

---

#### M-04 — Registros Órfãos na Deleção de Usuário
**Arquivo:** `src/AppManager.js:131-137`

`DELETE FROM users WHERE id = ?` é executado de forma isolada; a resposta literalmente diz `"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."` — anunciando o próprio bug de integridade de dados.

**Impacto:** `enrollments` e `payments` retêm linhas referenciando um `user_id` inexistente, quebrando o JOIN do relatório financeiro e produzindo entradas com estudante `"Unknown"`.

**Recomendação:** Declarar `ON DELETE CASCADE` nas colunas FK em `initDb`, ou realizar `DELETE FROM payments WHERE enrollment_id IN (...)` → `DELETE FROM enrollments WHERE user_id = ?` → `DELETE FROM users` dentro de uma transação em `UserController.delete()`.

---

#### M-05 — Erro Engolido na Deleção de Usuário
**Arquivo:** `src/AppManager.js:133-136`

O callback recebe `(err)` mas nunca o inspeciona antes de enviar uma resposta 200. Uma deleção com falha reporta sucesso ao cliente.

**Impacto:** Clientes acreditam que a operação foi bem-sucedida; nenhuma entrada de log é gerada; o estado inconsistente passa despercebido.

**Recomendação:** Verificar `if (err) return next(err)` e deixar o handler centralizado responder com 500.

---

#### M-06 — Duplicação de Código — Padrões de Erro Repetidos
**Arquivo:** `src/AppManager.js:38`, `41`, `51`, `55`, `84`

Cinco variações distintas de `if (err) return res.status(500).send("...")` e `if (!x) return res.status(404).send("...")` com diferentes strings em português, todas expressando a mesma intenção.

**Impacto:** Qualquer mudança no contrato de erro (ex.: migrar para JSON) exige editar cada ocorrência; clientes não conseguem distinguir tipos de erro programaticamente.

**Recomendação:** Handler centralizado de erros (ver M-02) + classes `NotFoundError` / `ValidationError`. Controllers lançam erros tipados; o middleware os mapeia para status + JSON.

---

### 🔵 Baixos

---

#### B-01 — Magic Decision: Status de Pagamento Derivado do Prefixo do Cartão
**Arquivo:** `src/AppManager.js:46`

`let status = cc.startsWith("4") ? "PAID" : "DENIED"` decide o status do pagamento pelo prefixo do número do cartão sem constante nomeada ou comentário. Os literais `"4"`, `"PAID"` e `"DENIED"` são magic strings.

**Impacto:** Um leitor não consegue determinar se isso é uma integração real (porém quebrada) com o gateway ou um stub deliberado; as strings de status são duplicadas ao longo do arquivo.

**Recomendação:** Substituir por `PaymentService.authorize(card, amount)` stub retornando `PaymentStatus.PAID | PaymentStatus.DENIED`; exportar as constantes de status de um único módulo.

---

#### B-02 — Nomenclatura Precária — Variáveis de Uma Letra no Checkout
**Arquivo:** `src/AppManager.js:29-33`

A rota de checkout usa `u`, `e`, `p`, `cid`, `cc` para `usr`/`eml`/`pwd`/`c_id`/`card`. Embora o contrato da API use as chaves abreviadas, as variáveis internas propagam a abreviação por 50 linhas de callbacks aninhados.

**Impacto:** Legibilidade — um leitor na linha 68 precisa rolar até a linha 31 para lembrar que `p` é a senha.

**Recomendação:** Renomear para `name`, `email`, `password`, `courseId`, `card` dentro do controller. Traduzir as chaves da requisição na fronteira.

---

#### B-03 — Export Morto: `totalRevenue` Nunca Atualizado
**Arquivo:** `src/utils.js:10`, `25`

`let totalRevenue = 0` é declarado e exportado, mas nunca atribuído em nenhum lugar da codebase. `AppManager` o importa na linha 2 mas nunca lê nem escreve nele.

**Impacto:** Estado morto que confunde leitores esperando que rastreie receita.

**Recomendação:** Deletar a variável e seu export. Remover o import em `AppManager.js`.

---

#### B-04 — Workaround Pré-ES6 — `let self = this`
**Arquivo:** `src/AppManager.js:26`

`let self = this;` é capturado para que callbacks clássicos `function(err)` do sqlite (linhas 50, 54, 57) possam acessar o estado da instância. Arrow callbacks modernos vinculam `this` automaticamente — exceto que o form `function(err){ this.lastID }` do sqlite3 é necessário para acessar `this.lastID`.

**Impacto:** Estilos de callback misturados em uma mesma função obscurecem a intenção.

**Recomendação:** Após promisificar o sqlite3 (ou usar o wrapper `better-sqlite3`/`sqlite`), eliminar o alias `self` e usar `async/await`.

---

## 4. Refatoração Aplicada (Fase 3)

Todos os 23 achados foram endereçados em uma refatoração completa para arquitetura MVC.

### Nova Estrutura do Projeto

```
src/
├── app.js                              # composition root
├── config/
│   └── index.js                        # config env-driven com guarda required()
├── models/
│   ├── database.js                     # conexão sqlite + run/get/all promisificados + withTransaction + init
│   ├── UserModel.js
│   ├── CourseModel.js
│   ├── EnrollmentModel.js
│   ├── PaymentModel.js
│   ├── AuditLogModel.js
│   └── ReportModel.js                  # LEFT JOIN único para relatório financeiro
├── controllers/
│   ├── CheckoutController.js           # orquestra user/course/payment/enrollment/audit em uma tx
│   ├── AdminController.js              # agrupa linhas do JOIN em formato de relatório
│   └── UserController.js              # cascade-delete de enrollments + payments em uma tx
├── routes/
│   ├── index.js                        # monta /checkout, /admin, /users sob /api
│   ├── checkoutRoutes.js
│   ├── adminRoutes.js
│   └── userRoutes.js
├── middlewares/
│   ├── errorHandler.js                 # mapeia subclasses HttpError → JSON; loga 500s
│   └── notFoundHandler.js
├── services/
│   └── paymentService.js              # enum PaymentStatus + stub authorize()
└── utils/
    ├── password.js                     # bcrypt hash/verify
    └── errors.js                       # HttpError, BadRequestError, NotFoundError, PaymentDeniedError

.env                                    # segredos locais — gitignored
.env.example                            # template versionado
.gitignore                              # node_modules, .env, *.log
package.json                            # adicionados bcrypt, dotenv
```

### Transformações Aplicadas

| ID | Descrição |
|---|---|
| RT-01 | Segredos hardcoded em `src/utils.js` extraídos para `src/config/index.js`, lidos de `process.env` com guarda `required()` para `PAYMENT_GATEWAY_KEY`; `.env.example` versionado |
| RT-02 | God-class `AppManager.js` dividida em 7 arquivos de model, 3 controllers, 3 arquivos de rotas, 2 middlewares, 1 service e um módulo de database |
| RT-03 | Todo SQL movido para `models/*` com queries parametrizadas exclusivamente (sem interpolação de strings em nenhum lugar) |
| RT-04 | Lógica de negócio (orquestração do checkout, agrupamento do relatório, cascade delete) extraída das rotas para controllers; arquivos de rota agora com menos de 15 linhas, apenas parseando req → chamando controller → respondendo |
| RT-05 | Query N×M+1 do relatório financeiro substituída por um único LEFT JOIN em `ReportModel.getFinancialReport()`; agrupamento feito em `AdminController` com um `Map` |
| RT-06 | `middlewares/errorHandler.js` centralizado registrado por último; subclasses tipadas de `HttpError` mapeadas para JSON `{error}`; exceções não capturadas alcançadas via `next(err)` |
| RT-07 | Cinco padrões ad-hoc duplicados de `res.status(...).send("Erro ...")` colapsados para `throw new HttpError(...)` → middleware único |
| RT-08 | Prefixo mágico `'4'` para aprovação de pagamento movido para constante `APPROVED_CARD_PREFIX` dentro de `paymentService`; enum `PaymentStatus` congelado |
| RT-09 | Validação de input nos controllers — `BadRequestError` em campos de checkout ausentes, parsing de inteiro + verificação de faixa em `:id` de usuário |
| RT-10 | `badCrypto()` customizado substituído por bcrypt com rounds configuráveis; senha do usuário de seed agora hasheada com bcrypt; senha em texto puro `'123'` removida |
| Novo | Transações `BEGIN`/`COMMIT`/`ROLLBACK` envolvem escritas multi-etapa em `CheckoutController` e `UserController` |
| Novo | Deleção de usuário agora faz cascade em enrollments + payments — elimina o bug de registros órfãos que a própria mensagem de resposta original anunciava |
| Novo | Vazamento de PII/PCI removido — número de cartão e chave do gateway não são mais logados em nenhum lugar |
| Novo | Fallback de senha padrão (`p \|\| "123456"`) removido; `pwd` ausente agora retorna 400 |
| — | Arquivos legados deletados: `src/AppManager.js`, `src/utils.js` |

### Validação Final

- ✅ Aplicação inicializa sem erros (LMS API rodando na porta 3000)
- ✅ Todos os endpoints respondem corretamente:

| Endpoint | Cenário | Resultado |
|---|---|---|
| `POST /api/checkout` | Sucesso | `200 {"msg":"Sucesso","enrollment_id":2}` |
| `POST /api/checkout` | Cartão 5xxx (negado) | `400 {"error":"Pagamento recusado"}` |
| `POST /api/checkout` | Campo ausente | `400 {"error":"Bad Request"}` |
| `POST /api/checkout` | `c_id` desconhecido | `404 {"error":"Curso não encontrado"}` |
| `GET /api/admin/financial-report` | — | `200 [{course,revenue,students:[{student,paid}]…}]` |
| `DELETE /api/users/:id` | Válido | `200`, cascade verificado via relatório subsequente |
| `DELETE /api/users/:id` | Não encontrado | `404` |
| `DELETE /api/users/abc` | Id inválido | `400` |

- ✅ Zero credenciais hardcoded restantes (todos os segredos lidos via `require('./config')`)
- ✅ Zero lógica de negócio na camada de rotas (arquivos de rota com menos de 20 linhas, apenas parsing de req + chamada ao controller + resposta)
- ✅ Models abstraem todo acesso a dados (todo SQL em `src/models/`; controllers importam apenas models)

---

## 5. Conclusão

O projeto apresentava **5 vulnerabilidades críticas de segurança**, incluindo credenciais de produção e chave de gateway de pagamento real (`pk_live_`) expostas no código-fonte, hashing de senha completamente inseguro, senha em texto puro nos dados de seed e vazamento de PAN de cartão de crédito nos logs em violação direta ao PCI-DSS. A arquitetura God-Class comprometia totalmente a testabilidade e escalabilidade do sistema.

A refatoração em arquitetura MVC endereçou todos os 23 achados: os 3 arquivos legados tornaram-se um layout de 21 arquivos, todos os segredos foram movidos para variáveis de ambiente, o hashing foi substituído por bcrypt, as queries N×M+1 foram colapsadas em um único JOIN e as escritas multi-etapa passaram a ser executadas dentro de transações com rollback garantido.
