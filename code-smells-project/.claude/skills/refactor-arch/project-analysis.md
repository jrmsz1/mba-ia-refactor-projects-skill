# Project Analysis — Detection Heuristics

Use this reference during **Phase 1** to detect the project's stack, architecture, and domain with precision.

---

## 1. Language Detection

Scan file extensions and configuration files:

| Signal | Language |
|--------|----------|
| `*.py` + `requirements.txt` or `pyproject.toml` | Python |
| `*.js` / `*.ts` + `package.json` | JavaScript / TypeScript |
| `*.rb` + `Gemfile` | Ruby |
| `*.java` + `pom.xml` or `build.gradle` | Java |
| `*.go` + `go.mod` | Go |
| `*.php` + `composer.json` | PHP |

**Primary language**: whichever extension appears most in source files (excluding config/lock files).

---

## 2. Framework Detection

### Python
| Signal | Framework |
|--------|-----------|
| `from flask import Flask` or `import flask` | Flask |
| `import django` or `settings.py` + `urls.py` | Django |
| `from fastapi import FastAPI` | FastAPI |

To get version: search `requirements.txt` or `pyproject.toml` for `Flask==x.x.x`.

### JavaScript / TypeScript
| Signal | Framework |
|--------|-----------|
| `require('express')` or `import express` | Express |
| `require('fastify')` | Fastify |
| `NestFactory.create` | NestJS |
| `next()` in pages/ or app/ | Next.js |

To get version: read `package.json` → `dependencies`.

---

## 3. Database Detection

| Signal | Database |
|--------|----------|
| `sqlite3` import / `.db` file / `sqlite:///` | SQLite |
| `psycopg2` / `pg` / `postgresql://` | PostgreSQL |
| `pymysql` / `mysql2` / `mysql://` | MySQL |
| `pymongo` / `mongoose` | MongoDB |
| `redis` import | Redis |
| Raw `sqlite3.connect()` without ORM | Raw SQL (no ORM) |
| `SQLAlchemy` / `sequelize` / `typeorm` | ORM present |

Also check for `.env`, `config.py`, or hardcoded connection strings in source files.

---

## 4. Architecture Classification

After reading source files, classify the current architecture:

### Monolithic / God-File
- Signs: 1-4 files contain everything (routes, DB calls, business logic, response formatting)
- Example: single `app.py` with 500+ lines doing it all

### Partially Layered
- Signs: some separation exists (e.g., `models/` folder) but controllers mix concerns, or services are entangled with routes
- Example: `routes/` exists but each route function contains DB queries and business logic

### MVC-Compliant
- Signs: clear `models/`, `views/` (or `routes/`), `controllers/` separation; each layer has a single responsibility
- Thin controllers, fat models, routes only handle HTTP

### Other Patterns
- Services layer: `services/` directory with business logic separated from controllers
- Repository pattern: `repositories/` abstracts data access from models

---

## 5. Domain Detection

Look for entity names in routes, models, table names, and variable names:

| Entity keywords found | Domain |
|-----------------------|--------|
| `produto`, `pedido`, `carrinho`, `usuario`, `checkout` | E-commerce |
| `task`, `tarefa`, `todo`, `status`, `priority` | Task Manager |
| `curso`, `aluno`, `enrollment`, `lesson`, `course` | LMS / Education |
| `user`, `auth`, `token`, `login`, `register` | Auth Service |
| `invoice`, `payment`, `subscription` | Billing |

---

## 6. File Counting

Count only files that contain application logic. **Exclude**:
- `node_modules/`, `venv/`, `.git/`, `__pycache__/`
- `*.lock`, `*.log`, `*.env`
- `dist/`, `build/`, `.cache/`
- Migration files (count separately if relevant)

---

## 7. DB Table / Schema Detection

| Source | How to find tables |
|--------|--------------------|
| Raw SQL in code | Search for `CREATE TABLE`, `INSERT INTO`, `SELECT FROM` |
| SQLite `.db` file | Note file name and any `CREATE TABLE` statements |
| Flask-SQLAlchemy | Look for `class X(db.Model):` — class name = table |
| Sequelize | Look for `sequelize.define('tableName'` or `Model.init` |
| Mongoose | Look for `new Schema({` — variable name = collection |

---

## 8. Phase 1 Output Rules

- Print detected values confidently; if truly uncertain, write "not detected" — do not guess.
- Framework version: use exact version from dependency file, not an estimate.
- Domain description: 1 sentence describing what the API does.
- Architecture description: classify + brief explanation of how files are currently organized.
