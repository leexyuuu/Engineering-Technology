/**
 * 报销单路由：创建/编辑/提交/撤回/删除/详情 + 审批通过/驳回/批量审核/打款
 * 状态机：draft → pending_dept → pending_finance →(金额≥5000) pending_final → approved → paid
 *         任意审批步骤可 reject → rejected（可修改后重新提交，历史版本留痕）
 */
const router = require('express').Router();
const fs = require('fs');
const path = require('path');
const { db, save, id, now, todayStr, nextBillNo, UPLOAD_DIR } = require('../db');
const { requireRole } = require('../auth');
const H = require('../helpers');

const moneyText = (n) => '¥' + Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function validate({ type, amount, reason, expenseDate, deptId }) {
  if (!type || !H.EXPENSE_TYPES.includes(type)) return '请选择正确的报销类型';
  const amt = Number(amount);
  if (!isFinite(amt) || amt <= 0) return '报销金额必须大于 0';
  if (amt > 1000000) return '报销金额超出上限（100 万元）';
  if (!reason || !String(reason).trim()) return '请填写报销事由';
  if (String(reason).length > 500) return '报销事由不能超过 500 字';
  if (!expenseDate || !/^\d{4}-\d{2}-\d{2}$/.test(expenseDate)) return '请选择费用发生日期';
  if (expenseDate > todayStr()) return '费用发生日期不能晚于今天';
  if (!db.departments.find((d) => d.id === deptId)) return '请选择有效部门';
  return null;
}

/** 关联附件到单据 */
function linkAttachments(bill, attachmentIds) {
  (attachmentIds || []).forEach((aid) => {
    const att = db.attachments.find((a) => a.id === aid);
    if (att && att.uploaderId === bill.userId && (!att.billId || att.billId === bill.id)) {
      att.billId = bill.id;
    }
  });
}

/** 删除单据附件文件（草稿删除时） */
function removeBillAttachments(billId) {
  db.attachments
    .filter((a) => a.billId === billId)
    .forEach((a) => {
      const p = path.join(UPLOAD_DIR, a.path);
      try { fs.unlinkSync(p); } catch (e) { /* 文件可能已不存在 */ }
    });
  db.attachments = db.attachments.filter((a) => a.billId !== billId);
}

/** 开启审批流：部门负责人提交 / 超管提交 → 跳过部门审核 */
function startFlow(bill, user) {
  bill.submittedAt = now();
  const skipDept = (user.role === 'manager' && user.deptId === bill.deptId) || user.role === 'admin';
  if (skipDept) {
    toFinance(bill);
    H.notifyFinance('待财务审核', `${H.userName(bill.userId)} 提交了报销单 ${bill.billNo}（${bill.type} ${moneyText(bill.amount)}），请财务审核`, bill);
  } else {
    bill.status = 'pending_dept';
    bill.currentStep = 'dept';
    H.notifyDeptManagers(bill, '待审批提醒', `${H.userName(bill.userId)} 提交了报销单 ${bill.billNo}（${bill.type} ${moneyText(bill.amount)}），请及时审批`);
  }
  H.log(bill.id, user.id, '提交审批', `提交报销单 ${bill.billNo}（${moneyText(bill.amount)}）进入审批流程`);
}

function toFinance(bill) {
  bill.status = 'pending_finance';
  bill.currentStep = 'finance';
}

/** 审批通过（按当前状态推进流程） */
function doApprove(bill, user, comment) {
  const step = bill.status;
  db.approvals.push({ id: id('a'), billId: bill.id, approverId: user.id, step, action: 'approve', comment: comment || '', createdAt: now() });
  if (step === 'pending_dept') {
    toFinance(bill);
    H.notifyOwner(bill, '审批进度', `您的报销单 ${bill.billNo} 已通过部门审核，等待财务审核`);
    H.notifyFinance('待财务审核', `${H.userName(bill.userId)} 的报销单 ${bill.billNo} 已通过部门审核，请财务审核`, bill);
  } else if (step === 'pending_finance') {
    if (bill.amount >= H.FINAL_THRESHOLD) {
      bill.status = 'pending_final';
      bill.currentStep = 'final';
      H.notifyOwner(bill, '审批进度', `您的报销单 ${bill.billNo} 已通过财务审核，进入终审`);
      H.notifyAdmins('待终审提醒', `${H.userName(bill.userId)} 的报销单 ${bill.billNo}（${moneyText(bill.amount)}）已通过财务审核，等待终审`, bill);
    } else {
      bill.status = 'approved';
      bill.currentStep = '';
      H.notifyOwner(bill, '审批通过', `您的报销单 ${bill.billNo} 已审批通过，等待财务打款`);
    }
  } else if (step === 'pending_final') {
    bill.status = 'approved';
    bill.currentStep = '';
    H.notifyOwner(bill, '审批通过', `您的报销单 ${bill.billNo} 已终审通过，等待财务打款`);
  }
  H.log(bill.id, user.id, '审批通过', step === 'pending_dept' ? '部门审核通过' : step === 'pending_finance' ? '财务审核通过' : '终审通过', );
}

/** 驳回 */
function doReject(bill, user, reason) {
  const step = bill.status;
  db.approvals.push({ id: id('a'), billId: bill.id, approverId: user.id, step, action: 'reject', comment: reason, createdAt: now() });
  bill.status = 'rejected';
  bill.currentStep = '';
  bill.rejectReason = reason;
  H.notifyOwner(bill, '报销单已驳回', `您的报销单 ${bill.billNo} 已被驳回：${reason}`);
  H.log(bill.id, user.id, '驳回', `于 ${step === 'pending_dept' ? '部门审核' : step === 'pending_finance' ? '财务审核' : '终审'} 环节驳回：${reason}`);
}

/* ---------- 列表 ---------- */
router.get('/', (req, res) => {
  const { list, error } = H.filterBills(req.user, req.query);
  if (error) return res.status(403).json({ message: error });
  res.json({ code: 0, data: list.map(H.billListItem) });
});

/* ---------- 创建 / 编辑（保存草稿或直接提交） ---------- */
router.post('/', (req, res) => {
  const { id: billId, type, amount, reason, expenseDate, deptId, attachmentIds, submit } = req.body || {};
  const err = validate({ type, amount, reason, expenseDate, deptId });
  if (err) return res.status(400).json({ message: err });

  let bill = billId ? db.reimbursements.find((b) => b.id === billId) : null;
  if (bill) {
    if (bill.userId !== req.user.id) return res.status(403).json({ message: '只能操作自己的报销单' });
    if (!['draft', 'rejected'].includes(bill.status)) {
      return res.status(400).json({ message: '该单据已进入审批流程，禁止修改（数据留痕）' });
    }
    // 修改留痕：保存修改前快照
    db.versions.push({ id: id('v'), billId: bill.id, version: bill.version, snapshot: { type: bill.type, amount: bill.amount, reason: bill.reason, expenseDate: bill.expenseDate, deptId: bill.deptId }, updatedAt: now() });
    Object.assign(bill, {
      type, amount: Number(amount), reason: String(reason).trim(), expenseDate, deptId,
      version: (bill.version || 1) + 1,
      updatedAt: now(),
      rejectReason: bill.status === 'rejected' ? bill.rejectReason : '',
    });
    linkAttachments(bill, attachmentIds);
    if (submit) {
      startFlow(bill, req.user);
      save();
      return res.json({ code: 0, data: bill.id, message: '已重新提交审批' });
    }
  } else {
    bill = {
      id: id('r'),
      billNo: nextBillNo(),
      userId: req.user.id,
      deptId,
      type,
      amount: Number(amount),
      reason: String(reason).trim(),
      expenseDate,
      status: 'draft',
      currentStep: '',
      rejectReason: '',
      version: 1,
      submittedAt: '',
      createdAt: now(),
      updatedAt: now(),
      paidAt: '',
    };
    db.reimbursements.push(bill);
    linkAttachments(bill, attachmentIds);
    if (submit) startFlow(bill, req.user);
  }
  save();
  res.json({ code: 0, data: bill.id });
});

/* ---------- 详情 ---------- */
router.get('/:id', (req, res) => {
  const bill = db.reimbursements.find((b) => b.id === req.params.id);
  if (!bill) return res.status(404).json({ message: '报销单不存在' });
  if (!H.canViewBill(req.user, bill)) return res.status(403).json({ message: '无权限查看该报销单' });
  res.json({ code: 0, data: H.billDetail(bill) });
});

/* ---------- 提交草稿 ---------- */
router.post('/:id/submit', (req, res) => {
  const bill = db.reimbursements.find((b) => b.id === req.params.id);
  if (!bill) return res.status(404).json({ message: '报销单不存在' });
  if (bill.userId !== req.user.id) return res.status(403).json({ message: '只能操作自己的报销单' });
  if (bill.status !== 'draft') return res.status(400).json({ message: '仅草稿状态可提交' });
  const err = validate(bill);
  if (err) return res.status(400).json({ message: '草稿信息不完整：' + err });
  startFlow(bill, req.user);
  save();
  res.json({ code: 0, data: bill.id, message: '提交成功' });
});

/* ---------- 撤回（仅部门审核前） ---------- */
router.post('/:id/withdraw', (req, res) => {
  const bill = db.reimbursements.find((b) => b.id === req.params.id);
  if (!bill) return res.status(404).json({ message: '报销单不存在' });
  if (bill.userId !== req.user.id) return res.status(403).json({ message: '只能操作自己的报销单' });
  if (bill.status !== 'pending_dept') return res.status(400).json({ message: '当前状态不可撤回（仅部门审核前可撤回）' });
  bill.status = 'draft';
  bill.currentStep = '';
  bill.updatedAt = now();
  H.log(bill.id, req.user.id, '撤回', '撤回到草稿');
  save();
  res.json({ code: 0, data: bill.id, message: '已撤回到草稿' });
});

/* ---------- 删除草稿 ---------- */
router.delete('/:id', (req, res) => {
  const bill = db.reimbursements.find((b) => b.id === req.params.id);
  if (!bill) return res.status(404).json({ message: '报销单不存在' });
  if (bill.userId !== req.user.id) return res.status(403).json({ message: '只能操作自己的报销单' });
  if (bill.status !== 'draft') return res.status(400).json({ message: '仅草稿状态可删除' });
  removeBillAttachments(bill.id);
  db.reimbursements = db.reimbursements.filter((b) => b.id !== bill.id);
  save();
  res.json({ code: 0, message: '草稿已删除' });
});

/* ---------- 审批通过 ---------- */
router.post('/:id/approve', requireRole('manager', 'finance', 'admin'), (req, res) => {
  const bill = db.reimbursements.find((b) => b.id === req.params.id);
  if (!bill) return res.status(404).json({ message: '报销单不存在' });
  if (!H.canApprove(req.user, bill)) return res.status(403).json({ message: '您无权在当前环节审批该单据' });
  doApprove(bill, req.user, (req.body && req.body.comment) || '');
  save();
  res.json({ code: 0, message: '审批通过' });
});

/* ---------- 驳回 ---------- */
router.post('/:id/reject', requireRole('manager', 'finance', 'admin'), (req, res) => {
  const bill = db.reimbursements.find((b) => b.id === req.params.id);
  if (!bill) return res.status(404).json({ message: '报销单不存在' });
  if (!H.canApprove(req.user, bill)) return res.status(403).json({ message: '您无权在当前环节审批该单据' });
  const reason = (req.body && req.body.comment) || '';
  if (!reason.trim()) return res.status(400).json({ message: '驳回时必须填写驳回原因' });
  doReject(bill, req.user, reason.trim());
  save();
  res.json({ code: 0, message: '已驳回' });
});

/* ---------- 批量审核（财务/超管，仅财务审核环节） ---------- */
router.post('/batch-approve', requireRole('finance', 'admin'), (req, res) => {
  const ids = (req.body && req.body.ids) || [];
  const comment = (req.body && req.body.comment) || '批量审核通过';
  if (!ids.length) return res.status(400).json({ message: '请先选择要审核的单据' });
  let ok = 0;
  const skipped = [];
  for (const bid of ids) {
    const bill = db.reimbursements.find((b) => b.id === bid);
    if (!bill || bill.status !== 'pending_finance') { skipped.push(bill ? bill.billNo : bid); continue; }
    doApprove(bill, req.user, comment);
    ok += 1;
  }
  save();
  res.json({ code: 0, data: { ok, skipped }, message: `批量通过 ${ok} 单${skipped.length ? `，跳过 ${skipped.length} 单（非财务审核环节）` : ''}` });
});

/* ---------- 登记打款 ---------- */
router.post('/:id/payment', requireRole('finance', 'admin'), (req, res) => {
  const bill = db.reimbursements.find((b) => b.id === req.params.id);
  if (!bill) return res.status(404).json({ message: '报销单不存在' });
  if (bill.status !== 'approved') return res.status(400).json({ message: '仅「审核通过」的单据可登记打款' });
  const { payMethod, remark } = req.body || {};
  bill.status = 'paid';
  bill.currentStep = '';
  bill.paidAt = now();
  bill.updatedAt = now();
  db.payments.push({ id: id('p'), billId: bill.id, operatorId: req.user.id, amount: bill.amount, payMethod: payMethod || '银行转账', remark: remark || '', createdAt: now() });
  H.notifyOwner(bill, '打款完成', `您的报销单 ${bill.billNo} 已完成打款 ${moneyText(bill.amount)}`);
  H.log(bill.id, req.user.id, '登记打款', `${payMethod || '银行转账'} ${moneyText(bill.amount)}${remark ? '，备注：' + remark : ''}`);
  save();
  res.json({ code: 0, message: '打款登记完成' });
});

module.exports = router;
