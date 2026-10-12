/**
 * 附件路由：上传（JPG/PNG/PDF，≤10MB）、预览/下载、删除
 */
const router = require('express').Router();
const multer = require('multer');
const crypto = require('crypto');
const path = require('path');
const fs = require('fs');
const { db, save, id, now, UPLOAD_DIR } = require('../db');
const H = require('../helpers');

const ALLOWED = { 'image/jpeg': '.jpg', 'image/png': '.png', 'application/pdf': '.pdf' };
const MAX_SIZE = 10 * 1024 * 1024;

const upload = multer({
  storage: multer.diskStorage({
    destination: UPLOAD_DIR,
    filename: (req, file, cb) => cb(null, crypto.randomUUID() + (ALLOWED[file.mimetype] || '')),
  }),
  limits: { fileSize: MAX_SIZE },
  fileFilter: (req, file, cb) => {
    if (!ALLOWED[file.mimetype]) return cb(new Error('仅支持 JPG / PNG 图片和 PDF 文件'));
    cb(null, true);
  },
});

/** 修正中文文件名乱码（multipart 默认 latin1 解码） */
function fixName(name) {
  if (!name) return '未命名';
  const needFix = /^[\x00-\xff]*$/.test(name) && /[^\x20-\x7e]/.test(name);
  return needFix ? Buffer.from(name, 'latin1').toString('utf8') : name;
}

router.post('/', upload.single('file'), (req, res) => {
  if (!req.file) return res.status(400).json({ message: '请选择文件' });
  const att = {
    id: id('f'),
    billId: null,
    uploaderId: req.user.id,
    fileName: fixName(req.file.originalname),
    path: req.file.filename,
    mime: req.file.mimetype,
    size: req.file.size,
    createdAt: now(),
  };
  db.attachments.push(att);
  save();
  res.json({ code: 0, data: { id: att.id, fileName: att.fileName, mime: att.mime, size: att.size } });
});

function findAndCheck(req, res) {
  const att = db.attachments.find((a) => a.id === req.params.id);
  if (!att) { res.status(404).json({ message: '附件不存在' }); return null; }
  let ok = att.uploaderId === req.user.id;
  if (!ok && att.billId) {
    const bill = db.reimbursements.find((b) => b.id === att.billId);
    ok = bill && H.canViewBill(req.user, bill);
  }
  if (!ok) { res.status(403).json({ message: '无权限访问该附件' }); return null; }
  const filePath = path.join(UPLOAD_DIR, att.path);
  if (!fs.existsSync(filePath)) { res.status(404).json({ message: '附件文件已丢失' }); return null; }
  return att;
}

/* 预览 / 下载（支持 ?token= 鉴权，便于 <img> 与新窗口打开） */
router.get('/:id', (req, res) => {
  const att = findAndCheck(req, res);
  if (!att) return;
  res.setHeader('Content-Type', att.mime);
  res.setHeader('Content-Disposition', `inline; filename*=UTF-8''${encodeURIComponent(att.fileName)}`);
  res.sendFile(path.join(UPLOAD_DIR, att.path));
});

/* 删除（仅上传人；单据已提交后不可删） */
router.delete('/:id', (req, res) => {
  const att = db.attachments.find((a) => a.id === req.params.id);
  if (!att) return res.status(404).json({ message: '附件不存在' });
  if (att.uploaderId !== req.user.id) return res.status(403).json({ message: '只能删除自己上传的附件' });
  if (att.billId) {
    const bill = db.reimbursements.find((b) => b.id === att.billId);
    if (bill && !['draft', 'rejected'].includes(bill.status)) {
      return res.status(400).json({ message: '单据已提交审批，附件不可删除（数据留痕）' });
    }
  }
  const p = path.join(UPLOAD_DIR, att.path);
  try { fs.unlinkSync(p); } catch (e) { /* 忽略 */ }
  db.attachments = db.attachments.filter((a) => a.id !== att.id);
  save();
  res.json({ code: 0, message: '附件已删除' });
});

module.exports = router;
