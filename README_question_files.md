# 题目多文件答题和资料文件功能说明

## 功能概述

本次更新为题目编辑页面添加了以下新功能：

1. **多文件答题功能**：可以为题目设置多个需要上传的文件，每个文件都有独立的说明和要求
2. **资料文件功能**：可以为题目上传多个资料文件，供学生在考试时下载参考

## 数据库变更

### 新增字段

在 `questions` 表中新增了两个字段：

- `required_files` (TEXT): 存储多文件答题要求的JSON数据
- `material_files` (TEXT): 存储资料文件的JSON数据

### 字段结构

#### required_files 字段结构
```json
[
  {
    "name": "文件名称",
    "type": "pdf",
    "required": true,
    "description": "文件说明",
    "uuid": "唯一标识"
  }
]
```

#### material_files 字段结构
```json
[
  {
    "name": "文件名称",
    "type": "pdf",
    "description": "文件说明",
    "url": "文件URL",
    "originalName": "原始文件名",
    "uuid": "唯一标识"
  }
]
```

## 前端功能

### 多文件答题设置

1. 在题目编辑页面，当启用"需要上传文件答题"时，会显示"多文件答题设置"区域
2. 可以添加多个文件要求，每个文件要求包含：
   - 文件名称
   - 文件类型（PDF、Word、Excel、图片、其他）
   - 是否必填
   - 文件说明

### 资料文件设置

1. 在题目编辑页面新增"资料文件"区域
2. 可以添加多个资料文件，每个文件包含：
   - 文件名称
   - 文件类型
   - 文件上传功能
   - 文件说明

## 后端接口

### 新增接口

1. **文件上传接口**
   - URL: `POST /exam/upload-file`
   - 功能：上传文件到服务器
   - 返回：文件URL和元数据

2. **文件下载接口**
   - URL: `GET /uploads/{filename}`
   - 功能：下载上传的文件

### 更新接口

1. **创建题目接口**
   - 新增 `required_files` 和 `material_files` 参数

2. **更新题目接口**
   - 新增 `required_files` 和 `material_files` 参数

## 使用步骤

### 1. 数据库迁移

运行迁移脚本添加新字段：

```bash
cd fapi
python migration_add_question_files.py
```

### 2. 启动服务

启动后端服务：

```bash
cd fapi
python main.py
```

启动前端服务：

```bash
cd admin
npm run dev
```

### 3. 使用功能

1. 进入题目编辑页面
2. 启用"需要上传文件答题"
3. 在"多文件答题设置"中添加文件要求
4. 在"资料文件"中上传资料文件
5. 保存题目

## 注意事项

1. 文件上传大小限制：建议不超过10MB
2. 支持的文件类型：PDF、Word、Excel、图片等
3. 文件存储在 `fapi/uploads/` 目录下
4. 确保服务器有足够的存储空间

## 技术实现

### 前端技术栈
- Vue.js 2.x
- Element UI
- Axios

### 后端技术栈
- FastAPI
- SQLAlchemy
- SQLite/MySQL

### 文件存储
- 本地文件系统存储
- 支持文件类型验证
- 唯一文件名生成 