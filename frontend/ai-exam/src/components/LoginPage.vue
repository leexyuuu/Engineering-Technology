<template>
  <div class="login-container">
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

    <!-- 右侧白色登录表单区域 -->
    <div class="right-section">
      <div class="login-form">
        <h2 class="login-title">登录</h2>
        
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input 
            type="text" 
            v-model="username" 
            placeholder="请输入用户名"
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
          :disabled="!username || !password"
        >
          登录
        </button>
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

const togglePassword = () => {
  showPassword.value = !showPassword.value
}

const handleLogin = () => {
  if (!username.value || !password.value) {
    alert('请输入用户名和密码')
    return
  }
  
  // 这里可以添加登录逻辑
  console.log('登录信息:', {
    username: username.value,
    password: password.value
  })
  
  // 模拟登录成功，跳转到考试页面
  alert('登录成功！')
  router.push('/exam')
}
</script>

<style scoped>
.login-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  margin: 0;
  padding: 0;
}

.left-section {
  flex: 2;
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
  right: -50px;
  top: 0;
  bottom: 0;
  width: 100px;
  background: white;
  border-radius: 50% 0 0 50%;
  transform: translateX(50%);
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
  background: #e74c3c;
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
  color: #e74c3c;
}

.exam-title {
  font-size: 20px;
  font-weight: normal;
  margin: 0;
  color: white;
}

.right-section {
  flex: 3;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  margin: 0;
}

.login-form {
  width: 100%;
  max-width: 350px;
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
  border-color: #3498db;
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
  background: #3498db;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.login-button:hover:not(:disabled) {
  background: #2980b9;
}

.login-button:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
  }
  
  .left-section {
    flex: 1;
    min-height: 200px;
  }
  
  .left-section::after {
    display: none;
  }
  
  .right-section {
    flex: 1;
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