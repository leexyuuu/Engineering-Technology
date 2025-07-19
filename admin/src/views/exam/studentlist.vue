<template>
  <div class="app-container">
    <el-button type="primary" @click="handleAdd">添加学生</el-button>
    <el-table :data="studentList" style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="学生姓名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column label="操作" width="180">
        <template slot-scope="scope">
          <el-button size="mini" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="mini" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      background
      layout="prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :current-page.sync="page"
      @current-change="fetchList"
    />
    <el-dialog :visible.sync="dialogVisible" title="编辑学生">
      <el-form :model="form" :rules="rules" ref="form" label-width="100px">
        <el-form-item label="学生姓名" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" />
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" @click="onSubmit">保存</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { fetchExamStudentList, createExamStudent, updateExamStudent, deleteExamStudent } from '@/api/exam'
export default {
  data() {
    return {
      studentList: [],
      loading: false,
      total: 0,
      page: 1,
      pageSize: 10,
      exam_id: null,
      dialogVisible: false,
      form: { name: '', email: '' },
      rules: {
        name: [{ required: true, message: '请输入学生姓名', trigger: 'blur' }],
        email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }]
      },
      editId: null
    }
  },
  created() {
    this.exam_id = this.$route.params.exam_id
    this.fetchList()
  },
  methods: {
    fetchList() {
      this.loading = true
      fetchExamStudentList(this.exam_id, { page: this.page, page_size: this.pageSize }).then(res => {
        this.studentList = res.items || res.data || []
        this.total = res.total || 0
        this.loading = false
      }).catch(() => { this.loading = false })
    },
    handleAdd() {
      this.form = { name: '', email: '' }
      this.editId = null
      this.dialogVisible = true
    },
    handleEdit(row) {
      this.form = { ...row }
      this.editId = row.id
      this.dialogVisible = true
    },
    handleDelete(row) {
      this.$confirm('确定删除该学生吗？', '提示', { type: 'warning' }).then(() => {
        deleteExamStudent(this.exam_id, row.id).then(() => {
          this.$message.success('删除成功')
          this.fetchList()
        })
      })
    },
    onSubmit() {
      this.$refs.form.validate(valid => {
        if (!valid) return
        const action = this.editId ? updateExamStudent(this.exam_id, this.editId, this.form) : createExamStudent(this.exam_id, this.form)
        action.then(() => {
          this.$message.success('保存成功')
          this.dialogVisible = false
          this.fetchList()
        })
      })
    }
  }
}
</script> 