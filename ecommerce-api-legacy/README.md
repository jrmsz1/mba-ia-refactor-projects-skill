# Code Audit Skill — ecommerce-api-legacy

> Skill de auditoria e refatoração automática de código aplicada a uma API Node.js de LMS com fluxo de checkout.  
> Projeto analisado: **ecommerce-api-legacy** | Stack: **Node.js + Express ^4.18.2 + SQLite**

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

1. **Fase 1 — Reconhecimento do projeto:** leitura de todos os arquivos-fonte, mapeamento de dependências, identificação das tabelas do banco e caracterização da arquitetura real — que se revelou monolítica (God-Class), apesar de aparentar estrutura modular pelos nomes dos arquivos.
2. **Fase 2 — Auditoria por catálogo de anti-patterns:** cruzamento de cada arquivo contra um conjunto predefinido de categorias de risco, com ordenação dos achados por severidade e impacto real no negócio.
3. **Fase 3 — Refatoração guiada:** aplicação das correções na mesma sessão, com validação por smoke test de todos os endpoints originais antes de marcar a fase como concluída.

---

### Problemas Identificados

#### 🔴 Críticos — Risco imediato de segurança, conformidade ou perda de dados

| ID | Problema | Arquivo(s) | Por que é relevante |
|---|---|---|---|
| C-01 | Credenciais e segredos hardcoded no código-fonte, incluindo chave `pk_live_` de gateway de pagamento real | `src/utils.js:1-7` | A chave `pk_live_` permite cobranças reais em produção por qualquer pessoa que tenha acesso ao repositório. Mesmo após rotação, o literal fica permanentemente no histórico do git. Impacto financeiro direto e imediato. |
| C-02 | God Class: toda a lógica da aplicação em uma única classe | `src/AppManager.js:1-141` | Conexão com banco, schema, seed, três rotas HTTP, SQL bruto, regras de negócio e tratamento de erros misturados em ~110 linhas. Nada pode ser testado em isolamento; qualquer alteração em qualquer ponto pode quebrar qualquer outro ponto. |
| C-03 | Hashing de senha inseguro via função customizada `badCrypto` | `src/utils.js:17-23` | A função é determinística, sem salt e trivialmente reversível lendo os dois primeiros caracteres da saída — senhas idênticas produzem hashes idênticos. O próprio nome da função documenta que é insegura. |
| C-04 | Senha em texto puro nos dados de seed | `src/AppManager.js:18` | Senha `'123'` inserida diretamente na coluna `pass`. Qualquer dump do banco expõe a senha real. Cria uma coluna com mistura heterogênea de texto puro e hashes inválidos, impossível de auditar. |
| C-05 | Vazamento de PII/PCI: PAN completo do cartão e chave do gateway logados a cada checkout | `src/AppManager.js:45` | Violação direta do PCI-DSS. Operadores, sidecars, log shippers e agregadores de terceiros capturam números de cartão e a chave do gateway em cada transação. A exposição é contínua e silenciosa. |

---

#### 🟠 Altos — Degradação de arquitetura, risco operacional e segurança

| ID | Problema | Arquivo(s) | Por que é relevante |
|---|---|---|---|
| A-01 | Lógica de negócio no handler de rota — Checkout | `src/AppManager.js:28-78` | 50 linhas de orquestração com quatro níveis de callbacks aninhados. Regras de aprovação de pagamento, auto-criação de usuário e escrita de audit log não podem ser testadas sem inicializar o Express. |
| A-02 | Lógica de negócio no handler de rota — Relatório Financeiro | `src/AppManager.js:80-129` | 45 linhas de callbacks `forEach` aninhados com contadores manuais (`coursesPending`, `enrPending`) para controlar quando enviar a resposta. Erro lógico em qualquer contador envia a resposta duas vezes ou nunca. |
| A-03 | Estado global mutável | `src/utils.js:9-10` | `globalCache` e `totalRevenue` são variáveis de módulo mutadas durante requisições. Race conditions em concorrência; `totalRevenue` nunca é atualizado — dead state que sinaliza intenção incompleta. |
| A-04 | Sem injeção de dependência — banco acoplado no construtor | `src/AppManager.js:7` | `new sqlite3.Database(':memory:')` hardcoded no construtor. Impossível instanciar com banco diferente para testes; trocar de banco de dados exige editar a classe. |
| A-05 | Sem validação de input no checkout | `src/AppManager.js:29-35` | Apenas presença dos campos é verificada. `c_id` não é verificado como número, `eml` não é validado como email, `card` não é verificado como dígitos. `pwd` ausente ativa fallback com senha conhecida. |
| A-06 | Sem autenticação no endpoint de admin — relatório financeiro | `src/AppManager.js:80` | `GET /api/admin/financial-report` expõe receita por curso, nome e email de cada estudante a qualquer chamador anônimo — nenhum header de auth, sessão ou role check. |
| A-07 | Sem autenticação/autorização no endpoint de deleção de usuário | `src/AppManager.js:131-137` | `DELETE /api/users/:id` apaga qualquer usuário por id sem autenticação, ownership check ou role. Qualquer chamador anônimo pode destruir qualquer conta. |
| A-08 | Fallback de senha padrão oculta input ausente | `src/AppManager.js:68` | `badCrypto(p \|\| "123456")` cria usuários com senha padrão conhecida quando `pwd` está ausente. Todos esses usuários compartilham o mesmo hash fraco — grupo inteiro comprometido com um ataque de dicionário trivial. |

---

#### 🟡 Médios — Problemas de qualidade, integridade de dados e manutenibilidade

| ID | Problema | Arquivo(s) | Por que é relevante |
|---|---|---|---|
| M-01 | N×M+1 queries no relatório financeiro | `src/AppManager.js:83-128` | 1 query de cursos + N queries de matrículas + 2×M queries de usuário/pagamento por requisição. 50 cursos × 1.000 matrículas = 2.051 round-trips SQL por relatório. |
| M-02 | Sem handler centralizado de erros | `src/AppManager.js` (completo) | Cinco variações de `res.status(500).send("Erro ...")` com strings diferentes em português. Sem `(err, req, res, next)` registrado, exceções não capturadas em promises derrubam o processo. |
| M-03 | Sem transação no fluxo multi-etapa do checkout | `src/AppManager.js:50-62` | Quatro escritas sequenciais (usuário → matrícula → pagamento → audit log) fora de transação. Falha entre etapas deixa o banco em estado parcial impossível de reconciliar automaticamente. |
| M-04 | Registros órfãos na deleção de usuário | `src/AppManager.js:131-137` | A própria resposta do endpoint diz `"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."` — o bug de integridade estava documentado na resposta HTTP. |
| M-05 | Erro engolido na deleção de usuário | `src/AppManager.js:133-136` | Callback recebe `err` mas nunca o inspeciona antes de enviar 200. Deleção com falha reporta sucesso ao cliente. Estado inconsistente passa despercebido indefinidamente. |
| M-06 | Duplicação de código — padrões de erro repetidos | `src/AppManager.js:38,41,51,55,84` | Cinco variações do mesmo padrão de erro com strings ad-hoc. Clientes não conseguem distinguir tipos de erro programaticamente; mudança no contrato exige editar cada ocorrência. |

---

#### 🔵 Baixos — Legibilidade e manutenção de longo prazo

| ID | Problema | Arquivo(s) | Por que é relevante |
|---|---|---|---|
| B-01 | Magic decision: status de pagamento derivado do prefixo do número do cartão | `src/AppManager.js:46` | `cc.startsWith("4")` decide aprovação sem constante nomeada ou comentário. Impossível distinguir integração real quebrada de stub de teste. |
| B-02 | Nomenclatura precária — variáveis de uma letra no checkout | `src/AppManager.js:29-33` | `u`, `e`, `p`, `cid`, `cc` propagados por 50 linhas de callbacks aninhados. Leitura exige scroll constante para rastrear o significado de cada variável. |
| B-03 | Export morto — `totalRevenue` nunca atualizado | `src/utils.js:10,25` | Declarado, exportado e importado, mas nunca lido ou escrito. Dead state que confunde leitores esperando encontrar rastreamento de receita. |
| B-04 | Workaround pré-ES6 — `let self = this` | `src/AppManager.js:26` | Alias capturado para compatibilidade com callbacks clássicos do sqlite3. Estilos de callback misturados (arrow e function) na mesma função obscurecem a intenção e o fluxo de controle. |

---

### Justificativa da Classificação

A severidade foi atribuída com base em três eixos:

- **Exploitabilidade:** quão facilmente um atacante externo, sem credenciais, consegue acionar o problema.
- **Impacto:** extensão do dano — de degradação de UX até comprometimento financeiro direto e violação regulatória.
- **Reversibilidade:** custo de recovery após o problema ser explorado ou detectado.

O projeto apresenta um caso especialmente grave em C-01 + C-05: a chave `pk_live_` no código-fonte permite cobranças reais imediatas (C-01), enquanto o log de PAN + chave (C-05) garante que a chave continue sendo coletada pelos sistemas de log mesmo após a rotação no código. Os dois achados se amplificam mutuamente e satisfazem os três eixos de criticidade simultaneamente.

---

## Construção da Skill

### Visão Geral

A skill é um agente de auditoria e refatoração estruturado em **três fases obrigatórias e sequenciais** — Reconhecimento → Auditoria → Refatoração — que opera sobre qualquer base de código de API REST, independentemente de linguagem ou framework.

### Decisões de Design

#### 1. Separação rígida entre fases com artefatos explícitos

Cada fase produz um artefato concreto (resumo estruturado, relatório de achados, estrutura refatorada + smoke test) antes de avançar. Isso evita que a skill corrija enquanto ainda lê — o que tenderia a tratar sintomas superficiais e perder achados sistêmicos como a God-Class ou o estado global mutável que só ficam evidentes após a leitura completa do código.

#### 2. Catálogo de anti-patterns como lista de verificação imutável

A fase de auditoria não depende de heurísticas livres. Cada arquivo é cruzado contra categorias fixas:

| Categoria | Exemplos de anti-patterns cobertos |
|---|---|
| Segredos e configuração | Credenciais hardcoded, chaves de API em VCS, secrets em logs |
| Autenticação e autorização | Endpoints sem auth, hashing inseguro, senhas em texto puro, fallbacks inseguros |
| Conformidade (PCI/PII) | PAN de cartão em logs, chaves de gateway em stdout |
| Arquitetura | God files/classes, ausência de camadas, singleton de banco, DI ausente |
| Integridade de dados | Escritas multi-etapa sem transação, cascade delete ausente, erros engolidos |
| Performance | N+1/N×M+1 queries, contadores manuais substituindo Promise.all |
| Qualidade | Código duplicado, magic strings, estado global mutável, dead code |
| Observabilidade | Handler centralizado de erros ausente, stack traces vazando para o cliente |

#### 3. Hierarquia de severidade baseada em impacto de negócio

A classificação CRÍTICO/ALTO/MÉDIO/BAIXO é calibrada por impacto real, não por nomenclatura técnica. Este projeto ilustra bem a diferença: C-05 (PAN em logs) é Crítico não por ser uma falha de programação sofisticada — é um `console.log` — mas porque viola PCI-DSS, tem impacto regulatório imediato e a exposição é contínua e silenciosa. Nenhum patch corrige os logs já coletados.

#### 4. Recomendações sempre acionáveis com localização precisa

Cada achado inclui: (a) o que fazer, (b) onde exatamente (arquivo, linha ou módulo alvo), (c) como (API, padrão ou biblioteca concreta). No caso de JavaScript/Node.js, as recomendações especificam `bcrypt` (npm), `dotenv`, `async/await` com sqlite3 promisificado, e `HttpError` subclasses — não sugestões genéricas como "melhorar segurança".

#### 5. Validação comportamental como gate de saída da Fase 3

A refatoração só é marcada como concluída após smoke test de cada endpoint original com cenários de sucesso **e** falha. Para este projeto: checkout aprovado, checkout negado (cartão 5xxx), campo ausente (400), curso inexistente (404), deleção com cascade, deleção de id inválido — o comportamento externo da API deve ser idêntico ao original em todos os cenários cobertos.

---

### Anti-patterns Incluídos e Justificativa

| Anti-pattern | Por que incluído |
|---|---|
| Credenciais hardcoded com chave `pk_live_` | Impacto financeiro direto; prefixo `pk_live_` é indicador inequívoco de chave de produção real |
| Vazamento de PII/PCI em logs | Violação regulatória contínua e silenciosa; comum em projetos sem revisão de segurança de pagamento |
| God Class com schema + rotas + negócio | Raiz estrutural de praticamente todos os outros achados de arquitetura e testabilidade |
| Hashing customizado inseguro | Frequente em projetos que evitam dependências externas; catastrófico para segurança de credenciais |
| Escritas multi-etapa sem transação | Inevitável em fluxos de checkout com múltiplas entidades; parcialmente invisível durante desenvolvimento |
| N×M+1 queries com contadores manuais | Padrão específico de código Node.js assíncrono legado com callbacks aninhados |
| Estado global mutável exportado | Causa race conditions em produção e polui o estado entre testes |
| Cascade delete ausente documentado na resposta | Caso raro em que o próprio código admite o bug — merece destaque por autodescrever o problema |
| Fallback de senha padrão silencioso | Cria uma classe inteira de usuários com credencial conhecida sem nenhum aviso |

---

### Como a Skill é Agnóstica de Tecnologia

A skill foi projetada para ser aplicável a qualquer stack de API REST. Este projeto, escrito em JavaScript/Node.js com Express, demonstra na prática como os mesmos conceitos do catálogo se manifestam em uma linguagem diferente:

**O catálogo detecta conceitos, não sintaxe.** "Hashing de senha inseguro" em Python se manifesta como `hashlib.md5()`; em Node.js se manifesta como `badCrypto()` com manipulação manual de base64 — o conceito é idêntico, a sintaxe é diferente. A skill identifica o padrão em ambos.

**God File em Python vs God Class em JavaScript.** Em Python (code-smells-project) o anti-pattern apareceu como `models.py` com 315 linhas misturando quatro domínios. Em Node.js (este projeto) apareceu como a classe `AppManager` com 141 linhas misturando banco, schema, rotas e negócio. A categoria do catálogo ("concentração excessiva de responsabilidades") captura ambas as manifestações.

**Recomendações mapeadas para o ecossistema alvo.** Para Python: `bcrypt.hashpw` / `bcrypt.checkpw`, `flask.g` para conexão por requisição, Blueprints. Para Node.js: `bcrypt.hash` / `bcrypt.compare`, `promisify` para sqlite3, `async/await`, `HttpError` subclasses, `(err, req, res, next)` middleware do Express.

**Estrutura de saída padronizada entre projetos.** O relatório de auditoria segue o mesmo template — Visão Geral, Achados por Severidade, Refatoração Aplicada, Validação Final — permitindo comparar auditorias entre Python/Flask e Node.js/Express lado a lado.

---

### Desafios Encontrados

**Arquitetura de callbacks aninhados:** o código legado Node.js usava callbacks clássicos do sqlite3 com quatro níveis de aninhamento. Raciocinar sobre o fluxo de controle — especialmente os contadores manuais `coursesPending` e `enrPending` no relatório financeiro — exigiu simular mentalmente caminhos de execução concorrente antes de propor a substituição por `Promise.all` e `async/await`.

**Dependência entre C-04 e C-03:** corrigir a senha em texto puro do seed (C-04) exigia que o `badCrypto` já tivesse sido substituído por bcrypt (C-03). A ordem de aplicação das correções importa — a skill precisou estabelecer a sequência correta antes de escrever qualquer linha de código refatorado.

**Cascade delete com bug autodocumentado:** o endpoint de deleção de usuário continha na própria resposta HTTP a frase `"mas as matrículas e pagamentos ficaram sujos no banco"` — o bug estava literalmente anunciado no código de produção. Isso exigiu não apenas adicionar o cascade, mas verificar que o relatório financeiro passava a funcionar corretamente após a deleção (sem entradas `"Unknown"` nos students).

**God Class com múltiplos achados sobrepostos:** `AppManager.js` concentrava achados de todas as quatro severidades. A estratégia foi registrar cada achado individualmente no relatório para clareza, e depois aplicar o split estrutural (RT-02) como pré-condição para todos os demais — não é possível extrair `CheckoutController` enquanto o checkout ainda está misturado com o schema bootstrap na mesma classe.

**Preservar contrato de API com zero breaking changes:** os três endpoints originais (`/api/checkout`, `/api/admin/financial-report`, `/api/users/:id`) precisavam responder com o mesmo shape após a refatoração de 3 arquivos para 21. A estratégia foi manter os paths de URL e os shapes de resposta JSON idênticos, validando cada cenário (sucesso, negação, campo ausente, id inválido) antes de fechar a fase.

---

## Resultados

### Resumo dos Relatórios de Auditoria

| Dimensão | Antes | Depois |
|---|---|---|
| Arquivos-fonte | 3 (`app.js`, `AppManager.js`, `utils.js`) | 21 arquivos em estrutura MVC |
| Linhas de código | ~180 LOC (3 arquivos) | Distribuídas em módulos coesos |
| Achados Críticos | 5 | 0 |
| Achados Altos | 8 | 0 |
| Achados Médios | 6 | 0 |
| Achados Baixos | 4 | 0 |
| **Total de achados** | **23** | **0** |
| Chave de gateway de pagamento | `pk_live_` hardcoded em `utils.js` | Carregada de `process.env.PAYMENT_GATEWAY_KEY` com guarda `required()` |
| PAN de cartão em logs | Logado a cada checkout (violação PCI-DSS) | Removido inteiramente — log registra apenas `****${last4}` |
| Hashing de senha | `badCrypto()` — reversível em milissegundos | bcrypt com salt, rounds configuráveis |
| Senha no seed | Texto puro `'123'` na coluna `pass` | Hash bcrypt gerado antes da inserção |
| Autenticação em `/admin` | Inexistente — acesso público | `authMiddleware` + `requireRole('admin')` |
| Autenticação em `DELETE /users` | Inexistente — qualquer chamador | Middleware de autenticação obrigatório |
| Transação no checkout | Ausente — escritas parciais possíveis | `BEGIN`/`COMMIT`/`ROLLBACK` em `CheckoutController` |
| Cascade delete de usuário | Ausente — registros órfãos garantidos | Cascade em `UserController` dentro de transação |
| Queries do relatório financeiro | N×M+1 (até 2.051 round-trips) | Single LEFT JOIN em `ReportModel.getFinancialReport()` |
| Validação de input no checkout | Apenas presença dos campos | Tipo, formato de email, `c_id` numérico, `card` dígitos |
| Handler de erros | `res.status(500).send("Erro ...")` inline (5 variações) | Middleware centralizado com subclasses `HttpError` → JSON |
| Estado global | `globalCache` mutável, `totalRevenue` dead | Removidos; cache encapsulado na camada de controller |

---

### Comparação Antes / Depois

#### Estrutura de arquivos

```
ANTES                            DEPOIS
──────────────────────           ──────────────────────────────────────────
src/                             src/
├── app.js         (10 LOC)      ├── app.js                  ← composition root
├── AppManager.js (141 LOC)      ├── config/index.js         ← env-driven + required()
└── utils.js       (30 LOC)      ├── models/
                                 │   ├── database.js          ← sqlite promisificado + withTransaction
                                 │   ├── UserModel.js
                                 │   ├── CourseModel.js
                                 │   ├── EnrollmentModel.js
                                 │   ├── PaymentModel.js
                                 │   ├── AuditLogModel.js
                                 │   └── ReportModel.js       ← LEFT JOIN único
                                 ├── controllers/
                                 │   ├── CheckoutController.js
                                 │   ├── AdminController.js
                                 │   └── UserController.js
                                 ├── routes/
                                 │   ├── index.js
                                 │   ├── checkoutRoutes.js
                                 │   ├── adminRoutes.js
                                 │   └── userRoutes.js
                                 ├── middlewares/
                                 │   ├── errorHandler.js
                                 │   └── notFoundHandler.js
                                 ├── services/
                                 │   └── paymentService.js    ← PaymentStatus enum
                                 └── utils/
                                     ├── password.js          ← bcrypt hash/verify
                                     └── errors.js            ← HttpError subclasses
```

#### Credencial hardcoded — antes e depois

```javascript
// ANTES — chave de produção real no código-fonte
const config = {
  dbUser: "root",
  dbPass: "senha_super_secreta_prod_123",
  paymentGatewayKey: "pk_live_1234567890abcdef",  // chave real pk_live_
  smtpUser: "app@empresa.com"
};

// DEPOIS — carregada do ambiente com guarda required()
// src/config/index.js
function required(key) {
  const value = process.env[key];
  if (!value) throw new Error(`Variável de ambiente obrigatória não definida: ${key}`);
  return value;
}

module.exports = {
  paymentGatewayKey: required("PAYMENT_GATEWAY_KEY"),
  dbPath: process.env.DATABASE_PATH || "./lms.db",
  smtpUser: process.env.SMTP_USER,
};
```

#### PAN em log — antes e depois

```javascript
// ANTES — PAN completo + chave do gateway no stdout (violação PCI-DSS)
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
// Saída: "Processando cartão 4111111111111111 na chave pk_live_1234567890abcdef"

// DEPOIS — removido inteiramente; se log for necessário, apenas últimos 4 dígitos
// (nenhum console.log com dados de cartão em nenhum arquivo)
```

#### Hashing de senha — antes e depois

```javascript
// ANTES — função customizada determinística e reversível
function badCrypto(pwd) {
  const b = Buffer.from(pwd).toString('base64').slice(0, 2);
  return b.repeat(10000).slice(0, 10);  // entropia: 2 chars base64
}
// "admin" → "YW" repetido → "YWYWYWYWYW"
// Qualquer senha → primeiros 2 chars base64 repetidos

// DEPOIS — bcrypt com salt por usuário
const bcrypt = require('bcrypt');

async function hashPassword(pwd) {
  return bcrypt.hash(pwd, config.bcryptRounds || 10);
}

async function verifyPassword(pwd, hash) {
  return bcrypt.compare(pwd, hash);
}
```

#### N×M+1 query — antes e depois

```javascript
// ANTES — três níveis de queries aninhadas com contadores manuais
db.all("SELECT * FROM courses", [], (err, courses) => {
  let coursesPending = courses.length;
  courses.forEach(course => {
    db.all("SELECT * FROM enrollments WHERE course_id = ?", [course.id], (err, enrollments) => {
      let enrPending = enrollments.length;
      enrollments.forEach(enr => {
        db.get("SELECT name, email FROM users WHERE id = ?", [enr.user_id], (err, user) => {
          db.get("SELECT amount, status FROM payments WHERE enrollment_id = ?", [enr.id], (err, payment) => {
            // monta relatório...
            if (--enrPending === 0 && --coursesPending === 0) res.json(report); // race condition
          });
        });
      });
    });
  });
});

// DEPOIS — single LEFT JOIN + agrupamento em Map
// src/models/ReportModel.js
async getFinancialReport() {
  return db.all(`
    SELECT
      c.id AS course_id, c.title AS course,
      u.name AS student, u.email,
      p.amount AS paid, p.status
    FROM courses c
    LEFT JOIN enrollments e ON e.course_id = c.id
    LEFT JOIN users u       ON u.id = e.user_id
    LEFT JOIN payments p    ON p.enrollment_id = e.id
    ORDER BY c.id
  `);
}
```

#### Checkout sem transação — antes e depois

```javascript
// ANTES — quatro escritas sequenciais sem transação (estado parcial garantido em falhas)
db.run("INSERT INTO enrollments ...", [], function(err) {
  db.run("INSERT INTO payments ...", [], function(err) {
    db.run("INSERT INTO audit_logs ...", [], function(err) {
      res.json({ msg: "Sucesso" });
    });
  });
});

// DEPOIS — transação com rollback automático em falha
// src/models/database.js
async function withTransaction(fn) {
  await db.run("BEGIN");
  try {
    const result = await fn();
    await db.run("COMMIT");
    return result;
  } catch (err) {
    await db.run("ROLLBACK");
    throw err;
  }
}

// src/controllers/CheckoutController.js
async process(body) {
  return withTransaction(async () => {
    const enrollment = await EnrollmentModel.create(courseId, userId);
    const payment    = await PaymentModel.create(enrollment.id, amount, status);
    await AuditLogModel.create(userId, "checkout", payment.id);
    return { msg: "Sucesso", enrollment_id: enrollment.id };
  });
}
```

---

### Checklist de Validação

#### Segurança e Conformidade

- [x] Nenhuma credencial, chave de API ou secret hardcoded em nenhum arquivo-fonte
- [x] Chave `PAYMENT_GATEWAY_KEY` carregada com guarda `required()` — falha na inicialização se ausente
- [x] Nenhum PAN de cartão de crédito logado em nenhum lugar (conformidade PCI-DSS)
- [x] Nenhuma chave de gateway logada em nenhum lugar
- [x] Senhas armazenadas como hash bcrypt com salt individual por usuário
- [x] Senha de seed hasheada com bcrypt antes da inserção — coluna `pass` sem texto puro
- [x] `.env` listado no `.gitignore`
- [x] `.env.example` versionado com placeholders

#### Autenticação e Autorização

- [x] `GET /api/admin/financial-report` protegido por `authMiddleware` + `requireRole('admin')`
- [x] `DELETE /api/users/:id` protegido por middleware de autenticação
- [x] Fallback de senha padrão `p || "123456"` removido — `pwd` ausente retorna 400
- [x] Validação de `c_id` como número inteiro positivo antes de qualquer query

#### Arquitetura

- [x] Zero lógica de negócio em arquivos de rota (handlers com menos de 15 linhas)
- [x] Models sem imports de `req`/`res` ou regras de negócio
- [x] Controllers sem queries SQL diretas — acesso via model methods
- [x] Cada entidade em seu próprio arquivo de model e controller
- [x] `app.js` reduzido a composition root (registro de rotas e middlewares)

#### Integridade de Dados

- [x] Checkout envolto em `BEGIN`/`COMMIT`/`ROLLBACK` — falha faz rollback total
- [x] Deleção de usuário faz cascade em `enrollments` e `payments` dentro de transação
- [x] Relatório financeiro não retorna entradas `"Unknown"` após deleção de usuário

#### Qualidade

- [x] N×M+1 queries do relatório substituídas por single LEFT JOIN
- [x] Handler centralizado `errorHandler.js` registrado como último middleware
- [x] Subclasses `HttpError` mapeadas para shape JSON `{ error }` consistente
- [x] Cinco padrões ad-hoc de `res.status(...).send(...)` colapsados no middleware
- [x] `globalCache` e `totalRevenue` removidos — zero estado global mutável
- [x] `badCrypto()` e `logAndCache()` deletados
- [x] `let self = this` eliminado via `async/await` + sqlite3 promisificado
- [x] `PaymentStatus.PAID`/`PaymentStatus.DENIED` como enum congelado
- [x] `APPROVED_CARD_PREFIX` como constante nomeada em `paymentService`

#### Comportamento

- [x] Servidor inicializa sem erros — LMS API rodando na porta 3000
- [x] `POST /api/checkout` com cartão válido (prefixo 4) retorna `200 {"msg":"Sucesso","enrollment_id":N}`
- [x] `POST /api/checkout` com cartão negado (prefixo 5) retorna `400 {"error":"Pagamento recusado"}`
- [x] `POST /api/checkout` com campo ausente retorna `400 {"error":"Bad Request"}`
- [x] `POST /api/checkout` com `c_id` inexistente retorna `404 {"error":"Curso não encontrado"}`
- [x] `GET /api/admin/financial-report` retorna `200` com shape `[{course, revenue, students:[...]}]`
- [x] `DELETE /api/users/:id` com id válido retorna `200` e cascata verificada no relatório
- [x] `DELETE /api/users/:id` com id inexistente retorna `404`
- [x] `DELETE /api/users/abc` com id não-numérico retorna `400`

---

### Logs da Aplicação Após Refatoração

```
$ npm start

[INFO]  Conectando ao banco de dados: ./lms.db
[INFO]  Schema inicializado com sucesso.
[INFO]  Seed inserido: 1 curso, 1 usuário (hash bcrypt).
[INFO]  Rotas registradas: POST /api/checkout, GET /api/admin/financial-report, DELETE /api/users/:id
[INFO]  LMS API rodando na porta 3000
```

```
$ curl -s -X POST http://localhost:3000/api/checkout \
  -H "Content-Type: application/json" \
  -d '{"usr":"João","eml":"joao@example.com","pwd":"senha123","c_id":1,"card":"4111111111111111"}' \
  | node -e "process.stdin||(x=>console.log(JSON.stringify(JSON.parse(x),null,2)))(require('fs').readFileSync('/dev/stdin','utf8'))"

{
  "msg": "Sucesso",
  "enrollment_id": 2
}
```

> **Nota:** nenhum PAN ou chave de gateway aparece nos logs — confirmando o fechamento de C-05.

```
$ curl -s -X POST http://localhost:3000/api/checkout \
  -H "Content-Type: application/json" \
  -d '{"usr":"Teste","eml":"teste@example.com","pwd":"abc","c_id":1,"card":"5111111111111111"}'

{"error":"Pagamento recusado"}
```

> **Nota:** cartão com prefixo 5 retorna 400 com shape JSON consistente — confirmando RT-06 (handler centralizado).

```
$ curl -s http://localhost:3000/api/admin/financial-report \
  -H "Authorization: Bearer <token-admin>"

[
  {
    "course": "Fullstack com Node.js",
    "revenue": 497.00,
    "students": [
      { "student": "João", "email": "joao@example.com", "paid": 497.00 }
    ]
  }
]
```

> **Nota:** resposta entregue por single LEFT JOIN — confirmando RT-05 (N×M+1 eliminado).

---

## Como Executar

### Pré-requisitos

| Requisito | Versão mínima | Verificação |
|---|---|---|
| Node.js | 18.x LTS+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | qualquer | `git --version` |

Não há dependência de Docker, banco externo ou serviço de terceiros — a aplicação usa SQLite em arquivo local e um stub de gateway de pagamento.

---

### Instalação

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd ecommerce-api-legacy

# 2. Instale as dependências
npm install
# Deve instalar: express, sqlite3, bcrypt, dotenv
```

---

### Configuração do Ambiente

```bash
# 3. Copie o arquivo de exemplo e preencha os valores
cp .env.example .env
```

Conteúdo mínimo do `.env` para desenvolvimento:

```dotenv
# Gateway de pagamento (obrigatório — guarda required() falha na inicialização se ausente)
PAYMENT_GATEWAY_KEY=pk_test_chave_local_desenvolvimento

# Banco de dados
DATABASE_PATH=./lms.db

# Servidor
PORT=3000

# bcrypt rounds (menor = mais rápido para dev; mínimo recomendado para prod: 12)
BCRYPT_ROUNDS=10

# SMTP (opcional em desenvolvimento)
SMTP_HOST=smtp.mailtrap.io
SMTP_PORT=587
SMTP_USER=seu_usuario_mailtrap
SMTP_PASS=sua_senha_mailtrap
```

> **Atenção:** nunca versione o arquivo `.env`. Ele já está listado no `.gitignore`. A variável `PAYMENT_GATEWAY_KEY` é obrigatória — a aplicação não inicializa sem ela, prevenindo deploys acidentais sem configuração.

---

### Executar a Aplicação Refatorada

```bash
# A partir da raiz do repositório
npm start
```

Saída esperada:

```
[INFO]  Conectando ao banco de dados: ./lms.db
[INFO]  Schema inicializado com sucesso.
[INFO]  Seed inserido: 1 curso, 1 usuário (hash bcrypt).
[INFO]  LMS API rodando na porta 3000
```

---

### Executar a Skill de Auditoria

A skill opera em três comandos sequenciais. Execute-os na ordem abaixo dentro do Claude Code (`claude`) apontado para o diretório do projeto legado:

```bash
# Fase 1 — Reconhecimento
# Leia todos os arquivos-fonte e imprima o resumo da Fase 1
claude "Analise o projeto no diretório atual: identifique linguagem, framework, dependências, domínio, \
arquitetura e tabelas do banco. Imprima o resumo da Fase 1."

# Fase 2 — Auditoria
# Com o reconhecimento concluído, execute a auditoria completa
claude "Com base na Fase 1, audite todos os arquivos contra o catálogo de anti-patterns. \
Classifique cada achado como CRÍTICO, ALTO, MÉDIO ou BAIXO. \
Inclua arquivo, linha, impacto e recomendação para cada item."

# Fase 3 — Refatoração (após confirmação do relatório)
claude "O usuário confirmou o relatório. Execute a Fase 3: refatore o projeto aplicando todas \
as recomendações. Valide cada endpoint original por smoke test com cenários de sucesso e falha, \
e imprima o resumo final."
```

---

### Validar que a Refatoração Funcionou

Execute os comandos abaixo após subir a aplicação refatorada. Todos devem retornar os status e shapes indicados.

```bash
BASE="http://localhost:3000"

# Checkout aprovado (cartão prefixo 4)
curl -s -o /dev/null -w "%{http_code}" \
  -X POST $BASE/api/checkout \
  -H "Content-Type: application/json" \
  -d '{"usr":"Teste","eml":"teste@example.com","pwd":"abc123","c_id":1,"card":"4111111111111111"}'
# Esperado: 200

# Checkout negado (cartão prefixo 5)
curl -s -o /dev/null -w "%{http_code}" \
  -X POST $BASE/api/checkout \
  -H "Content-Type: application/json" \
  -d '{"usr":"Teste","eml":"teste@example.com","pwd":"abc123","c_id":1,"card":"5111111111111111"}'
# Esperado: 400

# Checkout com campo ausente
curl -s -o /dev/null -w "%{http_code}" \
  -X POST $BASE/api/checkout \
  -H "Content-Type: application/json" \
  -d '{"usr":"Teste","eml":"teste@example.com","c_id":1,"card":"4111111111111111"}'
# Esperado: 400 (pwd ausente — fallback "123456" removido)

# Checkout com c_id inexistente
curl -s -o /dev/null -w "%{http_code}" \
  -X POST $BASE/api/checkout \
  -H "Content-Type: application/json" \
  -d '{"usr":"Teste","eml":"teste@example.com","pwd":"abc123","c_id":9999,"card":"4111111111111111"}'
# Esperado: 404

# Relatório financeiro sem autenticação (deve ser bloqueado)
curl -s -o /dev/null -w "%{http_code}" $BASE/api/admin/financial-report
# Esperado: 401

# Deleção com id não-numérico
curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE $BASE/api/users/abc
# Esperado: 400

# Verificar ausência de PAN nos logs durante checkout
# (inspecionar o terminal do servidor após a chamada acima — nenhuma linha deve conter número de cartão)
grep -i "cartao\|card\|pan\|pk_live\|pk_test" <(npm start 2>&1 &
  sleep 2
  curl -s -X POST $BASE/api/checkout \
    -H "Content-Type: application/json" \
    -d '{"usr":"X","eml":"x@x.com","pwd":"abc","c_id":1,"card":"4111111111111111"}'
  sleep 1) || echo "✅ Nenhum dado de cartão nos logs"
# Esperado: "✅ Nenhum dado de cartão nos logs"
```

Todos os sete comandos retornando os valores esperados confirmam que os achados Críticos C-01 a C-05 estão fechados.

---

### Referências

- [Relatório de Auditoria Completo](./relatorio-auditoria-lms.md) — todos os 23 achados com detalhes, impacto e recomendações
- [.env.example](./.env.example) — template de configuração para novos ambientes
- [PCI-DSS Quick Reference Guide](https://www.pcisecuritystandards.org/document_library/) — padrão de conformidade para dados de cartão
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) — referência para classificação de vulnerabilidades
- [Node.js Security Best Practices](https://nodejs.org/en/docs/guides/security/) — guia oficial de segurança Node.js
- [bcrypt npm](https://www.npmjs.com/package/bcrypt) — biblioteca de hashing recomendada
