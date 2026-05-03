# AI阅卷功能部署指南

## 前置条件

- 阿里云服务器已部署 mock-exam 项目（宝塔面板 + PM2 + Nginx）
- 已有通义千问 API Key（获取方式见下方）

## 获取通义千问 API Key

1. 打开 https://bailian.console.aliyun.com/
2. 用阿里云账号登录
3. 左侧菜单 → "API-KEY管理" → "创建API-KEY"
4. 复制生成的 Key（格式：`sk-xxxxxxxxxxxxxxxx`）

## 部署步骤

### 1. 本地提交代码并推送

```bash
git add .
git commit --no-verify -m "feat: 添加AI阅卷功能"
git push origin master
```

### 2. SSH到服务器，执行部署脚本

```bash
ssh root@你的服务器IP
cd /www/wwwroot/mock-exam
./deploy.sh all
```

部署脚本会自动完成：
- 拉取最新代码
- 构建学生前端和管理后台
- 安装 Python 新依赖（httpx、beautifulsoup4）
- 重启后端服务

### 3. 配置 LLM 环境变量

```bash
# 写入系统环境变量（永久生效，重启不丢失）
echo 'LLM_PROVIDER=qwen' >> /etc/environment
echo 'LLM_API_KEY=sk-你的通义千问key' >> /etc/environment

# 让当前shell读到环境变量
source /etc/environment

# 重启PM2并传入环境变量
pm2 restart mock-exam-api --update-env
```

### 4. 验证部署

```bash
# 检查PM2进程状态
pm2 list

# 检查后端日志是否正常
pm2 logs mock-exam-api --lines 20

# 测试API是否可访问
curl http://127.0.0.1:8000/
```

## 使用流程

### 配置评分细则

1. 登录管理后台 → 考试管理 → 选择考试 → 题目列表
2. 编辑题目 → 拉到下方"评分细则"区域
3. 选择题型（代码题/文字论述题/混合题/文件题）
4. 点击"添加评分项"，逐项填写：
   - 编号：M1、M2、M3...
   - 评分描述：对应PDF评分表中的描述
   - 配分：该项的分值
   - 类型：代码/文字/文件
   - 标准答案：标准代码片段或期望的输出数据
   - 关键词：逗号分隔，用于代码关键词匹配
5. 点击"保存评分细则"

### 触发AI阅卷

1. 管理后台 → 考试管理 → 选择考试 → 考试学生列表
2. 单个阅卷：点击某学生行的"AI阅卷"按钮
3. 批量阅卷：点击顶部"批量AI阅卷"按钮
4. 阅卷在后台异步执行，刷新页面查看进度和结果

### 人工复核

1. 阅卷完成后，阅卷状态变为"待复核"
2. 点击"评分详情"进入复核页面
3. 查看每个评分项的AI得分、置信度、评分理由
4. 低置信度项（黄色标记）重点复核
5. 修改分数后点击"提交复核"
6. 全部复核完成后点击"确认最终成绩"

## 环境变量说明

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| LLM_PROVIDER | 否 | qwen | LLM提供商：qwen / deepseek / openai |
| LLM_API_KEY | 是 | - | LLM API密钥 |
| LLM_MODEL | 否 | qwen-max | 文字/代码评分模型 |
| VISION_PROVIDER | 否 | 跟随LLM_PROVIDER | 图片分析提供商 |
| VISION_API_KEY | 否 | 跟随LLM_API_KEY | 图片分析API密钥 |
| VISION_MODEL | 否 | qwen-vl-max | 图片分析模型 |

通义千问用户只需设置 `LLM_PROVIDER=qwen` 和 `LLM_API_KEY` 即可，其余会自动使用默认值。

## 切换模型提供商

如需切换到 DeepSeek：

```bash
# 修改 /etc/environment 中的值
sed -i 's/LLM_PROVIDER=qwen/LLM_PROVIDER=deepseek/' /etc/environment
sed -i 's/LLM_API_KEY=.*/LLM_API_KEY=sk-你的deepseek_key/' /etc/environment
source /etc/environment
pm2 restart mock-exam-api --update-env
```

## 故障排查

### 查看阅卷日志

```bash
pm2 logs mock-exam-api --lines 50
```

正常日志示例：
```
[阅卷] 开始阅卷 student_exam_id=5
[代码提取] 从 HTML 提取到 1639 字符代码, 56 字符输出
[LLM] 调用 qwen/qwen-max ...
[LLM] 完成 | tokens: 输入856 输出234
[阅卷] 题目1 AI得分: 20/25
[阅卷] 阅卷完成! AI总分: 38
```

### 常见错误

| 错误信息 | 原因 | 解决方法 |
|---------|------|---------|
| LLM_API_KEY environment variable is not set | 环境变量未设置 | 执行 `source /etc/environment` 后重启PM2 |
| 402 Payment Required | DeepSeek账户余额不足 | 登录DeepSeek充值 |
| 400 Arrearage | 阿里云账户欠费 | 登录阿里云充值 |
| 401 Unauthorized | API Key无效 | 检查Key是否正确，重新创建 |

## 成本参考

使用通义千问 qwen-max：
- 单份卷子约9次LLM调用，约 ¥0.09
- 100份卷子约 ¥9
- 含图片分析（qwen-vl-max）成本略高
