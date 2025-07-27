<template>
  <div class="app-container">
    <div class="header-info">
      <h2>考试详情</h2>
      <div class="student-info">
        <p><strong>学生姓名：</strong>{{ studentInfo.name }}</p>
        <p><strong>手机号：</strong>{{ studentInfo.phone }}</p>
        <p><strong>准考证号：</strong>{{ studentInfo.exam_number }}</p>
        <p><strong>考试状态：</strong>
          <el-tag :type="getStatusType(studentInfo.status)">
            {{ getStatusText(studentInfo.status) }}
          </el-tag>
        </p>
        <p><strong>开始时间：</strong>{{ formatDateTime(studentInfo.start_time) }}</p>
        <p><strong>结束时间：</strong>{{ formatDateTime(studentInfo.end_time) }}</p>
      </div>
    </div>

    <div class="questions-container" v-loading="loading">
      <div 
        v-for="(question, index) in examResults" 
        :key="question.id"
        class="question-item"
      >
        <div class="question-header">
          <h3>第{{ question.order }}题</h3>
          <div class="question-meta">
            <span class="question-type">{{ getQuestionType(question) }}</span>
            <span v-if="question.requires_file" class="file-required">需要上传文件</span>
          </div>
        </div>

        <div class="question-content">
          <p><strong>题目描述：</strong>{{ question.content }}</p>
          
          <!-- 文件说明 -->
          <div v-if="question.requires_file && question.file_description" class="file-description">
            <p><strong>文件说明：</strong>{{ question.file_description }}</p>
          </div>

          <!-- 子问题列表 -->
          <div v-if="question.sub_questions_str" class="sub-questions">
            <div 
              v-for="(subQuestion, subIndex) in parseSubQuestions(question.sub_questions_str)" 
              :key="subQuestion.uuid"
              class="sub-question"
            >
              <div class="sub-question-header">
                <span class="sub-order">{{ subQuestion.order }}.</span>
                <span class="sub-content">{{ subQuestion.content }}</span>
                <span class="sub-score">({{ subQuestion.score }}分)</span>
                <span class="sub-type">{{ getSubQuestionType(subQuestion.question_type) }}</span>
              </div>

              <!-- 选项（如果是选择题） -->
              <div v-if="subQuestion.question_type === 'single_choice' || subQuestion.question_type === 'multiple_choice'" class="options">
                <div 
                  v-for="option in subQuestion.options" 
                  :key="option.uuid"
                  class="option"
                >
                  <span class="option-content">{{ option.content }}</span>
                  <el-tag v-if="option.is_correct" type="success" size="mini">正确答案</el-tag>
                </div>
              </div>
            </div>
          </div>

          <!-- 学生答案（针对整个题目） -->
          <div v-if="getStudentAnswer(question)" class="student-answer">
            <p><strong>学生答案：</strong></p>
            <!-- 选择题答案 -->
            <div v-if="getStudentAnswer(question).option_answers">
              <div 
                v-for="answer in parseOptionAnswers(getStudentAnswer(question).option_answers)" 
                :key="answer"
                class="answer-item"
              >
                <el-tag type="info">{{ answer }}</el-tag>
              </div>
            </div>
            <!-- 填空题答案 -->
            <div v-else-if="getStudentAnswer(question).answer_text">
              <p class="text-answer">{{ getStudentAnswer(question).answer_text }}</p>
            </div>
            <div v-else class="no-answer">未作答</div>
          </div>
          <div v-else class="student-answer">
            <p><strong>学生答案：</strong></p>
            <div class="no-answer">未作答</div>
          </div>

          <!-- 文件题答案 -->
          <div v-if="question.requires_file" class="file-answer">
            <p><strong>学生上传的文件：</strong></p>
            <div v-if="getStudentAnswer(question) && getStudentAnswer(question).file_url">
              <a :href="getStudentAnswer(question).file_url" target="_blank" class="file-link">
                <el-button type="primary" size="small">查看文件</el-button>
              </a>
            </div>
            <div v-else class="no-answer">未上传文件</div>
          </div>
        </div>
      </div>
    </div>

    <div class="actions">
      <el-button @click="$router.back()">返回</el-button>
    </div>
  </div>
</template>

<script>
import { fetchStudentExamResult } from '@/api/exam'

export default {
  name: 'ExamDetail',
  data() {
    return {
      loading: false,
      examResults: [],
      studentInfo: {},
      exam_id: null,
      student_id: null
    }
  },
  created() {
    this.exam_id = this.$route.params.exam_id
    this.student_id = this.$route.params.student_id
    this.fetchExamDetail()
  },
  methods: {
    fetchExamDetail() {
      this.loading = true
      // 从路由参数获取学生信息
      this.studentInfo = {
        name: this.$route.query.studentName || '未知',
        phone: this.$route.query.studentPhone || '未知',
        exam_number: this.$route.query.examNumber || '未知',
        status: this.$route.query.status || 'unknown',
        start_time: this.$route.query.startTime || null,
        end_time: this.$route.query.endTime || null
      }
      
      fetchStudentExamResult(this.exam_id, this.student_id)
        .then(res => {
          this.examResults = res.data || []
          this.loading = false
        })
        .catch(error => {
          console.error('获取考试详情失败:', error)
          this.$message.error('获取考试详情失败')
          this.loading = false
        })
    },
    parseSubQuestions(subQuestionsStr) {
      try {
        return JSON.parse(subQuestionsStr)
      } catch (e) {
        console.error('解析子问题失败:', e)
        return []
      }
    },
    parseOptionAnswers(optionAnswersStr) {
      try {
        return JSON.parse(optionAnswersStr)
      } catch (e) {
        console.error('解析选项答案失败:', e)
        return []
      }
    },
    getStudentAnswer(question) {
      return question.student_answer || null
    },
    getQuestionType(question) {
      if (question.requires_file) return '文件题'
      if (question.sub_questions_str) {
        const subQuestions = this.parseSubQuestions(question.sub_questions_str)
        if (subQuestions.length > 0) {
          const types = [...new Set(subQuestions.map(q => q.question_type))]
          return types.map(type => this.getSubQuestionType(type)).join('、')
        }
      }
      return '未知类型'
    },
    getSubQuestionType(type) {
      const typeMap = {
        'single_choice': '单选题',
        'multiple_choice': '多选题',
        'text': '填空题'
      }
      return typeMap[type] || '未知类型'
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
    }
  }
}
</script>

<style scoped>
.header-info {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.student-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
  margin-top: 15px;
}

.student-info p {
  margin: 5px 0;
}

.questions-container {
  margin-bottom: 20px;
}

.question-item {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 20px;
  overflow: hidden;
}

.question-header {
  background: #f5f7fa;
  padding: 15px 20px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.question-header h3 {
  margin: 0;
  color: #303133;
}

.question-meta {
  display: flex;
  gap: 10px;
  align-items: center;
}

.question-type {
  background: #409eff;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.file-required {
  background: #f56c6c;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.question-content {
  padding: 20px;
}

.file-description {
  background: #f0f9ff;
  padding: 10px;
  border-radius: 4px;
  margin: 10px 0;
  border-left: 4px solid #409eff;
}

.sub-questions {
  margin-top: 15px;
}

.sub-question {
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 15px;
  background: #fafafa;
}

.sub-question-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-weight: 500;
}

.sub-order {
  color: #409eff;
  font-weight: bold;
}

.sub-score {
  color: #f56c6c;
  font-weight: bold;
}

.sub-type {
  background: #67c23a;
  color: white;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
}

.options {
  margin: 10px 0;
}

.option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 0;
}

.option-content {
  flex: 1;
}

.student-answer {
  margin-top: 15px;
  padding: 10px;
  background: #f0f9ff;
  border-radius: 4px;
  border-left: 4px solid #409eff;
}

.answer-item {
  margin: 5px 0;
}

.text-answer {
  background: white;
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
  margin: 5px 0;
}

.no-answer {
  color: #909399;
  font-style: italic;
}

.file-answer {
  margin-top: 15px;
  padding: 10px;
  background: #f0f9ff;
  border-radius: 4px;
  border-left: 4px solid #409eff;
}

.file-link {
  text-decoration: none;
}

.actions {
  text-align: center;
  margin-top: 20px;
}
</style> 