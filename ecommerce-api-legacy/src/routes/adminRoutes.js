const express = require('express');
const AdminController = require('../controllers/AdminController');

const router = express.Router();

router.get('/financial-report', async (req, res, next) => {
    try {
        const report = await AdminController.financialReport();
        res.status(200).json(report);
    } catch (err) {
        next(err);
    }
});

module.exports = router;
