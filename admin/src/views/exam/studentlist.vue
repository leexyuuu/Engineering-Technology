<template>
  <div class="app-container">
    <h3>考试：{{ examName }}</h3>
    
    <!-- 添加Excel导入功能 -->
    <div class="import-section" style="margin-bottom: 20px;">
      <el-button type="primary" @click="showImportDialog = true" icon="el-icon-upload">
        导入学生列表
      </el-button>
    </div>

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

    <!-- Excel导入对话框 -->
    <el-dialog
      title="导入学生列表"
      :visible.sync="showImportDialog"
      width="600px"
      :close-on-click-modal="false"
    >
      <div class="import-content">
        <div class="import-tips">
          <h4>导入说明：</h4>
          <ul>
            <li>请上传Excel文件，文件格式为.xlsx或.xls</li>
            <li>Excel文件必须包含以下列：学生姓名、电话号码</li>
            <li>学生姓名列标题：姓名 或 name</li>
            <li>电话号码列标题：电话 或 phone 或 手机号</li>
            <li>如果学生之前没有注册过，系统会自动注册，密码为电话号码后四位</li>
            <li>导入的学生会自动绑定到当前考试</li>
          </ul>
        </div>
        
        <upload-excel-component 
          :on-success="handleImportSuccess" 
          :before-upload="beforeImportUpload"
          ref="uploadExcel"
        />
        <div slot="footer" class="dialog-footer">
        <el-button 
       
        style="float: right;"
          type="primary" 
          @click="confirmImport" 
          :loading="importLoading"
          :disabled="importPreview.length === 0"
        >
          确认导入
        </el-button>
         <el-button         style="float: right; margin-right: 20px;" @click="showImportDialog = false">取消</el-button>
       
      </div>
        <div v-if="importPreview.length > 0" class="import-preview">
          <h4>导入预览（共{{ importPreview.length }}条记录）：</h4>
          <el-table :data="importPreview" border style="width: 100%; margin-top: 10px;">
            <el-table-column prop="name" label="学生姓名" />
            <el-table-column prop="phone" label="电话号码" />
            <el-table-column prop="status" label="状态">
              <template slot-scope="scope">
                <el-tag :type="scope.row.status === 'success' ? 'success' : 'warning'">
                  {{ scope.row.status === 'success' ? '将导入' : '格式错误' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      
   
    </el-dialog>
  </div>
</template>

<script>
import { fetchExamStudentList, fetchExam, importStudentsToExam } from '@/api/exam'
import UploadExcelComponent from '@/components/UploadExcel/index.vue'

export default {
  components: {
    UploadExcelComponent
  },
  data() {
    return {
      studentList: [],
      loading: false,
      total: 0,
      page: 1,
      pageSize: 50,
      exam_id: null,
      examName: '',
      showImportDialog: false,
      importPreview: [],
      importLoading: false
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
        query: { exam_name: this.examName }
      })
    },
    beforeImportUpload(file) {
      const isLt2M = file.size / 1024 / 1024 < 2
      if (!isLt2M) {
        this.$message.error('文件大小不能超过2MB')
        return false
      }
      return true
    },
    handleImportSuccess({ results, header }) {
      // 处理Excel数据
      this.importPreview = []
      
      // 查找姓名和电话列
      const nameIndex = header.findIndex(h => ['姓名', 'name', '学生姓名'].includes(h))
      const phoneIndex = header.findIndex(h => ['电话', 'phone', '手机号', '电话号码'].includes(h))
      
      if (nameIndex === -1 || phoneIndex === -1) {
        this.$message.error('Excel文件必须包含姓名和电话号码列')
        return
      }
      
      // 处理每一行数据
      results.forEach((row, index) => {
        const name = row[header[nameIndex]]
        const phone = row[header[phoneIndex]]
        
        if (!name || !phone) {
          this.importPreview.push({
            name: name || '空',
            phone: phone || '空',
            status: 'error',
            error: '姓名或电话号码为空'
          })
          return
        }
        
        // 验证电话号码格式
        const phoneRegex = /^1[3-9]\d{9}$/
        if (!phoneRegex.test(phone)) {
          this.importPreview.push({
            name,
            phone,
            status: 'error',
            error: '电话号码格式不正确'
          })
          return
        }
        
        this.importPreview.push({
          name,
          phone,
          status: 'success'
        })
      })
      
      if (this.importPreview.length === 0) {
        this.$message.error('没有找到有效的数据')
      }
    },
    confirmImport() {
      const validData = this.importPreview.filter(item => item.status === 'success')
      
      if (validData.length === 0) {
        this.$message.error('没有有效的数据可以导入')
        return
      }
      
      this.importLoading = true
      const students= validData.map(item => ({
          name: item.name,
          phone: item.phone.toString()
        }))
      const params={
          exam_id: parseInt(this.exam_id),
          student_strs: JSON.stringify(students)
      }
      
      
      // 调用导入接口
      importStudentsToExam(params).then(res => {
        this.$message.success(`成功导入 ${res.data.success_count} 名学生`)
        this.showImportDialog = false
        this.importPreview = []
        this.fetchList() // 刷新列表
      }).catch(error => {
        this.$message.error('导入失败：' + (error.message || '未知错误'))
      }).finally(() => {
        this.importLoading = false
      })
    }
  }
}
</script>

<style scoped>

.dialog-footer{
  height: 30px;
  margin-top: 20px;
}
.import-section {
  margin-bottom: 20px;
}

.import-content {
  padding: 20px 0;
}

.import-tips {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.import-tips h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.import-tips ul {
  margin: 0;
  padding-left: 20px;
}

.import-tips li {
  margin-bottom: 5px;
  color: #606266;
}

.import-preview {
  margin-top: 20px;
}

.import-preview h4 {
  margin: 0 0 10px 0;
  color: #303133;
}
</style> 