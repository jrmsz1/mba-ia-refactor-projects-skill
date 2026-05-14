const express = require('express');
const UserController = require('../controllers/UserController');

const router = express.Router();

router.delete('/:id', async (req, res, next) => {
    try {
        const result = await UserController.deleteById(req.params.id);
        res.status(200).json(result);
    } catch (err) {
        next(err);
    }
});

module.exports = router;
