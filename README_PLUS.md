# README_PLUS — Adaptação para Google Antigravity

Este documento descreve todos os ajustes necessários para executar a skill `refactor-arch` no **Google Antigravity** usando os modelos **Claude Sonnet 4.6** ou **Claude Opus 4.6**.

Os cinco arquivos de referência (`project-analysis.md`, `antipatterns-catalog.md`, `audit-report-template.md`, `architecture-guidelines.md`, `refactoring-playbook.md`) **não precisam de nenhuma alteração** — são Markdown puro e funcionam identicamente nas duas ferramentas.

---

## Sumário

1. [Diferenças entre Claude Code e Antigravity](#1-diferenças-entre-claude-code-e-antigravity)
2. [Nova estrutura de diretórios](#2-nova-estrutura-de-diretórios)
3. [Ajuste 1 — Renomear a pasta da skill](#3-ajuste-1--renomear-a-pasta-da-skill)
4. [Ajuste 2 — Expandir o frontmatter do SKILL.md com `name` e `triggers`](#4-ajuste-2--expandir-o-frontmatter-do-skillmd-com-name-e-triggers)
5. [Ajuste 3 — Criar o Workflow de invocação](#5-ajuste-3--criar-o-workflow-de-invocação)
6. [SKILL.md completo adaptado](#6-skillmd-completo-adaptado)
7. [Escolha do modelo](#7-escolha-do-modelo)
8. [Como executar nos 3 projetos](#8-como-executar-nos-3-projetos)
9. [Checklist de migração](#9-checklist-de-migração)

---

## 1. Diferenças entre Claude Code e Antigravity

| Aspecto | Claude Code | Google Antigravity |
|---|---|---|
| Pasta da skill | `.claude/skills/refactor-arch/` | `.agent/skills/refactor-arch/` |
| Arquivo principal | `SKILL.md` **com frontmatter** (campo `description` apenas) | `SKILL.md` **com frontmatter expandido** (`name` + `description` + `triggers`) |
| Invocação via comando | `/refactor-arch` (nativo) | Requer um **Workflow** em `.agent/workflows/` |
| Ativação automática | Não — precisa do comando | **Sim** — agente detecta pela intenção do usuário |
| Arquivos de referência | Iguais | **Iguais — sem mudança** |
| Suporte a Claude Sonnet 4.6 | ✓ | ✓ |
| Suporte a Claude Opus 4.6 | ✓ | ✓ |

---

## 2. Nova estrutura de diretórios

Replique esta estrutura dentro de **cada um dos 3 projetos**:

```
<projeto>/
└── .agent/
    ├── skills/
    │   └── refactor-arch/
    │       ├── SKILL.md                    ← modificado (ver seção 4 e 6)
    │       ├── project-analysis.md         ← sem alteração
    │       ├── antipatterns-catalog.md     ← sem alteração
    │       ├── audit-report-template.md    ← sem alteração
    │       ├── architecture-guidelines.md  ← sem alteração
    │       └── refactoring-playbook.md     ← sem alteração
    └── workflows/
        └── refactor-arch.md               ← novo arquivo (ver seção 5)
```

---

## 3. Ajuste 1 — Renomear a pasta da skill

O Antigravity lê skills do diretório `.agent/skills/`, não `.claude/skills/`.

### Comando de migração (a partir da raiz de cada projeto)

```bash
# Copiar os arquivos existentes para o novo caminho
mkdir -p .agent/skills/refactor-arch
mkdir -p .agent/workflows

cp .claude/skills/refactor-arch/project-analysis.md     .agent/skills/refactor-arch/
cp .claude/skills/refactor-arch/antipatterns-catalog.md .agent/skills/refactor-arch/
cp .claude/skills/refactor-arch/audit-report-template.md .agent/skills/refactor-arch/
cp .claude/skills/refactor-arch/architecture-guidelines.md .agent/skills/refactor-arch/
cp .claude/skills/refactor-arch/refactoring-playbook.md .agent/skills/refactor-arch/
# O SKILL.md será copiado e o frontmatter expandido manualmente (ver seção 4 e 6)
```

> **Nota:** Se você estiver iniciando direto no Antigravity sem ter usado Claude Code antes, basta criar a estrutura `.agent/` do zero com os arquivos fornecidos neste repositório.

---

## 4. Ajuste 2 — Expandir o frontmatter do SKILL.md com `name` e `triggers`

O `SKILL.md` do Claude Code **já possui frontmatter** com o campo `description`. O Antigravity requer dois campos adicionais para funcionar corretamente: `name` e `triggers`. Sem eles, a skill existe no disco mas o agente não consegue associá-la a intenções do usuário nem ao comando `/refactor-arch`.

### O que cada campo faz

- `name` — identificador único da skill (deve bater com o nome da pasta); **campo novo, não existe no SKILL.md do Claude Code**
- `description` — texto que o agente lê para decidir se deve ativar a skill; **já existe no SKILL.md do Claude Code**, mas é expandido aqui com mais casos de uso
- `triggers` — palavras-chave e frases que sinalizam intenção de uso; também registra o comando `/refactor-arch` para compatibilidade com o Workflow; **campo novo, não existe no SKILL.md do Claude Code**

### Frontmatter expandido — substitui o bloco existente no topo do SKILL.md

```yaml
---
name: refactor-arch
description: >
  Analyzes any backend codebase to detect the current stack, framework, and
  architecture. Generates a structured audit report classifying anti-patterns
  by severity (CRITICAL, HIGH, MEDIUM, LOW) with exact file and line references.
  Then refactors the project to the MVC pattern, eliminating all findings.
  Use when asked to: audit code architecture, detect code smells, refactor to MVC,
  fix anti-patterns, analyze a legacy project, or run /refactor-arch.
  Works with Python/Flask and Node.js/Express projects.
triggers:
  - refactor architecture
  - audit code
  - detect code smells
  - refactor to mvc
  - analyze legacy project
  - fix anti-patterns
  - /refactor-arch
---
```

**Substitua o bloco frontmatter existente** (as linhas `---` … `---` no topo do `SKILL.md` atual) por este bloco expandido. O restante do arquivo — a partir de `# Skill: refactor-arch` — permanece inalterado.

---

## 5. Ajuste 3 — Criar o Workflow de invocação

No Antigravity, **Workflows** são os orquestradores invocados com `/comando` — equivalente direto ao sistema de skills-como-comandos do Claude Code. Criar este arquivo garante que `/refactor-arch` continue funcionando exatamente como antes.

### Criar o arquivo `.agent/workflows/refactor-arch.md`

```markdown
# Workflow: /refactor-arch
> Trigger: Automated Architectural Refactoring

Activate the `refactor-arch` skill and execute all three phases in strict sequence.

## Execution order

1. **Phase 1 — Project Analysis**
   Scan all source files, detect language, framework, database, domain, and current
   architecture. Print the Phase 1 summary before proceeding.

2. **Phase 2 — Architecture Audit**
   Read every source file and cross-reference against the anti-patterns catalog.
   Generate the full audit report sorted by severity (CRITICAL → LOW).
   **PAUSE and ask for confirmation before any file modification.**

3. **Phase 3 — MVC Refactoring**
   Only after the user confirms with "y": apply all transformations from the
   refactoring playbook in severity order. Validate the application boots and
   all endpoints respond correctly. Print the Phase 3 summary.

## Rules

- Never skip a phase.
- Never modify files before the user confirms at the end of Phase 2.
- If the user answers "n" at the confirmation prompt, stop immediately and
  print: "Refactoring cancelled. No files were modified."
```

---

## 6. SKILL.md completo adaptado

Este é o conteúdo final do `SKILL.md` com o frontmatter já expandido. O corpo do arquivo (a partir de `# Skill: refactor-arch`) é idêntico ao original do Claude Code — a única diferença está no bloco `---` … `---` do topo, que agora inclui `name` e `triggers` além do `description` já existente. Substitua o arquivo original por este:

```markdown
---
name: refactor-arch
description: >
  Analyzes any backend codebase to detect the current stack, framework, and
  architecture. Generates a structured audit report classifying anti-patterns
  by severity (CRITICAL, HIGH, MEDIUM, LOW) with exact file and line references.
  Then refactors the project to the MVC pattern, eliminating all findings.
  Use when asked to: audit code architecture, detect code smells, refactor to MVC,
  fix anti-patterns, analyze a legacy project, or run /refactor-arch.
  Works with Python/Flask and Node.js/Express projects.
triggers:
  - refactor architecture
  - audit code
  - detect code smells
  - refactor to mvc
  - analyze legacy project
  - fix anti-patterns
  - /refactor-arch
---

# Skill: refactor-arch
> Automated Architectural Refactoring — Technology-Agnostic

You are an expert software architect and code quality engineer. When the user invokes
`/refactor-arch` or expresses intent to audit or refactor a project, execute the three
phases below **in strict sequence**. Never skip a phase. Never modify files before the
user confirms at the end of Phase 2.

Read all reference files in this skill folder before starting:
- `project-analysis.md` — stack detection heuristics
- `antipatterns-catalog.md` — anti-patterns with severity classification
- `audit-report-template.md` — standardized report format
- `architecture-guidelines.md` — target MVC architecture rules
- `refactoring-playbook.md` — concrete transformation patterns

---

## PHASE 1 — PROJECT ANALYSIS

**Goal:** Understand what the project is before touching anything.

### Steps

1. **Scan all source files** in the current directory (recursively). Exclude:
   `node_modules/`, `venv/`, `.git/`, `__pycache__/`, `dist/`, `build/`.

2. **Detect** (using heuristics from `project-analysis.md`):
   - Primary language (Python, JavaScript/TypeScript, etc.)
   - Framework and version (Flask, Express, Django, etc.)
   - Database(s) in use (SQLite, PostgreSQL, MongoDB, etc.)
   - Key dependencies / external libraries
   - Current architectural style (monolithic, layered, MVC, etc.)
   - Application domain (e-commerce, task manager, LMS, etc.)

3. **Count** source files analyzed (exclude config/lock files).

4. **Identify DB tables or collections** if schema/migrations are present.

5. **Print the Phase 1 summary** in EXACTLY this format:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <detected>
Framework:     <name + version>
Dependencies:  <comma-separated key deps>
Domain:        <short domain description>
Architecture:  <current style description>
Source files:  <N> files analyzed
DB tables:     <table/collection names or "not detected">
================================
```

Do NOT proceed to Phase 2 until this summary is printed.

---

## PHASE 2 — ARCHITECTURE AUDIT

**Goal:** Identify all anti-patterns and architectural issues. Produce a structured
report. Wait for user confirmation before any file modification.

### Steps

1. **Read every source file** identified in Phase 1.

2. **Cross-reference each file** against the full anti-pattern catalog in
   `antipatterns-catalog.md`. For each anti-pattern, check its detection signals
   carefully against the actual code.

3. **Record every finding** with:
   - Severity: CRITICAL | HIGH | MEDIUM | LOW
   - Anti-pattern name
   - Exact file path and line number(s) — e.g., `app.py:42` or `models.py:1-120`
   - Concrete description of what was found (quote the problematic code/pattern)
   - Impact on maintainability, security, or correctness
   - Recommendation for fixing

4. **Sort findings** by severity: CRITICAL → HIGH → MEDIUM → LOW.

5. **Count findings** per severity level.

6. **Generate the audit report** following the template in `audit-report-template.md`
   exactly.

7. **Print the full report** to the terminal.

8. **PAUSE** — print this prompt and wait for user input:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

- If user answers `n` or anything other than `y`: print
  "Refactoring cancelled. No files were modified." and stop.
- If user answers `y`: proceed to Phase 3.

**Do NOT modify any file before this confirmation.**

---

## PHASE 3 — MVC REFACTORING

**Goal:** Restructure the project to the MVC pattern, eliminating all identified
anti-patterns.

### Steps

1. **Design the new structure** based on `architecture-guidelines.md` for the detected
   stack. Adapt directory names to language conventions:
   - Python/Flask: `src/config/`, `src/models/`, `src/views/`, `src/controllers/`,
     `src/middlewares/`
   - Node.js/Express: `src/config/`, `src/models/`, `src/routes/`, `src/controllers/`,
     `src/middlewares/`

2. **Apply transformations** from `refactoring-playbook.md` for each finding, in order
   of severity (CRITICAL first).

3. **For each transformation:**
   - Extract hardcoded config → `config/settings.py` or `config/index.js`
   - Move DB/data logic → `models/` (one file per domain entity)
   - Move business logic → `controllers/` (one file per domain)
   - Move routing/HTTP layer → `views/` or `routes/` (thin layer, no business logic)
   - Create centralized error handler → `middlewares/error_handler.py` or
     `middlewares/errorHandler.js`
   - Ensure `app.py` or `app.js` is a clean composition root only

4. **Preserve all original endpoints** — every route that existed before must still
   exist and return the same response shape.

5. **Create a `.env.example`** file listing all required environment variables
   extracted from hardcoded values.

6. **Validate the result:**
   - Run the application: `python app.py` or `node src/app.js` (adapt to project)
   - Check that it boots without errors
   - Test at least one endpoint per domain with curl or equivalent
   - Confirm zero remaining hardcoded credentials or SQL inside controllers

7. **Print the Phase 3 summary** in EXACTLY this format:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<print the actual directory tree>

## Transformations Applied
- <list each transformation made, one per line>

## Validation
  ✓/✗ Application boots without errors
  ✓/✗ All endpoints respond correctly
  ✓/✗ Zero hardcoded credentials remaining
  ✓/✗ Zero business logic in routes/views layer
  ✓/✗ Models abstract all data access
================================
```

---

## General Rules

- **Be surgical**: only change what is needed. Do not rewrite working logic
  unnecessarily.
- **Preserve tests**: if test files exist, update imports/paths but do not delete tests.
- **Stay idiomatic**: follow the conventions of the detected language and framework.
- **One entity per file**: each model, controller, and route file covers one domain
  entity.
- **Never hardcode**: all secrets, DB URIs, and environment-specific values go in `.env`
  (loaded via `python-dotenv` or `dotenv` for Node).
- **Inform the user** at each step what you are doing and why.
- **If unsure** about a transformation, ask the user before proceeding.
```

---

## 7. Escolha do modelo

O Antigravity permite trocar o modelo ativo no painel de configurações. Para esta skill:

| Modelo | Quando usar |
|---|---|
| **Claude Sonnet 4.6** | Projetos menores, iterações rápidas, quando custo e velocidade importam. Resolve bem os 3 projetos do desafio. |
| **Claude Opus 4.6** | Projetos com arquitetura mais complexa, quando a Fase 2 deixa de detectar problemas sutis, ou quando a refatoração da Fase 3 produz resultados incompletos. Recomendado para o `task-manager-api` por já ter alguma organização parcial. |

Para trocar o modelo no Antigravity: **Agent Manager → ícone de configurações (⚙) → Model → selecionar o desejado**.

---

## 8. Como executar nos 3 projetos

### Pré-requisitos

- Google Antigravity instalado ([antigravity.google/download](https://antigravity.google/download))
- Conta Google vinculada ao Antigravity
- Modelo selecionado: Claude Sonnet 4.6 ou Claude Opus 4.6

### Projeto 1 — code-smells-project (Python/Flask)

```bash
# 1. Copiar os arquivos da skill
mkdir -p code-smells-project/.agent/skills/refactor-arch
mkdir -p code-smells-project/.agent/workflows

cp refactor-arch/SKILL.md                    code-smells-project/.agent/skills/refactor-arch/
cp refactor-arch/project-analysis.md         code-smells-project/.agent/skills/refactor-arch/
cp refactor-arch/antipatterns-catalog.md     code-smells-project/.agent/skills/refactor-arch/
cp refactor-arch/audit-report-template.md    code-smells-project/.agent/skills/refactor-arch/
cp refactor-arch/architecture-guidelines.md  code-smells-project/.agent/skills/refactor-arch/
cp refactor-arch/refactoring-playbook.md     code-smells-project/.agent/skills/refactor-arch/
cp refactor-arch/refactor-arch.md            code-smells-project/.agent/workflows/
```

```
# 2. No Antigravity: abrir a pasta code-smells-project como workspace
# 3. No Agent Manager, iniciar nova conversa e digitar:
/refactor-arch
```

### Projeto 2 — ecommerce-api-legacy (Node.js/Express)

```bash
mkdir -p ecommerce-api-legacy/.agent/skills/refactor-arch
mkdir -p ecommerce-api-legacy/.agent/workflows

cp refactor-arch/SKILL.md                    ecommerce-api-legacy/.agent/skills/refactor-arch/
cp refactor-arch/project-analysis.md         ecommerce-api-legacy/.agent/skills/refactor-arch/
cp refactor-arch/antipatterns-catalog.md     ecommerce-api-legacy/.agent/skills/refactor-arch/
cp refactor-arch/audit-report-template.md    ecommerce-api-legacy/.agent/skills/refactor-arch/
cp refactor-arch/architecture-guidelines.md  ecommerce-api-legacy/.agent/skills/refactor-arch/
cp refactor-arch/refactoring-playbook.md     ecommerce-api-legacy/.agent/skills/refactor-arch/
cp refactor-arch/refactor-arch.md            ecommerce-api-legacy/.agent/workflows/
```

```
# No Antigravity: trocar o workspace para ecommerce-api-legacy
# Iniciar nova conversa e digitar:
/refactor-arch
```

### Projeto 3 — task-manager-api (Python/Flask)

```bash
mkdir -p task-manager-api/.agent/skills/refactor-arch
mkdir -p task-manager-api/.agent/workflows

cp refactor-arch/SKILL.md                    task-manager-api/.agent/skills/refactor-arch/
cp refactor-arch/project-analysis.md         task-manager-api/.agent/skills/refactor-arch/
cp refactor-arch/antipatterns-catalog.md     task-manager-api/.agent/skills/refactor-arch/
cp refactor-arch/audit-report-template.md    task-manager-api/.agent/skills/refactor-arch/
cp refactor-arch/architecture-guidelines.md  task-manager-api/.agent/skills/refactor-arch/
cp refactor-arch/refactoring-playbook.md     task-manager-api/.agent/skills/refactor-arch/
cp refactor-arch/refactor-arch.md            task-manager-api/.agent/workflows/
```

```
# No Antigravity: trocar o workspace para task-manager-api
# Iniciar nova conversa e digitar:
/refactor-arch
```

### Salvar os relatórios de auditoria

Após a Fase 2 de cada projeto, copie o output do Agent Manager para:

```
reports/audit-project-1.md   ← code-smells-project
reports/audit-project-2.md   ← ecommerce-api-legacy
reports/audit-project-3.md   ← task-manager-api
```

---

## 9. Checklist de migração

Use este checklist para confirmar que tudo está configurado corretamente antes de executar:

### Estrutura de arquivos
- [ ] `.agent/skills/refactor-arch/SKILL.md` contém o frontmatter expandido com `name`, `description` **e** `triggers` (não apenas `description`)
- [ ] `.agent/skills/refactor-arch/project-analysis.md` presente
- [ ] `.agent/skills/refactor-arch/antipatterns-catalog.md` presente
- [ ] `.agent/skills/refactor-arch/audit-report-template.md` presente
- [ ] `.agent/skills/refactor-arch/architecture-guidelines.md` presente
- [ ] `.agent/skills/refactor-arch/refactoring-playbook.md` presente
- [ ] `.agent/workflows/refactor-arch.md` presente

### Configuração do Antigravity
- [ ] Workspace aberto na raiz do projeto correto
- [ ] Modelo selecionado: Claude Sonnet 4.6 ou Claude Opus 4.6
- [ ] Permissões de escrita habilitadas para o workspace (necessário para a Fase 3)

### Execução
- [ ] Fase 1 imprime o resumo com stack detectada corretamente
- [ ] Fase 2 encontra ≥ 5 findings com pelo menos 1 CRITICAL ou HIGH
- [ ] Fase 2 pausa e aguarda confirmação antes de qualquer modificação
- [ ] Fase 3 executada somente após confirmação com "y"
- [ ] Aplicação inicializa sem erros após a Fase 3
- [ ] Todos os endpoints originais respondem corretamente
- [ ] Relatório de auditoria salvo em `reports/audit-project-N.md`
