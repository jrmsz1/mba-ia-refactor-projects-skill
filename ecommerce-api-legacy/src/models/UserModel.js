const { run, get } = require('./database');

class UserModel {
    static getById(id) {
        return get('SELECT id, name, email FROM users WHERE id = ?', [id]);
    }

    static getByEmail(email) {
        return get('SELECT id, name, email FROM users WHERE email = ?', [email]);
    }

    static async create({ name, email, passwordHash }) {
        const { lastID } = await run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            [name, email, passwordHash]
        );
        return lastID;
    }

    static async delete(id) {
        const { changes } = await run('DELETE FROM users WHERE id = ?', [id]);
        return changes;
    }
}

module.exports = UserModel;
