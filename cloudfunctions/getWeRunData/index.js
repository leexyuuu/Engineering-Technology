// 云函数入口文件
const cloud = require('wx-server-sdk')

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

// 云函数入口函数
exports.main = async (event, context) => {
  try {
    // 获取微信运动数据
    const wxContext = cloud.getWXContext()
    
    // 检查 weRunData 是否存在
    if (!event.weRunData) {
      return {
        success: false,
        error: '缺少 weRunData 参数'
      }
    }
    
    // 检查数据结构
    if (typeof event.weRunData !== 'object' || !event.weRunData.data) {
      return {
        success: false,
        error: 'weRunData 数据结构不正确'
      }
    }
    
    if (!event.weRunData.data.stepInfoList) {
      return {
        success: false,
        error: 'stepInfoList 不存在'
      }
    }
    
    // 返回解密后的数据
    return {
      success: true,
      weRunData: event.weRunData
    }
  } catch (err) {
    console.error(err)
    return {
      success: false,
      error: err.message || '处理失败'
    }
  }
} 