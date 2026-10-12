/**
 * 导出路由：报销台账导出 Excel（xlsx）
 * scope=mine 任何用户可导出自己的记录；scope=all 需财务 / 超管
 */
const router = require('express').Router();
const ExcelJS = require('exceljs');
const { requireRole } = require('../auth');
const H = require('../helpers');

const STATUS_TEXT = {
  draft: '草稿',
  pending_dept: '待部门审核',
  pending_finance: '财务审核中',
  pending_final: '终审中',
  approved: '审核通过',
  rejected: '已驳回',
  paid: '已打款',
};

router.get('/reimbursements', async (req, res) => {
  const q = { ...req.query };
  if (q.scope === 'all') {
    if (!['finance', 'admin'].includes(req.user.role)) {
      return res.status(403).json({ message: '无权限导出全部报销台账' });
    }
  } else {
    q.scope = 'mine';
  }
  const { list, error } = H.filterBills(req.user, q);
  if (error) return res.status(403).json({ message: error });

  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('报销台账');
  ws.columns = [
    { header: '报销单号', key: 'billNo', width: 18 },
    { header: '报销类型', key: 'type', width: 10 },
    { header: '金额（元）', key: 'amount', width: 14 },
    { header: '报销事由', key: 'reason', width: 40 },
    { header: '申请人', key: 'userName', width: 10 },
    { header: '部门', key: 'deptName', width: 10 },
    { header: '状态', key: 'statusText', width: 12 },
    { header: '费用发生日期', key: 'expenseDate', width: 14 },
    { header: '提交时间', key: 'submittedAt', width: 20 },
    { header: '打款时间', key: 'paidAt', width: 20 },
    { header: '驳回原因', key: 'rejectReason', width: 30 },
  ];
  list.forEach((b) => {
    ws.addRow({
      billNo: b.billNo,
      type: b.type,
      amount: b.amount,
      reason: b.reason,
      userName: b.userName,
      deptName: b.deptName,
      statusText: STATUS_TEXT[b.status] || b.status,
      expenseDate: b.expenseDate,
      submittedAt: b.submittedAt || '-',
      paidAt: b.paidAt || '-',
      rejectReason: b.rejectReason || '',
    });
  });
  ws.getRow(1).font = { bold: true };
  ws.getRow(1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8F0FE' } };
  ws.getColumn('amount').numFmt = '#,##0.00';

  const name = `报销台账_${H.todayStr()}.xlsx`;
  res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
  res.setHeader('Content-Disposition', `attachment; filename=export.xlsx; filename*=UTF-8''${encodeURIComponent(name)}`);
  await wb.xlsx.write(res);
  res.end();
});

module.exports = router;
