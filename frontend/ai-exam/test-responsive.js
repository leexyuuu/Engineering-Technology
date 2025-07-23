// PC Web端响应式测试脚本
// 在浏览器控制台中运行此脚本

const testSizes = [
  // 小屏笔记本
  { width: 1024, height: 768, name: "小屏笔记本" },
  { width: 1366, height: 768, name: "标准笔记本" },
  
  // 桌面显示器
  { width: 1440, height: 900, name: "MacBook Pro" },
  { width: 1920, height: 1080, name: "1080p 显示器" },
  { width: 1920, height: 1200, name: "16:10 显示器" },
  
  // 高分辨率显示器
  { width: 2560, height: 1440, name: "2K 显示器" },
  { width: 2560, height: 1600, name: "2K 16:10" },
  { width: 3840, height: 2160, name: "4K 显示器" },
  
  // 超宽屏
  { width: 2560, height: 1080, name: "21:9 超宽屏" },
  { width: 3440, height: 1440, name: "34寸 超宽屏" },
  { width: 3840, height: 1080, name: "32:9 超宽屏" },
  
  // 多屏/大屏
  { width: 5120, height: 1440, name: "双屏 2K" },
  { width: 7680, height: 2160, name: "三屏 4K" }
];

let currentIndex = 0;

function testNextSize() {
  if (currentIndex >= testSizes.length) {
    console.log('所有PC屏幕尺寸测试完成！');
    return;
  }
  
  const size = testSizes[currentIndex];
  console.log(`测试 ${size.name}: ${size.width}x${size.height}`);
  
  // 设置视口大小
  window.resizeTo(size.width, size.height);
  
  // 等待页面重新渲染
  setTimeout(() => {
    // 检查页面元素
    checkPageElements(size);
    currentIndex++;
    
    // 继续下一个测试
    setTimeout(testNextSize, 2000);
  }, 1000);
}

function checkPageElements(size) {
  const currentPath = window.location.pathname;
  
  if (currentPath === '/') {
    // 登录页面测试
    console.log('检查登录页面...');
    
    // 检查容器是否填满屏幕
    const container = document.querySelector('.login-container');
    if (container) {
      const rect = container.getBoundingClientRect();
      console.log(`容器尺寸: ${rect.width}x${rect.height}`);
      console.log(`屏幕尺寸: ${size.width}x${size.height}`);
      
      if (rect.width < size.width * 0.95 || rect.height < size.height * 0.95) {
        console.warn('⚠️ 容器可能没有完全填满屏幕');
      } else {
        console.log('✅ 容器完全填满屏幕');
      }
    }
    
    // 检查表单元素是否可见
    const inputs = document.querySelectorAll('input');
    inputs.forEach((input, index) => {
      const rect = input.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) {
        console.error(`❌ 输入框 ${index + 1} 不可见`);
      } else {
        console.log(`✅ 输入框 ${index + 1} 正常显示 (${rect.width}x${rect.height})`);
      }
    });
    
    // 检查登录按钮
    const loginBtn = document.querySelector('.login-button');
    if (loginBtn) {
      const rect = loginBtn.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) {
        console.error('❌ 登录按钮不可见');
      } else {
        console.log(`✅ 登录按钮正常显示 (${rect.width}x${rect.height})`);
      }
    }
    
  } else if (currentPath === '/exam') {
    // 考试页面测试
    console.log('检查考试页面...');
    
    // 检查左右面板
    const leftPanel = document.querySelector('.left-panel');
    const rightPanel = document.querySelector('.right-panel');
    
    if (leftPanel && rightPanel) {
      const leftRect = leftPanel.getBoundingClientRect();
      const rightRect = rightPanel.getBoundingClientRect();
      
      console.log(`左侧面板: ${leftRect.width}x${leftRect.height}`);
      console.log(`右侧面板: ${rightRect.width}x${rightRect.height}`);
      
      // 检查面板比例
      const totalWidth = leftRect.width + rightRect.width;
      const leftRatio = leftRect.width / totalWidth;
      const rightRatio = rightRect.width / totalWidth;
      
      console.log(`面板比例: 左侧 ${(leftRatio * 100).toFixed(1)}%, 右侧 ${(rightRatio * 100).toFixed(1)}%`);
      
      if (rightRatio < 0.3) {
        console.warn('⚠️ 右侧面板可能过窄');
      }
    }
    
    // 检查表格是否完整显示
    const table = document.querySelector('.upload-table table');
    if (table) {
      const rect = table.getBoundingClientRect();
      console.log(`表格尺寸: ${rect.width}x${rect.height}`);
      
      // 检查表格列数
      const headers = table.querySelectorAll('th');
      console.log(`表格列数: ${headers.length}`);
      
      if (headers.length < 4) {
        console.warn('⚠️ 表格可能缺少列');
      } else {
        console.log('✅ 表格显示所有4列');
      }
      
      // 检查表格是否被截断
      const tableContainer = document.querySelector('.upload-table');
      if (tableContainer) {
        const containerRect = tableContainer.getBoundingClientRect();
        if (rect.width > containerRect.width) {
          console.warn('⚠️ 表格可能被截断，需要水平滚动');
        } else {
          console.log('✅ 表格完整显示，无需滚动');
        }
      }
    }
    
    // 检查提交按钮
    const submitBtn = document.querySelector('.submit-btn');
    if (submitBtn) {
      const rect = submitBtn.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) {
        console.error('❌ 提交按钮不可见');
      } else {
        console.log(`✅ 提交按钮正常显示 (${rect.width}x${rect.height})`);
      }
    }
  }
  
  console.log('---');
}

// 开始测试
console.log('开始PC Web端响应式测试...');
testNextSize(); 