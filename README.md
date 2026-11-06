# 知行职业学院 · 排课选课与教务协作智能体

面向学生、教师、教务管理员的选课问答与申请协作系统：**RAG 制度问答 + Agent 工具调用 + 选课申请确认门**（学生确认 → 教务审核，系统只读不代选）。

## 技术栈

- **Web**：FastAPI + Uvicorn + SSE 流式响应 + Jinja2 页面
- **数据**：SQLAlchemy 2.0（async）+ SQLite（aiosqlite，可平滑切换 PostgreSQL）
- **检索**：Markdown 按标题切界 + 500 字聚合切片 → FAISS（向量）+ BM25（jieba 分词）→ RRF 融合（k=60，top3）
- **安全**：PyJWT（HS256）三角色鉴权、PBKDF2 密码哈希、/api/chat 内存滑动窗口限流
- **LLM / Embedding 供应商可替换**：`mock`（离线开箱即跑） / `openai_compatible`（真实接口，.env 切换）

## 快速开始（Windows PowerShell）

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
# 可选：copy .env.example .env（默认 mock 供应商，离线可用）
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

首次启动自动完成：建表 → 种子用户 → 默认提示词模板 → `data/docs/教务管理制度.md` 入库 → 构建 FAISS 索引。

- 学生端聊天：http://127.0.0.1:8000 （登录页 `/login`）
- 管理端页面：`/admin/kb`（知识库）`/admin/prompt`（提示词）`/admin/audit`（审计）`/admin/applications`（选课申请审核）
- 演示账号：`student1` / `teacher1` / `admin1`，密码均为 `123456`

## 功能概览（按建设阶段）

1. **RAG 制度问答**：回答附引用来源与制度条款号；超范围问题明确回答"制度中未找到"，不编造。
2. **鉴权与教务管理**：JWT 三角色权限边界；知识库文档上传 / 删除后索引热生效；系统提示词模板在线修改即时生效；对话审计（角色 / 关键词 / 日期 / 违规标记筛选）；接口限流 20 次/分钟/IP。
3. **Agent 执行循环**：5 个工具（课表查询、选课规则检索、课程要求查询、资格校验、创建选课申请），≤5 轮决策循环 + 决策日志落库；确认门双层防护——提示词层工具顺序约束 + 代码层硬约束（未经 `validate_eligibility` 通过的课程一律拒绝建申请）；申请单状态机 draft → student_confirmed → admin_confirmed → executed / rejected。
4. **评测体系**：30 条用例覆盖制度问答（含陷阱）、工具调用轨迹、违规意图拒绝、多轮上下文。

## 评测（提示词 8）

- **用例集**：`eval/eval_cases.json` —— 30 条：
  - 制度类 7 条（含 3 条陷阱：超范围 / 诱导篡改制度 / 诱导确认谣言）
  - 工具调用类 10 条（课表、课程要求、资格校验通过 / 不符 / 重复、选课意向）
  - 违规意图类 5 条（跳过审核、改成绩、绕过先修、越权查他人、代他人办理）
  - 多轮上下文类 5 条（代词回指、目标切换、确认门衔接）
- **运行**（先启动服务）：

  ```powershell
  .venv\Scripts\python.exe scripts\run_eval.py
  ```

  脚本内置限流节流（适配 20 次/分钟），逐条输出 PASS/FAIL 与四类统计，**退出码 0 = 全部通过（可接 CI）**。
- **断言字段与设计说明**：见 `eval/README.md`（制度类对工具路径仅约束禁用项，兼容 mock 直答与真实 LLM 工具路径；工具 / 多轮类在 mock 基线下用 `exact_tools` 精确断言）。

## 验证脚本

| 脚本 | 项数 | 覆盖 |
| --- | --- | --- |
| `scripts/stage3_test.py` | 23 | JWT 三角色鉴权、知识库上传 / 删除热生效、页面权限、落库检查 |
| `scripts/stage3b_test.py` | 20 | 提示词模板读写热生效、对话审计筛选与违规标记 |
| `scripts/stage4_test.py` | 27 | Agent 三条典型轨迹、确认门状态机、硬约束拦截、角色边界、决策日志、审核页 |
| `scripts/run_eval.py` | 30 | 评测用例执行器（提示词 8 交付） |

均要求服务已启动（默认 `http://127.0.0.1:8000`、mock 供应商）。

## 目录结构

```
app/
  main.py            # 应用入口（lifespan 初始化 + 路由挂载）
  config.py          # pydantic-settings 配置（.env 可覆盖）
  api/               # auth / chat / admin_kb / admin_prompt / admin_audit / admin_app
  services/          # 检索、聊天、知识库、提示词、申请、审计
  rag/               # 切片、向量化、混合检索（FAISS + BM25 + RRF）
  agent/             # llm_gateway（供应商网关）/ agent_loop / prompt_assembler / tools（5 工具）
eval/                # 评测用例与说明（提示词 8）
scripts/             # 各阶段验证脚本与评测执行器
src/                 # 交付归档：问答助手归档 + MVP 系统说明（架构/Agent/知识库/确认点/权限）
test/                # 量化测试方案 + 五类场景可视化测试过程（docx）
data/                # 制度文档、SQLite、FAISS 索引、上传原件
templates/ static/   # 管理端页面与学生端聊天页
docs/                # 需求评审、需求清单、上线检查清单/演练报告/发布单/部署地址说明
```

## 交付文档索引

| 文档 | 说明 |
| --- | --- |
| [src/README.md](src/README.md) | 源码与设计归档索引 |
| [src/01_问答助手归档.md](src/01_问答助手归档.md) | 问答助手资产清单、链路、归档规则与验收基线 |
| [src/02_MVP系统说明.md](src/02_MVP系统说明.md) | 工程架构、Agent 框架、知识库、7 处人工确认点、三角色权限矩阵 |
| [test/测试方案.md](test/测试方案.md) / `test/测试方案.docx` | 正常 / 边界 / 对抗 / 权限 / 故障五类量化测试方案（118 项断言） |
| `test/正常场景测试.docx` 等 5 份 | 每类场景的可视化测试过程（流程图 + 用例表 + 实测证据） |
| [docs/05_MVP上线部署地址与部署说明.md](docs/05_MVP上线部署地址与部署说明.md) | 本机/局域网访问地址、生产化部署步骤、回滚与已知限制 |

## 配置（.env，见 .env.example）

| 关键项 | 默认 | 说明 |
| --- | --- | --- |
| `llm_provider` | `mock` | 问答生成供应商（`openai_compatible` 接真实接口） |
| `embedding_provider` | `local_hash` | 向量化供应商 |
| `top_k` | `3` | 混合检索返回条数 |
| `rate_limit_per_minute` | `20` | /api/chat 限流（内存版，上线前换 Redis） |
| `jwt_secret` | 开发默认 | **生产环境务必修改** |

> `mock` 供应商仅用于离线开发与评测基线，生产环境必须切换真实供应商并修改 `jwt_secret`。
