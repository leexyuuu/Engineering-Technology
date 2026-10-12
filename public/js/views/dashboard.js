/** 首页：数据概览 + 快捷入口 + 进度提醒 + 待办审批 */
window.DashboardView = {
  data() {
    return { d: null, loading: false };
  },
  computed: {
    isApprover() { return ['manager', 'finance', 'admin'].includes(Store.user.role); },
    isFiscal() { return ['finance', 'admin'].includes(Store.user.role); },
  },
  template: `
  <div v-loading="loading">
    <template v-if="d">
    <el-row :gutter="16" class="stat-cards">
      <el-col :xs="12" :sm="12" :md="6">
        <div class="stat-card">
          <div class="label">{{ isApprover ? '待我审批' : '我的审核中' }}</div>
          <div class="value blue">{{ isApprover ? d.todoCount + ' 单' : d.myPendingCount + ' 单' }}</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <div class="stat-card">
          <div class="label">已报销（本月打款）</div>
          <div class="value green">{{ money(d.myPaidTotal) }}</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <div class="stat-card">
          <div class="label">{{ isFiscal ? '全公司本月报销总额' : '我本月报销总额' }}</div>
          <div class="value orange">{{ money(d.monthTotalAll) }}</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <div class="stat-card">
          <div class="label">我的草稿</div>
          <div class="value">{{ d.draftCount }} 单</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :md="14" :xs="24">
        <div class="page-card">
          <div class="toolbar" style="justify-content:space-between">
            <b>进度提醒（我的最近报销单）</b>
            <div>
              <el-button type="primary" size="small" @click="$router.push('/submit')"><el-icon><Plus /></el-icon> 提交报销</el-button>
              <el-button size="small" @click="$router.push('/my')">查看全部</el-button>
            </div>
          </div>
          <el-table :data="d.recent" size="small" @row-click="(r) => $router.push('/my?detail=' + r.id)" style="cursor:pointer">
            <el-table-column prop="billNo" label="单号" min-width="150" />
            <el-table-column prop="type" label="类型" width="90" />
            <el-table-column label="金额" width="100"><template #default="{ row }"><span class="amount">{{ money(row.amount) }}</span></template></el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }"><el-tag :type="STATUS_MAP[row.status].tag" size="small">{{ STATUS_MAP[row.status].label }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="updatedAt" label="最近更新" width="160" />
          </el-table>
        </div>
      </el-col>
      <el-col :md="10" :xs="24">
        <div class="page-card" v-if="isApprover">
          <div class="toolbar" style="justify-content:space-between">
            <b>待我审批（{{ d.todoCount }}）</b>
            <el-button type="primary" size="small" text @click="$router.push('/approve')">去审批</el-button>
          </div>
          <el-empty v-if="!d.todoApprovals.length" description="暂无待审批单据" :image-size="60" />
          <el-table v-else :data="d.todoApprovals" size="small">
            <el-table-column prop="billNo" label="单号" min-width="140" />
            <el-table-column prop="userName" label="申请人" width="80" />
            <el-table-column label="金额" width="90"><template #default="{ row }"><span class="amount">{{ money(row.amount) }}</span></template></el-table-column>
            <el-table-column label="环节" width="90">
              <template #default="{ row }"><el-tag size="small" type="info">{{ STEP_LABEL[row.currentStep] }}</el-tag></template>
            </el-table-column>
          </el-table>
        </div>
        <div class="page-card">
          <b>审批流程说明</b>
          <el-steps direction="vertical" style="margin-top:14px" :active="3">
            <el-step title="提交报销单" description="填写信息、上传发票凭证，可先保存草稿" />
            <el-step title="部门负责人审核" description="部门负责人审核通过后自动流转至财务" />
            <el-step title="财务审核" description="财务核对凭证；金额 ≥ 5000 元进入终审" />
            <el-step title="终审 / 打款" description="终审通过后财务登记打款，完成报销" />
          </el-steps>
        </div>
      </el-col>
    </el-row>
    </template>
  </div>`,
  async created() {
    this.loading = true;
    try {
      this.d = await API.get('/api/dashboard');
    } catch (e) {
      ElementPlus.ElMessage.error(e.message);
    }
    this.loading = false;
  },
};
