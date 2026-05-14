const UserModel = require('../models/UserModel');
const EnrollmentModel = require('../models/EnrollmentModel');
const PaymentModel = require('../models/PaymentModel');
const { withTransaction } = require('../models/database');
const { BadRequestError, NotFoundError } = require('../utils/errors');

class UserController {
    static async deleteById(rawId) {
        const id = parseInt(rawId, 10);
        if (!Number.isInteger(id) || id <= 0) {
            throw new BadRequestError('Invalid user id');
        }

        const user = await UserModel.getById(id);
        if (!user) throw new NotFoundError('Usuário não encontrado');

        await withTransaction(async () => {
            const enrollments = await EnrollmentModel.listIdsByUserId(id);
            const enrollmentIds = enrollments.map((e) => e.id);
            await PaymentModel.deleteByEnrollmentIds(enrollmentIds);
            await EnrollmentModel.deleteByUserId(id);
            await UserModel.delete(id);
        });

        return { msg: 'Usuário deletado com sucesso' };
    }
}

module.exports = UserController;
