/** 我的报销：列表 + 筛选 + 详情 + 编辑/撤回/删除 + 导出 */
window.MyView = {
  data() {
    return {
      filters: { status: '', type: '', keyword: '', from: '', to: '' },
      list: [],
      loading: false,
      page: 1,
      pageSize: 10,
      detailBillId: '',
    };
  },
  computed: {
    paged() {
      const start = (this.page - 1) * this.pageSize;
      return this.list.slice(start, start + this.pageSize);
    },
    rangeDates: {
      get() { return this.filters.from || this.filters.to ? [this.filters.from, this.filters.to] : ''; },
      set(v) { this.filters.from = v ? v[0] : ''; this.filters.to = v ? v[1] : ''; },
    },
  },
  template: `
  <div>
    <div class="page-card">
      <div class="toolbar">
        <el-select v-model="filters.status" placeholder="全部状态" clearable style="width:140px">
          <el-option v-for="(v, k) in STATUS_MAP" :key="k" :label="v.label" :value="k" />
        </el-select>
        <el-select v-model="filters.type" placeholder="全部类型" clearable style="width:120px">
          <el-option v-for="t in EXPENSE_TYPES" :key="t" :label="t" :value="t" />
        </el-select>
        <el-date-picker v-model="rangeDates" type="daterange" value-format="YYYY-MM-DD"
                        start-placeholder="开始日期" end-placeholder="结束日期" style="width:260px" />
        <el-input v-model="filters.keyword" placeholder="单号 / 事由关键词" clearable style="width:200px" @keyup.enter="load" />
        <el-button type="primary" @click="load"><el-icon><Search /></el-icon>&nbsp;查询</el-button>
        <el-button @click="reset">重置</el-button>
        <el-button type="success" plain @click="exportMine"><el-icon><Download /></el-icon>&nbsp;导出记录</el-button>
      </div>
      <el-table :data="paged" v-loading="loading" size="default">
        <el-table-column prop="billNo" label="报销单号" min-width="155" />
        <el-table-column prop="type" label="类型" width="90" />
        <el-table-column label="金额" width="110"><template #default="{ row }"><span class="amount">{{ money(row.amount) }}</span></template></el-table-column>
        <el-table-column prop="reason" label="报销事由" min-width="160" show-overflow-tooltip />
        <el-table-column prop="expenseDate" label="发生日期" width="110" />
        <el-table-column label="附件" width="60">
          <template #default="{ row }">{{ row.attachmentCount || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="112">
          <template #default="{ row }"><el-tag :type="STATUS_MAP[row.status].tag" size="small">{{ STATUS_MAP[row.status].label }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="detailBillId = row.id">详情</el-button>
            <el-button v-if="['draft', 'rejected'].includes(row.status)" size="small" text type="primary" @click="$router.push('/submit?id=' + row.id)">编辑</el-button>
            <el-button v-if="row.status === 'pending_dept'" size="small" text type="warning" @click="withdraw(row)">撤回</el-button>
            <el-button v-if="row.status === 'draft'" size="small" text type="danger" @click="delDraft(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:12px; text-align:right">
        <el-pagination background layout="total, prev, pager, next" :total="list.length"
                       :page-size="pageSize" v-model:current-page="page" />
      </div>
    </div>

    <bill-detail v-if="detailBillId" :bill-id="detailBillId" @close="detailBillId = ''" />
  </div>`,
  async created() {
    if (this.$route.query.detail) this.detailBillId = this.$route.query.detail;
    await this.load();
  },
  methods: {
    async load() {
      this.loading = true;
      try {
        const q = new URLSearchParams({ scope: 'mine' });
        Object.entries(this.filters).forEach(([k, v]) => { if (v) q.set(k, v); });
        this.list = await API.get('/api/reimbursements?' + q.toString());
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
      this.loading = false;
    },
    reset() {
      this.filters = { status: '', type: '', keyword: '', from: '', to: '' };
      this.load();
    },
    exportMine() {
      const q = new URLSearchParams({ scope: 'mine' });
      Object.entries(this.filters).forEach(([k, v]) => { if (v) q.set(k, v); });
      q.set('token', API.token);
      window.open('/api/export/reimbursements?' + q.toString());
    },
    async withdraw(row) {
      try {
        await ElementPlus.ElMessageBox.confirm('确定撤回该报销单吗？撤回后回到草稿状态可继续编辑。', '撤回确认', { type: 'warning' });
      } catch (e) { return; }
      try {
        await API.post('/api/reimbursements/' + row.id + '/withdraw');
        ElementPlus.ElMessage.success('已撤回到草稿');
        this.load();
      } catch (e) { ElementPlus.ElMessage.error(e.message); }
    },
    async delDraft(row) {
      try {
        await ElementPlus.ElMessageBox.confirm('确定删除该草稿吗？删除后不可恢复。', '删除确认', { type: 'warning' });
      } catch (e) { return; }
      try {
        await API.del('/api/reimbursements/' + row.id);
        ElementPlus.ElMessage.success('草稿已删除');
        this.load();
      } catch (e) { ElementPlus.ElMessage.error(e.message); }
    },
  },
};
