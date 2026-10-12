/** 报销提交页：表单 + 附件上传（预览/删除）+ 草稿自动保存 + 提交 */
window.SubmitView = {
  data() {
    return {
      form: { type: '', amount: undefined, reason: '', expenseDate: '', deptId: '' },
      depts: [],
      attachments: [], // { id, fileName, mime }
      billId: '',
      status: '',
      rejectReason: '',
      dirty: false,
      savedAt: '',
      saving: false,
      submitting: false,
      previewImg: '',
      rules: {
        type: [{ required: true, message: '请选择报销类型', trigger: 'change' }],
        amount: [{ required: true, message: '请填写报销金额', trigger: 'blur' }],
        expenseDate: [{ required: true, message: '请选择费用发生日期', trigger: 'change' }],
        deptId: [{ required: true, message: '请选择对应部门', trigger: 'change' }],
        reason: [
          { required: true, message: '请填写报销事由', trigger: 'blur' },
          { max: 500, message: '报销事由不能超过 500 字', trigger: 'blur' },
        ],
      },
    };
  },
  template: `
  <div>
    <el-alert v-if="status === 'rejected'" type="error" :closable="false" style="margin-bottom:14px">
      <template #title>该单据已被驳回，请查看原因并修改后重新提交</template>
      <div>驳回原因：{{ rejectReason }}</div>
    </el-alert>

    <el-row :gutter="16">
      <el-col :md="15" :xs="24">
        <div class="page-card">
          <div class="toolbar" style="justify-content:space-between">
            <b>{{ billId ? '编辑报销单' : '新建报销单' }}</b>
            <span v-if="savedAt" class="muted">草稿已自动保存（{{ savedAt }}）</span>
          </div>
          <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
            <el-form-item label="报销类型" prop="type">
              <el-select v-model="form.type" placeholder="请选择报销类型" style="width:100%">
                <el-option v-for="t in EXPENSE_TYPES" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
            <el-form-item label="报销金额" prop="amount">
              <el-input-number v-model="form.amount" :min="0.01" :max="1000000" :precision="2" :step="100"
                               controls-position="right" placeholder="元" style="width:220px" />
              <span class="muted" style="margin-left:8px">上限 100 万元</span>
            </el-form-item>
            <el-form-item label="费用发生日期" prop="expenseDate">
              <el-date-picker v-model="form.expenseDate" type="date" value-format="YYYY-MM-DD"
                              :disabled-date="(d) => d.getTime() > Date.now()" placeholder="选择日期" style="width:220px" />
            </el-form-item>
            <el-form-item label="对应部门" prop="deptId">
              <el-select v-model="form.deptId" placeholder="请选择部门" style="width:220px">
                <el-option v-for="dp in depts" :key="dp.id" :label="dp.name" :value="dp.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="报销事由" prop="reason">
              <el-input v-model="form.reason" type="textarea" :rows="4" maxlength="500" show-word-limit
                        placeholder="请简要描述报销事由（500 字以内）" />
            </el-form-item>

            <el-form-item label="发票 / 凭证">
              <div style="width:100%">
                <el-upload
                  action="/api/attachments"
                  :headers="{ Authorization: 'Bearer ' + API.token }"
                  name="file"
                  multiple
                  :limit="10"
                  :on-success="onUploadSuccess"
                  :on-error="onUploadError"
                  :before-upload="beforeUpload"
                  :on-exceed="() => ElementPlus.ElMessage.warning('最多上传 10 个附件')"
                  :file-list="fileListDisplay"
                  :on-remove="onRemove"
                  :on-preview="onPreview">
                  <el-button type="primary" plain><el-icon><Upload /></el-icon>&nbsp;上传图片 / PDF</el-button>
                  <template #tip>
                    <div class="el-upload__tip">支持 JPG / PNG 图片、PDF 发票凭证，单个不超过 10MB，最多 10 个；点击文件可预览</div>
                  </template>
                </el-upload>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button @click="saveDraft()" :loading="saving">保存草稿</el-button>
              <el-button type="primary" :loading="submitting" @click="doSubmit">提交审批</el-button>
              <span class="muted" style="margin-left:10px">表单内容变更后约 3 秒自动保存草稿</span>
            </el-form-item>
          </el-form>
        </div>
      </el-col>
      <el-col :md="9" :xs="24">
        <div class="page-card">
          <b>填写须知</b>
          <ul class="tips">
            <li>报销金额需大于 0，且与发票金额一致。</li>
            <li>费用发生日期不能晚于今天。</li>
            <li>请上传清晰的发票照片或 PDF 电子发票。</li>
            <li>提交后单据进入「部门负责人 → 财务 →（大额）终审」流程，提交后不可修改。</li>
            <li>被驳回的单据可查看原因，修改后重新提交，修改历史会留痕。</li>
          </ul>
        </div>
      </el-col>
    </el-row>

    <el-image-viewer v-if="previewImg" :url-list="[previewImg]" @close="previewImg = ''" />
  </div>`,
  computed: {
    fileListDisplay() {
      return this.attachments.map((a) => ({ name: a.fileName, id: a.id, mime: a.mime }));
    },
  },
  async created() {
    const depts = await API.get('/api/departments');
    this.depts = depts;
    this.form.deptId = Store.user.deptId;

    const editId = this.$route.query.id;
    if (editId) {
      const b = await API.get('/api/reimbursements/' + editId);
      if (!['draft', 'rejected'].includes(b.status)) {
        ElementPlus.ElMessage.warning('该单据已进入审批流程，不可修改');
        return this.$router.push('/my');
      }
      this.billId = b.id;
      this.status = b.status;
      this.rejectReason = b.rejectReason;
      this.form = { type: b.type, amount: b.amount, reason: b.reason, expenseDate: b.expenseDate, deptId: b.deptId };
      this.attachments = b.attachments.map((a) => ({ id: a.id, fileName: a.fileName, mime: a.mime }));
    } else {
      // 恢复本地未保存的草稿内容（防止页面意外关闭丢失）
      try {
        const cached = JSON.parse(localStorage.getItem('bx_draft_new') || 'null');
        if (cached && typeof cached === 'object') Object.assign(this.form, cached);
      } catch (e) { /* 忽略 */ }
    }
    this.$nextTick(() => {
      this.dirty = false;
      this.$watch('form', () => { this.dirty = true; this.queueSave(); }, { deep: true });
    });
  },
  methods: {
    queueSave: null, // created 中赋值（见下方 setupQueueSave）
    async saveDraft(silent) {
      if (!this.form.type && !this.form.amount && !this.form.reason) return;
      this.saving = true;
      try {
        const payload = { ...this.form, attachmentIds: this.attachments.map((a) => a.id), submit: false };
        if (this.billId) payload.id = this.billId;
        this.billId = await API.post('/api/reimbursements', payload);
        this.status = 'draft';
        this.dirty = false;
        localStorage.removeItem('bx_draft_new');
        this.savedAt = new Date().toLocaleTimeString('zh-CN', { hour12: false });
        if (!silent) ElementPlus.ElMessage.success('草稿已保存');
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
      this.saving = false;
    },
    async doSubmit() {
      try {
        await this.$refs.formRef.validate();
      } catch (e) {
        return ElementPlus.ElMessage.warning('请完善表单必填项');
      }
      try {
        await ElementPlus.ElMessageBox.confirm(
          '提交后单据将进入审批流程（部门负责人 → 财务 → 终审），提交后不可修改。确定提交吗？',
          '提交确认',
          { type: 'warning', confirmButtonText: '确定提交', cancelButtonText: '再检查一下' }
        );
      } catch (e) { return; }
      this.submitting = true;
      try {
        const payload = { ...this.form, attachmentIds: this.attachments.map((a) => a.id), submit: true };
        if (this.billId) payload.id = this.billId;
        await API.post('/api/reimbursements', payload);
        localStorage.removeItem('bx_draft_new');
        ElementPlus.ElMessage.success('提交成功，请等待审批');
        this.$router.push('/my');
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
      this.submitting = false;
    },
    beforeUpload(file) {
      const okType = ['image/jpeg', 'image/png', 'application/pdf'].includes(file.type);
      if (!okType) { ElementPlus.ElMessage.error('仅支持 JPG / PNG 图片和 PDF 文件'); return false; }
      if (file.size > 10 * 1024 * 1024) { ElementPlus.ElMessage.error('文件大小不能超过 10MB'); return false; }
      return true;
    },
    onUploadSuccess(resp) {
      if (resp && resp.code === 0 && resp.data) {
        this.attachments.push(resp.data);
        ElementPlus.ElMessage.success('上传成功');
      } else {
        ElementPlus.ElMessage.error((resp && resp.message) || '上传失败');
      }
    },
    onUploadError(err) {
      let msg = '上传失败';
      try { msg = JSON.parse(err.message).message || msg; } catch (e) { /* 忽略 */ }
      ElementPlus.ElMessage.error(msg);
    },
    async onRemove(file) {
      const att = this.attachments.find((a) => a.id === file.id);
      if (!att) return;
      try {
        await API.del('/api/attachments/' + att.id);
        this.attachments = this.attachments.filter((a) => a.id !== att.id);
      } catch (e) {
        ElementPlus.ElMessage.error(e.message);
      }
    },
    onPreview(file) {
      if (file.mime === 'application/pdf') {
        window.open('/api/attachments/' + file.id + '?token=' + API.token, '_blank');
      } else {
        this.previewImg = '/api/attachments/' + file.id + '?token=' + API.token;
      }
    },
  },
  mounted() {
    // 绑定防抖自动保存（3 秒）
    this.queueSave = debounce(async function () {
      if (!this.dirty) return;
      await this.saveDraft(true);
    }, 3000);
    // 本地缓存兜底
    this.$watch('form', {
      handler(v) { localStorage.setItem('bx_draft_new', JSON.stringify(v)); },
      deep: true,
    });
  },
};
