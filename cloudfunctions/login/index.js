const cloud = require('wx-server-sdk')
cloud.init({
    env: cloud.DYNAMIC_CURRENT_ENV
  })

const db = cloud.database()

// 云函数入口函数
exports.main = async (event, context) => {
  
  try {
    const wxContext = cloud.getWXContext()
    const { name, employeeId } = event

    // 去除首尾空格，防止输入时意外输入空格
    const employeeIdTrimmed = employeeId ? employeeId.trim() : ''
    const nameTrimmed = name ? name.trim() : ''
    
    // 查询条件：先按姓名查询（因为工号匹配需要忽略大小写）
    const queryCondition = {
      name: nameTrimmed
    };

    try {
      // 先按姓名查询所有匹配的用户
      const userResult = await db.collection('user')
        .where(queryCondition)
        .get()

      // 在结果中查找工号匹配的用户（忽略大小写）
      let matchedUser = null
      if (userResult.data && userResult.data.length > 0) {
        // 遍历查找工号匹配的用户（大小写不敏感）
        matchedUser = userResult.data.find(user => {
          const dbTeacherId = user.teacherId ? String(user.teacherId).trim() : ''
          const inputTeacherId = employeeIdTrimmed
          // 将两者都转为小写进行比较（或者都转为大写也可以）
          return dbTeacherId.toLowerCase() === inputTeacherId.toLowerCase()
        })
      }

      // 检查是否找到用户
      if (matchedUser) {
        const user = matchedUser

        // 将 openid 更新到用户记录中
        await db.collection('user').doc(user._id).update({
          data: {
            openid: wxContext.OPENID,
            lastLoginTime: Date.now()
          }
        })
        
        return {
          code: 0,
          openid: wxContext.OPENID,
          name: user.name,
          teacherId: user.teacherId,
          avatarUrl: user.avatarUrl,
          department: user.department || '', // 返回部门信息
          role: user.role || 0, // 默认普通用户
          message: '登录成功'
        };
      } else {
        return {
          code: 1,
          message: '姓名与工号不匹配，请检查输入信息',
          data: null
        }
      }
    } catch (dbError) {
      console.error('数据库查询错误：', dbError);
      throw dbError;
    }
  } catch (err) {
    console.error('云函数执行错误：', err);
    return {
      code: -1,
      message: '系统错误',
      data: null
    }
  }
}