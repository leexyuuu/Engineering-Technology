
<template>
  <div class="exam-notice-page">
    <div class="container">
      <div class="scroll-area">
        <h1 class="title">考试须知</h1>
        <div class="content-text">
          <p v-for="(value , index ) in content"  :key="index" class="content-item">
            <span class="content-index">{{ index + 1 }}.</span>
            <span class="content-value">{{ value }}</span>
          </p>
        </div>
      </div>
      <div class="button-container">
        <button class="button" @click="goToExam" :class="{'countdown-active': time > 0 || isLoading }" :disabled="time > 0 || isLoading">
          {{ time > 0 ? `考试将在 ${time}s 后开始` : (isLoading ? '正在开始考试...' : '进入考试') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
  import { createApp , ref ,onMounted ,onUnmounted } from 'vue';

  const content = [
  '考生必须同时持有本人准考证和身份证原件于开考前 10 分钟入场，对号入座。入场后将身份证和准考证同时放在课桌左上角，便于监考人员查对。',
  '考生参加考试，只准使用必须的书写文具，如钢笔、铅笔、角尺、橡皮等物品。禁止携带书籍、笔记等资料。考生携带的物品必须按监考人员指定的位置集中存放。',
  '开考 15 分钟后，考生不得入场。开考 30 分钟后，考生才能交卷出场。考生离场后不得再进场续考。',
  '考场内不准私自借用文具，不许自备草稿纸、不得使用手机、拷机或手提电脑等通讯工具，违者作违纪处理。',
  '考生若遇试题字迹不清，可举手询问，但不得要求监考人员对题意做任何解释或提示。',
  '考生必须严格遵守考场纪律，考试时不准交头接耳、左顾右盼、抄袭他人试卷；不准冒名替考或与他人换卷；不准吸烟、吃零食。违纪或作弊者，一律取消考试资格，成绩作无效处理。',
  '考生离开考场时必须交卷，不准携带试卷离开考场，违者成绩作无效处理，取消补考资格并通知相关部门。考生离开考场后，不准在考场附近逗留和交谈。考试结束后考生应立即停止答卷，并将试卷按顺序整理好后，放在课桌上有监考人员统一收取。',
  '考生应自觉服从监考人员管理，不得以任何理由妨碍监考人员进行正常工作。监考人员有权对考场内发生的各类违纪事件，按规定作出处理意见。情节严重、态度恶劣者，将通知所在单位或提交公安部门处理。'
  ]

  const time = ref(10)
  const definestatus = ref(true)
  let countdown = null

  onMounted(() => {
     countdown= setInterval (() => {
      if ( time.value > 0 ){
         time.value --;
      }else {
          definestatus.value = false;
          clearInterval(countdown);

      }
    }, 1000);
  })

  onUnmounted (() =>{
    clearInterval(countdown);
  })


import { useRouter } from 'vue-router'

const router = useRouter()
const isLoading = ref(false)

const goToExam = async () => {
  if (isLoading.value) return // 防止重复点击
  
  try {
    isLoading.value = true
    
    // 先调用开始考试API
    const token = localStorage.getItem('studentToken')
    const studentData = JSON.parse(localStorage.getItem('studentData'))
    
    if (!token) {
      alert('登录信息已过期，请重新登录')
      router.push('/')
      return
    }
    
    if (!studentData?.upcoming_exam?.exam_id) {
      alert('当前暂无可参加的考试')
      return
    }

    const response = await fetch('/api/student/exams/start', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        exam_id: studentData.upcoming_exam.exam_id
      })
    })

    const result = await response.json()

    if (response.ok) {
      // 开始考试成功，跳转到考试页面
      router.push('/exam')
    } else {
      // 开始考试失败，显示错误信息
      alert(`开始考试失败: ${result.detail || result.message || '未知错误'}`)
    }
  } catch (error) {
    console.error('开始考试请求失败:', error)
    alert('网络错误，请稍后重试')
  } finally {
    isLoading.value = false
  }
}
</script>

<style>
/* 强制覆盖所有背景色，包括全局样式 test*/


body, html {
  background-color: #fffefe ;
}

/* 覆盖Vue应用的默认样式 */
#app {
  max-width: none !important;
  margin: 0 !important;
  padding: 0 !important;
  background-color: #fffefe !important;
}

.exam-notice-page {
  background-color: #fffefe !important;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}

.container {
  background-color: #fffefe;
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  padding: 40px 24px 0;
  display: flex;
  flex-direction: column;
  text-align: center;
  box-sizing: border-box;
}

.scroll-area {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.title {
  font-weight: bold;
  font-size: 30px;
  margin: 0 0 24px 0;
}

.content-text {
  text-align: left;
}

.content-item {
   margin-bottom: 35px;
   padding-left: 5%;
   padding-right: 5%;
    text-align: justify;
}

.content-index {
  font-weight: bold;
  min-width: 50px;
  padding-right:5px ;
}

.content-value{
  flex: 1;
  text-align: justify;
}

.button-container {
  flex-shrink: 0;
  padding: 20px 0 24px;
  display: flex;
  justify-content: center;
}

.button {
  background-color: rgb(80, 157, 234);
  border: none;
  border-radius: 10px;
  height: 50px;
  width:300px;
  font-size: large;
  color: white;
}

.countdown-active {
  color: grey !important;
  opacity: 0.7;
}

.button:not(.countdown-active) {
  color: white !important;
  font-weight: bold;
  opacity: 1;
}

</style>
