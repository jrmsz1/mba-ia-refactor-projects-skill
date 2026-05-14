const bcrypt = require('bcrypt');
const config = require('../config');

const hash = (plain) => bcrypt.hash(plain, config.bcryptRounds);
const verify = (plain, stored) => bcrypt.compare(plain, stored);

module.exports = { hash, verify };
