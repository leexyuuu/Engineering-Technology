const cloud = require('wx-server-sdk')
cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database()

exports.main = async (event, context) => {
  const { teacherId, updateData } = event;  // 改用 updateData 对象接收要更新的字段

  try {
    // 更新数据库中的用户信息
    const result = await db.collection('user')
      .where({
        teacherId: teacherId
      })
      .update({
        data: updateData  // 直接使用传入的更新数据
      });

    if (result.stats.updated > 0) {
      return {
        code: 0,
        message: '更新成功'
      };
    } else {
      return {
        code: 1,
        message: '未找到用户'
      };
    }
  } catch (err) {
    console.error('更新用户信息失败：', err);
    return {
      code: -1,
      message: '系统错误'
    };
  }
} 