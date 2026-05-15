# Audit Report Template

Use this template **exactly** when generating the Phase 2 output. Fill in all bracketed placeholders with real values found in the project. Do not omit any section.

---

## Template

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <directory name>
Stack:   <Language> + <Framework version>
Files:   <N> analyzed | ~<estimated LOC> lines of code

## Summary
CRITICAL: <N> | HIGH: <N> | MEDIUM: <N> | LOW: <N>
Total findings: <N>

## Findings
(ordered CRITICAL → HIGH → MEDIUM → LOW; within same severity, ordered by file)

---

### [<SEVERITY>] <Anti-Pattern Name>
File: <relative/path/to/file.py>:<line or line-range>
Description: <Concrete description of what was found — quote the specific problematic code or pattern>
Impact: <What harm this causes: security risk, maintenance burden, test impossibility, etc.>
Recommendation: <Specific action to fix this finding>

---

### [<SEVERITY>] <Anti-Pattern Name>
File: <relative/path/to/file.js>:<line or line-range>
Description: <...>
Impact: <...>
Recommendation: <...>

(repeat for each finding)

---

================================
Total: <N> findings
Breakdown: CRITICAL <N> | HIGH <N> | MEDIUM <N> | LOW <N>
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

---

## Filling Rules

### File + Line Reference
- Always use relative path from project root: `src/app.py:42`, not `/home/user/project/src/app.py:42`
- For a range: `models.py:1-120`
- For a class or function: `controllers.py:45-89 (class OrderController)`
- Never write "unknown" or "multiple files" — pick the primary location

### Description
- Quote the actual code when it is short (< 2 lines): `SECRET_KEY = 'minha-chave-super-secreta-123'`
- For longer patterns, describe the structural issue: "The function `get_orders()` (lines 45-89) executes a separate SELECT query inside a for-loop over all orders, causing N queries per request."
- Be specific — "bad code" is not acceptable; describe *why* it's bad

### Impact
- CRITICAL: mention security, data exposure, or total architectural failure
- HIGH: mention testability, maintainability, coupling
- MEDIUM: mention performance, reliability, or data integrity
- LOW: mention readability or convention compliance

### Recommendation
- Write one clear, actionable sentence: "Extract to `models/produto_model.py` and use parameterized queries."
- Do not write vague advice like "refactor this" or "improve the code"

---

## Example Findings

### [CRITICAL] Hardcoded Credentials
File: app.py:8  
Description: `SECRET_KEY = 'minha-chave-super-secreta-123'` is written directly in source code and will be committed to version control.  
Impact: Any developer with repo access — or anyone who finds the repository — can forge session tokens.  
Recommendation: Move to environment variable: `SECRET_KEY = os.environ.get('SECRET_KEY')` and add to `.env` file.

---

### [CRITICAL] God File — All Logic in Single Module
File: models.py:1-350  
Description: This single file contains DB schema definitions, raw SQL queries, business logic for 4 domains (products, users, orders, cart), input validation, and response formatting — approximately 350 lines with no separation.  
Impact: Impossible to unit-test any domain in isolation; any change risks breaking unrelated functionality.  
Recommendation: Split into `models/produto_model.py`, `models/usuario_model.py`, `models/pedido_model.py`; move business logic to corresponding controllers.

---

### [HIGH] Business Logic in Route Handler
File: app.py:89-112  
Description: The `/checkout` route handler directly calculates order totals, applies discount rules (`if total > 500: total *= 0.9`), and inserts records — 23 lines of mixed business and persistence logic.  
Impact: Cannot test discount logic without spinning up the HTTP server and database.  
Recommendation: Extract to `controllers/pedido_controller.py::process_checkout()`.

---

### [MEDIUM] N+1 Query in Order Listing
File: models.py:198-210  
Description: `get_all_orders()` fetches all orders and then runs a separate `SELECT` for each order's items inside a for-loop, resulting in N+1 database round-trips.  
Impact: 1000 orders = 1001 queries; API latency grows linearly with data size.  
Recommendation: Use a JOIN query or batch fetch all items with `WHERE order_id IN (...)`.

---

### [LOW] Magic Number in Discount Calculation
File: app.py:97  
Description: `total *= 0.9` uses the magic number `0.9` with no explanation or named constant.  
Impact: Any developer maintaining this code cannot tell if `0.9` is the correct discount rate without reading surrounding context.  
Recommendation: Define `BULK_DISCOUNT_RATE = 0.10` in config and use `total *= (1 - BULK_DISCOUNT_RATE)`.
```
