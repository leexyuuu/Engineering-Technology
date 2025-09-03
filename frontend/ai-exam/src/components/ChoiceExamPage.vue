<template>
  <div class="choice-exam-container">
    <!-- 顶部考试信息 -->
    <header class="exam-header">
      <div class="exam-title">人工智能训练师(三级)理论知识考试</div>
      <div class="exam-timer">考试倒计时: {{ formatTime(remainingTime) }}</div>
    </header>

    <!-- 主要内容区域 -->
    <main class="exam-main">
      <!-- 左侧边栏 -->
      <div class="left-sidebar">
        <!-- 考生信息 -->
        <div class="student-info">
          <div class="info-item">座位号: 011</div>
          <div class="info-item">考生姓名: 某某某</div>
          <div class="info-item">身份证号: 31000000000000000X</div>
          <div class="info-item">准考证号: 2024090100090035</div>
        </div>

        <!-- 答题状态 -->
        <div class="answer-status">
          <div class="status-item">
            <span class="status-label">标记:</span>
            <span class="status-value">{{ markedCount }}题</span>
          </div>
          <div class="status-item">
            <span class="status-label">已答:</span>
            <span class="status-value">{{ answeredCount }}题</span>
          </div>
          <div class="status-item">
            <span class="status-label">未答:</span>
            <span class="status-value">{{ unansweredCount }}题</span>
          </div>
        </div>

        <!-- 题目导航 -->
        <div class="question-navigation">
          <!-- 判断题 -->
          <div class="question-section">
            <h3 class="section-title">判断题 (共40题 合计20分)</h3>
            <div class="question-grid">
              <button 
                v-for="i in 40" 
                :key="i"
                :class="['question-btn', { 
                  'current': currentQuestion === i,
                  'answered': answers[i] !== undefined,
                  'marked': markedQuestions.includes(i)
                }]"
                @click="goToQuestion(i)"
              >
                {{ String(i).padStart(2, '0') }}
              </button>
            </div>
          </div>

          <!-- 单选题 -->
          <div class="question-section">
            <h3 class="section-title">单选题 (共140题 合计70分)</h3>
            <div class="question-grid">
              <button 
                v-for="i in 41" 
                :key="i + 40"
                :class="['question-btn', { 
                  'current': currentQuestion === i + 40,
                  'answered': answers[i + 40] !== undefined,
                  'marked': markedQuestions.includes(i + 40)
                }]"
                @click="goToQuestion(i + 40)"
              >
                {{ String(i + 40).padStart(2, '0') }}
              </button>
            </div>
          </div>
        </div>

        <!-- 交卷按钮 -->
        <button class="submit-btn" @click="submitExam">交卷</button>
      </div>

      <!-- 右侧题目内容 -->
      <div class="right-content">
        <!-- 题目描述区 (占30%) -->
        <div class="question-description">
          <div class="question-text">
            {{ currentQuestion }}. {{ getCurrentQuestionText() }} [{{ getCurrentQuestionScore() }}分]
          </div>
        </div>
        
        <!-- 答题区 (占70%) -->
        <div class="answer-area">
          <!-- 判断题选项 -->
          <div v-if="currentQuestion <= 40" class="options">
            <label class="option-item">
              <input 
                type="radio" 
                :name="'question-' + currentQuestion"
                value="true"
                :checked="answers[currentQuestion] === true"
                @change="selectAnswer(true)"
              />
              <span class="option-text">● 正确</span>
            </label>
            <label class="option-item">
              <input 
                type="radio" 
                :name="'question-' + currentQuestion"
                value="false"
                :checked="answers[currentQuestion] === false"
                @change="selectAnswer(false)"
              />
              <span class="option-text">错误</span>
            </label>
          </div>

          <!-- 单选题选项 -->
          <div v-else class="options">
            <label 
              v-for="option in getCurrentQuestionOptions()" 
              :key="option.key"
              class="option-item"
            >
              <input 
                type="radio" 
                :name="'question-' + currentQuestion"
                :value="option.key"
                :checked="answers[currentQuestion] === option.key"
                @change="selectAnswer(option.key)"
              />
              <span class="option-text">{{ option.key }}. {{ option.text }}</span>
            </label>
          </div>

          <!-- 题目导航按钮 -->
          <div class="question-navigation-buttons">
            <button 
              class="nav-btn prev-btn" 
              @click="previousQuestion"
              :disabled="currentQuestion <= 1"
            >
              上一题
            </button>
            <button 
              class="nav-btn next-btn" 
              @click="nextQuestion"
              :disabled="currentQuestion >= 180"
            >
              下一题
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

// 考试状态
const currentQuestion = ref(1)
const answers = ref({})
const markedQuestions = ref([])
const remainingTime = ref(13 * 60 * 60 + 2 * 60 + 58) // 13小时2分58秒

// 计算属性
const answeredCount = computed(() => Object.keys(answers.value).length)
const unansweredCount = computed(() => 180 - answeredCount.value)
const markedCount = computed(() => markedQuestions.value.length)

// 题目数据（模拟数据）
const questions = ref({
  // 判断题
  1: { text: "深度学习中的卷积神经网络CNN主要用于处理序列数据", score: 0.5, type: "judgment" },
  2: { text: "机器学习中的监督学习需要标注数据", score: 0.5, type: "judgment" },
  3: { text: "神经网络中的激活函数用于增加模型的非线性", score: 0.5, type: "judgment" },
  
  // 单选题
  41: { 
    text: "以下哪个不是机器学习的主要类型？", 
    score: 0.5, 
    type: "choice",
    options: [
      { key: "A", text: "监督学习" },
      { key: "B", text: "无监督学习" },
      { key: "C", text: "强化学习" },
      { key: "D", text: "深度学习" }
    ]
  },
  42: { 
    text: "卷积神经网络主要用于处理什么类型的数据？", 
    score: 0.5, 
    type: "choice",
    options: [
      { key: "A", text: "文本数据" },
      { key: "B", text: "图像数据" },
      { key: "C", text: "音频数据" },
      { key: "D", text: "时间序列数据" }
    ]
  }
})

// 方法
const getCurrentQuestionText = () => {
  return questions.value[currentQuestion.value]?.text || "题目加载中..."
}

const getCurrentQuestionScore = () => {
  return questions.value[currentQuestion.value]?.score || 0
}

const getCurrentQuestionOptions = () => {
  return questions.value[currentQuestion.value]?.options || []
}

const selectAnswer = (answer) => {
  answers.value[currentQuestion.value] = answer
}

const goToQuestion = (questionNumber) => {
  currentQuestion.value = questionNumber
}

const previousQuestion = () => {
  if (currentQuestion.value > 1) {
    currentQuestion.value--
  }
}

const nextQuestion = () => {
  if (currentQuestion.value < 180) {
    currentQuestion.value++
  }
}

const submitExam = () => {
  if (confirm('确定要交卷吗？交卷后将无法修改答案。')) {
    alert('考试完成！感谢您的参与。')
  }
}

const formatTime = (seconds) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  return `${hours}时${minutes.toString().padStart(2, '0')}分${secs.toString().padStart(2, '0')}秒`
}

// 倒计时
let timer = null

const startTimer = () => {
  timer = setInterval(() => {
    if (remainingTime.value > 0) {
      remainingTime.value--
    } else {
      clearInterval(timer)
      alert('考试时间已到，系统将自动交卷！')
    }
  }, 1000)
}

onMounted(() => {
  startTimer()
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>

<style scoped>
.choice-exam-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.exam-header {
  background: white;
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e0e0e0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.exam-title {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}

.exam-timer {
  font-size: 16px;
  color: #e74c3c;
  font-weight: bold;
}

.exam-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.left-sidebar {
  width: 300px;
  background: white;
  border-right: 1px solid #e0e0e0;
  padding: 20px;
  overflow-y: auto;
}

.student-info {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.info-item {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.answer-status {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.status-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.status-label {
  font-size: 14px;
  color: #666;
}

.status-value {
  font-size: 14px;
  color: #4A90E2;
  font-weight: bold;
}

.question-navigation {
  margin-bottom: 20px;
}

.question-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 14px;
  font-weight: bold;
  color: #333;
  margin-bottom: 10px;
}

.question-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-bottom: 15px;
}

.question-btn {
  width: 40px;
  height: 40px;
  border: 1px solid #ddd;
  background: white;
  color: #666;
  font-size: 12px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.3s ease;
}

.question-btn:hover {
  border-color: #4A90E2;
}

.question-btn.current {
  background: #4A90E2;
  color: white;
  border-color: #4A90E2;
}

.question-btn.answered {
  background: #27ae60;
  color: white;
  border-color: #27ae60;
}

.question-btn.marked {
  background: #f39c12;
  color: white;
  border-color: #f39c12;
}

.submit-btn {
  width: 100%;
  padding: 12px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.submit-btn:hover {
  background: #c0392b;
}

.right-content {
  flex: 1;
  background: white;
  display: flex;
  flex-direction: column;
}

.question-description {
  flex: 0 0 30%; /* 占30%高度 */
  background: white;
  padding: 30px 30px 20px 30px;
  border-bottom: 1px solid #e0e0e0;
}

.answer-area {
  flex: 0 0 70%; /* 占70%高度 */
  background: white;
  padding: 20px 30px 30px 30px;
  display: flex;
  flex-direction: column;
}

.question-text {
  font-size: 18px;
  color: #333;
  line-height: 1.6;
  margin-bottom: 30px;
}

.options {
  display: flex;
  flex-direction: column;
  gap: 15px;
  flex: 1;
  justify-content: center;
}

.option-item {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 10px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.option-item:hover {
  border-color: #4A90E2;
  background: #f8f9fa;
}

.option-item input[type="radio"] {
  margin-right: 10px;
  transform: scale(1.2);
}

.option-text {
  font-size: 16px;
  color: #333;
}

.question-navigation-buttons {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-top: auto;
  padding-top: 20px;
}

.nav-btn {
  padding: 12px 30px;
  border: 2px solid #4A90E2;
  border-radius: 6px;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 100px;
}

.prev-btn {
  background: white;
  color: #4A90E2;
}

.prev-btn:hover:not(:disabled) {
  background: #4A90E2;
  color: white;
}

.next-btn {
  background: #4A90E2;
  color: white;
}

.next-btn:hover:not(:disabled) {
  background: #357abd;
  border-color: #357abd;
}

.nav-btn:disabled {
  background: #f8f9fa;
  border-color: #dee2e6;
  color: #6c757d;
  cursor: not-allowed;
}
</style>
