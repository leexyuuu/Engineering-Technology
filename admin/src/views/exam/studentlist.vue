<template>
  <div class="app-container">
    <h3>考试：{{ examName }}</h3>
    <el-table :data="studentList" style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="学生ID" width="80" />
      <el-table-column prop="name" label="学生姓名" />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column prop="exam_number" label="准考证号" />
      <el-table-column label="考试状态" width="100">
        <template slot-scope="scope">
          <el-tag :type="getStatusType(scope.row.status)">
            {{ getStatusText(scope.row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="开始时间" width="160">
        <template slot-scope="scope">
          {{ formatDateTime(scope.row.start_time) }}
        </template>
      </el-table-column>
      <el-table-column label="结束时间" width="160">
        <template slot-scope="scope">
          {{ formatDateTime(scope.row.end_time) }}
        </template>
      </el-table-column>
      <el-table-column label="考试时长" width="100">
        <template slot-scope="scope">
          {{ scope.row.duration_minutes ? scope.row.duration_minutes + '分钟' : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template slot-scope="scope">
          <el-button size="mini" @click="handleViewDetail(scope.row)">查看详情</el-button>
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
import { fetchExamStudentList, fetchExam } from '@/api/exam'
export default {
  data() {
    return {
      studentList: [],
      loading: false,
      total: 0,
      page: 1,
      pageSize: 50,
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
      fetchExamStudentList(this.exam_id, { page: this.page, page_size: this.pageSize }).then(res => {
        this.studentList = res.data.items || []
        this.total = res.data.total || 0
        this.loading = false
      }).catch(() => { this.loading = false })
    },
    getStatusType(status) {
      const statusMap = {
        'not_started': 'info',
        'in_progress': 'warning',
        'submitted': 'success'
      }
      return statusMap[status] || 'info'
    },
    getStatusText(status) {
      const statusMap = {
        'not_started': '未开始',
        'in_progress': '进行中',
        'submitted': '已提交'
      }
      return statusMap[status] || '未知'
    },
    formatDateTime(dateTime) {
      if (!dateTime) return '-'
      const date = new Date(dateTime)
      return date.toLocaleString('zh-CN')
    },
    handleViewDetail(row) {
      // 跳转到学生考试详情页面
      this.$router.push({
        path: `/exam/examdetail/${this.exam_id}/${row.id}`,
        query: {
          studentName: row.name,
          studentPhone: row.phone,
          examNumber: row.exam_number,
          status: row.status,
          startTime: row.start_time,
          endTime: row.end_time
        }
      })
    }
  }
}
</script> 