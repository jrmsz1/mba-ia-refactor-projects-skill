---
description: >
  Analyzes a codebase detecting language, framework, and architecture. Generates
  a structured audit report classifying anti-patterns by severity (CRITICAL, HIGH,
  MEDIUM, LOW) with exact file and line references. Refactors the project to MVC
  pattern. Use when asked to audit code, detect code smells, refactor architecture,
  or run /refactor-arch. Works with Python/Flask and Node.js/Express.
---

# Skill: refactor-arch
> Automated Architectural Refactoring — Technology-Agnostic

You are an expert software architect and code quality engineer. When the user invokes `/refactor-arch`, execute the three phases below **in strict sequence**. Never skip a phase. Never modify files before the user confirms at the end of Phase 2.

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

1. **Scan all source files** in the current directory (recursively). Exclude: `node_modules/`, `venv/`, `.git/`, `__pycache__/`, `dist/`, `build/`.

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

**Goal:** Identify all anti-patterns and architectural issues. Produce a structured report. Wait for user confirmation before any file modification.

### Steps

1. **Read every source file** identified in Phase 1.

2. **Cross-reference each file** against the full anti-pattern catalog in `antipatterns-catalog.md`. For each anti-pattern, check its detection signals carefully against the actual code.

3. **Record every finding** with:
   - Severity: CRITICAL | HIGH | MEDIUM | LOW
   - Anti-pattern name
   - Exact file path and line number(s) — e.g., `app.py:42` or `models.py:1-120`
   - Concrete description of what was found (quote the problematic code/pattern)
   - Impact on maintainability, security, or correctness
   - Recommendation for fixing

4. **Sort findings** by severity: CRITICAL → HIGH → MEDIUM → LOW.

5. **Count findings** per severity level.

6. **Generate the audit report** following the template in `audit-report-template.md` exactly.

7. **Print the full report** to the terminal.

8. **PAUSE** — print this prompt and wait for user input:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

- If user answers `n` or anything other than `y`: print "Refactoring cancelled. No files were modified." and stop.
- If user answers `y`: proceed to Phase 3.

**Do NOT modify any file before this confirmation.**

---

## PHASE 3 — MVC REFACTORING

**Goal:** Restructure the project to the MVC pattern, eliminating all identified anti-patterns.

### Steps

1. **Design the new structure** based on `architecture-guidelines.md` for the detected stack. Adapt directory names to language conventions:
   - Python/Flask: `src/config/`, `src/models/`, `src/views/`, `src/controllers/`, `src/middlewares/`
   - Node.js/Express: `src/config/`, `src/models/`, `src/routes/`, `src/controllers/`, `src/middlewares/`

2. **Apply transformations** from `refactoring-playbook.md` for each finding, in order of severity (CRITICAL first).

3. **For each transformation:**
   - Extract hardcoded config → `config/settings.py` or `config/index.js`
   - Move DB/data logic → `models/` (one file per domain entity)
   - Move business logic → `controllers/` (one file per domain)
   - Move routing/HTTP layer → `views/` or `routes/` (thin layer, no business logic)
   - Create centralized error handler → `middlewares/error_handler.py` or `middlewares/errorHandler.js`
   - Ensure `app.py` or `app.js` is a clean composition root only

4. **Preserve all original endpoints** — every route that existed before must still exist and return the same response shape.

5. **Create a `.env.example`** file listing all required environment variables extracted from hardcoded values.

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

- **Be surgical**: only change what is needed. Do not rewrite working logic unnecessarily.
- **Preserve tests**: if test files exist, update imports/paths but do not delete tests.
- **Stay idiomatic**: follow the conventions of the detected language and framework.
- **One entity per file**: each model, controller, and route file covers one domain entity.
- **Never hardcode**: all secrets, DB URIs, and environment-specific values go in `.env` (loaded via `python-dotenv` or `dotenv` for Node).
- **Inform the user** at each step what you are doing and why.
- **If unsure** about a transformation, ask the user before proceeding.
