const { run, all } = require('./database');

class EnrollmentModel {
    static async create({ userId, courseId }) {
        const { lastID } = await run(
            'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
            [userId, courseId]
        );
        return lastID;
    }

    static listIdsByUserId(userId) {
        return all('SELECT id FROM enrollments WHERE user_id = ?', [userId]);
    }

    static async deleteByUserId(userId) {
        const { changes } = await run('DELETE FROM enrollments WHERE user_id = ?', [userId]);
        return changes;
    }
}

module.exports = EnrollmentModel;
