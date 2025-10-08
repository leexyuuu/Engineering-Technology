<template>
  <div class="exam-container">
    <!-- 顶部导航栏 -->
    <header class="exam-header">
      <div class="header-left">
        <button class="menu-btn">☰</button>
        <h1 class="page-title">{{ examData?.exam?.name || '试题单' }}</h1>
      </div>
      <div class="header-right">
        <span class="user-info">姓名: {{ studentData?.name || '未知用户' }}</span>
        <span class="timer">{{ formatTime(remainingTime) }}</span>
      </div>
    </header>

    <!-- 主要内容区域 -->
    <main class="exam-main">
      <!-- 左侧题目详情 -->
      <div class="left-panel">
        <!-- 题目导航标签 -->
        <div class="question-tabs">
          <button 
            v-for="question in examData?.questions" 
            :key="question.id"
            :class="['tab-btn', { active: currentQuestion === question.order }]"
            @click="currentQuestion = question.order"
          >
            第{{ question.order }}题
            <span v-if="answerStatus[question.id]" class="answer-status">
              {{ 
                answerStatus[question.id] === 'answered' ? '✅' : 
                answerStatus[question.id] === 'in_progress' ? '🔄' : '⭕' 
              }}
            </span>
          </button>
        </div>

        <!-- 题目内容 - 支持富文本展示 -->
        <div class="question-content">
          <div v-if="currentQuestionData?.content" class="question-rich-content" v-html="renderedContent"></div>
          <div v-else class="question-loading">加载中...</div>
        </div>
      </div>

      <!-- 右侧答案上传区域 -->
      <div class="right-panel">
        <!-- 右侧标签页 -->
        <div class="upload-tabs">
          <button 
            :class="['upload-tab-btn', { active: activeTab === 'upload' }]"
            @click="activeTab = 'upload'"
          >
            答案上传
          </button>
          <button 
            :class="['upload-tab-btn', { active: activeTab === 'download' }]"
            @click="activeTab = 'download'"
          >
            素材下载
          </button>
        </div>

        <!-- 答案上传内容 -->
        <div v-if="activeTab === 'upload'" class="upload-content">
          <div class="instructions">
            <p>考生文件夹可以保存在桌面。</p>
            <p>jupyter notebook 工作目录:虚拟机环境中的D:\jupyter_notebook.</p>
            <p>jupyter notebook 打开方式:在终端中输入jupyter notebook启动。</p>
          </div>

          <div class="upload-table">
            <table>
              <thead>
                <tr>
                  <th>序号</th>
                  <th>要求</th>
                  <th>上传</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(file, index) in currentQuestionRequiredFiles" :key="index">
                  <td>{{ index + 1 }}</td>
                  <td>{{ file.description || `上传文件 ${index + 1}` }}</td>
                  <td>
                    <input 
                      type="file" 
                      :id="'file-' + currentQuestionData?.id + '-' + index" 
                      style="display: none;" 
                      @change="onFileSelected($event, index)"
                    />
                    <label :for="'file-' + currentQuestionData?.id + '-' + index" class="file-input-label">选择文件</label>
                    <div v-if="getSelectedFile(currentQuestionData?.id, index)" class="selected-file">
                      📎 {{ getSelectedFile(currentQuestionData?.id, index).name }}
                    </div>
                  </td>
                  <td>
                    <button 
                      class="upload-btn" 
                      @click="uploadAnswerFile(index)"
                      :disabled="!getSelectedFile(currentQuestionData?.id, index) || uploadStatus[currentQuestionData?.id + '_' + index] === 'uploading'"
                      :class="{
                        'uploading': uploadStatus[currentQuestionData?.id + '_' + index] === 'uploading',
                        'success': uploadStatus[currentQuestionData?.id + '_' + index] === 'success',
                        'error': uploadStatus[currentQuestionData?.id + '_' + index] === 'error'
                      }"
                    >
                      <span v-if="uploadStatus[currentQuestionData?.id + '_' + index] === 'uploading'">上传中...</span>
                      <span v-else-if="uploadStatus[currentQuestionData?.id + '_' + index] === 'success'">✅ 已上传</span>
                      <span v-else-if="uploadStatus[currentQuestionData?.id + '_' + index] === 'error'">❌ 重试</span>
                      <span v-else>上传答案{{ index + 1 }}</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 文件上传进度 - 移动到表格下方 -->
          <div v-if="currentQuestionRequiredFiles.length > 0" class="upload-progress">
            <div class="progress-info">
              文件上传进度: {{ uploadedFilesCount }}/{{ currentQuestionRequiredFiles.length }}
            </div>
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: `${(uploadedFilesCount / currentQuestionRequiredFiles.length) * 100}%` }"
              ></div>
            </div>
          </div>

        </div>

        <!-- 素材下载内容 -->
        <div v-if="activeTab === 'download'" class="download-content">
          <h3 class="download-title">文件列表</h3>
          <div class="download-table">
            <table>
              <thead>
                <tr>
                  <th>序号</th>
                  <th>文件名</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(file, index) in downloadFiles" :key="index">
                  <td>{{ index + 1 }}</td>
                  <td>{{ file.name }}</td>
                  <td>
                    <button class="download-btn" @click="downloadFile(file)">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7,10 12,15 17,10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                      </svg>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>

    <!-- 底部导航按钮 -->
    <footer class="exam-footer">
      <div class="navigation-buttons">
        <button 
          class="nav-btn prev-btn" 
          @click="goToPreviousQuestion"
          :disabled="currentQuestion <= 1"
        >
          上一题
        </button>
        <button 
          class="nav-btn next-btn" 
          @click="currentQuestion >= (examData?.questions?.length || 6) ? submitExam() : goToNextQuestion()"
          :disabled="false"
        >
          {{ currentQuestion >= (examData?.questions?.length || 6) ? '交卷' : '下一题' }}
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const currentQuestion = ref(1)
const activeTab = ref('upload')

// 倒计时相关
const totalTime = 90 * 60 // 1小时30分钟 = 90分钟 = 5400秒
const remainingTime = ref(totalTime)
let timer = null

// 接口数据
const examData = ref(null)
const studentData = ref(null)

// 答案状态管理
const answerStatus = ref({}) // 记录每个题目的答题状态
const currentAnswerStatus = ref('not_answered') // 当前题目的答题状态
const uploadedFilesCount = ref(0) // 当前题目已上传的文件数量

// Markdown渲染函数
const renderMarkdown = (content) => {
  if (!content) return ''
  
  // 先处理通用的加粗语法
  let processedContent = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  
  // 然后处理其他格式
  return processedContent
    // 处理列表项
    .replace(/^[-*]\s*(.*)$/gim, '<div class="list-item">- $1</div>')
    // 处理普通段落
    .replace(/^([^-*].*)$/gim, '<div class="paragraph">$1</div>')
    // 清理空行
    .replace(/\n\s*\n/g, '')
    // 清理多余的div
    .replace(/<div class="paragraph"><\/div>/g, '');
}

// 渲染后的内容
const renderedContent = computed(() => {
  if (!currentQuestionData.value?.content) return ''
  return renderMarkdown(currentQuestionData.value.content)
})

// 计算当前题目数据
const currentQuestionData = computed(() => {
  if (!examData.value?.questions) {
    return null
  }
  
  const found = examData.value.questions.find(q => q.order === currentQuestion.value)
  
  if (!found) {
    const firstQuestion = examData.value.questions[0]
    return firstQuestion
  }
  
  return found
})

// 计算当前题目的required_files
const currentQuestionRequiredFiles = computed(() => {
  if (!currentQuestionData.value?.required_files) return []
  
  try {
    const requiredFiles = JSON.parse(currentQuestionData.value.required_files)
    return Array.isArray(requiredFiles) ? requiredFiles : []
  } catch (e) {
    console.error('解析required_files失败:', e)
    return []
  }
})

// 检查当前题目是否所有文件都已上传
const isCurrentQuestionComplete = computed(() => {
  const requiredCount = currentQuestionRequiredFiles.value.length
  return uploadedFilesCount.value >= requiredCount
})

// 下载文件列表 - 从当前题目数据获取
const downloadFiles = computed(() => {
  if (!currentQuestionData.value?.material_files) {
    return [
      { name: '2.2.3.ipynb', url: '#' },
      { name: '2.2.3.docx', url: '#' },
      { name: 'fitness analysis.csv', url: '#' }
    ]
  }
  
  try {
    const materialFiles = JSON.parse(currentQuestionData.value.material_files)
    return materialFiles.map(file => ({
      name: file.name,
      url: file.url.startsWith('http') ? file.url : `/api${file.url}`
    }))
  } catch (e) {
    console.error('解析material_files失败:', e)
    return []
  }
})

// 文件上传状态
const selectedFiles = ref([])
const uploadStatus = ref({}) // 记录每个文件的上传状态

// 获取选中文件的辅助函数
const getSelectedFile = (questionId, index) => {
  const arrayIndex = questionId * 100 + index
  return selectedFiles.value[arrayIndex]
}


// 加载考试数据
const loadExamData = async () => {
  try {
    // 从localStorage获取考试数据
    const examQuestionsData = localStorage.getItem('examQuestions')
    
    if (examQuestionsData) {
      const data = JSON.parse(examQuestionsData)
      examData.value = data
      
      // 设置当前题目为第一题
      if (data.questions && data.questions.length > 0) {
        currentQuestion.value = data.questions[0].order
      }
    }

    // 从localStorage获取学生数据
    const studentDataStr = localStorage.getItem('studentData')
    
    if (studentDataStr) {
      studentData.value = JSON.parse(studentDataStr)
    }
  } catch (error) {
    console.error('加载考试数据失败:', error)
  }
}

// 导航方法
const goToPreviousQuestion = async () => {
  if (!examData.value?.questions) return
  
  // 保存当前题目的答题状态
  await saveCurrentAnswerStatus()
  
  const currentIndex = examData.value.questions.findIndex(q => q.order === currentQuestion.value)
  if (currentIndex > 0) {
    currentQuestion.value = examData.value.questions[currentIndex - 1].order
    // 重置当前题目的答题状态和上传计数
    const prevQuestion = examData.value.questions[currentIndex - 1]
    currentAnswerStatus.value = answerStatus.value[prevQuestion.id] || 'not_answered'
    uploadedFilesCount.value = 0 // 重置上传计数
    // 不重置selectedFiles，保持文件选择状态
  }
}

const goToNextQuestion = async () => {
  if (!examData.value?.questions) return
  
  // 保存当前题目的答题状态
  await saveCurrentAnswerStatus()
  
  const currentIndex = examData.value.questions.findIndex(q => q.order === currentQuestion.value)
  if (currentIndex < examData.value.questions.length - 1) {
    currentQuestion.value = examData.value.questions[currentIndex + 1].order
    // 重置当前题目的答题状态和上传计数
    const nextQuestion = examData.value.questions[currentIndex + 1]
    currentAnswerStatus.value = answerStatus.value[nextQuestion.id] || 'not_answered'
    uploadedFilesCount.value = 0 // 重置上传计数
    // 不重置selectedFiles，保持文件选择状态
  }
}

const submitExam = async () => {
  if (confirm('确定要交卷吗？交卷后将无法修改答案。')) {
    try {
      const token = localStorage.getItem('studentToken')
      if (!token) {
        alert('登录信息已过期，请重新登录！')
        router.push('/')
        return
      }

      // 获取考试数据
      const examQuestionsData = localStorage.getItem('examQuestions')
      if (!examQuestionsData) {
        alert('考试数据不存在，请重新登录！')
        router.push('/')
        return
      }

      const examData = JSON.parse(examQuestionsData)
      const examId = examData.exam.id

      // 调用交卷接口
      const response = await fetch(`/api/student/exams/${examId}/submit`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      const result = await response.json()
      
      if (response.ok && result.code === 20000) {
        alert('考试完成！感谢您的参与。')
        // 停止倒计时
        if (timer) {
          clearInterval(timer)
        }
        // 清除本地存储的考试数据
        localStorage.removeItem('examQuestions')
        localStorage.removeItem('studentData')
        // 跳转回登录页面
        router.push('/')
      } else {
        // 处理不同的错误情况
        let errorMessage = '交卷失败'
        if (result.code === 404) {
          if (result.message === '没有开始考试') {
            errorMessage = '您还没有开始这场考试'
          } else if (result.message === '考试不存在') {
            errorMessage = '考试不存在'
          }
        } else if (result.code === 400) {
          if (result.message === '考试已经截止了') {
            errorMessage = '考试已经截止了'
          }
        } else {
          errorMessage = result.message || '未知错误'
        }
        alert(`交卷失败: ${errorMessage}`)
      }
    } catch (error) {
      console.error('交卷请求失败:', error)
      alert('交卷失败，请检查网络连接后重试。')
    }
  }
}

// 格式化时间显示
const formatTime = (seconds) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  return `${hours.toString().padStart(2, '0')}时${minutes.toString().padStart(2, '0')}分${secs.toString().padStart(2, '0')}秒`
}

// 下载文件方法
const downloadFile = (file) => {
  // 创建下载链接
  const link = document.createElement('a')
  link.href = file.url
  link.download = file.name
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  // 显示下载提示
  alert(`文件 ${file.name} 开始下载`)
}

// 文件选择事件
const onFileSelected = (event, index) => {
  const file = event.target.files[0]
  const questionId = currentQuestionData.value.id
  
  if (file) {
    // 使用题目ID作为数组的偏移量，避免不同题目间的文件冲突
    const arrayIndex = questionId * 100 + index
    selectedFiles.value[arrayIndex] = file
    uploadStatus.value[questionId + '_' + index] = 'ready'
    // 更新答题状态为"进行中"
    currentAnswerStatus.value = 'in_progress'
  } else {
    const arrayIndex = questionId * 100 + index
    selectedFiles.value[arrayIndex] = null
    uploadStatus.value[questionId + '_' + index] = null
  }
}

// 保存当前题目的答题状态
const saveCurrentAnswerStatus = async () => {
  if (!currentQuestionData.value) return
  
  // 检查是否有任何操作（选择文件或上传文件）
  const hasAnyOperation = uploadedFilesCount.value > 0 || 
                         currentQuestionRequiredFiles.value.some((_, index) => getSelectedFile(currentQuestionData.value.id, index))
  
  if (!hasAnyOperation) {
    return
  }
  
  try {
    const token = localStorage.getItem('studentToken')
    if (!token) {
      console.error('未找到登录token')
      return
    }

    const response = await fetch('/api/student/answers/save', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        question_id: currentQuestionData.value.id,
        exam_id: examData.value.exam.id,
        option_answers: JSON.stringify({
          question_type: 'file_upload',
          answer_status: currentAnswerStatus.value,
          required_files_count: currentQuestionRequiredFiles.value.length,
          uploaded_files_count: uploadedFilesCount.value,
          selected_files_count: currentQuestionRequiredFiles.value.filter((_, index) => getSelectedFile(currentQuestionData.value.id, index)).length,
          timestamp: new Date().toISOString()
        })
      })
    })

    const result = await response.json()
    
    if (response.ok && result.code === 20000) {
      // 更新全局答题状态
      answerStatus.value[currentQuestionData.value.id] = currentAnswerStatus.value
    } else {
      console.error('保存答题状态失败:', result)
    }
  } catch (error) {
    console.error('保存答题状态请求失败:', error)
  }
}

// 上传答案文件
const uploadAnswerFile = async (index) => {
  const questionId = currentQuestionData.value?.id
  if (!questionId) {
    alert('题目信息错误！')
    return
  }

  const file = getSelectedFile(currentQuestionData.value.id, index)
  if (!file) {
    alert('请选择要上传的文件！')
    return
  }

  // 获取当前题目的required_files信息
  const currentRequiredFiles = currentQuestionRequiredFiles.value
  const targetFile = currentRequiredFiles[index]
  
  if (!targetFile || !targetFile.uuid) {
    alert('文件配置信息错误！')
    return
  }

  // 设置上传状态
  uploadStatus.value[currentQuestionData.value.id + '_' + index] = 'uploading'

  const formData = new FormData()
  formData.append('file', file)
  formData.append('question_id', currentQuestionData.value.id)
  formData.append('exam_id', examData.value.exam.id)
  formData.append('required_file_uuid', targetFile.uuid)

  try {
    // 获取学生token
    const token = localStorage.getItem('studentToken')
    if (!token) {
      alert('登录信息已过期，请重新登录！')
      router.push('/')
      return
    }

    const response = await fetch('/api/student/answers/file', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    })

    const result = await response.json()

    if (response.ok && result.code === 20000) {
      uploadStatus.value[currentQuestionData.value.id + '_' + index] = 'success'
      alert(`文件 ${file.name} 上传成功！`)
      selectedFiles.value[questionId * 100 + index] = null // 清空已上传的文件
      // 清空文件输入框
      const fileInput = document.getElementById(`file-${questionId}-${index}`)
      if (fileInput) {
        fileInput.value = ''
      }
      
      // 增加已上传文件计数
      uploadedFilesCount.value++
      
      // 检查是否所有文件都已上传完成
      if (isCurrentQuestionComplete.value) {
        // 所有文件上传完成，更新答题状态
        currentAnswerStatus.value = 'answered'
        // 保存答题状态到后端
        await saveCurrentAnswerStatus()
      }
    } else {
      uploadStatus.value[currentQuestionData.value.id + '_' + index] = 'error'
      alert(`文件 ${file.name} 上传失败: ${result.message || '未知错误'}`)
    }
  } catch (error) {
    uploadStatus.value[currentQuestionData.value.id + '_' + index] = 'error'
    console.error('上传文件失败:', error)
    alert('上传文件失败，请稍后再试。')
  }
}

// 开始倒计时
const startTimer = () => {
  timer = setInterval(() => {
    if (remainingTime.value > 0) {
      remainingTime.value--
    } else {
      // 时间到，自动交卷
      clearInterval(timer)
      alert('考试时间已到，系统将自动交卷！')
      router.push('/')
    }
  }, 1000)
}

// 组件挂载时开始倒计时和加载数据
onMounted(() => {
  startTimer()
  loadExamData()
})

// 组件卸载时清理定时器
onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>

<style scoped>
.exam-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background: blue; /* 调试背景色 */
  overflow: hidden;
}

.exam-header {
  background: white;
  padding: 0 20px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e0e0e0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin: 0;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.menu-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  color: #666;
  font-size: 18px;
}

.page-title {
  font-size: 18px;
  font-weight: bold;
  color: #FF3355;
  margin: 0;
}

.user-info {
  font-size: 14px;
  color: #666;
  margin-right: 20px;
}

.timer {
  font-size: 14px;
  color: #FF3355;
  font-weight: bold;
  background: #fff5f5;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #FF3355;
}

.exam-main {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  overflow: hidden;
  margin: 0;
  padding: 0;
  width: 100%;
  background: green; /* 调试背景色 */
}

.left-panel {
  background: white;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e0e0e0;
  margin: 0;
  padding: 0;
}

.question-tabs {
  display: flex;
  background: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
}

.tab-btn {
  padding: 12px 20px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
}

.tab-btn.active {
  color: #FF3355;
  border-bottom-color: #FF3355;
  background: white;
}

.answer-status {
  margin-left: 4px;
  font-size: 12px;
}

.upload-progress {
  margin: 15px 0;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 6px;
}

.progress-info {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #FF3355;
  transition: width 0.3s ease;
}

.question-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  overflow-x: hidden;
}

.question-rich-content {
  line-height: 1.6;
  color: #333;
  font-size: 14px;
}

.question-rich-content .question-item {
  margin-bottom: 8px;
  display: flex;
  align-items: flex-start;
}

.question-rich-content .label {
  font-weight: bold;
  color: #333;
  min-width: 80px;
  margin-right: 8px;
}

.question-rich-content .value {
  color: #666;
  flex: 1;
}

.question-rich-content .list-item {
  margin: 4px 0 4px 20px;
  color: #666;
}

.question-rich-content .paragraph {
  margin: 8px 0;
  color: #666;
  line-height: 1.6;
}

.question-rich-content h1 {
  font-size: 24px;
  font-weight: bold;
  color: #FF3355;
  margin: 0 0 16px 0;
  border-bottom: 2px solid #FF3355;
  padding-bottom: 8px;
}

.question-rich-content h2 {
  font-size: 20px;
  font-weight: bold;
  color: #333;
  margin: 20px 0 12px 0;
}

.question-rich-content h3 {
  font-size: 18px;
  font-weight: bold;
  color: #555;
  margin: 16px 0 8px 0;
}

.question-rich-content p {
  margin: 0 0 12px 0;
  text-align: justify;
}

.question-rich-content strong {
  font-weight: bold;
  color: #FF3355;
}

.question-rich-content em {
  font-style: italic;
  color: #666;
}

.question-rich-content code {
  background: #f4f4f4;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}

.question-rich-content pre {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 12px;
  margin: 12px 0;
  overflow-x: auto;
}

.question-rich-content pre code {
  background: none;
  padding: 0;
  border-radius: 0;
}

.question-rich-content li {
  margin: 4px 0;
  padding-left: 8px;
}

.question-loading {
  text-align: center;
  color: #666;
  font-style: italic;
  padding: 40px 0;
}

.exam-title {
  font-size: 20px;
  font-weight: bold;
  color: #333;
  margin: 0 0 20px 0;
}

.question-info {
  margin-bottom: 20px;
}

.info-item {
  margin-bottom: 10px;
  display: flex;
  align-items: flex-start;
}

.label {
  font-weight: bold;
  color: #333;
  min-width: 80px;
  margin-right: 10px;
}

.value {
  color: #666;
  flex: 1;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.requirements, .work-content, .detailed-description {
  margin-bottom: 20px;
}

.requirements h3, .work-content h3, .detailed-description h3 {
  font-size: 16px;
  font-weight: bold;
  color: #333;
  margin: 0 0 10px 0;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.data-table th,
.data-table td {
  border: 1px solid #e0e0e0;
  padding: 10px;
  text-align: left;
}

.data-table th {
  background: #f8f9fa;
  font-weight: bold;
  color: #333;
}

.data-table td {
  color: #666;
}

.requirements ul {
  margin: 0;
  padding-left: 20px;
}

.requirements li {
  margin-bottom: 5px;
  color: #666;
}

.work-content p {
  color: #666;
  line-height: 1.6;
  margin: 0;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.data-table th,
.data-table td {
  border: 1px solid #e0e0e0;
  padding: 10px;
  text-align: left;
}

.data-table th {
  background: #f8f9fa;
  font-weight: bold;
  color: #333;
}

.data-table td {
  color: #666;
}

.right-panel {
  background: white;
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

.upload-tabs {
  display: flex;
  background: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
}

.upload-tab-btn {
  flex: 1;
  padding: 12px 20px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
}

.upload-tab-btn.active {
  color: #FF3355;
  border-bottom-color: #FF3355;
  background: white;
}

.upload-content, .download-content {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
  overflow-x: auto;
  width: 100%;
}

.instructions {
  background: #f8f9fa;
  padding: 10px;
  border-radius: 6px;
  margin-bottom: 15px;
}

.instructions p {
  margin: 0 0 6px 0;
  color: #666;
  font-size: 12px;
  line-height: 1.4;
}

.instructions p:last-child {
  margin-bottom: 0;
}

.upload-table {
  overflow-x: auto;
  width: 100%;
  min-width: 0;
  flex: 1;
}

.upload-table table {
  width: 100%;
  border-collapse: collapse;
}

.upload-table th,
.upload-table td {
  border: 1px solid #e0e0e0;
  padding: 8px 6px;
  text-align: left;
  font-size: 12px;
  word-wrap: break-word;
  overflow-wrap: break-word;
  vertical-align: middle;
  white-space: nowrap;
}

.upload-table th {
  background: #f8f9fa;
  font-weight: bold;
  color: #333;
}

.upload-table th:nth-child(1) { width: auto; }
.upload-table th:nth-child(2) { width: auto; }
.upload-table th:nth-child(3) { width: auto; }
.upload-table th:nth-child(4) { width: auto; }

.file-input-label {
  display: inline-block;
  padding: 4px 8px;
  background: #6c757d;
  color: white;
  border-radius: 3px;
  cursor: pointer;
  font-size: 11px;
  transition: background-color 0.3s ease;
  white-space: nowrap;
}

.file-input-label:hover {
  background: #E62A4A;
}

.upload-btn {
  padding: 4px 8px;
  background: #FF3355;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 11px;
  transition: background-color 0.3s ease;
  white-space: nowrap;
  min-width: 50px;
}

.upload-btn:hover {
  background: #E62A4A;
}

.upload-btn.uploading {
  background: #6c757d;
  cursor: not-allowed;
}

.upload-btn.success {
  background: #28a745;
}

.upload-btn.error {
  background: #dc3545;
}

.upload-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.upload-arrow-btn {
  padding: 4px 8px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  transition: background-color 0.3s ease;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 4px;
}

.upload-arrow-btn::before {
  content: "↑";
  font-size: 12px;
}

.upload-arrow-btn:hover {
  background: #5a6268;
}

.file-icon {
  margin-right: 2px;
  font-size: 12px;
}

.status {
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}

.status.not-uploaded {
  background: #f8f9fa;
  color: #6c757d;
}

.status.uploaded {
  background: #d4edda;
  color: #155724;
}


.download-content {
  padding: 20px;
  color: #666;
}

.download-title {
  font-size: 18px;
  font-weight: bold;
  color: #333;
  margin: 0 0 20px 0;
  text-align: center;
}

.download-table {
  width: 100%;
  overflow-x: auto;
}

.download-table table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.download-table th,
.download-table td {
  padding: 8px 10px;
  text-align: left;
  border: 1px solid #e0e0e0;
}

.download-table th:nth-child(1) { width: 60px; }
.download-table th:nth-child(2) { width: 200px; }
.download-table th:nth-child(3) { width: 80px; }

.download-table th {
  background: #f8f9fa;
  font-weight: bold;
  color: #333;
  font-size: 14px;
}

.download-table td {
  color: #666;
  font-size: 14px;
}

.download-table tr:hover {
  background: #f8f9fa;
}

.download-btn {
  background: #FF3355;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 6px 8px;
  cursor: pointer;
  transition: background-color 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.download-btn:hover {
  background: #E62A4A;
}

.download-btn svg {
  width: 16px;
  height: 16px;
}

/* 底部导航按钮样式 */
.exam-footer {
  background: white;
  border-top: 1px solid #e0e0e0;
  padding: 15px 20px;
  box-shadow: 0 -2px 4px rgba(0,0,0,0.1);
}

.navigation-buttons {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 400px;
  margin: 0 auto;
}

.nav-btn {
  padding: 12px 30px;
  border: 2px solid #FF3355;
  border-radius: 6px;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 100px;
}

.prev-btn {
  background: white;
  color: #FF3355;
}

.prev-btn:hover:not(:disabled) {
  background: #FF3355;
  color: white;
}

.next-btn {
  background: #FF3355;
  color: white;
}

.next-btn:hover:not(:disabled) {
  background: #E62A4A;
  border-color: #E62A4A;
}

.nav-btn:disabled {
  background: #f8f9fa;
  border-color: #dee2e6;
  color: #6c757d;
  cursor: not-allowed;
}

.nav-btn:disabled:hover {
  background: #f8f9fa;
  border-color: #dee2e6;
  color: #6c757d;
}

.selected-file {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.selected-file .file-icon {
  font-size: 14px;
}

</style> 