const PaymentStatus = Object.freeze({
    PAID: 'PAID',
    DENIED: 'DENIED',
});

const APPROVED_CARD_PREFIX = '4';

const authorize = ({ card }) => {
    const approved = typeof card === 'string' && card.startsWith(APPROVED_CARD_PREFIX);
    return approved ? PaymentStatus.PAID : PaymentStatus.DENIED;
};

module.exports = { PaymentStatus, authorize };
