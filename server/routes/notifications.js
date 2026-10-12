/**
 * 通知路由：我的通知列表、未读数、标记已读
 */
const router = require('express').Router();
const { db, save } = require('../db');

router.get('/', (req, res) => {
  const items = db.notifications
    .filter((n) => n.userId === req.user.id)
    .sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1))
    .slice(0, 50);
  res.json({ code: 0, data: items });
});

router.get('/unread-count', (req, res) => {
  const count = db.notifications.filter((n) => n.userId === req.user.id && !n.read).length;
  res.json({ code: 0, data: { count } });
});

router.post('/read', (req, res) => {
  const { ids, all } = req.body || {};
  db.notifications.forEach((n) => {
    if (n.userId !== req.user.id) return;
    if (all || (Array.isArray(ids) && ids.includes(n.id))) n.read = true;
  });
  save();
  const count = db.notifications.filter((n) => n.userId === req.user.id && !n.read).length;
  res.json({ code: 0, data: { count } });
});

module.exports = router;
