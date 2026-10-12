/** 数据统计页（财务/超管）：概览卡片 + 部门/类型/月度图表 + 台账导出 */
window.StatsView = {
  data() {
    return {
      range: [firstDayOfMonth(), todayStr()],
      deptId: '',
      depts: [],
      summary: null,
      charts: [],
      loading: false,
    };
  },
  template: `
  <div v-loading="loading">
    <div class="page-card">
      <div class="toolbar">
        <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD"
                        start-placeholder="开始日期" end-placeholder="结束日期" style="width:280px" @change="load" />
        <el-select v-model="deptId" placeholder="全部部门" clearable style="width:150px" @change="load">
          <el-option v-for="d in depts" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
        <el-button type="primary" @click="load"><el-icon><Search /></el-icon>&nbsp;刷新</el-button>
        <el-button type="success" plain @click="exportAll"><el-icon><Download /></el-icon>&nbsp;导出报销台账（Excel）</el-button>
      </div>
      <el-row :gutter="16" class="stat-cards" style="margin-bottom:0" v-if="summary">
        <el-col :xs="12" :md="6"><div class="stat-card"><div class="label">报销总金额</div><div class="value red">{{ money(summary.totalAmount) }}</div></div></el-col>
        <el-col :xs="12" :md="6"><div class="stat-card"><div class="label">报销单数</div><div class="value">{{ summary.totalCount }} 单</div></div></el-col>
        <el-col :xs="12" :md="6"><div class="stat-card"><div class="label">已打款金额</div><div class="value green">{{ money(summary.paidAmount) }}</div></div></el-col>
        <el-col :xs="12" :md="6"><div class="stat-card"><div class="label">待审批 / 已驳回</div><div class="value orange">{{ summary.pendingCount }} / {{ summary.rejectedCount }} 单</div></div></el-col>
      </el-row>
    </div>

    <el-row :gutter="16" class="charts-row">
      <el-col :md="12" :xs="24"><div ref="deptChart" class="chart-box"></div></el-col>
      <el-col :md="12" :xs="24"><div ref="typeChart" class="chart-box"></div></el-col>
      <el-col :md="24" :xs="24"><div ref="monthChart" class="chart-box" style="height:320px"></div></el-col>
    </el-row>
  </div>`,
  async created() {
    this.depts = await API.get('/api/departments');
  },
  async mounted() {
    await this.load();
    this.onResize = () => this.charts.forEach((c) => c.resize());
    window.addEventListener('resize', this.onResize);
  },
  unmounted() {
    window.removeEventListener('resize', this.onResize);
    this.charts.forEach((c) => c.dispose());
  },
  methods: {
    qs() {
      const q = new URLSearchParams();
      if (this.range && this.range[0]) { q.set('from', this.range[0]); q.set('to', this.range[1]); }
      if (this.deptId) q.set('deptId', this.deptId);
      return q;
    },
    async load() {
      this.loading = true;
      try {
        const q = this.qs();
        this.summary = await API.get('/api/stats/summary?' + q.toString());
        const [byDept, byType, monthly] = await Promise.all([
          API.get('/api/stats/by-dept?' + q.toString()),
          API.get('/api/stats/by-type?' + q.toString()),
          API.get('/api/stats/monthly?year=' + new Date().getFullYear()),
        ]);
        this.$nextTick(() => {
          this.renderDept(byDept);
          this.renderType(byType);
          this.renderMonth(monthly);
        });
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
      this.loading = false;
    },
    makeChart(refName) {
      const el = this.$refs[refName];
      if (!el) return null;
      const c = echarts.init(el);
      this.charts.push(c);
      return c;
    },
    renderDept(data) {
      const c = this.makeChart('deptChart');
      if (!c) return;
      c.setOption({
        title: { text: '部门报销统计', left: 'center', textStyle: { fontSize: 14 } },
        tooltip: { trigger: 'axis' },
        grid: { left: 50, right: 20, bottom: 40, top: 50 },
        xAxis: { type: 'category', data: data.map((d) => d.deptName) },
        yAxis: { type: 'value', name: '金额（元）' },
        series: [{ type: 'bar', barMaxWidth: 42, data: data.map((d) => d.amount), itemStyle: { color: '#409eff' }, label: { show: true, position: 'top' } }],
      });
    },
    renderType(data) {
      const c = this.makeChart('typeChart');
      if (!c) return;
      c.setOption({
        title: { text: '费用类型分布', left: 'center', textStyle: { fontSize: 14 } },
        tooltip: { trigger: 'item', formatter: '{b}：{c} 元（{d}%）' },
        legend: { bottom: 0 },
        series: [{ type: 'pie', radius: ['35%', '62%'], center: ['50%', '50%'],
          data: data.map((d) => ({ name: d.type, value: d.amount })),
          label: { formatter: '{b}\n{d}%' } }],
      });
    },
    renderMonth(data) {
      const c = this.makeChart('monthChart');
      if (!c) return;
      c.setOption({
        title: { text: new Date().getFullYear() + ' 年度月度报销趋势', left: 'center', textStyle: { fontSize: 14 } },
        tooltip: { trigger: 'axis' },
        grid: { left: 60, right: 40, bottom: 40, top: 50 },
        xAxis: { type: 'category', data: data.map((d) => d.month.slice(5) + '月') },
        yAxis: [{ type: 'value', name: '金额（元）' }, { type: 'value', name: '单数' }],
        series: [
          { name: '报销金额', type: 'line', smooth: true, data: data.map((d) => d.amount), itemStyle: { color: '#e6a23c' }, areaStyle: { opacity: 0.15 } },
          { name: '报销单数', type: 'bar', yAxisIndex: 1, barMaxWidth: 22, data: data.map((d) => d.count), itemStyle: { color: '#a0cfff' } },
        ],
      });
    },
    exportAll() {
      const q = this.qs();
      q.set('scope', 'all');
      q.set('token', API.token);
      window.open('/api/export/reimbursements?' + q.toString());
    },
  },
};

function firstDayOfMonth() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-01';
}
function todayStr() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
