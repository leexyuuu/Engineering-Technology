<template>
  <div class="exam-detail-container">
    <!-- 页面头部信息 -->
    <div class="exam-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="exam-title">考试详情</h1>
          <div class="student-basic-info">
            <div class="info-item">
              <span class="label">学生姓名：</span>
              <span class="value">{{ studentInfo.name }}</span>
            </div>
            <div class="info-item">
              <span class="label">手机号：</span>
              <span class="value">{{ studentInfo.phone }}</span>
            </div>
            <div class="info-item">
              <span class="label">准考证号：</span>
              <span class="value">{{ studentInfo.exam_number }}</span>
            </div>
            <div class="info-item">
              <span class="label">考试状态：</span>
              <el-tag :type="getStatusType(studentInfo.status)" size="medium">
                {{ getStatusText(studentInfo.status) }}
              </el-tag>
            </div>
          </div>
        </div>
        <div class="header-right">
          <div class="exam-time-info">
            <div class="time-item">
              <span class="label">开始时间：</span>
              <span class="value">{{ formatDateTime(studentInfo.start_time) }}</span>
            </div>
            <div class="time-item">
              <span class="label">结束时间：</span>
              <span class="value">{{ formatDateTime(studentInfo.end_time) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 考试内容区域 -->
    <div class="exam-content" v-loading="loading">
      <div class="questions-section">
        <div 
          v-for="(question, index) in examResults" 
          :key="question.id"
          class="question-block"
        >
          <!-- 题目标题 -->
          <div class="question-title">
            <span class="question-number">第{{ question.order }}题</span>
            <div class="question-tags">
              <el-tag size="small" type="primary">{{ getQuestionType(question) }}</el-tag>
              <el-tag v-if="question.requires_file" size="small" type="warning">需要上传文件</el-tag>
            </div>
          </div>

          <!-- 题目内容 -->
          <div class="question-body">
            <div class="question-description">
              <h4>题目描述：</h4>
              <p>{{ question.content }}</p>
            </div>
            
            <!-- 文件说明 -->
            <div v-if="question.requires_file && question.file_description" class="file-instruction">
              <h4>文件说明：</h4>
              <p>{{ question.file_description }}</p>
            </div>

            <!-- 子问题列表 -->
            <div v-if="question.sub_questions_str" class="sub-questions-section">
              <div 
                v-for="(subQuestion, subIndex) in parseSubQuestions(question.sub_questions_str)" 
                :key="subQuestion.uuid"
                class="sub-question-block"
              >
                <div class="sub-question-title">
                  <span class="sub-number">{{ subQuestion.order }}.</span>
                  <span class="sub-content">{{ subQuestion.content }}</span>
                  <span class="sub-score">({{ subQuestion.score }}分)</span>
                  <el-tag size="mini" type="success">{{ getSubQuestionType(subQuestion.question_type) }}</el-tag>
                </div>

                <!-- 选项（如果是选择题） -->
                <div v-if="subQuestion.question_type === 'single_choice' || subQuestion.question_type === 'multiple_choice'" class="options-section">
                  <h5>选项：</h5>
                  <div class="options-list">
                    <div 
                      v-for="option in subQuestion.options" 
                      :key="option.uuid"
                      class="option-item"
                    >
                      <span class="option-text">{{ option.content }}</span>
                      <el-tag v-if="option.is_correct" type="success" size="mini">正确答案</el-tag>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 学生答案区域 -->
            <div class="student-answer-section">
              <h4>学生答案：</h4>
              <div v-if="getStudentAnswer(question)" class="answer-content">
                <!-- 选择题答案 -->
                <div v-if="getStudentAnswer(question).option_answers" class="choice-answer">
                  <div 
                    v-for="answer in parseOptionAnswers(getStudentAnswer(question).option_answers)" 
                    :key="answer"
                    class="answer-tag"
                  >
                    <el-tag type="info" size="medium">{{ answer }}</el-tag>
                  </div>
                </div>
                <!-- 填空题答案 -->
                <div v-else-if="getStudentAnswer(question).answer_text" class="text-answer">
                  <div class="answer-text">{{ getStudentAnswer(question).answer_text }}</div>
                </div>
                <div v-else class="no-answer">
                  <el-tag type="info" size="medium">未作答</el-tag>
                </div>
              </div>
              <div v-else class="no-answer">
                <el-tag type="info" size="medium">未作答</el-tag>
              </div>
            </div>

            <!-- 文件题答案 -->
            <div v-if="question.requires_file" class="file-answer-section">
              <h4>学生上传的文件：</h4>
              <div v-if="getStudentAnswer(question) && getStudentAnswer(question).file_url" class="file-link">
                <a :href="getStudentAnswer(question).file_url" target="_blank">
                  <el-button type="primary" icon="el-icon-download">查看文件</el-button>
                </a>
              </div>
              <div v-else class="no-file">
                <el-tag type="info" size="medium">未上传文件</el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 页面底部操作 -->
    <div class="exam-footer">
      <el-button @click="$router.back()" icon="el-icon-back">返回</el-button>
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
.exam-detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}

/* 页面头部样式 */
.exam-header {
  background: white;
  border-radius: 12px;
  padding: 30px;
  margin-bottom: 30px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-left {
  flex: 1;
}

.exam-title {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 20px 0;
  border-bottom: 3px solid #409eff;
  padding-bottom: 10px;
}

.student-basic-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item .label {
  font-weight: 600;
  color: #606266;
  min-width: 80px;
}

.info-item .value {
  color: #303133;
  font-weight: 500;
}

.header-right {
  text-align: right;
}

.exam-time-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.time-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.time-item .label {
  font-size: 12px;
  color: #909399;
}

.time-item .value {
  font-weight: 500;
  color: #303133;
}

/* 考试内容区域样式 */
.exam-content {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.questions-section {
  display: flex;
  flex-direction: column;
  gap: 40px;
}

.question-block {
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  overflow: hidden;
  background: white;
  transition: all 0.3s ease;
}

.question-block:hover {
  border-color: #409eff;
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.15);
}

.question-title {
  background: linear-gradient(135deg, #409eff 0%, #36a3f7 100%);
  color: white;
  padding: 20px 25px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.question-number {
  font-size: 20px;
  font-weight: 600;
}

.question-tags {
  display: flex;
  gap: 8px;
}

.question-body {
  padding: 25px;
}

.question-description h4 {
  color: #303133;
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 10px 0;
}

.question-description p {
  color: #606266;
  line-height: 1.6;
  margin: 0;
  font-size: 15px;
}

.file-instruction {
  background: #f0f9ff;
  border-left: 4px solid #409eff;
  padding: 15px;
  margin: 20px 0;
  border-radius: 0 8px 8px 0;
}

.file-instruction h4 {
  color: #409eff;
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.file-instruction p {
  color: #606266;
  margin: 0;
  line-height: 1.5;
}

/* 子问题样式 */
.sub-questions-section {
  margin: 25px 0;
}

.sub-question-block {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  background: #fafbfc;
}

.sub-question-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.sub-number {
  color: #409eff;
  font-weight: 600;
  font-size: 16px;
}

.sub-content {
  flex: 1;
  color: #303133;
  font-weight: 500;
  line-height: 1.5;
}

.sub-score {
  color: #f56c6c;
  font-weight: 600;
  font-size: 14px;
}

.options-section {
  margin-top: 15px;
}

.options-section h5 {
  color: #606266;
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 10px 0;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.option-text {
  flex: 1;
  color: #303133;
  line-height: 1.4;
}

/* 学生答案样式 */
.student-answer-section {
  margin: 25px 0;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.student-answer-section h4 {
  color: #303133;
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 15px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.student-answer-section h4::before {
  content: "📝";
  font-size: 18px;
}

.answer-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.choice-answer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.answer-tag {
  display: inline-block;
}

.text-answer {
  background: white;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 15px;
}

.answer-text {
  color: #303133;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.no-answer {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 文件答案样式 */
.file-answer-section {
  margin: 25px 0;
  padding: 20px;
  background: #f0f9ff;
  border-radius: 8px;
  border: 1px solid #b3d8ff;
}

.file-answer-section h4 {
  color: #409eff;
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 15px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-answer-section h4::before {
  content: "📎";
  font-size: 18px;
}

.file-link {
  display: inline-block;
}

.no-file {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 页面底部样式 */
.exam-footer {
  text-align: center;
  margin-top: 30px;
  padding: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .exam-detail-container {
    padding: 10px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 20px;
  }
  
  .header-right {
    text-align: left;
  }
  
  .time-item {
    align-items: flex-start;
  }
  
  .student-basic-info {
    grid-template-columns: 1fr;
  }
  
  .question-title {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .question-tags {
    align-self: flex-end;
  }
  
  .sub-question-title {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}

/* 加载状态样式 */
.el-loading-mask {
  background-color: rgba(255, 255, 255, 0.9);
}

/* 标签样式优化 */
.el-tag {
  border-radius: 6px;
}

/* 按钮样式优化 */
.el-button {
  border-radius: 8px;
  font-weight: 500;
}
</style> 