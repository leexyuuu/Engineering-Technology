const cloud = require('wx-server-sdk')
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

// 云函数入口函数
exports.main = async (event, context) => {
  try {
    const { action, teacherId, role } = event
    
    switch (action) {
      case 'setRole':
        // 设置指定用户的角色
        if (!teacherId || role === undefined) {
          return {
            code: -1,
            message: '参数不完整'
          }
        }
        
        const result = await db.collection('user')
          .where({
            teacherId: teacherId
          })
          .update({
            data: {
              role: role
            }
          })
        
        if (result.stats.updated > 0) {
          return {
            code: 0,
            message: '角色设置成功',
            data: {
              teacherId,
              role,
              updated: result.stats.updated
            }
          }
        } else {
          return {
            code: 1,
            message: '未找到指定用户'
          }
        }
        
      case 'getAllUsers':
        // 获取所有用户信息（用于管理）
        const users = await db.collection('user')
          .field({
            teacherId: true,
            name: true,
            department: true,
            role: true,
            lastLoginTime: true
          })
          .get()
        
        return {
          code: 0,
          message: '获取成功',
          data: users.data
        }
        
      case 'initAllUsers':
        // 为所有用户初始化role字段（默认值为0）
        const allUsers = await db.collection('user').get()
        let updatedCount = 0
        
        for (const user of allUsers.data) {
          if (user.role === undefined) {
            await db.collection('user').doc(user._id).update({
              data: {
                role: 0
              }
            })
            updatedCount++
          }
        }
        
        return {
          code: 0,
          message: '初始化完成',
          data: {
            totalUsers: allUsers.data.length,
            updatedCount: updatedCount
          }
        }
        
      default:
        return {
          code: -1,
          message: '未知操作'
        }
    }
  } catch (err) {
    console.error('操作失败：', err)
    return {
      code: -1,
      message: '操作失败',
      error: err
    }
  }
}
