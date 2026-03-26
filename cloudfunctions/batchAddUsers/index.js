const cloud = require('wx-server-sdk')
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

// 云函数入口函数
exports.main = async (event, context) => {
  try {
    const { batchSize = 20, skipExisting = true } = event
    
    console.log('开始批量添加用户数据...')
    
    // 从事件参数中获取用户数据，而不是从文件读取
    const jsonData = event.users || [];
    
    if (jsonData.length === 0) {
      return {
        code: -1,
        message: '没有提供用户数据',
        error: '请通过事件参数传递用户数据'
      };
    }
    
    // 转换数据格式，添加缺失字段
    const users = jsonData.map(user => ({
      teacherId: user.teacherId,
      name: user.name,
      department: user.department,
      role: user.role || 0,  // 默认为普通用户
      openid: "",
      avatarUrl: "",
      lastLoginTime: 0
    }));
    
    // 设置一些管理员用户
    const adminUsers = ['SD24069', 'SD14052', 'SD19017'];
    users.forEach(user => {
      if (adminUsers.includes(user.teacherId)) {
        user.role = 1;  // 设置为管理员
      }
    });
    
    console.log(`准备处理 ${users.length} 个用户`)
    
    // 如果需要跳过已存在的用户，先查询现有数据
    let usersToAdd = users;
    if (skipExisting) {
      console.log('检查现有用户数据...');
      const existingUsers = await db.collection('user').get();
      const existingTeacherIds = existingUsers.data.map(user => user.teacherId);
      
      usersToAdd = users.filter(user => !existingTeacherIds.includes(user.teacherId));
      console.log(`跳过 ${users.length - usersToAdd.length} 个已存在的用户`);
    }
    
    if (usersToAdd.length === 0) {
      return {
        code: 0,
        message: '所有用户已存在，无需添加',
        data: {
          added: 0,
          total: users.length,
          skipped: users.length
        }
      };
    }
    
    console.log(`准备添加 ${usersToAdd.length} 个新用户`)
    
    // 分批添加用户，避免一次性添加太多
    let totalAdded = 0;
    
    for (let i = 0; i < usersToAdd.length; i += batchSize) {
      const batch = usersToAdd.slice(i, i + batchSize);
      console.log(`正在添加第 ${Math.floor(i/batchSize) + 1} 批，共 ${batch.length} 个用户`);
      
      const result = await db.collection('user').add({
        data: batch
      });
      
      totalAdded += batch.length;
      console.log(`第 ${Math.floor(i/batchSize) + 1} 批添加完成`);
    }
    
    console.log('批量添加完成')
    
    return {
      code: 0,
      message: '批量添加成功',
      data: {
        added: totalAdded,
        total: users.length,
        skipped: users.length - usersToAdd.length
      }
    }
    
  } catch (err) {
    console.error('批量添加用户失败:', err)
    return {
      code: -1,
      message: '批量添加失败',
      error: err.message
    }
  }
}