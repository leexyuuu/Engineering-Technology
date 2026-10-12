/**
 * 用户管理路由（仅超管）
 */
const router = require('express').Router();
const bcrypt = require('bcryptjs');
const { db, save, id, now } = require('../db');
const { requireRole } = require('../auth');

router.use(requireRole('admin'));

function view(u) {
  const dept = db.departments.find((d) => d.id === u.deptId);
  return {
    id: u.id,
    username: u.username,
    realName: u.realName,
    role: u.role,
    deptId: u.deptId,
    deptName: dept ? dept.name : '',
    email: u.email || '',
    phone: u.phone || '',
    status: u.status,
    createdAt: u.createdAt,
  };
}

router.get('/', (req, res) => {
  res.json({ code: 0, data: db.users.map(view) });
});

router.post('/', (req, res) => {
  const { username, realName, role, deptId, password } = req.body || {};
  if (!username || !/^[a-zA-Z0-9_]{3,20}$/.test(username)) return res.status(400).json({ message: '用户名需为 3-20 位字母、数字或下划线' });
  if (db.users.find((u) => u.username === username)) return res.status(400).json({ message: '用户名已存在' });
  if (!realName || !String(realName).trim()) return res.status(400).json({ message: '请填写姓名' });
  if (!['employee', 'manager', 'finance', 'admin'].includes(role)) return res.status(400).json({ message: '角色不合法' });
  if (!db.departments.find((d) => d.id === deptId)) return res.status(400).json({ message: '请选择有效部门' });
  if (!password || String(password).length < 6) return res.status(400).json({ message: '初始密码至少 6 位' });
  const user = {
    id: id('u'),
    username,
    password: bcrypt.hashSync(String(password), 10),
    realName: String(realName).trim(),
    role,
    deptId,
    email: (req.body.email || '').trim(),
    phone: (req.body.phone || '').trim(),
    status: 'active',
    createdAt: now(),
  };
  db.users.push(user);
  save();
  res.json({ code: 0, data: view(user), message: '用户已创建' });
});

router.put('/:id', (req, res) => {
  const user = db.users.find((u) => u.id === req.params.id);
  if (!user) return res.status(404).json({ message: '用户不存在' });
  const { realName, role, deptId, status, email, phone } = req.body || {};
  if (realName !== undefined) {
    if (!String(realName).trim()) return res.status(400).json({ message: '姓名不能为空' });
    user.realName = String(realName).trim();
  }
  if (role !== undefined) {
    if (!['employee', 'manager', 'finance', 'admin'].includes(role)) return res.status(400).json({ message: '角色不合法' });
    if (user.id === req.user.id && role !== 'admin') return res.status(400).json({ message: '不能修改自己的超级管理员角色' });
    user.role = role;
  }
  if (deptId !== undefined) {
    if (!db.departments.find((d) => d.id === deptId)) return res.status(400).json({ message: '请选择有效部门' });
    user.deptId = deptId;
  }
  if (status !== undefined) {
    if (!['active', 'disabled'].includes(status)) return res.status(400).json({ message: '状态不合法' });
    if (user.id === req.user.id && status === 'disabled') return res.status(400).json({ message: '不能停用自己的账号' });
    user.status = status;
  }
  if (email !== undefined) user.email = String(email).trim();
  if (phone !== undefined) user.phone = String(phone).trim();
  save();
  res.json({ code: 0, data: view(user), message: '用户已更新' });
});

router.post('/:id/reset-password', (req, res) => {
  const user = db.users.find((u) => u.id === req.params.id);
  if (!user) return res.status(404).json({ message: '用户不存在' });
  const password = (req.body && req.body.password) || '';
  if (!password || String(password).length < 6) return res.status(400).json({ message: '新密码至少 6 位' });
  user.password = bcrypt.hashSync(String(password), 10);
  save();
  res.json({ code: 0, message: '密码已重置' });
});

module.exports = router;
