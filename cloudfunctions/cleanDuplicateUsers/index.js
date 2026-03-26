const cloud = require('wx-server-sdk')
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

// 云函数入口函数
exports.main = async (event, context) => {
  try {
    console.log('开始清理重复用户数据...')
    
    // 获取所有用户数据
    const allUsers = await db.collection('user').get()
    console.log(`当前共有 ${allUsers.data.length} 个用户`)
    
    // 按 teacherId 分组，找出重复的用户
    const userMap = new Map()
    const duplicates = []
    
    allUsers.data.forEach(user => {
      const teacherId = user.teacherId
      if (userMap.has(teacherId)) {
        // 发现重复，保留第一个，删除其他的
        duplicates.push(user._id)
      } else {
        userMap.set(teacherId, user._id)
      }
    })
    
    console.log(`发现 ${duplicates.length} 个重复用户`)
    
    if (duplicates.length > 0) {
      // 批量删除重复用户
      const deletePromises = duplicates.map(id => 
        db.collection('user').doc(id).remove()
      )
      
      await Promise.all(deletePromises)
      console.log('重复用户清理完成')
    }
    
    // 再次查询确认
    const finalUsers = await db.collection('user').get()
    
    return {
      code: 0,
      message: '清理完成',
      data: {
        originalCount: allUsers.data.length,
        duplicatesRemoved: duplicates.length,
        finalCount: finalUsers.data.length
      }
    }
    
  } catch (err) {
    console.error('清理重复用户失败:', err)
    return {
      code: -1,
      message: '清理失败',
      error: err.message
    }
  }
}
