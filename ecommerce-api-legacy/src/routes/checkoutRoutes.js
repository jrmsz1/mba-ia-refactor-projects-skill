const express = require('express');
const CheckoutController = require('../controllers/CheckoutController');

const router = express.Router();

router.post('/', async (req, res, next) => {
    try {
        const { usr, eml, pwd, c_id, card } = req.body || {};
        const result = await CheckoutController.process({
            name: usr,
            email: eml,
            plainPassword: pwd,
            courseId: c_id,
            card,
        });
        res.status(200).json(result);
    } catch (err) {
        next(err);
    }
});

module.exports = router;
