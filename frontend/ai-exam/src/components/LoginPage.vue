<template>
  <div class="login-container">
    <!-- 左侧蓝色背景区域 -->
    <div class="left-section">
      <div class="logo-section">
        <!-- <div class="logo-circle">
          <span class="logo-text">SDU</span>
        </div> -->
        <h1 class="university-name">人工智能推介官</h1>
        <h2 class="exam-title">定向培训考核</h2>
      </div>
    </div>

    <!-- 右侧白色登录表单区域 -->
    <div class="right-section">
      <div class="login-form">
        <h2 class="login-title">登录</h2>
        
        <div class="form-group">
          <label class="form-label">手机号码</label>
          <input 
            type="tel" 
            v-model="username" 
            placeholder="请输入手机号码"
            class="form-input"
          />
        </div>

        <div class="form-group">
          <label class="form-label">密码</label>
          <div class="password-input-container">
            <input 
              :type="showPassword ? 'text' : 'password'" 
              v-model="password" 
              placeholder="请输入密码"
              class="form-input"
            />
            <button 
              type="button" 
              @click="togglePassword"
              class="password-toggle"
            >
              <svg v-if="showPassword" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
        </div>

        <button 
          @click="handleLogin" 
          class="login-button"
          :disabled="!username || !password || loading"
        >
          {{ loading ? '登录中...' : '登录' }}
        </button>

        <!-- 错误信息显示 -->
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <!-- 测试按钮 -->
        <div class="test-buttons">
          <button @click="goToChoiceExam" class="test-btn">
            测试选择题考试界面
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const errorMessage = ref('')

const togglePassword = () => {
  showPassword.value = !showPassword.value
}

// 移除goToRegister函数

const goToChoiceExam = () => {
  router.push('/choice-exam')
}

const handleLogin = async () => {
  if (!username.value || !password.value) {
    errorMessage.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    // 调用后端学生登录接口
    const response = await fetch('http://localhost:8000/student/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        phone: username.value,
        password: password.value
      })
    })

    const data = await response.json()

    if (response.ok && data.code === 20000) {
      // 登录成功，保存token
      localStorage.setItem('studentToken', data.token)
      localStorage.setItem('studentData', JSON.stringify(data.data))
      
      console.log('登录成功:', data)

      // 如果有可参加的考试，获取试题
      if (data.data.upcoming_exam && data.data.upcoming_exam.exam_id) {
        try {
          const examResponse = await fetch(`http://localhost:8000/student/exams/${data.data.upcoming_exam.exam_id}/result/${data.data.id}`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${data.token}`,
              'Content-Type': 'application/json',
            }
          })
          
          const examData = await examResponse.json()
          
          if (examResponse.ok && examData.code === 20000) {
            console.log('获取试题成功:', examData)
            localStorage.setItem('examQuestions', JSON.stringify(examData.data))
          } else {
            console.error('获取试题失败:', examData)
            alert('登录成功！但获取试题失败')
          }
        } catch (examError) {
          console.error('获取试题请求错误:', examError)
          alert('登录成功！但获取试题时发生错误')
        }
      } else {
        alert('登录成功！暂无可参加的考试')
      }

      router.push('/exam')
    } else {
      // 登录失败
      errorMessage.value = data.message || '登录失败，请检查手机号码和密码'
      console.error('登录失败:', data)
    }
  } catch (error) {
    console.error('登录请求错误:', error)
    errorMessage.value = '网络错误，请检查服务器连接'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  overflow: hidden;
  background: red; /* 调试背景色 */
}

.left-section {
  background-image: url('@/assets/shanghai-skyline.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin: 0;
  padding: 0;
}

/* 添加蓝色蒙层 */
.left-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(30, 60, 114, 0.6); /* 浅浅的蓝色蒙层，透明度0.6 */
  z-index: 1;
}

.left-section::after {
  content: '';
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 80px;
  background: white;
  border-radius: 50% 0 0 50%;
  transform: translateX(50%) scaleX(0.5);
  z-index: -1;
}

/* 添加媒体查询处理大屏幕 */
@media (min-width: 1600px) {
  .left-section::after {
    display: none; /* 超大屏幕直接隐藏 */
  }
}

.logo-section {
  text-align: center;
  color: white;
  z-index: 2; /* 确保在蓝色蒙层之上 */
  position: relative;
}

.logo-circle {
  width: 80px;
  height: 80px;
  background: #FF3355;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
}

.logo-text {
  color: white;
  font-weight: bold;
  font-size: 18px;
}

.university-name {
  font-size: 28px;
  font-weight: bold;
  margin: 0 0 10px 0;
  color: #FF3355;
}

.exam-title {
  font-size: 20px;
  font-weight: normal;
  margin: 0;
  color: white;
}

.right-section {
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  margin: 0;
}

.login-form {
  width: 100%;
  max-width: 500px;
}

.login-title {
  font-size: 28px;
  font-weight: bold;
  color: #333;
  margin-bottom: 30px;
  text-align: center;
}

.form-group {
  margin-bottom: 24px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

.form-input {
  width: 100%;
  padding: 14px;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.3s ease;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #FF3355;
}

.password-input-container {
  position: relative;
}

.password-toggle {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  color: #666;
  padding: 4px;
}

.password-toggle:hover {
  color: #333;
}

.login-button {
  width: 100%;
  padding: 14px;
  background: #FF3355;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.login-button:hover:not(:disabled) {
  background: #E62A4A;
}

.login-button:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.error-message {
  margin-top: 16px;
  padding: 12px;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 6px;
  color: #c33;
  font-size: 14px;
  text-align: center;
}

/* 测试按钮样式 */
.test-buttons {
  margin-top: 20px;
  text-align: center;
}

.test-btn {
  padding: 10px 20px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.test-btn:hover {
  background: #5a6268;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .login-container {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }
  
  .left-section {
    min-height: 200px;
    background-size: cover;
    background-position: center;
  }
  
  .left-section::after {
    display: none;
  }
  
  .right-section {
    padding: 20px;
  }
  
  .university-name {
    font-size: 24px;
  }
  
  .exam-title {
    font-size: 18px;
  }
}

/* 大屏幕优化 */
@media (min-width: 1200px) {
  .left-section {
    background-size: cover;
    background-position: center;
  }
}
</style> 