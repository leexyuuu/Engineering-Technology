<template>
  <div class="app-container">
    <el-button type="primary" @click="handleAdd">添加学生</el-button>
    <el-table :data="studentList" style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column prop="gender" label="性别" />
      <el-table-column prop="id_number" label="证件号码" />
      <el-table-column prop="exam_number" label="准考证号" />
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
  </div>
</template>

<script>
import { fetchStudentList, deleteStudent } from '@/api/student'
export default {
  data() {
    return {
      studentList: [],
      loading: false,
      total: 0,
      page: 1,
      pageSize: 50
    }
  },
  created() {
    this.fetchList()
  },
  methods: {
    fetchList() {
      this.loading = true
      fetchStudentList({ page: this.page, page_size: this.pageSize }).then(res => {
        this.studentList = res.data.items || res.items || []
        this.total = res.data.total || res.total || 0
        this.loading = false
      }).catch(() => { this.loading = false })
    },
    handleAdd() {
      this.$router.push({ path: '/student/editstudent' })
    },
    handleEdit(row) {
      console.log("handleEdit "+`/student/editstudent/${row.id}`)
      this.$router.push({ path: `/student/editstudent/${row.id}` })
    },
    handleDelete(row) {
      this.$confirm('确定删除该学生吗？', '提示', { type: 'warning' }).then(() => {
        deleteStudent(row.id).then(() => {
          this.$message.success('删除成功')
          this.fetchList()
        })
      })
    }
  }
}
</script> 