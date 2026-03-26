const cloud = require('wx-server-sdk')
cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database()
const _ = db.command

// 云函数入口函数
exports.main = async (event, context) => {
  const { action, data } = event

  try {
    switch (action) {
      case 'add': // 添加步数记录
        return await addStepRecord(data)
      case 'batchAdd': // 批量添加步数记录
        return await batchAddStepRecords(data)
      case 'get': // 获取步数记录
        return await getStepRecord(data)
      case 'update': // 更新步数记录
        return await updateStepRecord(data)
      default:
        return {
          code: -1,
          message: '未知的操作类型'
        }
    }
  } catch (err) {
    console.error('步数记录操作失败：', err)
    return {
      code: -1,
      message: '操作失败',
      error: err
    }
  }
}

// 添加步数记录
async function addStepRecord(data) {
  const { teacherId, steps, date } = data
  
  // 检查是否已存在当天的记录
  const existingRecord = await db.collection('step_records')
    .where({
      teacherId: teacherId,
      date: date
    })
    .get()

  if (existingRecord.data.length > 0) {
    const record = existingRecord.data[0];
    if (record.steps === steps) {
      return {
        code: 0,
        message: '步数未变化，无需更新'
      }
    }
    // 已存在则更新
    const recordId = record._id
    const result = await db.collection('step_records')
      .doc(recordId)
      .update({
        data: {
          steps, // 更新为最新步数
          updateTime: db.serverDate()
        }
      })
    return {
      code: 0,
      data: result,
      message: '步数已更新'
    }
  }

  // 获取用户信息（包含学院信息）
  const userInfo = await db.collection('user')
    .where({
      teacherId: teacherId
    })
    .field({
      department: true
    })
    .get()

  if (!userInfo.data || userInfo.data.length === 0) {
    return {
      code: -1,
      message: '未找到用户信息'
    }
  }

  const department = userInfo.data[0].department

  // 添加新记录
  const result = await db.collection('step_records').add({
    data: {
      teacherId,      // 教师工号
      steps,          // 步数
      date,           // 日期（格式：YYYY-MM-DD）
      department,     // 教师所在学院
      createTime: db.serverDate(), // 记录创建时间
      updateTime: db.serverDate(), // 记录更新时间
      status: 'active', // 记录状态：active-有效，inactive-无效
      source: 'wechat', // 数据来源：wechat-微信运动，manual-手动录入
      remark: ''       // 备注信息
    }
  })

  return {
    code: 0,
    data: result,
    message: '添加成功'
  }
}

// 获取步数记录
async function getStepRecord(data) {
  const { teacherId, startDate, endDate, department } = data

  const query = {
    status: 'active'
  }

  // 添加查询条件
  if (teacherId) {
    query.teacherId = teacherId
  }
  if (department) {
    query.department = department
  }
  if (startDate && endDate) {
    query.date = _.gte(startDate).and(_.lte(endDate))
  }

  const result = await db.collection('step_records')
    .where(query)
    .orderBy('date', 'asc')
    .get()

  return {
    code: 0,
    data: result.data,
    message: '获取成功'
  }
}

// 更新步数记录
async function updateStepRecord(data) {
  const { _id, steps, remark } = data

  const updateData = {
    steps,
    updateTime: db.serverDate()
  }

  if (remark !== undefined) {
    updateData.remark = remark
  }

  const result = await db.collection('step_records')
    .doc(_id)
    .update({
      data: updateData
    })

  return {
    code: 0,
    data: result,
    message: '更新成功'
  }
}

// 获取用户最新的步数记录日期
async function getLatestStepDate(teacherId) {
  try {
    const result = await db.collection('step_records')
      .where({
        teacherId: teacherId,
        status: 'active'
      })
      .orderBy('date', 'desc')
      .limit(1)
      .get()
    
    return result.data.length > 0 ? result.data[0].date : '1970-01-01'
  } catch (err) {
    console.error('获取最新日期失败：', err)
    return '1970-01-01'
  }
}

// 时间戳转日期格式（使用中国时区 UTC+8，与前端保持一致）
function formatDate(timestamp) {
  const date = new Date(timestamp * 1000)
  // 使用 toLocaleString 转换为中国时区，然后提取日期
  const chinaDateStr = date.toLocaleString('zh-CN', { 
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
  // chinaDateStr 格式为 "2025/11/28"，转换为 "2025-11-28"
  return chinaDateStr.replace(/\//g, '-')
}

// 批量添加步数记录（增量同步 + 更新已存在记录）
async function batchAddStepRecords(data) {
  const { teacherId, stepInfoList } = data
  
  if (!stepInfoList || stepInfoList.length === 0) {
    return {
      code: -1,
      message: '步数数据为空'
    }
  }

  try {
    // 获取用户信息（包含学院信息）
    const userInfo = await db.collection('user')
      .where({
        teacherId: teacherId
      })
      .field({
        department: true
      })
      .get()

    if (!userInfo.data || userInfo.data.length === 0) {
      return {
        code: -1,
        message: '未找到用户信息'
      }
    }

    const department = userInfo.data[0].department

    // 1. 提取所有日期（过滤步数为0的数据）
    const validStepData = stepInfoList.filter(stepInfo => stepInfo.step > 0)
    if (validStepData.length === 0) {
      return {
        code: 0,
        message: '没有有效数据需要同步',
        data: { syncedCount: 0, updatedCount: 0 }
      }
    }

    const dates = validStepData.map(stepInfo => formatDate(stepInfo.timestamp))
    console.log(`用户 ${teacherId} 需要处理 ${dates.length} 条数据`)

    // 2. 批量查询已存在的记录（分批查询，因为 in 操作可能有限制）
    const existingRecords = []
    const inQueryBatchSize = 20 // 微信云数据库 in 查询建议不超过20个值
    
    for (let i = 0; i < dates.length; i += inQueryBatchSize) {
      const dateBatch = dates.slice(i, i + inQueryBatchSize)
      const result = await db.collection('step_records')
        .where({
          teacherId: teacherId,
          date: _.in(dateBatch)
        })
        .get()
      existingRecords.push(...result.data)
    }

    // 3. 在内存中构建映射表（date -> record）
    const existingMap = new Map()
    existingRecords.forEach(record => {
      existingMap.set(record.date, record)
    })

    // 4. 分类处理：需要更新的 vs 需要插入的
    const toUpdate = []
    const toInsert = []

    for (const stepInfo of validStepData) {
      const date = formatDate(stepInfo.timestamp)
      const existing = existingMap.get(date)
      
      if (existing) {
        // 已存在记录，检查步数是否变化
        if (existing.steps !== stepInfo.step) {
          toUpdate.push({
            _id: existing._id,
            steps: stepInfo.step
          })
        }
        // 如果步数相同，跳过（无需更新）
      } else {
        // 不存在记录，需要插入
        toInsert.push({
          teacherId: teacherId,
          steps: stepInfo.step,
          date: date,
          department: department,
          createTime: db.serverDate(),
          updateTime: db.serverDate(),
          status: 'active',
          source: 'wechat',
          remark: ''
        })
      }
    }

    console.log(`需要更新 ${toUpdate.length} 条，需要插入 ${toInsert.length} 条`)

    // 5. 批量更新（使用 Promise.all 并发更新）
    let updatedCount = 0
    if (toUpdate.length > 0) {
      const updatePromises = toUpdate.map(item =>
        db.collection('step_records')
          .doc(item._id)
          .update({
            data: {
              steps: item.steps,
              updateTime: db.serverDate()
            }
          })
      )
      await Promise.all(updatePromises)
      updatedCount = toUpdate.length
    }

    // 6. 批量插入（分批插入，每批最多20条）
    let insertedCount = 0
    if (toInsert.length > 0) {
      const insertBatchSize = 20
      for (let i = 0; i < toInsert.length; i += insertBatchSize) {
        const currentBatch = toInsert.slice(i, i + insertBatchSize)
        await db.collection('step_records').add({
          data: currentBatch
        })
        insertedCount += currentBatch.length
      }
    }

    const totalSyncedCount = updatedCount + insertedCount

    return {
      code: 0,
      message: totalSyncedCount > 0 
        ? `成功同步 ${totalSyncedCount} 条数据（更新 ${updatedCount} 条，新增 ${insertedCount} 条）`
        : '数据已是最新，无需同步',
      data: { 
        syncedCount: totalSyncedCount,
        updatedCount: updatedCount,
        insertedCount: insertedCount,
        totalData: stepInfoList.length,
        validData: validStepData.length
      }
    }

  } catch (err) {
    console.error('批量添加步数记录失败：', err)
    return {
      code: -1,
      message: '批量同步失败',
      error: err
    }
  }
} 