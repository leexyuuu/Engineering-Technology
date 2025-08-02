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
              <span class="label">考试状态：</span>
              <el-tag :type="getStatusType(student_exam.status)" size="medium">
                {{ getStatusText(student_exam.status) }}
              </el-tag>
            </div>
          </div>
        </div>
        <div class="header-right">
          <div class="exam-time-info">
            <div class="time-item">
              <span class="label">开始时间：</span>
              <span class="value">{{ formatDateTime(student_exam.start_time) }}</span>
            </div>
            <div class="time-item">
              <span class="label">结束时间：</span>
              <span class="value">{{ formatDateTime(student_exam.end_time) }}</span>
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
            <span class="question-number">第{{ (index+1) }}题</span>
            <div class="question-tags">
              <el-tag size="small" type="primary">{{ getQuestionType(question) }}</el-tag>
              <el-tag v-if="question.requires_file || question.required_files" size="small" type="warning">需要上传文件</el-tag>
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
                  <span class="sub-number">{{ subIndex+1}}.</span>
                  <span class="sub-content">{{ subQuestion.content }}</span>
                  <span class="sub-score">({{ subQuestion.score }}分)</span>
                  <el-tag size="mini" type="success">{{ getSubQuestionType(subQuestion.question_type) }}</el-tag>
                </div>

                <!-- 选项（如果是选择题） -->
                <div v-if="subQuestion.question_type === 'single_choice' || subQuestion.question_type === 'multiple_choice'" class="options-section">
                  <h5>选项：</h5>
                  <div class="options-list">
                    <div 
                      v-for="(option, optionIndex) in subQuestion.options" 
                      :key="option.uuid"
                      :class="['option-item', { 'selected': isOptionSelected(question, subIndex, optionIndex), 'correct': option.is_correct }]"
                    >
                      <span class="option-text">{{ option.content }}</span>
                      <div class="option-status">
                        <el-tag v-if="option.is_correct" type="success" size="mini">正确答案</el-tag>
                        <el-tag v-if="isOptionSelected(question, subIndex, optionIndex)" type="info" size="mini">学生选择</el-tag>
                        <el-tag v-if="isOptionSelected(question, subIndex, optionIndex) && option.is_correct" type="success" size="mini">✓ 正确</el-tag>
                        <el-tag v-if="isOptionSelected(question, subIndex, optionIndex) && !option.is_correct" type="danger" size="mini">✗ 错误</el-tag>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 填空题答案 -->
                <div v-else-if="subQuestion.question_type === 'text'" class="text-answer-section">
                  <h5>学生答案：</h5>
                  <div v-if="getSubQuestionAnswer(question, subIndex)" class="text-answer">
                    <div class="answer-text">{{ getSubQuestionAnswer(question, subIndex) }}</div>
                  </div>
                  <div v-else class="no-answer">
                    <el-tag type="info" size="medium">未作答</el-tag>
                  </div>
                </div>
              </div>
            </div>

            <!-- 多文件答题区域 -->
            <div v-if="question.required_files" class="multi-file-answer-section">
              <h4>多文件答题要求：</h4>
              <div class="required-files-list">
                <div 
                  v-for="(requiredFile, fileIndex) in parseRequiredFiles(question.required_files)" 
                  :key="requiredFile.uuid"
                  class="required-file-item"
                >
                  <div class="file-requirement">
                    <div class="file-header">
                      <span class="file-name">{{ requiredFile.name || `文件${fileIndex + 1}` }}</span>
                      <div class="file-tags">
                        <el-tag size="mini" type="primary">{{ requiredFile.type }}</el-tag>
                        <el-tag v-if="requiredFile.required" size="mini" type="danger">必填</el-tag>
                        <el-tag v-else size="mini" type="info">可选</el-tag>
                      </div>
                    </div>
                    <div v-if="requiredFile.description" class="file-description">
                      <p>{{ requiredFile.description }}</p>
                    </div>
                  </div>

                  <!-- 学生上传的文件 -->
                  <div class="student-file-section">
                    <h5>学生上传的文件：</h5>
                    <div v-if="getStudentFileForRequiredFile(question, requiredFile.uuid)" class="file-display">
                      <div v-if="isImageFile(getStudentFileForRequiredFile(question, requiredFile.uuid))" class="image-file">
                        <div class="image-container">
                          <img 
                            :src="getStudentFileForRequiredFile(question, requiredFile.uuid)" 
                            @click="previewImage(getStudentFileForRequiredFile(question, requiredFile.uuid))"
                            class="preview-image"
                            alt="学生上传的图片"
                          />
                          <div class="image-overlay">
                            <el-button type="primary" size="small" icon="el-icon-zoom-in" @click="previewImage(getStudentFileForRequiredFile(question, requiredFile.uuid))">预览</el-button>
                          </div>
                        </div>
                        <div class="file-actions">
                          <el-button type="success" size="small" icon="el-icon-download" @click="downloadFile(getStudentFileForRequiredFile(question, requiredFile.uuid))">下载</el-button>
                        </div>
                      </div>
                      <div v-else class="other-file">
                        <div class="file-info">
                          <i class="el-icon-document"></i>
                          <span class="file-name">{{ getFileName(getStudentFileForRequiredFile(question, requiredFile.uuid)) }}</span>
                        </div>
                        <div class="file-actions">
                          <el-button type="primary" size="small" icon="el-icon-download" @click="downloadFile(getStudentFileForRequiredFile(question, requiredFile.uuid))">下载</el-button>
                        </div>
                      </div>
                    </div>
                    <div v-else class="no-file">
                      <el-tag type="info" size="medium">未上传文件</el-tag>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 单文件题答案（保持向后兼容） -->
            <div v-else-if="question.requires_file" class="file-answer-section">
              <h4>学生上传的文件：</h4>
              <div v-if="getStudentAnswer(question) && getStudentAnswer(question).file_url" class="file-display">
                <div v-if="isImageFile(getStudentAnswer(question).file_url)" class="image-file">
                  <div class="image-container">
                    <img 
                      :src="getStudentAnswer(question).file_url" 
                      @click="previewImage(getStudentAnswer(question).file_url)"
                      class="preview-image"
                      alt="学生上传的图片"
                    />
                    <div class="image-overlay">
                      <el-button type="primary" size="small" icon="el-icon-zoom-in" @click="previewImage(getStudentAnswer(question).file_url)">预览</el-button>
                    </div>
                  </div>
                  <div class="file-actions">
                    <el-button type="success" size="small" icon="el-icon-download" @click="downloadFile(getStudentAnswer(question).file_url)">下载</el-button>
                  </div>
                </div>
                <div v-else class="other-file">
                  <div class="file-info">
                    <i class="el-icon-document"></i>
                    <span class="file-name">{{ getFileName(getStudentAnswer(question).file_url) }}</span>
                  </div>
                  <div class="file-actions">
                    <el-button type="primary" size="small" icon="el-icon-download" @click="downloadFile(getStudentAnswer(question).file_url)">下载</el-button>
                  </div>
                </div>
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
      student_exam:{},
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
          this.examResults = res.data.questions || []
          this.student_exam=res.data.student_exam
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
    parseRequiredFiles(requiredFilesStr) {
      try {
        return JSON.parse(requiredFilesStr)
      } catch (e) {
        console.error('解析required_files失败:', e)
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
    // 获取学生为特定required_file上传的文件
    getStudentFileForRequiredFile(question, requiredFileUuid) {
      const studentAnswer = this.getStudentAnswer(question)
      if (!studentAnswer || !studentAnswer.option_answers) return null
      
      try {
        const fileAnswers = JSON.parse(studentAnswer.option_answers)
        if (fileAnswers && fileAnswers[requiredFileUuid]) {
          return fileAnswers[requiredFileUuid]
        }
        return null
      } catch (e) {
        return null
      }
    },
    // 检查选项是否被选中
    isOptionSelected(question, subIndex, optionIndex) {
      const studentAnswer = this.getStudentAnswer(question)
      if (!studentAnswer || !studentAnswer.option_answers) return false
      
      try {
        const answers = JSON.parse(studentAnswer.option_answers)
        if (Array.isArray(answers)) {
          return answers.includes(optionIndex)
        } else {
          return answers === optionIndex
        }
      } catch (e) {
        return false
      }
    },
    // 获取子问题的答案
    getSubQuestionAnswer(question, subIndex) {
      const studentAnswer = this.getStudentAnswer(question)
      if (!studentAnswer || !studentAnswer.option_answers) return null
      
      try {
        const answers = JSON.parse(studentAnswer.option_answers)
        if (typeof answers === 'string') {
          return answers
        }
        return null
      } catch (e) {
        return null
      }
    },
    // 检查是否为图片文件
    isImageFile(fileUrl) {
      if (!fileUrl) return false
      const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
      const lowerUrl = fileUrl.toLowerCase()
      return imageExtensions.some(ext => lowerUrl.includes(ext))
    },
    // 获取文件名
    getFileName(fileUrl) {
      if (!fileUrl) return ''
      const parts = fileUrl.split('/')
      return parts[parts.length - 1] || '未知文件'
    },
    // 预览图片
    previewImage(imageUrl) {
      this.$alert(`<img src="${imageUrl}" style="max-width: 100%; height: auto;" />`, '图片预览', {
        dangerouslyUseHTMLString: true,
        confirmButtonText: '关闭',
        customClass: 'image-preview-dialog'
      })
    },
    // 下载文件
    downloadFile(fileUrl) {
      const link = document.createElement('a')
      link.href = fileUrl
      link.download = this.getFileName(fileUrl)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    },
    getQuestionType(question) {
      if (question.required_files) return '多文件题'
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
  transition: all 0.3s ease;
}

.option-item.selected {
  background: #e6f7ff;
  border-color: #91d5ff;
}

.option-item.correct {
  border-color: #52c41a;
}

.option-item.selected.correct {
  background: #f6ffed;
  border-color: #52c41a;
}

.option-item.selected:not(.correct) {
  background: #fff2f0;
  border-color: #ff4d4f;
}

.option-text {
  flex: 1;
  color: #303133;
  line-height: 1.4;
}

.option-status {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

/* 填空题答案样式 */
.text-answer-section {
  margin-top: 15px;
}

.text-answer-section h5 {
  color: #606266;
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 10px 0;
}

.text-answer {
  background: white;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 15px;
  margin-top: 8px;
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
  margin-top: 8px;
}

/* 多文件答题样式 */
.multi-file-answer-section {
  margin: 25px 0;
  padding: 20px;
  background: #f0f9ff;
  border-radius: 8px;
  border: 1px solid #b3d8ff;
}

.multi-file-answer-section h4 {
  color: #409eff;
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 15px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.multi-file-answer-section h4::before {
  content: "📁";
  font-size: 18px;
}

.required-files-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.required-file-item {
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
  transition: all 0.3s ease;
}

.required-file-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.file-requirement {
  margin-bottom: 15px;
}

.file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.file-name {
  font-weight: 600;
  color: #303133;
  font-size: 16px;
}

.file-tags {
  display: flex;
  gap: 6px;
}

.file-description {
  color: #606266;
  line-height: 1.5;
  font-size: 14px;
}

.file-description p {
  margin: 0;
}

.student-file-section {
  border-top: 1px solid #e4e7ed;
  padding-top: 15px;
}

.student-file-section h5 {
  color: #409eff;
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 10px 0;
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

.file-display {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.image-file {
  display: flex;
  align-items: flex-start;
  gap: 15px;
}

.image-container {
  position: relative;
  display: inline-block;
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.preview-image {
  width: 120px;
  height: 120px;
  object-fit: cover;
  border-radius: 8px;
  transition: transform 0.3s ease;
}

.preview-image:hover {
  transform: scale(1.05);
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.image-container:hover .image-overlay {
  opacity: 1;
}

.file-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.other-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-info i {
  font-size: 20px;
  color: #409eff;
}

.file-name {
  color: #303133;
  font-weight: 500;
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
  
  .file-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .file-tags {
    align-self: flex-end;
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

/* 图片预览对话框样式 */
:deep(.image-preview-dialog) {
  .el-message-box__content {
    text-align: center;
    padding: 20px;
  }
  
  .el-message-box__message {
    margin: 0;
  }
}
</style> 