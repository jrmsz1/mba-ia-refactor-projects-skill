const { NotFoundError } = require('../utils/errors');

module.exports = (req, res, next) => next(new NotFoundError('Route not found'));
