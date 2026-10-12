/** 登录页 */
window.LoginView = {
  data() {
    return {
      form: { username: '', password: '' },
      loading: false,
      demos: [
        { label: '普通员工', u: 'emp1' },
        { label: '部门负责人', u: 'manager1' },
        { label: '财务管理员', u: 'finance' },
        { label: '超级管理员', u: 'admin' },
      ],
    };
  },
  template: `
  <div class="login-page">
    <el-card class="login-card">
      <h2 class="login-title">企业报销管理系统</h2>
      <el-form :model="form" size="large" @submit.prevent="doLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" @keyup.enter="doLogin">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" show-password placeholder="密码" @keyup.enter="doLogin">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="doLogin">登 录</el-button>
      </el-form>
      <el-divider><span style="font-size:12px;color:#909399">演示账号（密码 123456）</span></el-divider>
      <div class="demo-accounts">
        <el-tag v-for="a in demos" :key="a.u" class="demo-tag" type="info" effect="plain" @click="fill(a)">
          {{ a.label }}：{{ a.u }}
        </el-tag>
      </div>
    </el-card>
  </div>`,
  methods: {
    fill(a) {
      this.form.username = a.u;
      this.form.password = '123456';
    },
    async doLogin() {
      if (!this.form.username || !this.form.password) {
        return ElementPlus.ElMessage.warning('请输入用户名和密码');
      }
      this.loading = true;
      try {
        const d = await API.post('/api/auth/login', this.form);
        API.token = d.token;
        Store.user = d.user;
        fetchUnread();
        ElementPlus.ElMessage.success('登录成功，欢迎 ' + d.user.realName);
        this.$router.push('/dashboard');
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
      this.loading = false;
    },
  },
};
