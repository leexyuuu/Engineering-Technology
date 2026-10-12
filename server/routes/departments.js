/**
 * 部门路由：所有登录用户可查询；超管可增改
 */
const router = require('express').Router();
const { db, save, id, now } = require('../db');
const { requireRole } = require('../auth');

router.get('/', (req, res) => {
  res.json({ code: 0, data: db.departments });
});

router.post('/', requireRole('admin'), (req, res) => {
  const name = String((req.body && req.body.name) || '').trim();
  if (!name) return res.status(400).json({ message: '部门名称不能为空' });
  if (db.departments.find((d) => d.name === name)) return res.status(400).json({ message: '部门已存在' });
  const dept = { id: id('d'), name };
  db.departments.push(dept);
  save();
  res.json({ code: 0, data: dept, message: '部门已创建' });
});

router.put('/:id', requireRole('admin'), (req, res) => {
  const dept = db.departments.find((d) => d.id === req.params.id);
  if (!dept) return res.status(404).json({ message: '部门不存在' });
  const name = String((req.body && req.body.name) || '').trim();
  if (!name) return res.status(400).json({ message: '部门名称不能为空' });
  dept.name = name;
  save();
  res.json({ code: 0, message: '部门已更新' });
});

module.exports = router;
