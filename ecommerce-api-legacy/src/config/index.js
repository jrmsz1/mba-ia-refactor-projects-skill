require('dotenv').config();

const required = (name) => {
    const value = process.env[name];
    if (value === undefined || value === '') {
        throw new Error(`Missing required environment variable: ${name}`);
    }
    return value;
};

module.exports = {
    port: parseInt(process.env.PORT, 10) || 3000,
    nodeEnv: process.env.NODE_ENV || 'development',

    databaseUrl: process.env.DATABASE_URL || ':memory:',

    paymentGatewayKey: required('PAYMENT_GATEWAY_KEY'),
    smtpUser: process.env.SMTP_USER || 'no-reply@example.com',

    bcryptRounds: parseInt(process.env.BCRYPT_ROUNDS, 10) || 10,
    seedAdminPassword: process.env.SEED_ADMIN_PASSWORD || 'change-me',
};
