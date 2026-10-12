/**
 * 主应用：布局外壳、单据详情抽屉、路由、启动引导
 */
/* ---------------- 单据详情抽屉（我的报销 / 审批中心共用） ---------------- */
window.BillDetail = {
  name: 'BillDetail',
  props: ['billId'],
  emits: ['close'],
  data() {
    return { bill: null, loading: false, previewImg: '' };
  },
  template: `
  <el-drawer :model-value="true" title="报销单详情" size="560px" @close="$emit('close')">
    <div v-loading="loading">
      <template v-if="bill">
        <el-alert v-if="bill.status === 'rejected'" type="error" :closable="false" style="margin-bottom:14px">
          <template #title>驳回原因：{{ bill.rejectReason }}</template>
        </el-alert>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="报销单号" :span="2">{{ bill.billNo }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="STATUS_MAP[bill.status].tag" size="small">{{ STATUS_MAP[bill.status].label }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="类型">{{ bill.type }}</el-descriptions-item>
          <el-descriptions-item label="金额"><b style="color:#f56c6c">{{ money(bill.amount) }}</b></el-descriptions-item>
          <el-descriptions-item label="发生日期">{{ bill.expenseDate }}</el-descriptions-item>
          <el-descriptions-item label="申请人">{{ bill.userName }}</el-descriptions-item>
          <el-descriptions-item label="部门">{{ bill.deptName }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ bill.submittedAt || '-' }}</el-descriptions-item>
          <el-descriptions-item label="报销事由" :span="2">{{ bill.reason }}</el-descriptions-item>
        </el-descriptions>

        <h4 class="detail-sec">附件凭证（{{ bill.attachments.length }}）</h4>
        <div v-if="!bill.attachments.length" class="muted">未上传附件</div>
        <div class="att-grid">
          <div v-for="a in bill.attachments" :key="a.id" class="att-item">
            <img v-if="a.mime === 'image/jpeg' || a.mime === 'image/png'"
                 :src="'/api/attachments/' + a.id + '?token=' + API.token" class="att-thumb"
                 @click="previewImg = '/api/attachments/' + a.id + '?token=' + API.token" />
            <div v-else class="att-pdf" @click="openFile(a)">
              <el-icon :size="26"><Document /></el-icon>
              <span>PDF</span>
            </div>
            <div class="att-name" :title="a.fileName">{{ a.fileName }}</div>
          </div>
        </div>

        <h4 class="detail-sec">审批记录</h4>
        <el-timeline>
          <el-timeline-item :timestamp="(bill.submittedAt || bill.createdAt) + ' · ' + bill.userName + ' 提交申请'" type="primary" hollow>
            提交报销单（{{ money(bill.amount) }}）
          </el-timeline-item>
          <el-timeline-item v-for="a in bill.approvals" :key="a.id" :timestamp="a.createdAt + ' · ' + a.approverName + '（' + (ROLE_LABEL[a.approverRole] || a.approverRole) + '）'"
                            :type="a.action === 'approve' ? 'success' : 'danger'" :hollow="false">
            <b>{{ a.action === 'approve' ? '【通过】' : '【驳回】' }}</b>{{ STEP_LABEL[stepOf(a.step)] || '' }}
            <div v-if="a.comment" class="comment">{{ a.comment }}</div>
          </el-timeline-item>
          <el-timeline-item v-if="bill.status === 'paid'" :timestamp="(bill.payments[0] && bill.payments[0].createdAt) || bill.paidAt" type="success">
            财务打款 {{ money(bill.amount) }}（{{ bill.payments[0] && bill.payments[0].payMethod || '银行转账' }}）
          </el-timeline-item>
        </el-timeline>

        <template v-if="bill.versions.length">
          <h4 class="detail-sec">修改留痕（{{ bill.versions.length }} 次修改前快照）</h4>
          <el-collapse>
            <el-collapse-item v-for="v in bill.versions" :key="v.version" :title="'版本 ' + v.version + '（' + v.updatedAt + '）'">
              <div class="ver-snap">
                <div>类型：{{ v.snapshot.type }}　金额：{{ money(v.snapshot.amount) }}</div>
                <div>日期：{{ v.snapshot.expenseDate }}</div>
                <div>事由：{{ v.snapshot.reason }}</div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </template>
      </template>
    </div>
    <el-image-viewer v-if="previewImg" :url-list="[previewImg]" @close="previewImg = ''" />
  </el-drawer>`,
  created() {
    this.load();
  },
  methods: {
    API: () => window.API,
    async load() {
      this.loading = true;
      try {
        this.bill = await API.get('/api/reimbursements/' + this.billId);
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
      this.loading = false;
    },
    openFile(a) {
      window.open('/api/attachments/' + a.id + '?token=' + API.token, '_blank');
    },
    stepOf(s) {
      return s === 'pending_dept' ? 'dept' : s === 'pending_finance' ? 'finance' : 'final';
    },
  },
};

/* ---------------- 布局外壳 ---------------- */
window.LayoutShell = {
  name: 'LayoutShell',
  data() {
    return {
      isMobile: window.innerWidth < 768,
      sidebarOpen: false,
      notifyVisible: false,
      notifications: [],
      previewImg: '',
    };
  },
  computed: {
    isApprover() { return ['manager', 'finance', 'admin'].includes(Store.user.role); },
    isFiscal() { return ['finance', 'admin'].includes(Store.user.role); },
    roleLabel() { return ROLE_LABEL[Store.user.role] || ''; },
    pageTitle() {
      const map = {
        '/dashboard': '首页 · 数据概览', '/submit': '报销提交', '/my': '我的报销',
        '/approve': '审批中心', '/stats': '数据统计', '/profile': '个人中心', '/users': '用户管理',
      };
      return map[this.$route.path] || '企业报销管理系统';
    },
  },
  mounted() {
    this.onResize = () => { this.isMobile = window.innerWidth < 768; if (!this.isMobile) this.sidebarOpen = false; };
    window.addEventListener('resize', this.onResize);
  },
  unmounted() {
    window.removeEventListener('resize', this.onResize);
  },
  template: `
  <el-container class="layout">
    <el-aside v-show="!isMobile || sidebarOpen" width="220px" class="aside">
      <div class="logo">
        <span class="logo-dot"></span>
        <span>企业报销系统</span>
      </div>
      <el-menu :default-active="$route.path" router background-color="#001529" text-color="#a6adb4" active-text-color="#ffffff">
        <el-menu-item index="/dashboard"><el-icon><Odometer /></el-icon><span>首页</span></el-menu-item>
        <el-menu-item index="/submit"><el-icon><EditPen /></el-icon><span>报销提交</span></el-menu-item>
        <el-menu-item index="/my"><el-icon><Tickets /></el-icon><span>我的报销</span></el-menu-item>
        <el-menu-item v-if="isApprover" index="/approve"><el-icon><Checked /></el-icon><span>审批中心</span></el-menu-item>
        <el-menu-item v-if="isFiscal" index="/stats"><el-icon><DataAnalysis /></el-icon><span>数据统计</span></el-menu-item>
        <el-menu-item v-if="Store.user.role === 'admin'" index="/users"><el-icon><Setting /></el-icon><span>用户管理</span></el-menu-item>
        <el-menu-item index="/profile"><el-icon><UserFilled /></el-icon><span>个人中心</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container class="right">
      <el-header class="header" height="56px">
        <div class="header-left">
          <el-icon class="collapse-btn" :size="20" @click="sidebarOpen = !sidebarOpen"><Fold /></el-icon>
          <span class="header-title">{{ pageTitle }}</span>
        </div>
        <div class="header-right">
          <el-badge :value="Store.unread" :hidden="!Store.unread" :max="99" class="bell-badge">
            <el-icon :size="20" class="bell" @click="openNotify"><Bell /></el-icon>
          </el-badge>
          <el-dropdown @command="onCommand">
            <span class="user-info">
              <span class="avatar">{{ Store.user.realName.slice(0, 1) }}</span>
              <span class="uname">{{ Store.user.realName }}（{{ roleLabel }}）</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>

    <el-drawer v-model="notifyVisible" title="消息通知" size="380px">
      <div style="margin-bottom:10px; text-align:right">
        <el-button size="small" text type="primary" @click="markAll">全部标记已读</el-button>
      </div>
      <el-empty v-if="!notifications.length" description="暂无消息" />
      <div v-for="n in notifications" :key="n.id" class="notify-item" :class="{ unread: !n.read }" @click="markOne(n)">
        <div class="notify-title">
          <el-badge is-dot :hidden="n.read" class="notify-dot">{{ n.title }}</el-badge>
          <span class="notify-time">{{ n.createdAt }}</span>
        </div>
        <div class="notify-content">{{ n.content }}</div>
      </div>
    </el-drawer>
  </el-container>`,
  methods: {
    onCommand(cmd) {
      if (cmd === 'profile') this.$router.push('/profile');
      if (cmd === 'logout') {
        API.token = '';
        Store.user = null;
        this.$router.push('/login');
      }
    },
    async openNotify() {
      this.notifyVisible = true;
      try {
        this.notifications = await API.get('/api/notifications');
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
    },
    async markAll() {
      await API.post('/api/notifications/read', { all: true });
      Store.unread = 0;
      this.notifications = this.notifications.map((n) => ({ ...n, read: true }));
    },
    async markOne(n) {
      if (n.read) return;
      await API.post('/api/notifications/read', { ids: [n.id] });
      n.read = true;
      fetchUnread();
    },
  },
};

/* ---------------- 路由 ---------------- */
const routes = [
  { path: '/login', component: window.LoginView },
  {
    path: '/',
    component: window.LayoutShell,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', component: window.DashboardView },
      { path: 'submit', component: window.SubmitView },
      { path: 'my', component: window.MyView },
      { path: 'approve', component: window.ApproveView, meta: { roles: ['manager', 'finance', 'admin'] } },
      { path: 'stats', component: window.StatsView, meta: { roles: ['finance', 'admin'] } },
      { path: 'profile', component: window.ProfileView },
      { path: 'users', component: window.UsersView, meta: { roles: ['admin'] } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
];

const router = VueRouter.createRouter({
  history: VueRouter.createWebHashHistory(),
  routes,
});

router.beforeEach((to) => {
  if (to.path !== '/login' && !Store.user) return '/login';
  if (to.path === '/login' && Store.user) return '/dashboard';
  if (to.meta && to.meta.roles && !to.meta.roles.includes(Store.user.role)) return '/dashboard';
  return true;
});

/* ---------------- 启动 ---------------- */
const app = Vue.createApp({
  template: '<router-view />',
});
app.use(ElementPlus, { locale: ElementPlusLocaleZhCn });
app.use(router);
for (const [name, comp] of Object.entries(ElementPlusIconsVue)) app.component(name, comp);

app.component('bill-detail', window.BillDetail);

app.config.globalProperties.Store = Store;
app.config.globalProperties.STATUS_MAP = STATUS_MAP;
app.config.globalProperties.ROLE_LABEL = ROLE_LABEL;
app.config.globalProperties.STEP_LABEL = STEP_LABEL;
app.config.globalProperties.EXPENSE_TYPES = EXPENSE_TYPES;
app.config.globalProperties.money = money;
app.config.globalProperties.canActOnStep = window.canActOnStep;
app.config.globalProperties.API = window.API;

initStore().finally(() => app.mount('#app'));
