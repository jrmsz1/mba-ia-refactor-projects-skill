const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const config = require('../config');

const db = new sqlite3.Database(config.databaseUrl);

const run = (sql, params = []) => new Promise((resolve, reject) => {
    db.run(sql, params, function (err) {
        if (err) return reject(err);
        resolve({ lastID: this.lastID, changes: this.changes });
    });
});

const get = (sql, params = []) => new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
});

const all = (sql, params = []) => new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
});

const withTransaction = async (fn) => {
    await run('BEGIN');
    try {
        const result = await fn();
        await run('COMMIT');
        return result;
    } catch (err) {
        await run('ROLLBACK').catch(() => {});
        throw err;
    }
};

const initSchema = async () => {
    await run(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        pass TEXT NOT NULL
    )`);
    await run(`CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        price REAL NOT NULL,
        active INTEGER NOT NULL DEFAULT 1
    )`);
    await run(`CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (course_id) REFERENCES courses(id)
    )`);
    await run(`CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY,
        enrollment_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (enrollment_id) REFERENCES enrollments(id)
    )`);
    await run(`CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY,
        action TEXT NOT NULL,
        created_at DATETIME NOT NULL
    )`);
};

const seed = async () => {
    const existing = await get('SELECT id FROM users WHERE email = ?', ['leonan@fullcycle.com.br']);
    if (existing) return;

    const hash = await bcrypt.hash(config.seedAdminPassword, config.bcryptRounds);
    await run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', ['Leonan', 'leonan@fullcycle.com.br', hash]);
    await run(
        'INSERT INTO courses (title, price, active) VALUES (?, ?, 1), (?, ?, 1)',
        ['Clean Architecture', 997.0, 'Docker', 497.0]
    );
    await run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [1, 1]);
    await run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [1, 997.0, 'PAID']);
};

const init = async () => {
    await initSchema();
    await seed();
};

module.exports = { db, run, get, all, withTransaction, init };
