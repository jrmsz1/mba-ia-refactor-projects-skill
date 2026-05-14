const { run } = require('./database');

class AuditLogModel {
    static async create(action) {
        await run(
            "INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))",
            [action]
        );
    }
}

module.exports = AuditLogModel;
