/**
 * 数据层：JSON 文件数据库（演示用，生产环境建议替换为 MySQL + ORM）
 * 所有集合：users / departments / reimbursements / versions / approvals / payments / attachments / notifications / logs / counters
 */
const fs = require('fs');
const path = require('path');
const bcrypt = require('bcryptjs');

const DATA_DIR = path.join(__dirname, '..', 'data');
const UPLOAD_DIR = path.join(DATA_DIR, 'uploads');
const DB_FILE = path.join(DATA_DIR, 'db.json');

for (const dir of [DATA_DIR, UPLOAD_DIR]) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

let db = null;

/** 生成短随机 ID */
function id(prefix) {
  return prefix + '_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

/** 当前时间字符串 YYYY-MM-DD HH:mm:ss */
function now() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/** 今天日期 YYYY-MM-DD */
function todayStr() {
  return now().slice(0, 10);
}

/** 生成报销单号 BX + 年月日 + 4 位流水 */
function nextBillNo() {
  const ymd = todayStr().replace(/-/g, '');
  db.counters.billSeq += 1;
  return `BX${ymd}${String(db.counters.billSeq).padStart(4, '0')}`;
}

function save() {
  const tmp = DB_FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(db, null, 2), 'utf8');
  fs.renameSync(tmp, DB_FILE);
}

/** 初始化演示数据 */
function seed() {
  const hash = bcrypt.hashSync('123456', 10);
  db = {
    counters: { billSeq: 10 },
    departments: [
      { id: 'd1', name: '技术部' },
      { id: 'd2', name: '市场部' },
      { id: 'd3', name: '财务部' },
      { id: 'd4', name: '人事部' },
    ],
    users: [
      { id: 'u1', username: 'admin', password: hash, realName: '系统管理员', role: 'admin', deptId: 'd3', email: 'admin@company.com', phone: '13800000001', status: 'active', createdAt: '2026-09-01 09:00:00' },
      { id: 'u2', username: 'finance', password: hash, realName: '王芳', role: 'finance', deptId: 'd3', email: 'wangfang@company.com', phone: '13800000002', status: 'active', createdAt: '2026-09-01 09:00:00' },
      { id: 'u3', username: 'manager1', password: hash, realName: '李强', role: 'manager', deptId: 'd1', email: 'liqiang@company.com', phone: '13800000003', status: 'active', createdAt: '2026-09-01 09:00:00' },
      { id: 'u4', username: 'manager2', password: hash, realName: '赵敏', role: 'manager', deptId: 'd2', email: 'zhaomin@company.com', phone: '13800000004', status: 'active', createdAt: '2026-09-01 09:00:00' },
      { id: 'u5', username: 'emp1', password: hash, realName: '张三', role: 'employee', deptId: 'd1', email: 'zhangsan@company.com', phone: '13800000005', status: 'active', createdAt: '2026-09-01 09:00:00' },
      { id: 'u6', username: 'emp2', password: hash, realName: '陈晨', role: 'employee', deptId: 'd1', email: 'chenchen@company.com', phone: '13800000006', status: 'active', createdAt: '2026-09-01 09:00:00' },
      { id: 'u7', username: 'emp3', password: hash, realName: '刘洋', role: 'employee', deptId: 'd2', email: 'liuyang@company.com', phone: '13800000007', status: 'active', createdAt: '2026-09-01 09:00:00' },
    ],
    reimbursements: [
      { id: 'r1', billNo: 'BX202610100001', userId: 'u5', deptId: 'd1', type: '差旅费', amount: 3200, reason: '北京客户现场技术支持差旅', expenseDate: '2026-10-09', status: 'pending_dept', currentStep: 'dept', rejectReason: '', version: 1, submittedAt: '2026-10-10 10:00:00', createdAt: '2026-10-10 10:00:00', updatedAt: '2026-10-10 10:00:00', paidAt: '' },
      { id: 'r2', billNo: 'BX202610090002', userId: 'u6', deptId: 'd1', type: '办公费', amount: 860, reason: '项目部办公用品采购（打印纸、签字笔、文件夹）', expenseDate: '2026-10-08', status: 'pending_dept', currentStep: 'dept', rejectReason: '', version: 1, submittedAt: '2026-10-09 14:30:00', createdAt: '2026-10-09 14:30:00', updatedAt: '2026-10-09 14:30:00', paidAt: '' },
      { id: 'r3', billNo: 'BX202609280003', userId: 'u5', deptId: 'd1', type: '餐费', amount: 450, reason: '项目组加班餐费', expenseDate: '2026-09-28', status: 'rejected', currentStep: '', rejectReason: '发票抬头与公司名称不符，请重新上传发票后重新提交', version: 1, submittedAt: '2026-09-28 18:00:00', createdAt: '2026-09-28 18:00:00', updatedAt: '2026-09-29 09:15:00', paidAt: '' },
      { id: 'r4', billNo: 'BX202610110004', userId: 'u7', deptId: 'd2', type: '交通费', amount: 120, reason: '市内客户拜访交通费', expenseDate: '2026-10-11', status: 'pending_dept', currentStep: 'dept', rejectReason: '', version: 1, submittedAt: '2026-10-11 16:00:00', createdAt: '2026-10-11 16:00:00', updatedAt: '2026-10-11 16:00:00', paidAt: '' },
      { id: 'r5', billNo: 'BX202610080005', userId: 'u3', deptId: 'd1', type: '差旅费', amount: 6800, reason: '深圳分公司技术交流差旅（机票 + 酒店）', expenseDate: '2026-10-07', status: 'pending_finance', currentStep: 'finance', rejectReason: '', version: 1, submittedAt: '2026-10-08 09:20:00', createdAt: '2026-10-08 09:20:00', updatedAt: '2026-10-08 09:20:00', paidAt: '' },
      { id: 'r6', billNo: 'BX202609050006', userId: 'u5', deptId: 'd1', type: '办公费', amount: 230, reason: '打印纸与墨盒采购', expenseDate: '2026-09-05', status: 'paid', currentStep: '', rejectReason: '', version: 1, submittedAt: '2026-09-05 11:00:00', createdAt: '2026-09-05 11:00:00', updatedAt: '2026-09-07 15:00:00', paidAt: '2026-09-07 15:00:00' },
      { id: 'r7', billNo: 'BX202610090007', userId: 'u4', deptId: 'd2', type: '餐费', amount: 5200, reason: '市场部季度客户答谢晚宴', expenseDate: '2026-10-09', status: 'pending_final', currentStep: 'final', rejectReason: '', version: 1, submittedAt: '2026-10-09 10:00:00', createdAt: '2026-10-09 10:00:00', updatedAt: '2026-10-10 11:00:00', paidAt: '' },
      { id: 'r8', billNo: 'BX202610060008', userId: 'u6', deptId: 'd1', type: '交通费', amount: 66, reason: '加班出租车费', expenseDate: '2026-10-06', status: 'approved', currentStep: '', rejectReason: '', version: 1, submittedAt: '2026-10-06 18:00:00', createdAt: '2026-10-06 18:00:00', updatedAt: '2026-10-07 10:30:00', paidAt: '' },
      { id: 'r9', billNo: 'BX202610050009', userId: 'u7', deptId: 'd2', type: '差旅费', amount: 9800, reason: '广州展会差旅费用（展位搭建差旅）', expenseDate: '2026-10-05', status: 'pending_finance', currentStep: 'finance', rejectReason: '', version: 1, submittedAt: '2026-10-05 09:00:00', createdAt: '2026-10-05 09:00:00', updatedAt: '2026-10-06 10:00:00', paidAt: '' },
      { id: 'r10', billNo: 'BX202610110010', userId: 'u5', deptId: 'd1', type: '办公费', amount: 150, reason: '会议用文具采购', expenseDate: '2026-10-11', status: 'draft', currentStep: '', rejectReason: '', version: 1, submittedAt: '', createdAt: '2026-10-11 20:00:00', updatedAt: '2026-10-11 20:00:00', paidAt: '' },
    ],
    versions: [
      { id: 'v1', billId: 'r3', version: 1, snapshot: { type: '餐费', amount: 450, reason: '项目组加班餐费', expenseDate: '2026-09-28' }, updatedAt: '2026-09-28 18:00:00' },
    ],
    approvals: [
      { id: 'a1', billId: 'r3', approverId: 'u3', step: 'pending_dept', action: 'reject', comment: '发票抬头与公司名称不符，请重新上传发票后重新提交', createdAt: '2026-09-29 09:15:00' },
      { id: 'a2', billId: 'r6', approverId: 'u3', step: 'pending_dept', action: 'approve', comment: '情况属实，同意', createdAt: '2026-09-06 09:30:00' },
      { id: 'a3', billId: 'r6', approverId: 'u2', step: 'pending_finance', action: 'approve', comment: '已核对凭证，同意报销', createdAt: '2026-09-06 15:00:00' },
      { id: 'a4', billId: 'r9', approverId: 'u4', step: 'pending_dept', action: 'approve', comment: '同意', createdAt: '2026-10-06 10:00:00' },
      { id: 'a5', billId: 'r7', approverId: 'u2', step: 'pending_finance', action: 'approve', comment: '凭证齐全，金额超过 5000 元，转终审', createdAt: '2026-10-10 11:00:00' },
      { id: 'a6', billId: 'r8', approverId: 'u3', step: 'pending_dept', action: 'approve', comment: '同意', createdAt: '2026-10-07 09:00:00' },
      { id: 'a7', billId: 'r8', approverId: 'u2', step: 'pending_finance', action: 'approve', comment: '同意报销', createdAt: '2026-10-07 10:30:00' },
    ],
    payments: [
      { id: 'p1', billId: 'r6', operatorId: 'u2', amount: 230, payMethod: '银行转账', remark: '9 月第一批打款', createdAt: '2026-09-07 15:00:00' },
    ],
    attachments: [],
    notifications: [
      { id: 'n1', userId: 'u3', title: '待审批提醒', content: '张三 提交了报销单 BX202610100001（差旅费 ¥3200.00），请及时审批', billId: 'r1', read: false, createdAt: '2026-10-10 10:00:00' },
      { id: 'n2', userId: 'u3', title: '待审批提醒', content: '陈晨 提交了报销单 BX202610090002（办公费 ¥860.00），请及时审批', billId: 'r2', read: false, createdAt: '2026-10-09 14:30:00' },
      { id: 'n3', userId: 'u4', title: '待审批提醒', content: '刘洋 提交了报销单 BX202610110004（交通费 ¥120.00），请及时审批', billId: 'r4', read: false, createdAt: '2026-10-11 16:00:00' },
      { id: 'n4', userId: 'u2', title: '待财务审核', content: '李强 提交了报销单 BX202610080005（差旅费 ¥6800.00），请财务审核', billId: 'r5', read: false, createdAt: '2026-10-08 09:20:00' },
      { id: 'n5', userId: 'u2', title: '待财务审核', content: '刘洋 的报销单 BX202610050009 已通过部门审核，请财务审核', billId: 'r9', read: false, createdAt: '2026-10-06 10:00:00' },
      { id: 'n6', userId: 'u1', title: '待终审提醒', content: '赵敏 的报销单 BX202610090007（¥5200.00）已通过财务审核，等待终审', billId: 'r7', read: false, createdAt: '2026-10-10 11:00:00' },
      { id: 'n7', userId: 'u4', title: '审批进度', content: '您的报销单 BX202610090007 已通过财务审核，进入终审', billId: 'r7', read: true, createdAt: '2026-10-10 11:00:00' },
      { id: 'n8', userId: 'u5', title: '报销单已驳回', content: '您的报销单 BX202609280003 已被驳回：发票抬头与公司名称不符，请重新上传发票后重新提交', billId: 'r3', read: false, createdAt: '2026-09-29 09:15:00' },
      { id: 'n9', userId: 'u5', title: '打款完成', content: '您的报销单 BX202609050006 已完成打款 ¥230.00', billId: 'r6', read: true, createdAt: '2026-09-07 15:00:00' },
    ],
    logs: [],
  };
}

function load() {
  if (fs.existsSync(DB_FILE)) {
    try {
      db = JSON.parse(fs.readFileSync(DB_FILE, 'utf8'));
      return;
    } catch (e) {
      console.error('数据库文件损坏，重新初始化：', e.message);
    }
  }
  seed();
  save();
  console.log('已初始化演示数据（data/db.json）');
}

load();

module.exports = {
  get db() { return db; },
  save,
  id,
  now,
  todayStr,
  nextBillNo,
  UPLOAD_DIR,
};
