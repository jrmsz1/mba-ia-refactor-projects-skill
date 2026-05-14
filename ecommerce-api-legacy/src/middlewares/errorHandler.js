const { HttpError } = require('../utils/errors');

const errorHandler = (err, req, res, next) => {
    if (res.headersSent) return next(err);

    if (err instanceof HttpError) {
        return res.status(err.status).json({ error: err.message });
    }

    console.error('[unhandled]', err);
    return res.status(500).json({ error: 'Internal server error' });
};

module.exports = errorHandler;
