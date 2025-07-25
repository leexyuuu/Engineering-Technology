<template>
  <div class="app-container">
    <h3>考试：{{ examName }}</h3>
    <el-button type="primary" @click="handleAdd">添加题目</el-button>
    <el-table :data="questionList" style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="id" width="80" />
        <el-table-column prop="order" label="排序" width="80" />
      <el-table-column prop="content" label="描述" />
      <el-table-column label="操作" width="180">
        <template slot-scope="scope">
          <el-button size="mini" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
   
  </div>
</template>

<script>
import { fetchExamQuestionList, deleteExamQuestion, fetchExam } from '@/api/exam'
export default {
  data() {
    return {
      questionList: [],
      loading: false,
      exam_id: null,
      examName: ''
    }
  },
  created() {
    this.exam_id = this.$route.params.exam_id
    this.fetchExamName()
    this.fetchList()
  },
  methods: {
    fetchExamName() {
      fetchExam(this.exam_id).then(res => {
        this.examName = res.name || (res.data && res.data.name) || ''
      })
    },
    fetchList() {
      this.loading = true
      fetchExamQuestionList(this.exam_id).then(res => {
        this.questionList = res.data.items || []
        console.log("this.questionList="+this.questionList)
        this.loading = false
      }).catch(() => { this.loading = false })
    },
    handleAdd() {
      this.$router.push({ path: `/exam/editquestion/${this.exam_id}/` })
    },
    handleEdit(row) {
      this.$router.push({ path: `/exam/editquestion/${this.exam_id}/${row.id}` })
    },
    handleDelete(row) {
      this.$confirm('确定删除该题目吗？', '提示', { type: 'warning' }).then(() => {
        deleteExamQuestion(row.id).then(() => {
          this.$message.success('删除成功')
          this.fetchList()
        })
      })
    }
  }
}
</script> 