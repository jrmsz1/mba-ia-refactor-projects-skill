# MVC Architecture Guidelines

Use this reference during **Phase 3** to design the target MVC structure. The goal is a clean, testable, maintainable layered architecture.

---

## Core Principle

**Each layer has ONE responsibility.** If a component is doing two jobs, it belongs in two places.

| Layer | Responsibility | Must NOT contain |
|-------|---------------|-----------------|
| Model | Data access + data shape | HTTP logic, response formatting, business rules |
| Controller | Business logic + orchestration | DB queries, HTTP details (`request`, `response` objects) |
| View / Routes | HTTP handling + routing | Business rules, DB queries, complex data transformations |
| Config | Environment + settings | Application logic |
| Middleware | Cross-cutting concerns | Domain logic |

---

## Target Directory Structure

### Python / Flask

```
src/
├── config/
│   └── settings.py          # All env-based configuration
├── models/
│   ├── __init__.py
│   ├── database.py          # DB connection factory
│   ├── usuario_model.py     # One file per domain entity
│   ├── produto_model.py
│   └── pedido_model.py
├── controllers/
│   ├── __init__.py
│   ├── usuario_controller.py
│   ├── produto_controller.py
│   └── pedido_controller.py
├── views/                   # or routes/
│   ├── __init__.py
│   ├── usuario_routes.py
│   ├── produto_routes.py
│   └── pedido_routes.py
├── middlewares/
│   ├── __init__.py
│   ├── auth.py
│   └── error_handler.py
├── app.py                   # Composition root only
└── .env.example
```

### Node.js / Express

```
src/
├── config/
│   └── index.js             # All env-based configuration
├── models/
│   ├── database.js          # DB connection / pool
│   ├── UserModel.js
│   ├── ProductModel.js
│   └── OrderModel.js
├── controllers/
│   ├── UserController.js
│   ├── ProductController.js
│   └── OrderController.js
├── routes/
│   ├── index.js             # Route aggregator
│   ├── userRoutes.js
│   ├── productRoutes.js
│   └── orderRoutes.js
├── middlewares/
│   ├── auth.js
│   └── errorHandler.js
└── app.js                   # Composition root only
```

---

## Layer Rules — Python / Flask

### `config/settings.py`
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-fallback')
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    # Domain-specific config
    BULK_DISCOUNT_THRESHOLD = int(os.environ.get('BULK_DISCOUNT_THRESHOLD', 500))
    BULK_DISCOUNT_RATE = float(os.environ.get('BULK_DISCOUNT_RATE', 0.10))
```

**Rules:**
- Never import Flask `app` here
- All values come from `os.environ.get()`; provide safe defaults only for non-secrets
- Secrets (SECRET_KEY, passwords, API keys) must NOT have non-empty defaults

---

### `models/<entity>_model.py`

```python
# models/produto_model.py
from models.database import get_db

class ProdutoModel:
    @staticmethod
    def get_all():
        db = get_db()
        return db.execute('SELECT id, name, price, stock FROM produtos').fetchall()

    @staticmethod
    def get_by_id(produto_id: int):
        db = get_db()
        return db.execute(
            'SELECT id, name, price, stock FROM produtos WHERE id = ?',
            (produto_id,)
        ).fetchone()

    @staticmethod
    def create(name: str, price: float, stock: int):
        db = get_db()
        cursor = db.execute(
            'INSERT INTO produtos (name, price, stock) VALUES (?, ?, ?)',
            (name, price, stock)
        )
        db.commit()
        return cursor.lastrowid
```

**Rules:**
- ONLY DB interaction — no business logic, no HTTP objects
- Always use parameterized queries (`?` for SQLite, `%s` for psycopg2) — never string interpolation
- Return raw data (dict, list, Row object) — do NOT return HTTP responses
- One class per entity; methods are static or class methods if no instance state needed

---

### `controllers/<entity>_controller.py`

```python
# controllers/produto_controller.py
from models.produto_model import ProdutoModel
from config.settings import Config

class ProdutoController:
    @staticmethod
    def list_produtos():
        produtos = ProdutoModel.get_all()
        return [{'id': p['id'], 'nome': p['name'], 'preco': p['price']} for p in produtos]

    @staticmethod
    def get_produto(produto_id: int):
        produto = ProdutoModel.get_by_id(produto_id)
        if not produto:
            return None, 'Produto não encontrado'
        return {'id': produto['id'], 'nome': produto['name'], 'preco': produto['price']}, None

    @staticmethod
    def apply_discount(total: float) -> float:
        if total > Config.BULK_DISCOUNT_THRESHOLD:
            return total * (1 - Config.BULK_DISCOUNT_RATE)
        return total
```

**Rules:**
- Import from `models/` and `config/` — NEVER import Flask's `request` or `jsonify`
- Return plain Python objects (dict, list, tuple) — NOT HTTP responses
- Business rules belong here (discounts, validations, orchestration)
- No raw SQL — always delegate to the Model

---

### `views/<entity>_routes.py`

```python
# views/produto_routes.py
from flask import Blueprint, request, jsonify
from controllers.produto_controller import ProdutoController

produto_bp = Blueprint('produto', __name__, url_prefix='/produtos')

@produto_bp.route('/', methods=['GET'])
def list_produtos():
    produtos = ProdutoController.list_produtos()
    return jsonify(produtos), 200

@produto_bp.route('/<int:produto_id>', methods=['GET'])
def get_produto(produto_id):
    produto, error = ProdutoController.get_produto(produto_id)
    if error:
        return jsonify({'error': error}), 404
    return jsonify(produto), 200
```

**Rules:**
- Import from `controllers/` — NEVER import from `models/` directly
- Max ~10 lines per route handler
- Only HTTP concerns: parse `request`, call controller, return `jsonify()`
- Use `Blueprint` — never define routes directly on the `app` object

---

### `middlewares/error_handler.py`

```python
# middlewares/error_handler.py
from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Bad request', 'detail': str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(Exception)
    def unhandled(e):
        import logging
        logging.exception(e)
        return jsonify({'error': 'Unexpected error'}), 500
```

---

### `app.py` — Composition Root

```python
# app.py
from flask import Flask
from config.settings import Config
from views.produto_routes import produto_bp
from views.usuario_routes import usuario_bp
from views.pedido_routes import pedido_bp
from middlewares.error_handler import register_error_handlers

def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)

    # Register blueprints
    app.register_blueprint(produto_bp)
    app.register_blueprint(usuario_bp)
    app.register_blueprint(pedido_bp)

    # Register error handlers
    register_error_handlers(app)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=Config.DEBUG)
```

**Rules:**
- ZERO business logic here
- ZERO route definitions here
- ZERO DB queries here
- Only: create app, register blueprints, register middleware, run

---

## Layer Rules — Node.js / Express

### `config/index.js`
```javascript
require('dotenv').config();

module.exports = {
  port: process.env.PORT || 3000,
  jwtSecret: process.env.JWT_SECRET,          // No default for secrets!
  databaseUrl: process.env.DATABASE_URL || './database.sqlite',
  nodeEnv: process.env.NODE_ENV || 'development',
};
```

### `models/ProductModel.js`
```javascript
const db = require('./database');

class ProductModel {
  static async getAll() {
    return db.all('SELECT id, name, price, stock FROM products');
  }

  static async getById(id) {
    return db.get('SELECT * FROM products WHERE id = ?', [id]);
  }

  static async create({ name, price, stock }) {
    const result = await db.run(
      'INSERT INTO products (name, price, stock) VALUES (?, ?, ?)',
      [name, price, stock]
    );
    return result.lastID;
  }
}

module.exports = ProductModel;
```

### `controllers/ProductController.js`
```javascript
const ProductModel = require('../models/ProductModel');

class ProductController {
  static async listProducts(req, res, next) {
    try {
      const products = await ProductModel.getAll();
      res.json(products);
    } catch (err) {
      next(err);
    }
  }

  static async getProduct(req, res, next) {
    try {
      const product = await ProductModel.getById(req.params.id);
      if (!product) return res.status(404).json({ error: 'Product not found' });
      res.json(product);
    } catch (err) {
      next(err);
    }
  }
}

module.exports = ProductController;
```

### `routes/productRoutes.js`
```javascript
const express = require('express');
const ProductController = require('../controllers/ProductController');

const router = express.Router();

router.get('/', ProductController.listProducts);
router.get('/:id', ProductController.getProduct);

module.exports = router;
```

### `middlewares/errorHandler.js`
```javascript
module.exports = (err, req, res, next) => {
  console.error(err.stack);
  res.status(err.status || 500).json({
    error: err.message || 'Internal Server Error',
  });
};
```

### `app.js` — Composition Root
```javascript
const express = require('express');
const config = require('./config');
const productRoutes = require('./routes/productRoutes');
const errorHandler = require('./middlewares/errorHandler');

const app = express();

app.use(express.json());
app.use('/products', productRoutes);
app.use(errorHandler);

app.listen(config.port, () => {
  console.log(`Server running on port ${config.port}`);
});

module.exports = app;
```

---

## Validation Checklist (Phase 3 Exit Criteria)

Before marking Phase 3 complete, verify:

- [ ] Every secret/credential is loaded from environment variable
- [ ] `.env.example` lists all required variables
- [ ] No raw SQL inside any controller or route file
- [ ] No business logic inside any route/view file
- [ ] No DB imports inside controller files (controllers use models only)
- [ ] One Blueprint/Router per domain entity
- [ ] Centralized error handler registered
- [ ] `app.py` / `app.js` contains only composition (no logic)
- [ ] All original endpoints still reachable
- [ ] Application boots without errors or warnings
