# Anti-Patterns Catalog

Use this catalog during **Phase 2** to identify problems in the codebase. For each anti-pattern, apply its detection signals to every source file. Report every occurrence with exact file and line numbers.

Severity scale: **CRITICAL → HIGH → MEDIUM → LOW**

---

## CRITICAL Anti-Patterns

### AP-01 — God Class / God File
**Severity:** CRITICAL  
**Description:** A single class or file contains the entire application — routing, business logic, DB queries, validation, and response formatting all in one place.

**Detection signals:**
- Single file > 300 lines containing route handlers AND raw SQL/ORM queries AND data transformation logic
- A class with methods covering multiple unrelated domains (e.g., user management + product management + order processing in one class)
- Flask `app.py` or Express `app.js` with direct `db.execute()` calls inside route handlers
- A `models.py` that contains both DB schema AND business rules AND utility functions

**Example (bad):**
```python
# app.py — 500 lines, does everything
@app.route('/products')
def get_products():
    conn = sqlite3.connect('db.sqlite')
    products = conn.execute('SELECT * FROM products').fetchall()
    result = [{'id': p[0], 'name': p[1], 'price': p[2]} for p in products]
    return jsonify(result)
```

---

### AP-02 — Hardcoded Credentials / Secrets
**Severity:** CRITICAL  
**Description:** Passwords, API keys, secret keys, or database URIs are written directly in source code.

**Detection signals:**
- `SECRET_KEY = 'some-literal-string'` in any Python file
- `password = "admin123"` or similar literals in DB connection setup
- `JWT_SECRET = "hardcoded-jwt-secret"` in JavaScript files
- `DATABASE_URL = "sqlite:///app.db"` hardcoded (not from env)
- Any `api_key = "sk-..."` or similar pattern

**Example (bad):**
```python
app.config['SECRET_KEY'] = 'minha-chave-super-secreta-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
```

---

### AP-03 — SQL Injection Vulnerability
**Severity:** CRITICAL  
**Description:** User-controlled input is concatenated directly into SQL strings without parameterization.

**Detection signals:**
- `f"SELECT * FROM users WHERE id = {user_id}"` — f-string interpolation in SQL
- `"SELECT ... WHERE name = '" + name + "'"` — string concatenation in SQL
- `.format()` used to build SQL queries with variables
- Any SQL string where a function parameter appears inside the query string without `?` or `%s` placeholders

**Example (bad):**
```python
query = f"SELECT * FROM users WHERE email = '{email}'"
cursor.execute(query)
```

**Example (good):**
```python
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
```

---

### AP-04 — Deprecated / Unsafe API Usage
**Severity:** CRITICAL or HIGH (depending on context)  
**Description:** Use of deprecated APIs, insecure cryptographic functions, or obsolete patterns.

**Detection signals (Python):**
- `md5` or `sha1` for password hashing → use `bcrypt` or `argon2`
- `pickle` for untrusted data deserialization
- `os.system()` with user input → use `subprocess` with list args
- `flask.ext.*` imports (deprecated since Flask 1.0)
- `@app.before_first_request` (deprecated in Flask 2.3+) → use `with app.app_context()`

**Detection signals (Node.js):**
- `require('crypto').createCipher()` (deprecated) → use `createCipheriv()`
- `new Buffer()` (deprecated) → use `Buffer.from()` or `Buffer.alloc()`
- `app.use(bodyParser.json())` with body-parser installed separately (built into Express 4.16+)
- `express-validator` v3 or earlier syntax
- `mongoose.connect()` without `useNewUrlParser` on old Mongoose versions
- `req.param()` (removed in Express 5) → use `req.params`, `req.query`, `req.body`

---

## HIGH Anti-Patterns

### AP-05 — Business Logic in Controllers / Routes
**Severity:** HIGH  
**Description:** Route handlers or controllers contain complex business rules that belong in a service/model layer.

**Detection signals:**
- Route handler > 30 lines of logic (not counting comments)
- Conditional business rules (`if order.total > 100: apply_discount()`) inside a route function
- Data transformation, calculation, or validation happening directly inside a Flask route or Express handler
- Multiple DB calls in a single route handler with intermediate data manipulation

**Example (bad):**
```python
@app.route('/checkout', methods=['POST'])
def checkout():
    items = request.json['items']
    total = sum(item['price'] * item['qty'] for item in items)
    if total > 500:
        total *= 0.9  # 10% discount — business rule inside route!
    conn.execute('INSERT INTO orders ...', (total,))
    return jsonify({'total': total})
```

---

### AP-06 — No Dependency Injection / Global State
**Severity:** HIGH  
**Description:** Components directly instantiate their own dependencies or rely on global mutable state, making testing impossible and coupling very high.

**Detection signals:**
- DB connection created inside route handlers (`conn = sqlite3.connect(...)` inside `def route():`)
- Global `db` or `conn` variable used across multiple unrelated functions
- Service classes instantiating their own repositories with `self.repo = Repository()`
- Flask `g` object abused to pass state between unrelated middlewares

---

### AP-07 — Missing Input Validation
**Severity:** HIGH  
**Description:** Route handlers accept user input without validating type, presence, or range, enabling crashes or data corruption.

**Detection signals:**
- `request.json['field']` without checking if key exists (will raise `KeyError` on missing data)
- No schema validation library in use (no `marshmallow`, `pydantic`, `joi`, `zod`, `express-validator`)
- Numeric fields not type-checked before arithmetic operations
- File upload routes without size or MIME type validation

---

## MEDIUM Anti-Patterns

### AP-08 — N+1 Query Problem
**Severity:** MEDIUM  
**Description:** A query is executed inside a loop, causing N+1 database round-trips instead of a single JOIN or batch fetch.

**Detection signals:**
- `for item in items: db.execute('SELECT ... WHERE id = ?', (item.id,))`
- ORM lazy-loading inside a loop without `joinedload` or `select_related`
- Any DB call inside a Python `for` loop or JavaScript `.map()` / `.forEach()`

**Example (bad):**
```python
orders = db.execute('SELECT * FROM orders').fetchall()
for order in orders:
    items = db.execute('SELECT * FROM items WHERE order_id = ?', (order['id'],)).fetchall()
```

---

### AP-09 — Missing Error Handling / No Centralized Error Handler
**Severity:** MEDIUM  
**Description:** Errors are handled inconsistently or not at all — some routes catch exceptions, others let them propagate as 500 errors with stack traces exposed to the client.

**Detection signals:**
- No `@app.errorhandler` (Flask) or `app.use((err, req, res, next) => ...)` (Express) present
- Mix of try/except in some routes but not others
- `except Exception as e: print(e)` — swallowing errors silently
- Raw stack traces potentially visible in API responses

---

### AP-10 — Code Duplication / Copy-Paste Logic
**Severity:** MEDIUM  
**Description:** The same logic block appears in multiple places with minor variations.

**Detection signals:**
- Identical DB connection setup repeated in multiple functions
- Same validation block copy-pasted across multiple routes
- Response formatting code duplicated across handlers
- Utility functions redefined in multiple files

---

## LOW Anti-Patterns

### AP-11 — Magic Numbers and Magic Strings
**Severity:** LOW  
**Description:** Numeric literals or string constants with no explanation are used inline in logic.

**Detection signals:**
- `if status == 3:` — what does 3 mean?
- `time.sleep(300)` — why 300?
- `price * 0.9` — 0.9 is a hidden business rule
- HTTP status codes as raw integers without named constants (minor)

---

### AP-12 — Poor Naming Conventions
**Severity:** LOW  
**Description:** Variable, function, or file names are unclear, misleading, or violate the language's naming conventions.

**Detection signals (Python):**
- camelCase for variables/functions (should be snake_case)
- Single-letter variables outside of loop counters (`x`, `d`, `tmp`)
- Function named `do_stuff()`, `process()`, `handle()` with no domain context

**Detection signals (Node.js):**
- snake_case for variables/functions (should be camelCase)
- PascalCase for non-class functions

---

### AP-13 — Commented-Out Dead Code
**Severity:** LOW  
**Description:** Large blocks of commented-out code remain in the codebase, adding noise and confusion.

**Detection signals:**
- Multi-line blocks of `#`-commented or `//`-commented code that looks like old implementation
- `# TODO: remove this` comments older than the current feature
- Entire functions commented out

---

## Deprecated API Quick Reference

### Python / Flask
| Deprecated | Replacement |
|------------|-------------|
| `flask.ext.*` | Direct package imports |
| `@app.before_first_request` | `with app.app_context():` in `__init__` |
| `md5`/`sha1` for passwords | `bcrypt`, `argon2-cffi` |
| `pickle` for untrusted data | `json`, `msgpack` |

### Node.js / Express
| Deprecated | Replacement |
|------------|-------------|
| `new Buffer(x)` | `Buffer.from(x)`, `Buffer.alloc(n)` |
| `crypto.createCipher()` | `crypto.createCipheriv()` |
| `body-parser` (separate) | `express.json()`, `express.urlencoded()` |
| `req.param('x')` | `req.params.x`, `req.query.x`, `req.body.x` |
| Callback-based `mongoose.connect` | Promise-based with `.then()` / `async/await` |
