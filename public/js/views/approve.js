/** 审批中心：待我审批（支持批量）+ 已处理记录 */
window.ApproveView = {
  data() {
    return {
      tab: 'pending',
      pending: [],
      history: [],
      loading: false,
      sel: [],
      act: { visible: false, bill: null, type: 'approve', comment: '' },
      detailBillId: '',
    };
  },
  computed: {
    isFiscal() { return ['finance', 'admin'].includes(Store.user.role); },
    canBatch() {
      return this.isFiscal && this.sel.length > 0 && this.sel.every((b) => b.status === 'pending_finance');
    },
  },
  template: `
  <div>
    <div class="page-card">
      <el-tabs v-model="tab" @tab-change="load">
        <el-tab-pane label="待我审批" name="pending">
          <div class="toolbar" style="justify-content:space-between">
            <span class="muted">共 {{ pending.length }} 单待处理</span>
            <el-button v-if="isFiscal" type="primary" :disabled="!canBatch" @click="batchApprove">
              批量通过（已选 {{ sel.length }} 单，仅限财务审核环节）
            </el-button>
          </div>
          <el-table :data="pending" v-loading="loading" @selection-change="(s) => (sel = s)">
            <el-table-column v-if="isFiscal" type="selection" width="44" :selectable="(r) => r.status === 'pending_finance'" />
            <el-table-column prop="billNo" label="单号" min-width="150" />
            <el-table-column prop="userName" label="申请人" width="90" />
            <el-table-column prop="deptName" label="部门" width="90" />
            <el-table-column prop="type" label="类型" width="88" />
            <el-table-column label="金额" width="105"><template #default="{ row }"><span class="amount">{{ money(row.amount) }}</span></template></el-table-column>
            <el-table-column prop="reason" label="事由" min-width="150" show-overflow-tooltip />
            <el-table-column label="当前环节" width="100">
              <template #default="{ row }"><el-tag size="small" type="warning">{{ STEP_LABEL[row.currentStep] }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="submittedAt" label="提交时间" width="160" />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text type="primary" @click="detailBillId = row.id">详情</el-button>
                <template v-if="canActOnStep(Store.user, row)">
                  <el-button size="small" text type="success" @click="openAct(row, 'approve')">通过</el-button>
                  <el-button size="small" text type="danger" @click="openAct(row, 'reject')">驳回</el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="已处理记录" name="history">
          <el-table :data="history" v-loading="loading">
            <el-table-column prop="billNo" label="单号" min-width="150" />
            <el-table-column prop="userName" label="申请人" width="90" />
            <el-table-column prop="deptName" label="部门" width="90" />
            <el-table-column label="金额" width="105"><template #default="{ row }"><span class="amount">{{ money(row.amount) }}</span></template></el-table-column>
            <el-table-column prop="type" label="类型" width="88" />
            <el-table-column label="当前状态" width="112">
              <template #default="{ row }"><el-tag :type="STATUS_MAP[row.status].tag" size="small">{{ STATUS_MAP[row.status].label }}</el-tag></template>
            </el-table-column>
            <el-table-column label="我的处理" width="90">
              <template #default="{ row }">
                <el-tag v-if="row.myAction" size="small" :type="row.myAction === '通过' ? 'success' : 'danger'">{{ row.myAction }}</el-tag>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="myComment" label="我的意见" min-width="140" show-overflow-tooltip />
            <el-table-column label="操作" width="90" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text type="primary" @click="detailBillId = row.id">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <bill-detail v-if="detailBillId" :bill-id="detailBillId" @close="detailBillId = ''" />

    <el-dialog v-model="act.visible" :title="act.type === 'approve' ? '审批通过' : '驳回单据'" width="440px">
      <template v-if="act.bill">
        <el-descriptions :column="1" border size="small" style="margin-bottom:14px">
          <el-descriptions-item label="单号">{{ act.bill.billNo }}</el-descriptions-item>
          <el-descriptions-item label="申请人">{{ act.bill.userName }}（{{ act.bill.deptName }}）</el-descriptions-item>
          <el-descriptions-item label="金额">{{ money(act.bill.amount) }}（{{ act.bill.type }}）</el-descriptions-item>
          <el-descriptions-item label="事由">{{ act.bill.reason }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <el-input v-model="act.comment" type="textarea" :rows="3" maxlength="200"
                :placeholder="act.type === 'approve' ? '审批意见（选填）' : '驳回原因（必填，将通知申请人）'" />
      <template #footer>
        <el-button @click="act.visible = false">取消</el-button>
        <el-button :type="act.type === 'approve' ? 'success' : 'danger'" @click="confirmAct">确定</el-button>
      </template>
    </el-dialog>
  </div>`,
  created() {
    this.load();
  },
  methods: {
    async load() {
      this.loading = true;
      try {
        if (this.tab === 'pending') this.pending = await API.get('/api/approvals/pending');
        else this.history = await API.get('/api/approvals/history');
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
      this.loading = false;
    },
    openAct(bill, type) {
      this.act = { visible: true, bill, type, comment: '' };
    },
    async confirmAct() {
      const { bill, type, comment } = this.act;
      if (type === 'reject' && !comment.trim()) return ElementPlus.ElMessage.warning('驳回必须填写原因');
      try {
        await API.post('/api/reimbursements/' + bill.id + (type === 'approve' ? '/approve' : '/reject'), { comment: comment.trim() });
        ElementPlus.ElMessage.success(type === 'approve' ? '已通过' : '已驳回');
        this.act.visible = false;
        this.load();
        fetchUnread();
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
    },
    async batchApprove() {
      const ids = this.sel.map((b) => b.id);
      try {
        await ElementPlus.ElMessageBox.confirm(`确定批量通过选中的 ${ids.length} 单吗？`, '批量审核', { type: 'warning' });
      } catch (e) { return; }
      try {
        const d = await API.post('/api/reimbursements/batch-approve', { ids, comment: '批量审核通过' });
        ElementPlus.ElMessage.success(d && d.message ? d.message : '批量通过完成');
        this.load();
        fetchUnread();
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
    },
  },
};
