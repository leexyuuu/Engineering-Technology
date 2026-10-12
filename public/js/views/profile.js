/** 个人中心：基本资料、修改密码、我的权限、草稿管理 */
window.ProfileView = {
  data() {
    return {
      profile: { realName: '', email: '', phone: '' },
      pwd: { oldPassword: '', newPassword: '', confirm: '' },
      drafts: [],
      perms: permList(Store.user.role),
    };
  },
  template: `
  <div>
    <el-row :gutter="16">
      <el-col :md="12" :xs="24">
        <div class="page-card">
          <b>基本信息</b>
          <el-form :model="profile" label-width="80px" style="margin-top:16px">
            <el-form-item label="用户名"><el-input :model-value="Store.user.username" disabled /></el-form-item>
            <el-form-item label="姓名"><el-input v-model="profile.realName" /></el-form-item>
            <el-form-item label="邮箱"><el-input v-model="profile.email" placeholder="选填" /></el-form-item>
            <el-form-item label="手机号"><el-input v-model="profile.phone" placeholder="选填" /></el-form-item>
            <el-form-item label="角色"><el-tag>{{ ROLE_LABEL[Store.user.role] }}</el-tag></el-form-item>
            <el-form-item label="部门"><el-tag type="info">{{ Store.user.deptName }}</el-tag></el-form-item>
            <el-form-item><el-button type="primary" @click="saveProfile">保存修改</el-button></el-form-item>
          </el-form>
        </div>

        <div class="page-card">
          <b>修改密码</b>
          <el-form :model="pwd" label-width="80px" style="margin-top:16px">
            <el-form-item label="原密码"><el-input v-model="pwd.oldPassword" type="password" show-password /></el-form-item>
            <el-form-item label="新密码"><el-input v-model="pwd.newPassword" type="password" show-password placeholder="至少 6 位" /></el-form-item>
            <el-form-item label="确认密码"><el-input v-model="pwd.confirm" type="password" show-password /></el-form-item>
            <el-form-item><el-button type="primary" @click="savePwd">修改密码</el-button></el-form-item>
          </el-form>
        </div>
      </el-col>

      <el-col :md="12" :xs="24">
        <div class="page-card">
          <b>我的权限</b>
          <ul class="tips">
            <li v-for="p in perms" :key="p">{{ p }}</li>
          </ul>
        </div>

        <div class="page-card">
          <b>草稿单据管理（{{ drafts.length }}）</b>
          <el-empty v-if="!drafts.length" description="暂无草稿" :image-size="70" />
          <el-table v-else :data="drafts" size="small" style="margin-top:10px">
            <el-table-column prop="billNo" label="单号" min-width="150" />
            <el-table-column prop="type" label="类型" width="88" />
            <el-table-column label="金额" width="100"><template #default="{ row }"><span class="amount">{{ money(row.amount) }}</span></template></el-table-column>
            <el-table-column prop="updatedAt" label="保存时间" width="160" />
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text type="primary" @click="$router.push('/submit?id=' + row.id)">继续填写</el-button>
                <el-button size="small" text type="danger" @click="delDraft(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>`,
  created() {
    this.profile = {
      realName: Store.user.realName,
      email: Store.user.email,
      phone: Store.user.phone,
    };
    this.loadDrafts();
  },
  methods: {
    async loadDrafts() {
      try {
        this.drafts = await API.get('/api/reimbursements?scope=mine&status=draft');
      } catch (e) { /* 忽略 */ }
    },
    async saveProfile() {
      try {
        const d = await API.put('/api/auth/profile', this.profile);
        Store.user = d.user;
        ElementPlus.ElMessage.success('资料已更新');
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
    },
    async savePwd() {
      if (!this.pwd.oldPassword || !this.pwd.newPassword) return ElementPlus.ElMessage.warning('请填写完整');
      if (this.pwd.newPassword.length < 6) return ElementPlus.ElMessage.warning('新密码至少 6 位');
      if (this.pwd.newPassword !== this.pwd.confirm) return ElementPlus.ElMessage.warning('两次输入的新密码不一致');
      try {
        await API.put('/api/auth/password', { oldPassword: this.pwd.oldPassword, newPassword: this.pwd.newPassword });
        ElementPlus.ElMessage.success('密码修改成功');
        this.pwd = { oldPassword: '', newPassword: '', confirm: '' };
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
    },
    async delDraft(row) {
      try {
        await ElementPlus.ElMessageBox.confirm('确定删除该草稿吗？', '删除确认', { type: 'warning' });
      } catch (e) { return; }
      try {
        await API.del('/api/reimbursements/' + row.id);
        ElementPlus.ElMessage.success('已删除');
        this.loadDrafts();
      } catch (e) { ElementPlus.ElMessage.error(e.message); }
    },
  },
};
