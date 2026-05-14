const express = require('express');
const checkoutRoutes = require('./checkoutRoutes');
const adminRoutes = require('./adminRoutes');
const userRoutes = require('./userRoutes');

const router = express.Router();

router.use('/checkout', checkoutRoutes);
router.use('/admin', adminRoutes);
router.use('/users', userRoutes);

module.exports = router;
