<template>
  <div class="exam-container">
    <!-- 顶部导航栏 -->
    <header class="exam-header">
      <div class="header-left">
        <button class="menu-btn">☰</button>
        <h1 class="page-title">试题单</h1>
      </div>
      <div class="header-right">
        <span class="user-info">姓名: 13916057361</span>
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
            v-for="i in 6" 
            :key="i"
            :class="['tab-btn', { active: currentQuestion === i }]"
            @click="currentQuestion = i"
          >
            第{{ i }}题
          </button>
        </div>

        <!-- 题目内容 -->
        <div class="question-content">
          <h2 class="exam-title">{{ currentQuestionData.title }}</h2>
          
          <div class="question-info">
            <div class="info-item">
              <span class="label">试题代码:</span>
              <span class="value">{{ currentQuestionData.code }}</span>
            </div>
            <div class="info-item">
              <span class="label">试题名称:</span>
              <span class="value">{{ currentQuestionData.name }}</span>
            </div>
            <div class="info-item">
              <span class="label">考试时间:</span>
              <span class="value">{{ currentQuestionData.time }}</span>
            </div>
          </div>

          <div class="requirements">
            <h3>场地要求:</h3>
            <ul>
              <li v-for="requirement in currentQuestionData.requirements" :key="requirement">{{ requirement }}</li>
            </ul>
          </div>

          <div class="work-content">
            <h3>工作内容:</h3>
            <p>{{ currentQuestionData.workContent }}</p>
          </div>
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
                <tr v-for="(file, index) in currentQuestionData.uploadFiles" :key="index">
                  <td>{{ index + 1 }}</td>
                  <td>上传{{ file }}</td>
                  <td>
                    <input type="file" :id="'file-' + index" style="display: none;" />
                    <label :for="'file-' + index" class="file-input-label">选择文件</label>
                  </td>
                  <td>
                    <button class="upload-btn">上传答案{{ index + 1 }}</button>
                  </td>
                </tr>
              </tbody>
            </table>
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
          @click="currentQuestion >= 6 ? submitExam() : goToNextQuestion()"
          :disabled="false"
        >
          {{ currentQuestion >= 6 ? '交卷' : '下一题' }}
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

// 题目数据
const questions = ref([
  {
    id: 1,
    title: '人工智能训练师三级',
    code: '2.2.3',
    name: '日常运动量随机森林预测模型开发与测试',
    time: '20min',
    requirements: [
      '人工智能训练师主机1台;',
      'Python 编译环境;',
      'fitness analysis数据集。'
    ],
    workContent: '随着人们健康意识的增强，越来越多的人开始关注日常运动和健康管理。使用提供的训练数据，补全2.2.3.ipynb代码。选择合适的特征，开发一个预测模型，基于个体性别，个体对运动的看法和个人健康评价来预测个体年龄。利用测试工具对模型进行测试，并对测试结果进行分析，完成测试报告，并运用工具对错误原因进行纠正。',
    uploadFiles: [
      '2.2.3_model.pki',
      '2.2.3_results.txt',
      '2.2.3_report.txt',
      '2.2.3.docx',
      '2.2.3_results_xgb.txt',
      '2.2.3.html'
    ]
  },
  {
    id: 2,
    title: '人工智能训练师三级',
    code: '2.2.4',
    name: '电商用户行为分析模型构建',
    time: '25min',
    requirements: [
      '人工智能训练师主机1台;',
      'Python 编译环境;',
      'ecommerce_behavior.csv数据集。'
    ],
    workContent: '电商平台需要分析用户行为模式以优化推荐系统。使用提供的电商用户行为数据，构建一个用户行为分析模型。分析用户的浏览、收藏、加购、购买等行为特征，建立用户画像模型，预测用户的购买概率。完成模型训练、验证和测试，并生成详细的分析报告。',
    uploadFiles: [
      '2.2.4_model.pkl',
      '2.2.4_analysis.txt',
      '2.2.4_report.txt',
      '2.2.4_presentation.pptx',
      '2.2.4_visualization.html'
    ]
  },
  {
    id: 3,
    title: '人工智能训练师三级',
    code: '2.2.5',
    name: '图像分类CNN模型开发',
    time: '30min',
    requirements: [
      '人工智能训练师主机1台;',
      'Python 编译环境;',
      'image_classification数据集。'
    ],
    workContent: '使用卷积神经网络(CNN)技术，开发一个图像分类模型。数据集包含多个类别的图像，需要构建CNN架构，进行数据预处理、模型训练和优化。实现数据增强技术，提高模型泛化能力。完成模型评估，生成分类报告和可视化结果。',
    uploadFiles: [
      '2.2.5_cnn_model.h5',
      '2.2.5_training_log.txt',
      '2.2.5_evaluation.txt',
      '2.2.5_classification_report.txt',
      '2.2.5_visualization.py'
    ]
  },
  {
    id: 4,
    title: '人工智能训练师三级',
    code: '2.2.6',
    name: '自然语言处理文本分类',
    time: '25min',
    requirements: [
      '人工智能训练师主机1台;',
      'Python 编译环境;',
      'text_classification.csv数据集。'
    ],
    workContent: '构建一个自然语言处理模型，用于文本分类任务。使用提供的文本数据集，实现文本预处理、特征提取和模型训练。应用词向量技术，构建深度学习模型进行文本分类。完成模型性能评估，生成分类准确率报告和错误分析。',
    uploadFiles: [
      '2.2.6_nlp_model.pkl',
      '2.2.6_preprocessing.py',
      '2.2.6_classification_results.txt',
      '2.2.6_accuracy_report.txt',
      '2.2.6_error_analysis.txt'
    ]
  },
  {
    id: 5,
    title: '人工智能训练师三级',
    code: '2.2.7',
    name: '时间序列预测模型开发',
    time: '20min',
    requirements: [
      '人工智能训练师主机1台;',
      'Python 编译环境;',
      'time_series_data.csv数据集。'
    ],
    workContent: '开发一个时间序列预测模型，用于预测未来趋势。使用提供的时间序列数据，实现数据清洗、特征工程和模型构建。应用ARIMA、LSTM等时间序列预测技术，完成模型训练和验证。生成预测结果和模型性能评估报告。',
    uploadFiles: [
      '2.2.7_arima_model.pkl',
      '2.2.7_lstm_model.h5',
      '2.2.7_predictions.csv',
      '2.2.7_forecast_report.txt',
      '2.2.7_model_comparison.txt'
    ]
  },
  {
    id: 6,
    title: '人工智能训练师三级',
    code: '2.2.8',
    name: '推荐系统协同过滤算法实现',
    time: '25min',
    requirements: [
      '人工智能训练师主机1台;',
      'Python 编译环境;',
      'recommendation_data.csv数据集。'
    ],
    workContent: '实现协同过滤推荐算法，构建个性化推荐系统。使用用户-物品交互数据，实现基于用户的协同过滤和基于物品的协同过滤算法。完成相似度计算、推荐生成和模型评估。生成推荐系统性能报告和用户推荐结果分析。',
    uploadFiles: [
      '2.2.8_user_cf_model.pkl',
      '2.2.8_item_cf_model.pkl',
      '2.2.8_recommendations.csv',
      '2.2.8_performance_report.txt',
      '2.2.8_user_analysis.txt'
    ]
  }
])

// 计算当前题目数据
const currentQuestionData = computed(() => {
  return questions.value.find(q => q.id === currentQuestion.value) || questions.value[0]
})



const fileSizes = ref({
  0: '0KB',
  1: '0KB',
  2: '0KB',
  3: '0KB',
  4: '0KB',
  5: '0KB'
})

const fileStatuses = ref({
  0: 'not-uploaded',
  1: 'not-uploaded',
  2: 'not-uploaded',
  3: 'not-uploaded',
  4: 'not-uploaded',
  5: 'not-uploaded'
})

// 下载文件列表
const downloadFiles = ref([
  { name: '2.2.3.ipynb', url: '#' },
  { name: '2.2.3.docx', url: '#' },
  { name: 'fitness analysis.csv', url: '#' }
])

// 导航方法
const goToPreviousQuestion = () => {
  if (currentQuestion.value > 1) {
    currentQuestion.value--
  }
}

const goToNextQuestion = () => {
  if (currentQuestion.value < 6) {
    currentQuestion.value++
  }
}

const submitExam = () => {
  // 这里可以添加交卷逻辑
  if (confirm('确定要交卷吗？交卷后将无法修改答案。')) {
    alert('考试完成！感谢您的参与。')
    // 停止倒计时
    if (timer) {
      clearInterval(timer)
    }
    // 跳转回登录页面
    router.push('/')
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
  // 这里可以添加实际的下载逻辑
  console.log(`开始下载文件: ${file.name}`)
  
  // 模拟下载过程
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

// 组件挂载时开始倒计时
onMounted(() => {
  startTimer()
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

.question-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  overflow-x: hidden;
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


</style> 