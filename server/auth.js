/**
 * 认证与权限：JWT 签发/校验、登录态中间件、角色权限中间件
 * 同时支持 Authorization: Bearer 头 与 ?token= 查询参数（用于附件预览/文件下载）
 */
const jwt = require('jsonwebtoken');
const { db } = require('./db');

const SECRET = 'bx-system-secret-2026-please-change-in-production';

function sign(user) {
  return jwt.sign({ uid: user.id, role: user.role }, SECRET, { expiresIn: '7d' });
}

function currentUser(req) {
  let token = '';
  const h = req.headers.authorization || '';
  if (h.startsWith('Bearer ')) token = h.slice(7);
  if (!token && req.query && req.query.token) token = String(req.query.token);
  if (!token) return null;
  let payload;
  try {
    payload = jwt.verify(token, SECRET);
  } catch (e) {
    return null;
  }
  const user = db.users.find((u) => u.id === payload.uid);
  if (!user || user.status !== 'active') return null;
  return user;
}

function auth(req, res, next) {
  const user = currentUser(req);
  if (!user) return res.status(401).json({ message: '未登录或登录已过期，请重新登录' });
  req.user = user;
  next();
}

function requireRole(...roles) {
  return (req, res, next) => {
    if (!roles.includes(req.user.role)) return res.status(403).json({ message: '无权限执行此操作' });
    next();
  };
}

module.exports = { sign, auth, requireRole };
