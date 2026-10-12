/**
 * 审批中心路由：待我审批列表、已处理记录
 */
const router = require('express').Router();
const { db } = require('../db');
const H = require('../helpers');

/* 待我审批 */
router.get('/pending', (req, res) => {
  res.json({ code: 0, data: H.pendingFor(req.user).map(H.billListItem) });
});

/* 已处理记录：我审批过的单据 + 按角色可见的已流转单据 */
router.get('/history', (req, res) => {
  const user = req.user;
  let list;
  if (user.role === 'manager') {
    list = db.reimbursements.filter(
      (b) => b.deptId === user.deptId && b.status !== 'pending_dept' && (b.status !== 'draft' || b.userId === user.id)
    );
  } else if (user.role === 'finance') {
    list = db.reimbursements.filter((b) => ['pending_final', 'approved', 'rejected', 'paid'].includes(b.status));
  } else if (user.role === 'admin') {
    list = db.reimbursements.filter((b) => b.status !== 'draft' || b.userId === user.id);
  } else {
    list = [];
  }
  // 我本人审批过的单据始终可见
  const mineApproved = new Set(db.approvals.filter((a) => a.approverId === user.id).map((a) => a.billId));
  list = db.reimbursements.filter((b) => mineApproved.has(b.id)).concat(list.filter((b) => !mineApproved.has(b.id)));

  const items = list
    .sort((a, z) => (a.updatedAt < z.updatedAt ? 1 : -1))
    .map((b) => {
      const myRecords = db.approvals
        .filter((a) => a.billId === b.id && a.approverId === user.id)
        .sort((a, z) => (a.createdAt < z.createdAt ? 1 : -1));
      const last = myRecords[0];
      return {
        ...H.billListItem(b),
        myAction: last ? (last.action === 'approve' ? '通过' : '驳回') : '',
        myActionAt: last ? last.createdAt : '',
        myComment: last ? last.comment : '',
      };
    });
  res.json({ code: 0, data: items });
});

module.exports = router;
