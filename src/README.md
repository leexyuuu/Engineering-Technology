# src · 交付归档索引

本目录是「知行职业学院 · 排课选课与教务协作智能体」MVP 的**源码与设计归档索引**，不复制代码本体，
代码唯一副本仍位于仓库根目录 `app/`。目的：让评审人能在一处看清「系统由什么组成、问答助手如何归档、
MVP 如何满足工程架构 / Agent 框架 / 知识库 / 人工确认点 / 权限数量」的硬要求。

| 文档 | 内容 | 对应交付要求 |
| --- | --- | --- |
| [01_问答助手归档.md](01_问答助手归档.md) | 问答助手资产清单、运行入口、问答链路、归档规则、验收基线 | src-1 问答助手归档 |
| [02_MVP系统说明.md](02_MVP系统说明.md) | 工程架构、Agent 框架、知识库管线、6 处人工确认/审核点、三角色权限矩阵 | src-2 MVP 项目说明 |

## 代码地图（唯一副本位置）

```text
app/
  main.py                应用入口：lifespan 初始化（建表→种子→索引）+ 路由挂载 + 统一异常
  config.py              pydantic-settings 配置（.env 覆盖）
  security.py            PBKDF2 密码哈希 / JWT 签发校验 / require_roles 权限依赖
  models.py              10 张表 ORM（用户/会话/消息/文档/切片/提示词/决策日志/申请单等）
  api/                   auth / chat / admin_kb / admin_prompt / admin_audit / admin_app
  services/              chat / retrieval / kb / prompt / application / audit
  rag/                   chunker（切界切片）/ embeddings / vector_store(FAISS) / bm25
  agent/                 llm_gateway / agent_loop / prompt_assembler / tools（5 个工具）
static/                  index.html 学生聊天页 + 样式
templates/               登录页与 4 个管理页（Jinja2）
data/docs/               种子制度文档（教务管理制度.md，JW-ZD-2026-001 / v2026.1）
eval/                    30 条评测用例与断言说明
scripts/                 stage3 / stage3b / stage4 / run_eval 验证与评测执行器
test/                    量化测试方案与五类场景可视化测试过程（docx）
docs/                    需求评审、需求清单、上线检查清单/演练报告/发布单/部署说明
```

## 快速定位

- 想跑起来：见根目录 `README.md` 的「快速开始」，默认 mock 供应商可离线运行。
- 想看 Agent 循环与确认门：`app/agent/agent_loop.py`、`app/agent/tools/eligibility_tools.py`。
- 想看权限边界：`app/security.py` + `app/api/*.py` 中的 `require_roles(...)`。
- 想看测试证据：`test/测试方案.md` 与 `test/*场景测试.docx`；历史演练结论见 `docs/03_上线演练报告.md`。

> 归档原则：**文档描述 + 路径指路，不复制第二份代码**，避免代码双副本产生版本漂移。
