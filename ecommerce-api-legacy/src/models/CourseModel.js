const { get } = require('./database');

class CourseModel {
    static getActiveById(id) {
        return get('SELECT id, title, price FROM courses WHERE id = ? AND active = 1', [id]);
    }
}

module.exports = CourseModel;
