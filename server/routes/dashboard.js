/**
 * 首页数据概览路由（按角色返回不同口径）
 */
const router = require('express').Router();
const { db } = require('../db');
const H = require('../helpers');

router.get('/', (req, res) => {
  const user = req.user;
  const monthPrefix = H.todayStr().slice(0, 7);
  const mine = db.reimbursements.filter((b) => b.userId === user.id);

  const myPendingCount = mine.filter((b) => ['pending_dept', 'pending_finance', 'pending_final'].includes(b.status)).length;
  const myPaidTotal = mine
    .filter((b) => b.status === 'paid' && (b.paidAt || '').startsWith(monthPrefix))
    .reduce((s, b) => s + b.amount, 0);
  const monthTotalAll = db.reimbursements
    .filter((b) => ['approved', 'paid'].includes(b.status) && (b.expenseDate || '').startsWith(monthPrefix))
    .reduce((s, b) => s + b.amount, 0);
  const monthCountMine = mine.filter((b) => (b.submittedAt || '').startsWith(monthPrefix)).length;
  const draftCount = mine.filter((b) => b.status === 'draft').length;

  const recent = mine
    .sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1))
    .slice(0, 6)
    .map(H.billListItem);

  let todoApprovals = [];
  let todoCount = 0;
  if (['manager', 'finance', 'admin'].includes(user.role)) {
    const pending = H.pendingFor(user);
    todoCount = pending.length;
    todoApprovals = pending.slice(0, 6).map(H.billListItem);
  }

  res.json({
    code: 0,
    data: { myPendingCount, myPaidTotal, monthTotalAll, monthCountMine, draftCount, recent, todoApprovals, todoCount },
  });
});

module.exports = router;
