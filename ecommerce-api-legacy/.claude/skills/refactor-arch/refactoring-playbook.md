# Refactoring Playbook

Use this playbook during **Phase 3** to apply concrete transformations for each anti-pattern found. Apply transformations in severity order: CRITICAL first, then HIGH, MEDIUM, LOW.

Each pattern shows the full before → after transformation with file targets.

---

## RT-01 — Extract Hardcoded Credentials to Environment Variables

**Addresses:** AP-02 (Hardcoded Credentials/Secrets)  
**Risk if skipped:** CRITICAL — credentials committed to VCS

### Python / Flask — Before
```python
# app.py
app.config['SECRET_KEY'] = 'minha-chave-super-secreta-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
ADMIN_PASSWORD = 'admin123'
```

### Python / Flask — After
```python
# config/settings.py
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')          # required — no default
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')  # required — no default
```

```ini
# .env.example
SECRET_KEY=your-random-secret-key-here
DATABASE_URL=sqlite:///app.db
ADMIN_PASSWORD=change-me-in-production
```

```python
# app.py (updated)
from config.settings import Config
app.config.from_object(Config)
```

### Node.js / Express — Before
```javascript
const JWT_SECRET = 'super-secret-jwt-key-123';
const DB_PATH = './database.sqlite';
```

### Node.js / Express — After
```javascript
// config/index.js
require('dotenv').config();
module.exports = {
  jwtSecret: process.env.JWT_SECRET,       // required
  dbPath: process.env.DB_PATH || './database.sqlite',
};
```

**Steps:**
1. Create `config/settings.py` (or `config/index.js`)
2. Move all literals to the config class/object
3. Replace usages with `Config.SECRET_KEY` (or `config.jwtSecret`)
4. Create `.env` with real values (add to `.gitignore`)
5. Create `.env.example` with placeholder values (commit this)
6. Add `python-dotenv` to `requirements.txt` or `dotenv` to `package.json`

---

## RT-02 — Split God File into Domain Modules

**Addresses:** AP-01 (God Class/File)  
**Risk if skipped:** CRITICAL — nothing can be tested or maintained

### Before
```
models.py          # 400 lines: User + Product + Order + Cart all mixed
```

### After
```
models/
├── __init__.py
├── database.py         # Connection only
├── usuario_model.py    # User queries only
├── produto_model.py    # Product queries only
└── pedido_model.py     # Order queries only
```

**Steps:**
1. Create `models/` directory
2. Create `models/database.py` with the connection factory (extracted from wherever `connect()` was called)
3. For each domain entity, create `models/<entity>_model.py`
4. Move all functions/methods related to that entity into its model file
5. Replace imports in `app.py` / routes: `from models.produto_model import ProdutoModel`
6. Delete the original god file after all references are updated

### Template: `models/database.py` (Python / SQLite)
```python
import sqlite3
import os
from flask import g
from config.settings import Config

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(Config.DATABASE_URL)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)
```

---

## RT-03 — Fix SQL Injection with Parameterized Queries

**Addresses:** AP-03 (SQL Injection)  
**Risk if skipped:** CRITICAL — full database compromise possible

### Before
```python
# DANGEROUS — user input directly in query string
email = request.json.get('email')
query = f"SELECT * FROM usuarios WHERE email = '{email}'"
user = db.execute(query).fetchone()
```

```javascript
// DANGEROUS
const query = `SELECT * FROM users WHERE email = '${email}'`;
db.get(query, callback);
```

### After (Python / SQLite)
```python
email = request.json.get('email')
user = db.execute(
    'SELECT * FROM usuarios WHERE email = ?',
    (email,)
).fetchone()
```

### After (Node.js / sqlite3)
```javascript
db.get('SELECT * FROM users WHERE email = ?', [email], callback);
```

### After (Node.js / better-sqlite3)
```javascript
const user = db.prepare('SELECT * FROM users WHERE email = ?').get(email);
```

**Steps:**
1. Find all occurrences of f-strings, string concatenation, or `.format()` in SQL queries
2. Replace the variable portion with `?` (SQLite) or `%s` (psycopg2)
3. Pass values as the second argument tuple/list
4. Verify query still returns correct results

---

## RT-04 — Extract Business Logic from Routes to Controllers

**Addresses:** AP-05 (Business Logic in Controllers/Routes)

### Before
```python
# app.py — route handler doing too much
@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.json
    items = data['items']
    total = 0
    for item in items:
        produto = db.execute('SELECT price FROM produtos WHERE id = ?', (item['id'],)).fetchone()
        total += produto['price'] * item['quantidade']
    if total > 500:
        total = total * 0.9
    pedido_id = db.execute('INSERT INTO pedidos (total, status) VALUES (?, ?)', (total, 'pending')).lastrowid
    db.commit()
    return jsonify({'pedido_id': pedido_id, 'total': total})
```

### After

```python
# models/pedido_model.py
class PedidoModel:
    @staticmethod
    def create(total: float, status: str = 'pending') -> int:
        db = get_db()
        cursor = db.execute(
            'INSERT INTO pedidos (total, status) VALUES (?, ?)', (total, status)
        )
        db.commit()
        return cursor.lastrowid

# controllers/pedido_controller.py
from models.pedido_model import PedidoModel
from models.produto_model import ProdutoModel
from config.settings import Config

class PedidoController:
    @staticmethod
    def process_checkout(items: list) -> dict:
        total = 0.0
        for item in items:
            produto = ProdutoModel.get_by_id(item['id'])
            if not produto:
                raise ValueError(f"Produto {item['id']} não encontrado")
            total += produto['price'] * item['quantidade']

        if total > Config.BULK_DISCOUNT_THRESHOLD:
            total *= (1 - Config.BULK_DISCOUNT_RATE)

        pedido_id = PedidoModel.create(total)
        return {'pedido_id': pedido_id, 'total': round(total, 2)}

# views/pedido_routes.py
from flask import Blueprint, request, jsonify
from controllers.pedido_controller import PedidoController

pedido_bp = Blueprint('pedido', __name__, url_prefix='/pedidos')

@pedido_bp.route('/checkout', methods=['POST'])
def checkout():
    data = request.get_json()
    result = PedidoController.process_checkout(data['items'])
    return jsonify(result), 201
```

---

## RT-05 — Fix N+1 Query with JOIN or Batch Fetch

**Addresses:** AP-08 (N+1 Query Problem)

### Before
```python
# 1 query for orders + N queries for items
orders = db.execute('SELECT * FROM pedidos').fetchall()
result = []
for order in orders:
    items = db.execute('SELECT * FROM itens WHERE pedido_id = ?', (order['id'],)).fetchall()
    result.append({'order': dict(order), 'items': [dict(i) for i in items]})
```

### After — Option A: JOIN query
```python
rows = db.execute('''
    SELECT p.id as pedido_id, p.total, p.status,
           i.id as item_id, i.produto_id, i.quantidade, i.preco_unitario
    FROM pedidos p
    LEFT JOIN itens i ON i.pedido_id = p.id
    ORDER BY p.id
''').fetchall()

# Group in Python
from itertools import groupby
orders = {}
for row in rows:
    pid = row['pedido_id']
    if pid not in orders:
        orders[pid] = {'id': pid, 'total': row['total'], 'items': []}
    if row['item_id']:
        orders[pid]['items'].append({
            'id': row['item_id'], 'quantidade': row['quantidade']
        })
result = list(orders.values())
```

### After — Option B: Batch fetch (when JOIN is complex)
```python
orders = db.execute('SELECT * FROM pedidos').fetchall()
order_ids = [o['id'] for o in orders]
placeholders = ','.join('?' * len(order_ids))
all_items = db.execute(
    f'SELECT * FROM itens WHERE pedido_id IN ({placeholders})', order_ids
).fetchall()

# Group items by order_id
from collections import defaultdict
items_by_order = defaultdict(list)
for item in all_items:
    items_by_order[item['pedido_id']].append(dict(item))

result = [{'order': dict(o), 'items': items_by_order[o['id']]} for o in orders]
```

---

## RT-06 — Add Centralized Error Handler

**Addresses:** AP-09 (Missing Error Handler)

### Python / Flask — Before
```python
# Errors handled (or not) ad-hoc in each route
@app.route('/produtos/<int:id>')
def get_produto(id):
    try:
        # ...
    except:
        return jsonify({'error': 'something went wrong'}), 500  # inconsistent
```

### Python / Flask — After
```python
# middlewares/error_handler.py
from flask import jsonify
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Bad request', 'detail': str(e.description)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({'error': 'Validation error', 'detail': str(e.description)}), 422

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Unhandled 500 error")
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(Exception)
    def unhandled_exception(e):
        logger.exception("Unhandled exception")
        return jsonify({'error': 'Unexpected error'}), 500

# app.py
from middlewares.error_handler import register_error_handlers
register_error_handlers(app)
```

### Node.js / Express — After
```javascript
// middlewares/errorHandler.js
const errorHandler = (err, req, res, next) => {
  const status = err.status || 500;
  const message = err.message || 'Internal Server Error';
  if (status === 500) console.error(err.stack);
  res.status(status).json({ error: message });
};

module.exports = errorHandler;

// app.js — register LAST, after all routes
app.use(errorHandler);
```

---

## RT-07 — Eliminate Code Duplication with Shared Utilities

**Addresses:** AP-10 (Code Duplication)

### Before
```python
# Duplicated in 3 route files
def format_produto(p):
    return {'id': p[0], 'nome': p[1], 'preco': p[2]}

# ... and again in another file ...
def to_produto_dict(produto):
    return {'id': produto[0], 'nome': produto[1], 'preco': produto[2]}
```

### After
```python
# models/produto_model.py — single canonical serializer
@staticmethod
def to_dict(row) -> dict:
    return {'id': row['id'], 'nome': row['name'], 'preco': row['price']}
```

---

## RT-08 — Replace Magic Numbers with Named Constants

**Addresses:** AP-11 (Magic Numbers)

### Before
```python
if total > 500:
    total *= 0.9
time.sleep(300)
if status == 3:
    send_notification()
```

### After
```python
# config/settings.py
BULK_DISCOUNT_THRESHOLD = int(os.environ.get('BULK_DISCOUNT_THRESHOLD', 500))
BULK_DISCOUNT_RATE = float(os.environ.get('BULK_DISCOUNT_RATE', 0.10))
CACHE_TTL_SECONDS = 300
ORDER_STATUS_COMPLETED = 3
```

```python
# controllers/pedido_controller.py
from config.settings import Config

if total > Config.BULK_DISCOUNT_THRESHOLD:
    total *= (1 - Config.BULK_DISCOUNT_RATE)
```

---

## RT-09 — Add Input Validation

**Addresses:** AP-07 (Missing Input Validation)

### Python / Flask — Before
```python
@app.route('/produtos', methods=['POST'])
def create_produto():
    data = request.json
    name = data['name']       # KeyError if missing
    price = data['price']     # No type check
    db.execute('INSERT INTO produtos ...', (name, price))
```

### Python / Flask — After
```python
from flask import abort

@produto_bp.route('/', methods=['POST'])
def create_produto():
    data = request.get_json(silent=True)
    if not data:
        abort(400, 'Request body must be JSON')

    name = data.get('name', '').strip()
    price = data.get('price')

    if not name:
        abort(400, 'Field "name" is required')
    if price is None or not isinstance(price, (int, float)) or price <= 0:
        abort(400, 'Field "price" must be a positive number')

    result = ProdutoController.create_produto(name=name, price=float(price))
    return jsonify(result), 201
```

### Node.js / Express — After
```javascript
router.post('/', (req, res, next) => {
  const { name, price } = req.body;
  if (!name || typeof name !== 'string') {
    return res.status(400).json({ error: '"name" is required and must be a string' });
  }
  if (typeof price !== 'number' || price <= 0) {
    return res.status(400).json({ error: '"price" must be a positive number' });
  }
  ProductController.createProduct(req, res, next);
});
```

---

## RT-10 — Upgrade Deprecated APIs

**Addresses:** AP-04 (Deprecated API Usage)

### Python — Replace `@app.before_first_request` (deprecated Flask 2.3+)

```python
# Before (deprecated)
@app.before_first_request
def setup_db():
    init_db()

# After
def create_app():
    app = Flask(__name__)
    with app.app_context():
        init_db()
    return app
```

### Python — Replace insecure password hashing

```python
# Before (insecure)
import hashlib
password_hash = hashlib.md5(password.encode()).hexdigest()

# After (secure)
import bcrypt
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
# Verify: bcrypt.checkpw(password.encode('utf-8'), password_hash)
```

Add to `requirements.txt`: `bcrypt>=4.0.0`

### Node.js — Replace deprecated `new Buffer()`

```javascript
// Before (deprecated and unsafe)
const buf = new Buffer(userInput);

// After
const buf = Buffer.from(userInput, 'utf8');   // from string
const buf = Buffer.alloc(size);               // zero-filled
const buf = Buffer.allocUnsafe(size);         // performance (uninitialized)
```

### Node.js — Replace `crypto.createCipher` (deprecated)

```javascript
// Before
const cipher = crypto.createCipher('aes-256-cbc', key);

// After (requires explicit IV)
const iv = crypto.randomBytes(16);
const cipher = crypto.createCipheriv('aes-256-cbc', key, iv);
```

---

## Transformation Application Order

When multiple findings exist, apply in this order to avoid broken intermediate states:

1. **RT-01** — Credentials first (safe, no logic change)
2. **RT-02** — Split god file (creates file structure)
3. **RT-03** — Fix SQL injection (safety, within model files)
4. **RT-04** — Extract business logic (depends on models existing)
5. **RT-05** — Fix N+1 queries (within model methods)
6. **RT-06** — Add error handler (independent)
7. **RT-07** — Eliminate duplication (after structure is clean)
8. **RT-08** — Named constants (after config is extracted)
9. **RT-09** — Input validation (after routes are isolated)
10. **RT-10** — Deprecated APIs (independent, low risk)
