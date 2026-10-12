/**
 * 数据统计路由（财务 / 超管）：汇总、部门维度、类型维度、月度趋势
 * 统计口径：已审核通过 + 已打款 的单据
 */
const router = require('express').Router();
const { db } = require('../db');
const { requireRole } = require('../auth');
const H = require('../helpers');

router.use(requireRole('finance', 'admin'));

function inRange(b, q) {
  if (q.from && (b.expenseDate || '') < q.from) return false;
  if (q.to && (b.expenseDate || '') > q.to) return false;
  if (q.deptId && b.deptId !== q.deptId) return false;
  return true;
}

const valid = (b) => ['approved', 'paid'].includes(b.status);

router.get('/summary', (req, res) => {
  const q = req.query;
  const all = db.reimbursements.filter((b) => b.status !== 'draft' && inRange(b, q));
  const passed = all.filter(valid);
  res.json({
    code: 0,
    data: {
      totalAmount: passed.reduce((s, b) => s + b.amount, 0),
      totalCount: passed.length,
      paidAmount: all.filter((b) => b.status === 'paid').reduce((s, b) => s + b.amount, 0),
      submittedCount: all.length,
      pendingCount: all.filter((b) => ['pending_dept', 'pending_finance', 'pending_final'].includes(b.status)).length,
      rejectedCount: all.filter((b) => b.status === 'rejected').length,
    },
  });
});

router.get('/by-dept', (req, res) => {
  const q = req.query;
  const map = new Map();
  db.reimbursements
    .filter((b) => valid(b) && inRange(b, q))
    .forEach((b) => {
      const cur = map.get(b.deptId) || { deptId: b.deptId, deptName: H.deptName(b.deptId), amount: 0, count: 0 };
      cur.amount += b.amount;
      cur.count += 1;
      map.set(b.deptId, cur);
    });
  res.json({ code: 0, data: [...map.values()].sort((a, b) => b.amount - a.amount) });
});

router.get('/by-type', (req, res) => {
  const q = req.query;
  const map = new Map();
  db.reimbursements
    .filter((b) => valid(b) && inRange(b, q))
    .forEach((b) => {
      const cur = map.get(b.type) || { type: b.type, amount: 0, count: 0 };
      cur.amount += b.amount;
      cur.count += 1;
      map.set(b.type, cur);
    });
  res.json({ code: 0, data: [...map.values()].sort((a, b) => b.amount - a.amount) });
});

router.get('/monthly', (req, res) => {
  const year = String(req.query.year || H.todayStr().slice(0, 4));
  const months = [];
  for (let m = 1; m <= 12; m++) {
    const prefix = `${year}-${String(m).padStart(2, '0')}`;
    const bills = db.reimbursements.filter((b) => valid(b) && (b.expenseDate || '').startsWith(prefix));
    months.push({ month: prefix, amount: bills.reduce((s, b) => s + b.amount, 0), count: bills.length });
  }
  res.json({ code: 0, data: months });
});

module.exports = router;
