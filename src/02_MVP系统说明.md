# MVP 系统说明（工程架构 · Agent 框架 · 知识库 · 人工确认点 · 权限）

> 交付项：src-2 ｜ 系统：知行职业学院 · 排课选课与教务协作智能体 ｜ 版本 v0.4.0 ｜ 2026-11-06

## 1. 项目定位与硬边界

面向学生、教师、教务管理员的**选课制度问答 + 选课申请协作**系统。核心承诺：

- **只读不代选**：系统对接教务系统的接口为只读，绝不替学生选课、不改成绩、不改培养计划。
- **答案可溯源**：制度类回答必须附引用来源（文件名 + 章节 + 切片号）；检索不到时明确回答"制度中未找到"。
- **人工在环**：任何写入型动作（选课申请）都必须经过「学生本人确认 → 教务管理员审核 → 人工执行」。

## 2. 工程架构

### 2.1 分层结构

```text
┌──────────────────────────────────────────────────────────────────────┐
│  展示层  static/index.html（学生聊天页，SSE 打字机）                    │
│          templates/*.html（登录页 + 知识库/提示词/审计/申请审核 4 页）  │
├──────────────────────────────────────────────────────────────────────┤
│  接口层  app/api/  auth · chat · admin_kb · admin_prompt ·             │
│                    admin_audit · admin_app                             │
│          统一异常：{code, message} 中文结构，禁止堆栈外泄               │
├──────────────────────────────────────────────────────────────────────┤
│  安全层  app/security.py  PBKDF2 密码哈希 · JWT(HS256) ·               │
│                           require_roles 接口级权限 · 数据归属校验       │
├──────────────────────────────────────────────────────────────────────┤
│  服务层  app/services/  chat · retrieval · kb · prompt ·                │
│                         application（状态机）· audit                    │
├──────────────────────────────────────────────────────────────────────┤
│  智能层  app/rag/   切片 · 向量化 · FAISS · BM25 · RRF 融合              │
│          app/agent/ llm_gateway · agent_loop · prompt_assembler ·      │
│                     tools（5 个工具）                                   │
├──────────────────────────────────────────────────────────────────────┤
│  数据层  SQLAlchemy 2.0 async + SQLite(aiosqlite)                       │
│          users / conversations / messages / documents / doc_chunks /   │
│          prompt_templates / agent_decision_logs / selection_applications│
│          文件：FAISS 索引、上传原件、备份                               │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 技术选型

| 层 | 选型 | 说明 |
| --- | --- | --- |
| Web | FastAPI + Uvicorn + SSE（sse-starlette） | 异步、流式、轻量 |
| 页面 | Jinja2 服务端渲染 + 原生 HTML/CSS/JS | 不引入前端构建链，降低交付成本 |
| 数据 | SQLAlchemy 2.0（async）+ SQLite | 单实例起步；`db_url` 可平滑切 PostgreSQL |
| 检索 | FAISS + rank-bm25 + jieba | 向量 + 词法双路召回，RRF 融合 |
| 安全 | PyJWT（HS256）、PBKDF2-HMAC-SHA256（10 万轮） | 零额外密码库依赖 |
| LLM / Embedding | `mock` / `openai_compatible` 可切换 | 离线可跑；生产切真实供应商 |

### 2.3 启动依赖链

```text
init_db（建表） → seed_demo_users（三角色） → init_default（提示词模板）
→ kb_service.seed_if_empty（制度文档入库） → retrieval.load_or_build（FAISS 装载/重建）
```

### 2.4 部署形态（MVP）

单实例：`Uvicorn` 进程 + 本地 SQLite/FAISS；限流为进程内内存滑动窗口（20 次/分钟/IP），
因此**限流与多实例不兼容**——扩容到多实例前必须把限流迁移到 Redis（见上线检查清单 CL-2）。
部署地址与生产化步骤见 `docs/05_上线部署地址与部署说明.md`。

## 3. Agent 框架

### 3.1 为什么自研轻量 Harness

- 确认门需要在循环中间**强制中断**并发确认卡片，重框架难以精确插桩；
- 决策日志需要在每轮工具执行前后落库，自研循环只需一个 `execute_tool` 包装；
- 循环本体不足百行，零新增依赖，便于评测与审计复现。

### 3.2 执行循环（`app/agent/agent_loop.py`）

```text
                    ┌───────────────────────────────┐
                    │ 系统提示词（含工具顺序约束）     │
                    │ + 最近 6 轮历史 + 脱敏问题       │
                    └───────────────┬───────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ 模型决策（带 5 个工具）│
                         └──────┬──────┬───────┘
                    工具调用 │      │ 直答（无 tool_calls）
                            ▼      ▼
             ┌──────────────────┐  ┌──────────────────────────┐
             │ execute_tool     │  │ 流式输出回答 → citations │
             │ 结果回填 tool 消息│  │ → done                   │
             └───┬───────┬──────┘  └──────────────────────────┘
                 │       │
       建申请成功 │       │ 其他工具（回到决策，最多 5 轮）
                 ▼       └──────────────► ↑
      ┌──────────────────────────┐
      │ 发 confirm_required 卡片 │
      │ 强制中断循环，等待学生确认│
      └──────────────────────────┘
```

### 3.3 工具清单（`app/agent/tools/`）

| # | 工具 | 类型 | 作用 | 关键约束 |
| --- | --- | --- | --- | --- |
| 1 | `query_course_schedule` | 只读 | 查课程排课（星期/节次/教室/教师/课表版本） | 课程不存在时明确"未找到该课程" |
| 2 | `search_selection_rules` | 只读 | 检索制度条文（RAG） | 引用来源从工具结果回填 |
| 3 | `check_course_requirements` | 只读 | 查课程类型/学分/学时/先修/容量 | 匹配多门课时要求先确认 |
| 4 | `validate_eligibility` | 只读 | 规则引擎五项校验：重复选课→先修课→时间冲突→学分上限→容量 | 全部通过才登记进 `validated_courses` |
| 5 | `create_selection_application` | 受控写入 | 生成 draft 选课申请单 | **硬约束**：未通过工具 4 一律拒绝；仅落 draft |

### 3.4 双层防护与确定性拦截

| 防护层 | 位置 | 行为 |
| --- | --- | --- |
| 提示词层 | `prompt_assembler` 系统提示词 | 规定工具调用顺序、禁止跳过审核、禁止编造 |
| 代码层 · 资格硬约束 | `eligibility_tools.create_selection_application` | `course_code not in ctx.validated_courses` → `created=False`，返回拦截原因 |
| 代码层 · 确认门状态 | `agent_loop._check_confirm_gate` | 历史必须已呈现选课信息（查课程要求/资格）且本轮有确认语，否则拒绝建单 |
| 代码层 · 违规意图 | `agent_loop._safety_refusal` | 正则命中"跳过审核/改学分/查他人" → 标准化拒答，不进入工具循环、不写入 |
| 代码层 · 未检索直答 | `agent_loop._looks_ungrounded` | 零工具且非安全话术 → 丢弃自由发挥内容，强制回退 RAG 直答 |
| 代码层 · 防重复调用 | `agent_loop.seen_calls` | 同工具同参数二次调用直接回填错误，防重试风暴 |

### 3.5 决策日志与兜底

- 每轮工具调用写 `agent_decision_logs`：轮次、工具名、参数、耗时、结果摘要。
- 特殊节点：`__final_answer__`（最终作答）、`__confirm_gate__`（等待学生确认）、
  `__safety_refusal__`（安全拒答）、`__confirm_nudge__`（确认语被打回）、
  `__fallback_answer__`（超 5 轮兜底）。
- 超轮次 → 自动退回 RAG 直答，保证任何问题都有回答。

## 4. 知识库（RAG）

### 4.1 入库管线

```text
Markdown 原文
  → 按标题切界（保留章节路径）
  → 500 字聚合切片（chunk_size=500，带 source / heading / chunk_no）
  → 向量化（local_hash 离线 / openai_compatible 生产）
  → FAISS 索引持久化 data/faiss/index.faiss + chunks.json
  → 同时把切片正文写入 doc_chunks 表（BM25 内存索引重启重建）
```

### 4.2 检索管线

```text
query
  ├─ 向量召回（FAISS，TopN）
  └─ 词法召回（BM25，jieba 分词，TopN）
        └─ RRF 融合（k=60）→ 取 top_k=3 → 返回 source / heading / chunk_no / preview
```

- **热更新**：管理员上传/删除文档后立即重建索引，无需重启（RB-4 已实证）。
- **引用约束**：回答必须基于检索切片；零命中时回答"制度中未找到"，且 `citations` 清空（演练发现 3 的修复）。
- **知识资产现状**：种子制度 1 份 / 6 个切片；上传件原件留档 `data/uploads/`。

## 5. 人工确认与审核点（共 7 处，满足 ≥3）

| # | 确认/审核点 | 触发时机 | 执行人 | 系统强制方式 | 留痕 |
| --- | --- | --- | --- | --- | --- |
| C1 | **选课意向确认语** | 创建申请前 | 学生 | 代码层确认门：历史须已呈现课程要求/资格，且本轮为确认语 | 决策日志 `__confirm_gate__`、会话消息 |
| C2 | **申请卡片确认** | 申请单 draft 已生成 | 学生本人 | `POST /api/chat/confirm`：归属 + 会话 + 状态机三重校验 | 申请单 `status=draft→student_confirmed`、更新时间 |
| C3 | **教务审核** | 学生确认后 | 教务管理员 | `POST /api/admin/applications/{no}/review`，仅 admin；驳回必填原因 | `admin_note`、`admin_id`（签核人）、状态流转 |
| C4 | **教务系统人工执行** | 审核通过后 | 教务管理员 | 系统不代选：接口只读，`execute` 仅标记状态，实际选课由人在教务系统完成 | 申请单 `admin_confirmed→executed` |
| C5 | **知识库变更审核** | 制度文档入库/下架 | 教务管理员 | 上传/删除接口仅 admin，变更即时生效并重建索引 | `documents.uploader_id`、版本、软删除记录 |
| C6 | **提示词模板变更** | 调整助手话术/禁令 | 教务管理员 | 在线编辑，保存即生效，无需发版 | `prompt_templates` 当前版本 |
| C7 | **审计违规复核** | 疑似违规对话 | 教务管理员 | 审计页人工标记/取消标记，必须填原因 | `messages.is_flagged`、`flag_reason` |

> 其中 C1–C4 构成选课申请主链路的**双人确认 + 人工执行**闭环：
> 申请单只能沿 `draft → student_confirmed → admin_confirmed → executed` 推进，
> 非法跳转返回 `40901`，终态不可再操作。

## 6. 权限设计（3 个角色，满足 ≥2）

### 6.1 角色定义

| 角色 | 对应岗位 | 核心能力 |
| --- | --- | --- |
| `student` | 学生 | 制度问答、查课表、选课资格预检、发起并确认本人选课申请 |
| `teacher` | 任课教师 / 课程负责人 | 制度问答、查课表；无学籍，不能做选课资格校验与建申请 |
| `admin` | 排课专员 / 教务主任 / 教学质量专员 | 知识库、提示词、审计、选课申请审核；不参与学生本人确认 |

### 6.2 权限矩阵

| 资源 / 能力 | 未登录 | student | teacher | admin |
| --- | --- | --- | --- | --- |
| `POST /api/auth/login` | ✅ | ✅ | ✅ | ✅ |
| `GET /api/auth/me` | ❌ 40101 | ✅ | ✅ | ✅ |
| `POST /api/chat`（问答） | ❌ 40101 | ✅ | ✅ | ✅（无学籍） |
| `POST /api/chat/confirm`（确认本人申请） | ❌ 40101 | ✅ 仅本人 | ❌ 无本人申请 | ❌ 无本人申请 |
| 资格校验 / 建申请（工具） | — | ✅ | ❌ "无学生学籍" | ❌ "无学生学籍" |
| `GET/POST/DELETE /api/admin/kb/*` | ❌ 40101 | ❌ 40301 | ❌ 40301 | ✅ |
| `GET/PUT /api/admin/prompt` | ❌ 40101 | ❌ 40301 | ❌ 40301 | ✅ |
| `GET/PUT /api/admin/audit/*` | ❌ 40101 | ❌ 40301 | ❌ 40301 | ✅ |
| `GET /api/admin/applications` | ❌ 40101 | ❌ 40301 | ❌ 40301 | ✅ |
| `POST /api/admin/applications/{no}/review` | ❌ 40101 | ❌ 40301 | ❌ 40301 | ✅ |
| 管理页面 `/admin/*` | ↪ 303 到 `/login` | ↪ 303 | ↪ 303 | ✅ 200 |

### 6.3 鉴权实现要点

- 凭证双通道：`Authorization: Bearer`（前端 API）+ HttpOnly Cookie（管理页导航）。
- `require_roles("admin")` 作为 FastAPI 依赖统一挂在管理接口，越权 → `403 + 40301`。
- 数据归属校验在服务层二次执行：确认接口校验 `app.user_id == 当前用户` 且会话匹配，防横向越权。
- 会话越权返回 `404 + 40401`（不暴露他人会话是否存在，防枚举）。

## 7. 统一错误码

| 错误码 | HTTP | 含义 |
| --- | --- | --- |
| 40001 | 400 | 参数缺失或非法 |
| 40101 | 401 | 未登录或登录过期 |
| 40102 | 401 | 用户名或密码错误 |
| 40301 | 403 | 无权访问该功能 |
| 40401 / 40402 / 40403 | 404 | 会话 / 文档 / 申请单不存在 |
| 40901 | 409 | 申请当前状态不允许该操作 |
| 42901 | 429 | 请求过于频繁 |
| 50001 | 500 | 检索服务异常 |
| 50003 | 500 | 工具执行异常 |
| 50301 / 50302 | 500 | LLM 调用失败 / 供应商配置错误 |

## 8. 关键配置项（`.env`）

| 配置 | 默认 | 生产要求 |
| --- | --- | --- |
| `LLM_PROVIDER` | `mock` | 改 `openai_compatible` + 真实端点/密钥/模型 |
| `EMBEDDING_PROVIDER` | `local_hash` | 改真实嵌入接口（哈希词袋无语义） |
| `JWT_SECRET` | 开发默认值 | 改 ≥32 字符强随机值 |
| `RATE_LIMIT_PER_MINUTE` | 20 | 按容量评估；多实例迁移 Redis |
| `TOP_K` | 3 | 可按召回质量调整 |
| `HISTORY_ROUNDS` | 6 | 上下文轮数 |
| `db_url` | SQLite | 高并发切 PostgreSQL |

## 9. 与需求的对应关系（摘要）

| 需求 | 落地位置 | 验证 |
| --- | --- | --- |
| REQ-1 选课冲突预检（确定性规则引擎） | 工具 4 `validate_eligibility` 五项检查 | `stage4_test.py` 轨迹 c、评测 U07/U08 |
| 制度问答必须附引用 | 检索 citations + 回答模板 | 评测 R01–R07、CS-4 抽查 |
| 选课申请草稿 + 双重确认 | 确认门 + 状态机 | `stage4_test.py` B1–B11 |
| 审计留痕（业务编号/版本/引用/轨迹/改动/签核人） | 申请单字段 + 决策日志 + 审计页 | `stage3b_test.py` T9–T16 |
| 违规意图拒绝 | 代码层正则拦截 + 提示词禁令 | 评测 V01–V05 |
| 超范围不编造 | 零命中话术 + citations 清空 | 评测 T01–T03 |
