const UserModel = require('../models/UserModel');
const CourseModel = require('../models/CourseModel');
const EnrollmentModel = require('../models/EnrollmentModel');
const PaymentModel = require('../models/PaymentModel');
const AuditLogModel = require('../models/AuditLogModel');
const { withTransaction } = require('../models/database');
const password = require('../utils/password');
const { authorize, PaymentStatus } = require('../services/paymentService');
const { BadRequestError, NotFoundError, PaymentDeniedError } = require('../utils/errors');

class CheckoutController {
    static async process({ name, email, plainPassword, courseId, card }) {
        if (!name || !email || !plainPassword || !courseId || !card) {
            throw new BadRequestError('Bad Request');
        }

        const course = await CourseModel.getActiveById(courseId);
        if (!course) throw new NotFoundError('Curso não encontrado');

        const status = authorize({ card });
        if (status !== PaymentStatus.PAID) throw new PaymentDeniedError();

        const existingUser = await UserModel.getByEmail(email);

        const enrollmentId = await withTransaction(async () => {
            let userId;
            if (existingUser) {
                userId = existingUser.id;
            } else {
                const passwordHash = await password.hash(plainPassword);
                userId = await UserModel.create({ name, email, passwordHash });
            }

            const enrId = await EnrollmentModel.create({ userId, courseId: course.id });
            await PaymentModel.create({ enrollmentId: enrId, amount: course.price, status });
            await AuditLogModel.create(`Checkout curso ${course.id} por ${userId}`);
            return enrId;
        });

        return { msg: 'Sucesso', enrollment_id: enrollmentId };
    }
}

module.exports = CheckoutController;
