class HttpError extends Error {
    constructor(status, message) {
        super(message);
        this.status = status;
        this.name = this.constructor.name;
    }
}

class BadRequestError extends HttpError {
    constructor(message) { super(400, message); }
}

class NotFoundError extends HttpError {
    constructor(message) { super(404, message); }
}

class PaymentDeniedError extends HttpError {
    constructor(message = 'Pagamento recusado') { super(400, message); }
}

module.exports = { HttpError, BadRequestError, NotFoundError, PaymentDeniedError };
