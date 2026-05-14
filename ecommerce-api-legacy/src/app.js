const express = require('express');
const config = require('./config');
const database = require('./models/database');
const apiRoutes = require('./routes');
const errorHandler = require('./middlewares/errorHandler');
const notFoundHandler = require('./middlewares/notFoundHandler');

const createApp = () => {
    const app = express();
    app.use(express.json());
    app.use('/api', apiRoutes);
    app.use(notFoundHandler);
    app.use(errorHandler);
    return app;
};

const start = async () => {
    await database.init();
    const app = createApp();
    app.listen(config.port, () => {
        console.log(`LMS API rodando na porta ${config.port}...`);
    });
};

if (require.main === module) {
    start().catch((err) => {
        console.error('Failed to start application:', err);
        process.exit(1);
    });
}

module.exports = { createApp, start };
