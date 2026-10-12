/**
 * 认证路由：登录、个人信息、修改资料、修改密码
 */
const router = require('express').Router();
const bcrypt = require('bcryptjs');
const { db, save } = require('../db');
const { sign, auth } = require('../auth');

function publicUser(u) {
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
  };
}

router.post('/login', (req, res) => {
  const { username, password } = req.body || {};
  const user = db.users.find((u) => u.username === username);
  if (!user || !bcrypt.compareSync(password || '', user.password)) {
    return res.status(400).json({ message: '用户名或密码错误' });
  }
  if (user.status !== 'active') return res.status(403).json({ message: '账号已被停用，请联系管理员' });
  res.json({ code: 0, data: { token: sign(user), user: publicUser(user) } });
});

router.get('/me', auth, (req, res) => {
  res.json({ code: 0, data: { user: publicUser(req.user) } });
});

router.put('/profile', auth, (req, res) => {
  const { realName, email, phone } = req.body || {};
  if (!realName || !String(realName).trim()) return res.status(400).json({ message: '姓名不能为空' });
  req.user.realName = String(realName).trim();
  req.user.email = email || '';
  req.user.phone = phone || '';
  save();
  res.json({ code: 0, data: { user: publicUser(req.user) }, message: '资料已更新' });
});

router.put('/password', auth, (req, res) => {
  const { oldPassword, newPassword } = req.body || {};
  if (!bcrypt.compareSync(oldPassword || '', req.user.password)) return res.status(400).json({ message: '原密码错误' });
  if (!newPassword || String(newPassword).length < 6) return res.status(400).json({ message: '新密码至少 6 位' });
  req.user.password = bcrypt.hashSync(String(newPassword), 10);
  save();
  res.json({ code: 0, message: '密码修改成功' });
});

module.exports = router;
