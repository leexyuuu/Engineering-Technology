/**
 * 公共助手：视图组装、权限判断、审批流转辅助、通知与日志
 */
const { db, id, now, todayStr } = require('./db');

/** 终审金额阈值：超过该金额需要超级管理员终审 */
const FINAL_THRESHOLD = 5000;

const EXPENSE_TYPES = ['差旅费', '办公费', '餐费', '交通费', '其他'];

function userName(uid) {
  const u = db.users.find((x) => x.id === uid);
  return u ? u.realName : '未知';
}

function userRole(uid) {
  const u = db.users.find((x) => x.id === uid);
  return u ? u.role : '';
}

function deptName(did) {
  const d = db.departments.find((x) => x.id === did);
  return d ? d.name : '未知部门';
}

/** 报销单可见性：本人 / 本部门负责人 / 财务 / 超管 */
function canViewBill(user, bill) {
  if (['admin', 'finance'].includes(user.role)) return true;
  if (bill.userId === user.id) return true;
  return user.role === 'manager' && bill.deptId === user.deptId;
}

/** 当前用户在当前步骤是否可审批 */
function canApprove(user, bill) {
  if (bill.status === 'pending_dept') {
    return user.role === 'admin' || (user.role === 'manager' && user.deptId === bill.deptId);
  }
  if (bill.status === 'pending_finance') {
    return user.role === 'finance' || user.role === 'admin';
  }
  if (bill.status === 'pending_final') {
    return user.role === 'admin';
  }
  return false;
}

/** 待我审批的报销单（按角色过滤） */
function pendingFor(user) {
  let list = [];
  if (user.role === 'manager') {
    list = db.reimbursements.filter((b) => b.status === 'pending_dept' && b.deptId === user.deptId);
  } else if (user.role === 'finance') {
    list = db.reimbursements.filter((b) => b.status === 'pending_finance');
  } else if (user.role === 'admin') {
    list = db.reimbursements.filter((b) => ['pending_dept', 'pending_finance', 'pending_final'].includes(b.status));
  }
  return list.sort((a, b) => ((a.submittedAt || '') < (b.submittedAt || '') ? -1 : 1));
}

/** 通知指定部门负责人 */
function notifyDeptManagers(bill, title, content) {
  db.users
    .filter((u) => u.role === 'manager' && u.deptId === bill.deptId && u.status === 'active')
    .forEach((u) => db.notifications.push({ id: id('n'), userId: u.id, title, content, billId: bill.id, read: false, createdAt: now() }));
}

/** 通知所有财务 */
function notifyFinance(title, content, bill) {
  db.users
    .filter((u) => u.role === 'finance' && u.status === 'active')
    .forEach((u) => db.notifications.push({ id: id('n'), userId: u.id, title, content, billId: bill.id, read: false, createdAt: now() }));
}

/** 通知所有超管 */
function notifyAdmins(title, content, bill) {
  db.users
    .filter((u) => u.role === 'admin' && u.status === 'active')
    .forEach((u) => db.notifications.push({ id: id('n'), userId: u.id, title, content, billId: bill.id, read: false, createdAt: now() }));
}

/** 通知单据归属人 */
function notifyOwner(bill, title, content) {
  db.notifications.push({ id: id('n'), userId: bill.userId, title, content, billId: bill.id, read: false, createdAt: now() });
}

/** 操作日志（数据留痕） */
function log(billId, userId, action, detail) {
  db.logs.push({ id: id('log'), billId, userId, action, detail, createdAt: now() });
}

/** 通用单据查询过滤（列表 / 导出共用） */
function filterBills(user, q) {
  const scope = q.scope || 'mine';
  let list = db.reimbursements.slice();
  if (scope === 'mine') {
    list = list.filter((b) => b.userId === user.id);
  } else if (scope === 'dept') {
    list = user.role === 'manager' ? list.filter((b) => b.deptId === user.deptId) : list.filter((b) => b.userId === user.id);
  } else if (scope === 'all') {
    if (!['finance', 'admin'].includes(user.role)) return { error: '无权限查看全部报销数据' };
  }
  if (q.status) list = list.filter((b) => b.status === q.status);
  if (q.type) list = list.filter((b) => b.type === q.type);
  if (q.deptId) list = list.filter((b) => b.deptId === q.deptId);
  if (q.keyword) {
    const k = String(q.keyword).toLowerCase();
    list = list.filter(
      (b) =>
        b.billNo.toLowerCase().includes(k) ||
        (b.reason || '').toLowerCase().includes(k) ||
        userName(b.userId).toLowerCase().includes(k)
    );
  }
  if (q.from) list = list.filter((b) => (b.expenseDate || '') >= q.from);
  if (q.to) list = list.filter((b) => (b.expenseDate || '') <= q.to);
  list.sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
  return { list };
}

/** 列表项视图 */
function billListItem(b) {
  return {
    id: b.id,
    billNo: b.billNo,
    type: b.type,
    amount: b.amount,
    reason: b.reason,
    expenseDate: b.expenseDate,
    status: b.status,
    currentStep: b.currentStep,
    rejectReason: b.rejectReason || '',
    userId: b.userId,
    userName: userName(b.userId),
    deptId: b.deptId,
    deptName: deptName(b.deptId),
    attachmentCount: db.attachments.filter((a) => a.billId === b.id).length,
    submittedAt: b.submittedAt || '',
    createdAt: b.createdAt,
    updatedAt: b.updatedAt,
    paidAt: b.paidAt || '',
  };
}

/** 详情视图 */
function billDetail(b) {
  const approvals = db.approvals
    .filter((a) => a.billId === b.id)
    .sort((a, z) => (a.createdAt < z.createdAt ? -1 : 1))
    .map((a) => ({
      id: a.id,
      approverName: userName(a.approverId),
      approverRole: userRole(a.approverId),
      step: a.step,
      action: a.action,
      comment: a.comment,
      createdAt: a.createdAt,
    }));
  const payments = db.payments
    .filter((p) => p.billId === b.id)
    .map((p) => ({ ...p, operatorName: userName(p.operatorId) }));
  const attachments = db.attachments
    .filter((a) => a.billId === b.id)
    .map((a) => ({ id: a.id, fileName: a.fileName, mime: a.mime, size: a.size }));
  const versions = db.versions
    .filter((v) => v.billId === b.id)
    .sort((a, z) => z.version - a.version)
    .map((v) => ({ version: v.version, updatedAt: v.updatedAt, snapshot: v.snapshot }));
  const logs = db.logs
    .filter((l) => l.billId === b.id)
    .sort((a, z) => (a.createdAt < z.createdAt ? 1 : -1))
    .map((l) => ({ id: l.id, action: l.action, detail: l.detail, operator: userName(l.userId), createdAt: l.createdAt }));
  return { ...billListItem(b), version: b.version, approvals, payments, attachments, versions, logs };
}

module.exports = {
  FINAL_THRESHOLD,
  EXPENSE_TYPES,
  userName,
  deptName,
  canViewBill,
  canApprove,
  pendingFor,
  notifyDeptManagers,
  notifyFinance,
  notifyAdmins,
  notifyOwner,
  log,
  filterBills,
  billListItem,
  billDetail,
  todayStr,
};
