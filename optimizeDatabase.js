// 数据库索引优化脚本
// 这个脚本用于在云开发控制台中执行，为step_records表添加必要的索引

// 在云开发控制台的数据库管理页面中执行以下命令：

// 1. 为 teacherId 和 date 创建复合索引（用于查询最新日期）
db.step_records.createIndex({
  "teacherId": 1,
  "date": -1
}, {
  "name": "teacherId_date_desc",
  "background": true
})

// 2. 为 teacherId 创建单字段索引（用于查询用户所有记录）
db.step_records.createIndex({
  "teacherId": 1
}, {
  "name": "teacherId_asc",
  "background": true
})

// 3. 为 date 创建单字段索引（用于按日期范围查询）
db.step_records.createIndex({
  "date": 1
}, {
  "name": "date_asc",
  "background": true
})

// 4. 为 status 创建单字段索引（用于过滤有效记录）
db.step_records.createIndex({
  "status": 1
}, {
  "name": "status_asc",
  "background": true
})

// 5. 为 teacherId, status, date 创建复合索引（用于查询用户的有效记录）
db.step_records.createIndex({
  "teacherId": 1,
  "status": 1,
  "date": -1
}, {
  "name": "teacherId_status_date_desc",
  "background": true
})

console.log('数据库索引创建完成！')

// 查看所有索引
db.step_records.getIndexes()

// 删除索引的命令（如果需要）
// db.step_records.dropIndex("teacherId_date_desc")
