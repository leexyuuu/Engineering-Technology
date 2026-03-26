const cloud = require('wx-server-sdk')
cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database()

exports.main = async (event, context) => {
  const { teacherId, avatarUrl } = event;

  try {
    // 更新数据库中的头像URL
    const result = await db.collection('user')
      .where({
        teacherId: teacherId
      })
      .update({
        data: {
          avatarUrl: avatarUrl
        }
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
    console.error('更新头像失败：', err);
    return {
      code: -1,
      message: '系统错误'
    };
  }
} 