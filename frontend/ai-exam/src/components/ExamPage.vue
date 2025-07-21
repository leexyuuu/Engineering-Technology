<template>
  <div class="exam-container">
    <!-- 顶部导航栏 -->
    <header class="exam-header">
      <div class="header-left">
        <button class="menu-btn">☰</button>
        <h1 class="page-title">试题单</h1>
      </div>
      <div class="header-right">
        <span class="user-info">X ceshi_001姓名:测试|座位号:1</span>
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
          <h2 class="exam-title">人工智能训练师三级</h2>
          
          <div class="question-info">
            <div class="info-item">
              <span class="label">试题代码:</span>
              <span class="value">2.2.3</span>
            </div>
            <div class="info-item">
              <span class="label">试题名称:</span>
              <span class="value">日常运动量随机森林预测模型开发与测试</span>
            </div>
            <div class="info-item">
              <span class="label">考试时间:</span>
              <span class="value">20min</span>
            </div>
          </div>

          <div class="requirements">
            <h3>场地要求:</h3>
            <ul>
              <li>人工智能训练师主机1台;</li>
              <li>Python 编译环境;</li>
              <li>fitness analysis数据集。</li>
            </ul>
          </div>

          <div class="work-content">
            <h3>工作内容:</h3>
            <p>随着人们健康意识的增强,越来越多的人开始关注日常运动和健康管理。使用提供的训练数据,补全2.2.3.ipynb代码。选择合适的特征,开发一个预测模型,基于个体性别,个体对运动的看法和个人健康评价来预测个体年龄。利用测试工具对模型进行测试,并对测试结果进行分析,完成测试报告,并运用工具对错误原因进行纠正。</p>
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
                <tr v-for="(file, index) in uploadFiles" :key="index">
                  <td>{{ index + 1 }}</td>
                  <td>{{ file }}</td>
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
          <p>素材下载功能开发中...</p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const currentQuestion = ref(3)
const activeTab = ref('upload')

const uploadFiles = ref([
  '2.2.3_model.pki',
  '2.2.3_results.txt',
  '2.2.3_report.txt',
  '2.2.3.docx',
  '2.2.3_results_xgb.txt',
  '2.2.3.html'
])
</script>

<style scoped>
.exam-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
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
  color: #3498db;
  margin: 0;
}

.user-info {
  font-size: 14px;
  color: #666;
}

.exam-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.left-panel {
  flex: 2;
  background: white;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e0e0e0;
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
  color: #3498db;
  border-bottom-color: #3498db;
  background: white;
}

.question-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
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
}

.requirements, .work-content {
  margin-bottom: 20px;
}

.requirements h3, .work-content h3 {
  font-size: 16px;
  font-weight: bold;
  color: #333;
  margin: 0 0 10px 0;
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
}

.right-panel {
  flex: 1;
  background: white;
  display: flex;
  flex-direction: column;
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
  color: #3498db;
  border-bottom-color: #3498db;
  background: white;
}

.upload-content, .download-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.instructions {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.instructions p {
  margin: 0 0 8px 0;
  color: #666;
  font-size: 14px;
}

.instructions p:last-child {
  margin-bottom: 0;
}

.upload-table table {
  width: 100%;
  border-collapse: collapse;
}

.upload-table th,
.upload-table td {
  border: 1px solid #e0e0e0;
  padding: 12px;
  text-align: left;
  font-size: 14px;
}

.upload-table th {
  background: #f8f9fa;
  font-weight: bold;
  color: #333;
}

.file-input-label {
  display: inline-block;
  padding: 6px 12px;
  background: #3498db;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.3s ease;
}

.file-input-label:hover {
  background: #2980b9;
}

.upload-btn {
  padding: 6px 12px;
  background: #27ae60;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.3s ease;
}

.upload-btn:hover {
  background: #229954;
}

.download-content {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
}
</style> 