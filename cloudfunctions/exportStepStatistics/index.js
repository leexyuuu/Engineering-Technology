const cloud = require('wx-server-sdk')
const ExcelJS = require('exceljs')
const nodemailer = require('nodemailer')
const departmentMapping = require('./department_mapping.json')
const jiashanCampusTeachers = require('./jiashan_campus_teachers.json')
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()
const _ = db.command

// 云函数入口函数
exports.main = async (event, context) => {
  try {
    let { year, month, source } = event
    
    // 如果是定时触发器触发，自动计算上个月
    if (event.source === 'timer' || (!year && !month)) {
      const now = new Date()
      const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      year = lastMonth.getFullYear()
      month = lastMonth.getMonth() + 1
      console.log(`定时触发器执行，自动生成${year}年${month}月报表`)
    }
    
    // 如果是管理员调用，验证权限
    if (source === 'admin') {
      const wxContext = cloud.getWXContext()
      const userResult = await db.collection('user')
        .where({
          openid: wxContext.OPENID
        })
        .get()
      
      if (userResult.data.length === 0 || userResult.data[0].role !== 1) {
        return {
          code: -1,
          message: '权限不足，只有管理员可以导出数据'
        }
      }
      console.log(`管理员${userResult.data[0].name}导出${year}年${month}月数据`)
    }
    
    const monthStr = `${year}-${String(month).padStart(2, '0')}`; // 例如 '2025-11'
    const startDateStr = `${monthStr}-01`;
    
    // 2. 生成该月的所有日期（先计算天数，再确定结束日期）
    const daysInMonth = new Date(year, month, 0).getDate()
    const endDateStr = `${monthStr}-${String(daysInMonth).padStart(2, '0')}`;
    
    console.log(`[导出日志] 导出月份: ${year}年${month}月，查询日期范围: ${startDateStr} 到 ${endDateStr}`)

    // 1. 查询步数记录（用字符串范围，分批查询）
    const MAX_LIMIT = 100
    const stepRecordsCountResult = await db.collection('step_records')
      .where({
        date: _.gte(startDateStr).and(_.lte(endDateStr))
      })
      .count()
    const totalStepRecords = stepRecordsCountResult.total
    
    const stepRecords = { data: [] }
    const stepRecordsBatchTimes = Math.ceil(totalStepRecords / MAX_LIMIT)
    
    for (let i = 0; i < stepRecordsBatchTimes; i++) {
      const stepRecordsBatch = await db.collection('step_records')
        .where({
          date: _.gte(startDateStr).and(_.lte(endDateStr))
        })
        .skip(i * MAX_LIMIT)
        .limit(MAX_LIMIT)
        .get()
      stepRecords.data.push(...stepRecordsBatch.data)
    }

    console.log(`[导出日志] 查询到 ${stepRecords.data.length} 条步数记录`)

    // 生成该月的所有日期列
    const dateColumns = []
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${monthStr}-${String(day).padStart(2, '0')}`
      dateColumns.push(dateStr)
    }

    // 3. 获取所有用户信息（分批查询，因为微信云数据库默认最多返回100条）
    const userCountResult = await db.collection('user').count()
    const totalUsers = userCountResult.total
    
    const allUsers = []
    const batchTimes = Math.ceil(totalUsers / MAX_LIMIT)
    
    for (let i = 0; i < batchTimes; i++) {
      const userBatch = await db.collection('user')
        .field({
          name: true,
          teacherId: true,
          department: true
        })
        .skip(i * MAX_LIMIT)
        .limit(MAX_LIMIT)
        .get()
      allUsers.push(...userBatch.data)
    }
    
    // 对用户列表进行排序：先按部门排序，再按姓名排序
    allUsers.sort((a, b) => {
      // 先按部门排序
      const deptA = a.department || ''
      const deptB = b.department || ''
      if (deptA !== deptB) {
        return deptA.localeCompare(deptB, 'zh-CN')
      }
      // 部门相同，按姓名排序
      const nameA = a.name || ''
      const nameB = b.name || ''
      return nameA.localeCompare(nameB, 'zh-CN')
    })
    
    console.log(`[导出日志] 查询到 ${allUsers.length} 个用户，已按部门和姓名排序`)

    // 4. 构建用户每日步数数据
    const userDailySteps = {}
    stepRecords.data.forEach(record => {
      if (!userDailySteps[record.teacherId]) {
        userDailySteps[record.teacherId] = {}
      }
      userDailySteps[record.teacherId][record.date] = record.steps
    })

    // 5. 生成导出数据
    const exportData = allUsers.map((user, userIndex) => {
      const userData = {
        department: user.department,
        name: user.name,
        teacherId: user.teacherId
      }
      
      // 添加每日步数数据
      let totalSteps = 0
      let qualifiedDays = 0
      
      dateColumns.forEach(date => {
        const steps = userDailySteps[user.teacherId]?.[date] || 0
        userData[`day_${date}`] = steps
        totalSteps += steps
        // 单日步数 >= 7000步算达标一天
        if (steps >= 7000) {
          qualifiedDays++
        }
      })
      
      // 添加统计信息
      userData.totalSteps = totalSteps
      userData.qualifiedDays = qualifiedDays
      // 一个月内达标天数 >= 22天，则判定为"是否达标"为"是"
      userData.isQualified = qualifiedDays >= 22 ? '是' : '否'
      
      return userData
    })

    const usersWithSteps = exportData.filter(user => user.totalSteps > 0).length
    console.log(`[导出日志] 生成导出数据: 总用户数 ${exportData.length}，有步数数据用户数 ${usersWithSteps}`)

    // 6. 按sheet分组用户数据
    // 6.1 提取嘉善校区ID列表
    const jiashanIds = new Set(jiashanCampusTeachers.jiashan_campus_teacher_ids || [])
    
    // 6.1.1 标准化部门名称：去除空格、统一括号类型
    function normalizeDepartment(dept) {
      if (!dept) return ''
      return dept
        .trim()
        .replace(/\s+/g, '') // 去除所有空格
        .replace(/[\(（]/g, '（') // 统一为中文左括号
        .replace(/[\)）]/g, '）') // 统一为中文右括号
    }
    
    // 6.2 构建部门到sheet名称的映射（一个部门可能对应多个sheet）
    // 使用标准化后的部门名称作为key
    const deptToSheets = {}
    Object.keys(departmentMapping).forEach(sheetName => {
      departmentMapping[sheetName].forEach(dept => {
        const normalizedDept = normalizeDepartment(dept)
        if (!deptToSheets[normalizedDept]) {
          deptToSheets[normalizedDept] = []
        }
        deptToSheets[normalizedDept].push(sheetName)
      })
    })
    
    // 6.3 按sheet分组用户数据
    const sheetDataMap = {}
    // 初始化所有sheet（包括"其他"）
    Object.keys(departmentMapping).forEach(sheetName => {
      sheetDataMap[sheetName] = []
    })
    sheetDataMap['其他'] = []
    
    // 遍历所有用户数据，分配到对应的sheet
    exportData.forEach(user => {
      // 优先级1：检查是否在嘉善校区ID列表中
      if (jiashanIds.has(user.teacherId)) {
        if (sheetDataMap['嘉善校区']) {
          sheetDataMap['嘉善校区'].push(user)
        } else {
          sheetDataMap['其他'].push(user)
        }
        return // 不再进行部门匹配
      }
      
      // 优先级2：按部门匹配（排除"嘉善校区"，因为"嘉善校区"只能通过ID匹配）
      // 使用标准化后的部门名称进行匹配
      const normalizedUserDept = normalizeDepartment(user.department)
      const matchedSheets = deptToSheets[normalizedUserDept] || []
      if (matchedSheets.length > 0) {
        // 如果匹配多个sheet，都添加进去（数据重复）
        // 但排除"嘉善校区"，因为"嘉善校区"只能通过ID匹配添加
        matchedSheets.forEach(sheetName => {
          if (sheetName !== '嘉善校区') {
            sheetDataMap[sheetName].push(user)
          }
        })
        
        // 如果匹配的sheet都被排除了（只匹配到"嘉善校区"），放入"其他"
        const validMatchedSheets = matchedSheets.filter(sheetName => sheetName !== '嘉善校区')
        if (validMatchedSheets.length === 0) {
          sheetDataMap['其他'].push(user)
        }
      } else {
        // 没有匹配到任何sheet，放入"其他"
        sheetDataMap['其他'].push(user)
      }
    })
    
    console.log('sheetDataMap统计:', Object.keys(sheetDataMap).map(sheetName => ({
      sheetName,
      count: sheetDataMap[sheetName].length
    })))

    // 7. 生成Excel - 为每个sheet创建工作表
    const workbook = new ExcelJS.Workbook()
    
    // 构建表头（所有sheet共用）
    const headers = ['学院', '姓名', '工号']
    
    // 添加每日日期列
    dateColumns.forEach(date => {
      const day = date.split('-')[2]
      headers.push(`${day}日`)
    })
    
    // 添加统计列
    headers.push('总步数', '达标天数', '是否达标')
    
    // 设置列宽（所有sheet共用）
    const columnWidths = [
      { header: '学院', width: 20 },
      { header: '姓名', width: 15 },
      { header: '工号', width: 15 }
    ]
    
    // 添加每日列宽
    dateColumns.forEach(() => {
      columnWidths.push({ width: 8 })
    })
    
    // 添加统计列宽
    columnWidths.push(
      { header: '总步数', width: 15 },
      { header: '达标天数', width: 15 },
      { header: '是否达标', width: 15 }
    )
    
    // 为每个sheet创建工作表（确保"机关"sheet是第一个）
    // 定义sheet的显示顺序：先"机关"，然后其他sheet（按字母顺序），最后"其他"
    const allSheetNames = Object.keys(sheetDataMap)
    const sortedSheetNames = []
    
    // 1. 先添加"机关"sheet（如果存在）
    if (sheetDataMap['机关']) {
      sortedSheetNames.push('机关')
    }
    
    // 2. 添加其他sheet（排除"机关"和"其他"），按字母顺序排序
    const otherSheets = allSheetNames
      .filter(name => name !== '机关' && name !== '其他')
      .sort((a, b) => a.localeCompare(b, 'zh-CN'))
    sortedSheetNames.push(...otherSheets)
    
    // 3. 最后添加"其他"sheet（如果存在）
    if (sheetDataMap['其他']) {
      sortedSheetNames.push('其他')
    }
    
    // 按照排序后的顺序创建sheet
    sortedSheetNames.forEach(sheetName => {
      const sheetData = sheetDataMap[sheetName]
      
      // 跳过空sheet（可选：如果不想生成空sheet，可以取消注释）
      // if (sheetData.length === 0) return
      
      const worksheet = workbook.addWorksheet(sheetName)
      worksheet.columns = columnWidths
      
      // 设置表头
      const headerRow = worksheet.getRow(1)
      headers.forEach((header, index) => {
        const cell = headerRow.getCell(index + 1)
        cell.value = header
      })
      
      // 设置表头样式
      headerRow.font = { bold: true, size: 12 }
      headerRow.alignment = { horizontal: 'center', vertical: 'middle' }
      headerRow.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'FFE6E6FA' }
      }
      
      // 添加数据行（从第二行开始）
      sheetData.forEach((user, index) => {
        const rowNumber = index + 2
        const row = worksheet.getRow(rowNumber)
        
        // 设置基础信息
        row.getCell(1).value = user.department
        row.getCell(2).value = user.name
        row.getCell(3).value = user.teacherId
        
        // 设置每日步数
        dateColumns.forEach((date, dateIndex) => {
          const cellIndex = dateIndex + 4 // 从第4列开始
          row.getCell(cellIndex).value = user[`day_${date}`] || 0
        })
        
        // 设置统计信息
        const statsStartIndex = dateColumns.length + 4
        row.getCell(statsStartIndex).value = user.totalSteps
        row.getCell(statsStartIndex + 1).value = user.qualifiedDays
        row.getCell(statsStartIndex + 2).value = user.isQualified
        
        // 设置行样式
        row.alignment = { horizontal: 'center', vertical: 'middle' }
        
        // 为达标用户设置绿色背景
        if (user.isQualified === '是') {
          row.fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: 'FFE6F7E6' }
          }
        }
      })
      
      // 添加边框
      worksheet.eachRow((row, rowNumber) => {
        row.eachCell((cell) => {
          cell.border = {
            top: { style: 'thin' },
            left: { style: 'thin' },
            bottom: { style: 'thin' },
            right: { style: 'thin' }
          }
        })
      })
    })
    
    const buffer = await workbook.xlsx.writeBuffer()

    // 8. 上传到云存储并返回下载链接
    const fileName = `步数统计报表_${year}年${month}月.xlsx`
    const cloudPath = `exports/${fileName}`
    
    // 上传文件到云存储
    const uploadResult = await cloud.uploadFile({
      cloudPath: cloudPath,
      fileContent: buffer
    })
    
    // 获取临时下载链接
    const tempFileURL = await cloud.getTempFileURL({
      fileList: [uploadResult.fileID]
    })
    
    // 统计每个sheet的达标人数
    const sheetStats = {}
    Object.keys(sheetDataMap).forEach(sheetName => {
      const sheetData = sheetDataMap[sheetName]
      sheetStats[sheetName] = {
        total: sheetData.length,
        qualified: sheetData.filter(user => user.isQualified === '是').length
      }
    })
    
    // 统计达标人数
    const totalQualifiedCount = exportData.filter(user => user.isQualified === '是').length

    return {
      code: 0,
      message: '导出成功',
      data: {
        year,
        month,
        totalCount: exportData.length, // 总人数
        qualifiedCount: totalQualifiedCount,
        sheetStats: sheetStats, // 每个sheet的统计信息
        filename: fileName,
        downloadUrl: tempFileURL.fileList[0].tempFileURL,
        fileID: uploadResult.fileID
      }
    }
  } catch (err) {
    console.error('导出步数统计失败：', err)
    return {
      code: -1,
      message: '导出失败',
      error: err
    }
  }
} 