const { run } = require('./database');

class PaymentModel {
    static async create({ enrollmentId, amount, status }) {
        const { lastID } = await run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, amount, status]
        );
        return lastID;
    }

    static async deleteByEnrollmentIds(enrollmentIds) {
        if (!enrollmentIds.length) return 0;
        const placeholders = enrollmentIds.map(() => '?').join(',');
        const { changes } = await run(
            `DELETE FROM payments WHERE enrollment_id IN (${placeholders})`,
            enrollmentIds
        );
        return changes;
    }
}

module.exports = PaymentModel;
