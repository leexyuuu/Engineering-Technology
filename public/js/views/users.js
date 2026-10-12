/** 用户管理（仅超管）：用户列表、新增/编辑、启停、重置密码 */
window.UsersView = {
  data() {
    return {
      list: [],
      depts: [],
      loading: false,
      dialog: { visible: false, isEdit: false, form: { username: '', realName: '', role: 'employee', deptId: '', password: '', email: '', phone: '' } },
      resetDialog: { visible: false, user: null, password: '' },
    };
  },
  template: `
  <div>
    <div class="page-card">
      <div class="toolbar" style="justify-content:space-between">
        <span class="muted">共 {{ list.length }} 个账号</span>
        <el-button type="primary" @click="openAdd"><el-icon><Plus /></el-icon>&nbsp;新增用户</el-button>
      </div>
      <el-table :data="list" v-loading="loading">
        <el-table-column prop="username" label="用户名" width="110" />
        <el-table-column prop="realName" label="姓名" width="100" />
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="{ employee: 'info', manager: '', finance: 'warning', admin: 'danger' }[row.role]" size="small">{{ ROLE_LABEL[row.role] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="deptName" label="部门" width="100" />
        <el-table-column prop="email" label="邮箱" min-width="140" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" width="120" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-switch :model-value="row.status === 'active'" @change="(v) => toggleStatus(row, v)" />
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="160" />
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" text type="warning" @click="resetDialog = { visible: true, user: row, password: '' }">重置密码</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '编辑用户' : '新增用户'" width="460px">
      <el-form :model="dialog.form" label-width="90px">
        <el-form-item label="用户名">
          <el-input v-model="dialog.form.username" :disabled="dialog.isEdit" placeholder="3-20 位字母数字下划线" />
        </el-form-item>
        <el-form-item label="姓名"><el-input v-model="dialog.form.realName" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="dialog.form.role" style="width:100%">
            <el-option label="普通员工" value="employee" />
            <el-option label="部门负责人" value="manager" />
            <el-option label="财务管理员" value="finance" />
            <el-option label="超级管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="dialog.form.deptId" style="width:100%">
            <el-option v-for="d in depts" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!dialog.isEdit" label="初始密码"><el-input v-model="dialog.form.password" placeholder="至少 6 位" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="dialog.form.email" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="dialog.form.phone" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetDialog.visible" title="重置密码" width="380px">
      <el-input v-model="resetDialog.password" type="password" show-password placeholder="输入新密码（至少 6 位）" />
      <template #footer>
        <el-button @click="resetDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="doReset">确定重置</el-button>
      </template>
    </el-dialog>
  </div>`,
  async created() {
    this.depts = await API.get('/api/departments');
    this.load();
  },
  methods: {
    async load() {
      this.loading = true;
      try {
        this.list = await API.get('/api/users');
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
      this.loading = false;
    },
    openAdd() {
      this.dialog = { visible: true, isEdit: false, form: { username: '', realName: '', role: 'employee', deptId: this.depts[0] ? this.depts[0].id : '', password: '', email: '', phone: '' } };
    },
    openEdit(row) {
      this.dialog = { visible: true, isEdit: true, form: { id: row.id, username: row.username, realName: row.realName, role: row.role, deptId: row.deptId, password: '', email: row.email, phone: row.phone } };
    },
    async saveUser() {
      try {
        if (this.dialog.isEdit) {
          await API.put('/api/users/' + this.dialog.form.id, this.dialog.form);
          ElementPlus.ElMessage.success('用户已更新');
        } else {
          await API.post('/api/users', this.dialog.form);
          ElementPlus.ElMessage.success('用户已创建');
        }
        this.dialog.visible = false;
        this.load();
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
    },
    async toggleStatus(row, v) {
      try {
        await API.put('/api/users/' + row.id, { status: v ? 'active' : 'disabled' });
        ElementPlus.ElMessage.success(v ? '已启用' : '已停用');
        this.load();
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
        this.load();
      }
    },
    async doReset() {
      try {
        await API.post('/api/users/' + this.resetDialog.user.id + '/reset-password', { password: this.resetDialog.password });
        ElementPlus.ElMessage.success('密码已重置');
        this.resetDialog.visible = false;
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
    },
  },
};
