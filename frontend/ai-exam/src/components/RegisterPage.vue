<template>
  <div class="register-container">
    <!-- 左侧蓝色背景区域 -->
    <div class="left-section">
      <div class="logo-section">
        <div class="logo-circle">
          <span class="logo-text">SDU</span>
        </div>
        <h1 class="university-name">杉达学院</h1>
        <h2 class="exam-title">职业技能等级认定考试</h2>
      </div>
    </div>

    <!-- 右侧白色注册表单区域 -->
    <div class="right-section">
      <div class="register-form">
        <h2 class="register-title">注册账号</h2>
        
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

        <div class="form-group">
          <label class="form-label">确认密码</label>
          <div class="password-input-container">
            <input 
              :type="showConfirmPassword ? 'text' : 'password'" 
              v-model="confirmPassword" 
              placeholder="请再次输入密码"
              class="form-input"
            />
            <button 
              type="button" 
              @click="toggleConfirmPassword"
              class="password-toggle"
            >
              <svg v-if="showConfirmPassword" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
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
          @click="handleRegister" 
          class="register-button"
          :disabled="!isFormValid || loading"
        >
          {{ loading ? '注册中...' : '注册' }}
        </button>

        <!-- 错误信息显示 -->
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <!-- 返回登录入口 -->
        <div class="login-section">
          <span class="login-text">已有账号？</span>
          <button @click="goToLogin" class="login-link">
            立即登录
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)
const errorMessage = ref('')

const togglePassword = () => {
  showPassword.value = !showPassword.value
}

const toggleConfirmPassword = () => {
  showConfirmPassword.value = !showConfirmPassword.value
}

const goToLogin = () => {
  router.push('/')
}

// 表单验证
const isFormValid = computed(() => {
  return username.value && 
         password.value && 
         confirmPassword.value && 
         password.value === confirmPassword.value &&
         /^1[3-9]\d{9}$/.test(username.value)
})

const handleRegister = async () => {
  // 表单验证
  if (!username.value || !password.value || !confirmPassword.value) {
    errorMessage.value = '请填写所有必填项'
    return
  }

  if (!/^1[3-9]\d{9}$/.test(username.value)) {
    errorMessage.value = '请输入正确的手机号码'
    return
  }

  if (password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }

  if (password.value.length < 6) {
    errorMessage.value = '密码长度至少6位'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    // 调用后端注册接口，使用JSON格式
    const response = await fetch('http://localhost:8000/student/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: `用户${username.value.slice(-4)}`, // 自动生成姓名
        phone: username.value,
        password: password.value
      })
    })

    const data = await response.json()

    if (response.ok && data.code === 20000) {
      console.log('注册成功:', data)
      alert('注册成功！请使用手机号码登录')
      router.push('/')
    } else {
      errorMessage.value = data.detail || '注册失败，请稍后重试'
      console.error('注册失败:', data)
    }
  } catch (error) {
    console.error('注册请求错误:', error)
    errorMessage.value = '网络错误，请检查服务器连接'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-container {
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
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin: 0;
  padding: 0;
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
  z-index: 1;
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
  overflow-y: auto;
}

.register-form {
  width: 100%;
  max-width: 500px;
}

.register-title {
  font-size: 28px;
  font-weight: bold;
  color: #333;
  margin-bottom: 30px;
  text-align: center;
}

.form-group {
  margin-bottom: 20px;
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

.register-button {
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

.register-button:hover:not(:disabled) {
  background: #E62A4A;
}

.register-button:disabled {
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

.login-section {
  margin-top: 24px;
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #e1e5e9;
}

.login-text {
  color: #666;
  font-size: 14px;
  margin-right: 8px;
}

.login-link {
  background: none;
  border: none;
  color: #FF3355;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
  margin: 0;
}

.login-link:hover {
  color: #E62A4A;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .register-container {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }
  
  .left-section {
    min-height: 200px;
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
</style> 