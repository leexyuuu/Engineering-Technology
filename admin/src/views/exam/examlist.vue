<template>
  <div class="app-container">
    <el-button type="primary" @click="handleAdd">添加考试</el-button>
    <el-table :data="examList" style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="考试名称" />
      <el-table-column prop="date" label="考试时间" />
      <el-table-column label="题目数">
        <template slot-scope="scope">
          <el-link type="primary" @click="goQuestionList(scope.row)">{{ scope.row.question_count }}</el-link>
        </template>
      </el-table-column>
      <el-table-column label="已考学生数">
        <template slot-scope="scope">
          <el-link type="primary" @click="goStudentList(scope.row)">{{ scope.row.student_count }}</el-link>
        </template>
      </el-table-column>
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
import { fetchExamList, deleteExam } from '@/api/exam'
export default {
  data() {
    return {
      examList: [],
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
      fetchExamList({ page: this.page, page_size: this.pageSize }).then(res => {
        this.examList = res.data.items || []
        this.total = res.data.total || 0
        this.loading = false
      }).catch(() => { this.loading = false })
    },
    handleAdd() {
      this.$router.push({ path: '/exam/editexam' })
    },
    handleEdit(row) {
      this.$router.push({ path: `/exam/editexam/${row.id}` })
    },
    handleDelete(row) {
      this.$confirm('确定删除该考试吗？', '提示', { type: 'warning' }).then(() => {
        deleteExam(row.id).then(() => {
          this.$message.success('删除成功')
          this.fetchList()
        })
      })
    },
    goQuestionList(row) {
      this.$router.push({ path: `/exam/questionlist/${row.id}` })
    },
    goStudentList(row) {
      this.$router.push({ path: `/exam/studentlist/${row.id}` })
    }
  }
}
</script> 