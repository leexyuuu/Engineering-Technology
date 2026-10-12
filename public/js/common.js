/** 公共常量与工具函数 */

window.ROLE_LABEL = { employee: '普通员工', manager: '部门负责人', finance: '财务管理员', admin: '超级管理员' };

window.STATUS_MAP = {
  draft: { label: '草稿', tag: 'info' },
  pending_dept: { label: '待部门审核', tag: 'warning' },
  pending_finance: { label: '财务审核中', tag: 'primary' },
  pending_final: { label: '终审中', tag: 'warning' },
  approved: { label: '审核通过', tag: 'success' },
  rejected: { label: '已驳回', tag: 'danger' },
  paid: { label: '已打款', tag: 'success' },
};

window.STEP_LABEL = { dept: '部门审核', finance: '财务审核', final: '终审' };

window.EXPENSE_TYPES = ['差旅费', '办公费', '餐费', '交通费', '其他'];

window.money = function (n) {
  return '¥' + Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

window.debounce = function (fn, wait) {
  let t;
  return function (...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), wait);
  };
};

/** 当前用户是否可在该单据当前环节操作 */
window.canActOnStep = function (user, bill) {
  if (!user) return false;
  if (bill.status === 'pending_dept') return user.role === 'admin' || (user.role === 'manager' && user.deptId === bill.deptId);
  if (bill.status === 'pending_finance') return user.role === 'finance' || user.role === 'admin';
  if (bill.status === 'pending_final') return user.role === 'admin';
  return false;
};

/** 各角色权限说明（个人中心展示） */
window.permList = function (role) {
  const base = ['提交报销单（支持草稿自动保存）、上传发票凭证', '查看自己的报销进度与审批记录', '驳回单据可修改后重新提交', '个人历史记录搜索、筛选、导出'];
  if (role === 'employee') return base;
  if (role === 'manager') return base.concat(['审批本部门员工提交的报销单', '查看本部门全部报销单']);
  if (role === 'finance') return base.concat(['财务审核全部报销单，支持批量审核', '核对凭证、登记打款', '部门 / 费用类型 / 月度统计与台账导出']);
  return base.concat(['审批本部门员工提交的报销单', '财务审核全部报销单，支持批量审核', '终审大额报销单（金额 ≥ 5000 元）', '登记打款、统计报表与台账导出', '用户与部门管理']);
};

/** 附件大小格式化 */
window.fmtSize = function (n) {
  if (!n) return '';
  if (n < 1024) return n + 'B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + 'KB';
  return (n / 1024 / 1024).toFixed(1) + 'MB';
};
