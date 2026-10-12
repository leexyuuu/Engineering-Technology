/**
 * 企业报销管理系统服务端入口
 */
const express = require('express');
const path = require('path');
require('./db'); // 初始化数据库（不存在时自动建种子数据）
const { auth } = require('./auth');

const app = express();
app.use(express.json({ limit: '2mb' }));

// 静态资源（前端页面与本地化的 vendor 库，离线可用；no-cache 保证更新即时生效）
app.use(express.static(path.join(__dirname, '..', 'public'), {
  setHeaders: (res) => res.setHeader('Cache-Control', 'no-cache'),
}));

app.use('/api/auth', require('./routes/auth'));
app.use('/api/departments', auth, require('./routes/departments'));
app.use('/api/reimbursements', auth, require('./routes/reimbursements'));
app.use('/api/approvals', auth, require('./routes/approvals'));
app.use('/api/attachments', auth, require('./routes/attachments'));
app.use('/api/stats', auth, require('./routes/stats'));
app.use('/api/export', auth, require('./routes/export'));
app.use('/api/notifications', auth, require('./routes/notifications'));
app.use('/api/users', auth, require('./routes/users'));
app.use('/api/dashboard', auth, require('./routes/dashboard'));

// 兜底：SPA 使用 hash 路由，未匹配路径回首页
app.get(/^\/(?!api\/).*/, (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
});

// 统一错误处理（含 multer 文件超限等）
app.use((err, req, res, next) => {
  if (err) {
    console.error('[Error]', err.message || err);
    const msg =
      err.code === 'LIMIT_FILE_SIZE'
        ? '文件大小超过限制（最大 10MB）'
        : err.message || '服务器内部错误';
    return res.status(err.status || 500).json({ message: msg });
  }
  next();
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log('========================================');
  console.log('  企业报销管理系统已启动');
  console.log(`  访问地址: http://localhost:${PORT}`);
  console.log('  演示账号（密码均为 123456）:');
  console.log('    员工: emp1   部门负责人: manager1');
  console.log('    财务管理员: finance   超级管理员: admin');
  console.log('========================================');
});
