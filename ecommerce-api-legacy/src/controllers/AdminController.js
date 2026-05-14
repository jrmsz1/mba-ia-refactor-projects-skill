const ReportModel = require('../models/ReportModel');
const { PaymentStatus } = require('../services/paymentService');

class AdminController {
    static async financialReport() {
        const rows = await ReportModel.getFinancialReport();
        const courses = new Map();

        for (const row of rows) {
            if (!courses.has(row.course_id)) {
                courses.set(row.course_id, {
                    course: row.course_title,
                    revenue: 0,
                    students: [],
                });
            }
            if (row.enrollment_id == null) continue;

            const courseEntry = courses.get(row.course_id);
            const paid = row.payment_status === PaymentStatus.PAID ? row.payment_amount : 0;
            if (paid) courseEntry.revenue += paid;

            courseEntry.students.push({
                student: row.student_name || 'Unknown',
                paid: row.payment_amount || 0,
            });
        }

        return Array.from(courses.values());
    }
}

module.exports = AdminController;
