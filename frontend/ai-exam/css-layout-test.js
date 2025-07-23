// CSS布局问题测试脚本
// 专门测试CSS布局相关的白色区域遮挡问题

const testLayoutIssues = () => {
  console.log('🔍 开始CSS布局问题检测...');
  
  // 1. 检查容器是否完全填充视口
  checkContainerFill();
  
  // 2. 检查是否有内容溢出
  checkContentOverflow();
  
  // 3. 检查CSS属性设置
  checkCSSProperties();
  
  // 4. 检查布局算法问题
  checkLayoutAlgorithm();
};

function checkContainerFill() {
  console.log('\n📏 检查容器填充情况:');
  
  const containers = [
    { selector: '.login-container', name: '登录容器' },
    { selector: '.exam-container', name: '考试容器' },
    { selector: '.left-panel', name: '左侧面板' },
    { selector: '.right-panel', name: '右侧面板' }
  ];
  
  containers.forEach(container => {
    const element = document.querySelector(container.selector);
    if (element) {
      const rect = element.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      
      console.log(`${container.name}:`);
      console.log(`  尺寸: ${rect.width}x${rect.height}`);
      console.log(`  视口: ${viewportWidth}x${viewportHeight}`);
      console.log(`  填充率: ${(rect.width/viewportWidth*100).toFixed(1)}% x ${(rect.height/viewportHeight*100).toFixed(1)}%`);
      
      if (rect.width < viewportWidth * 0.95 || rect.height < viewportHeight * 0.95) {
        console.warn(`  ⚠️ ${container.name}可能没有完全填充视口`);
      }
    }
  });
}

function checkContentOverflow() {
  console.log('\n📦 检查内容溢出情况:');
  
  const elements = [
    { selector: '.upload-table', name: '上传表格' },
    { selector: '.login-form', name: '登录表单' },
    { selector: '.question-content', name: '题目内容' }
  ];
  
  elements.forEach(element => {
    const el = document.querySelector(element.selector);
    if (el) {
      const rect = el.getBoundingClientRect();
      const parent = el.parentElement;
      const parentRect = parent.getBoundingClientRect();
      
      console.log(`${element.name}:`);
      console.log(`  元素尺寸: ${rect.width}x${rect.height}`);
      console.log(`  父容器尺寸: ${parentRect.width}x${parentRect.height}`);
      
      if (rect.width > parentRect.width || rect.height > parentRect.height) {
        console.warn(`  ⚠️ ${element.name}可能溢出父容器`);
      }
      
      // 检查CSS overflow属性
      const computedStyle = window.getComputedStyle(el);
      console.log(`  overflow: ${computedStyle.overflow}`);
    }
  });
}

function checkCSSProperties() {
  console.log('\n🎨 检查关键CSS属性:');
  
  const containers = [
    { selector: '.login-container', name: '登录容器' },
    { selector: '.exam-container', name: '考试容器' }
  ];
  
  containers.forEach(container => {
    const element = document.querySelector(container.selector);
    if (element) {
      const style = window.getComputedStyle(element);
      
      console.log(`${container.name} CSS属性:`);
      console.log(`  position: ${style.position}`);
      console.log(`  display: ${style.display}`);
      console.log(`  width: ${style.width}`);
      console.log(`  height: ${style.height}`);
      console.log(`  margin: ${style.margin}`);
      console.log(`  padding: ${style.padding}`);
      console.log(`  overflow: ${style.overflow}`);
      
      // 检查是否有问题
      if (style.position !== 'absolute') {
        console.warn(`  ⚠️ ${container.name}不是绝对定位，可能导致布局问题`);
      }
      
      if (style.margin !== '0px') {
        console.warn(`  ⚠️ ${container.name}有margin，可能影响布局`);
      }
    }
  });
}

function checkLayoutAlgorithm() {
  console.log('\n🧮 检查布局算法:');
  
  // 检查Grid布局
  const gridContainers = document.querySelectorAll('[style*="grid"], [style*="Grid"]');
  console.log(`Grid布局容器数量: ${gridContainers.length}`);
  
  // 检查Flexbox布局
  const flexContainers = document.querySelectorAll('[style*="flex"], [style*="Flex"]');
  console.log(`Flexbox布局容器数量: ${flexContainers.length}`);
  
  // 检查表格布局
  const tables = document.querySelectorAll('table');
  tables.forEach((table, index) => {
    const style = window.getComputedStyle(table);
    console.log(`表格${index + 1} table-layout: ${style.tableLayout}`);
    
    if (style.tableLayout === 'fixed') {
      console.log(`  使用固定表格布局`);
    }
  });
}

// 检测白色区域遮挡
function detectWhiteArea() {
  console.log('\n⚪ 检测白色区域遮挡:');
  
  // 检查body和html的背景色
  const bodyStyle = window.getComputedStyle(document.body);
  const htmlStyle = window.getComputedStyle(document.documentElement);
  
  console.log(`body背景色: ${bodyStyle.backgroundColor}`);
  console.log(`html背景色: ${htmlStyle.backgroundColor}`);
  
  // 检查#app的背景色
  const appStyle = window.getComputedStyle(document.getElementById('app'));
  console.log(`#app背景色: ${appStyle.backgroundColor}`);
  
  // 如果背景色是白色，可能是遮挡问题的原因
  if (appStyle.backgroundColor.includes('rgb(255, 255, 255)') || 
      appStyle.backgroundColor.includes('white')) {
    console.warn('⚠️ #app有白色背景，可能是白色区域遮挡的原因');
  }
}

// 运行所有检测
testLayoutIssues();
detectWhiteArea();

console.log('\n✅ CSS布局问题检测完成！'); 