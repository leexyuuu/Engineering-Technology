# MVP 上线部署地址与部署说明

> 交付项：MVP 系统上线部署网站地址（文档） ｜ 版本 v0.4.0 ｜ 更新日期：2026-11-06
> 适用：知行职业学院 · 排课选课与教务协作智能体

## 1. 当前可访问地址（本机演示环境）

系统当前以单实例方式运行在本机，**尚未发布到公网**。可直接访问：

| 入口 | 地址 | 说明 |
| --- | --- | --- |
| 学生 / 教师聊天页 | **http://127.0.0.1:8000/login** | 登录后进入问答与选课申请 |
| 登录页 | http://127.0.0.1:8000/login | 三角色统一入口 |
| 知识库管理 | http://127.0.0.1:8000/admin/kb | 仅 `admin` |
| 提示词模板 | http://127.0.0.1:8000/admin/prompt | 仅 `admin` |
| 对话审计 | http://127.0.0.1:8000/admin/audit | 仅 `admin` |
| 选课申请审核 | http://127.0.0.1:8000/admin/applications | 仅 `admin` |
| 接口文档（Swagger） | http://127.0.0.1:8000/docs | 开发/联调用，生产建议关闭 |

**演示账号**（仅演示环境有效，生产必须改密或禁用）：

| 账号 | 密码 | 角色 |
| --- | --- | --- |
| `student1` | `123456` | 学生 |
| `teacher1` | `123456` | 教师 |
| `admin1` | `123456` | 教务管理员 |

启动命令（项目根目录）：

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

首次启动自动建表、写入演示账号、导入制度文档并构建 FAISS 索引。

> 说明：当前运行实例加载 `.env` 配置。`.env` 含密钥，已被 `.gitignore` 排除，**不随仓库发布**；
> 评审环境若需完全离线复现，请使用 `LLM_PROVIDER=mock`（见第 5 节）。

## 2. 局域网访问地址（同一网段内演示）

若需让同网段电脑/手机访问，启动时绑定全部网卡，并放行防火墙端口：

```powershell
# 启动（监听 0.0.0.0）
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 放行端口（管理员 PowerShell，演示环境）
New-NetFirewallRule -DisplayName "MVP-Web-8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

本机当前局域网 IPv4 为 `10.201.33.2`（WLAN），因此同网段访问地址为：

**http://10.201.33.2:8000/login**

> 注意：局域网地址随网络环境变化（IP 可能被 DHCP 重新分配），正式演示前用
> `Get-NetIPAddress -AddressFamily IPv4` 复核；本地址仅供校内演示，**不是公网上线地址**。

## 3. 生产化部署（校内服务器 / 云主机）

### 3.1 前置条件

| 项 | 要求 |
| --- | --- |
| 操作系统 | Linux（推荐 Ubuntu 22.04+）或 Windows Server |
| Python | 3.11+（本项目在 3.14 环境验证通过） |
| 资源 | 2 vCPU / 4 GB 内存起步；磁盘 ≥20 GB（含备份） |
| 网络 | 仅开放 443（HTTPS）；8000 仅本机回环，供 Nginx 反代 |
| 数据库 | MVP 可用 SQLite；并发 >20 或多人协作建议 PostgreSQL（改 `DB_URL`） |
| 限流 | 单实例使用内存滑动窗口；**多实例必须迁移 Redis**（见检查清单 CL-2） |

### 3.2 部署步骤（Linux + systemd + Nginx）

```bash
# ① 取代码
git clone https://github.com/leexyuuu/Engineering-Technology.git /opt/campus-agent
cd /opt/campus-agent

# ② 虚拟环境与依赖
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# ③ 生产配置（不要把 .env 提交到 Git）
cp .env.example .env
#   必改：LLM_PROVIDER=openai_compatible + 真实 BASE_URL / API_KEY / MODEL
#   必改：EMBEDDING_PROVIDER=openai_compatible + 真实嵌入接口
#   必改：JWT_SECRET=<32 位以上强随机值>
#   按需：DB_URL=postgresql+asyncpg://...（需另装驱动）
#   按需：RATE_LIMIT_PER_MINUTE

# ④ 首次启动（初始化库与索引）
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

systemd 服务（`/etc/systemd/system/campus-agent.service`）：

```ini
[Unit]
Description=Campus Agent (FastAPI)
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/campus-agent
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/campus-agent/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> `--workers 1` 是**必须**的约束：限流、FAISS 索引与 SQLite 均为进程内状态，多 worker 会导致计数与索引不一致。

Nginx 反向代理（关键：SSE 必须关闭缓冲）：

```nginx
server {
    listen 443 ssl;
    server_name agent.example.edu.cn;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # SSE 流式：必须关闭缓冲与超时截断
        proxy_buffering    off;
        proxy_cache        off;
        proxy_read_timeout 300s;
        chunked_transfer_encoding on;
    }
}
```

启动与自启：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now campus-agent
sudo systemctl status campus-agent
```

### 3.3 生产检查清单（上线前必过）

| 类别 | 必须动作 | 通过标准 | 依据 |
| --- | --- | --- | --- |
| 配置 | 真实 LLM / Embedding 供应商 | 制度问答正常、回答有引用 | 检查清单第 1 节 |
| 安全 | 更换 `JWT_SECRET` | 旧密钥 token 401+40101 | DS-1（P0） |
| 安全 | 清除默认口令 | `123456` 三角色全部登录失败 | DS-2（P0） |
| 安全 | 越权隔离 | 学生调管理接口 403+40301 | DS-4（P0） |
| 可用 | 限流 | 第 21 次 429+42901，60s 恢复 | CL-1（P0） |
| 可用 | 供应商故障降级 | SSE error + 50301，无堆栈 | FB-1（P0） |
| 内容 | 诱导与违规拒绝 | 评测 T01–T03 / V01–V05 全过 | CS-1/CS-2（P0） |
| 内容 | 确认门双层防护 | 未校验不能建单；状态机不可跳级 | CS-3（P0） |
| 回滚 | 代码 tag + 冒烟 | 5 分钟内恢复上一版本 | RB-1（P0） |
| 回滚 | 数据备份恢复 | 申请单状态机字段无损 | DS-5 / RB-2 |

完整 25 项见 [02_上线检查清单.md](02_上线检查清单.md)，演练结论见 [03_上线演练报告.md](03_上线演练报告.md)。

### 3.4 上线后冒烟（5 分钟）

```bash
# 1) 健康入口
curl -I https://agent.example.edu.cn/login            # 期望 200

# 2) 三角色登录（演示账号在生产应已禁用，此处用正式账号）
curl -s -X POST https://agent.example.edu.cn/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<正式学生账号>","password":"<密码>"}'

# 3) 制度问答（SSE）
curl -N -X POST https://agent.example.edu.cn/api/chat \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"question":"补退选的截止时间是什么时候？"}'
# 期望：status → message → citations → done，回答含条文引用

# 4) 回归与评测（服务已启动）
.venv/bin/python scripts/stage3_test.py
.venv/bin/python scripts/stage3b_test.py
.venv/bin/python scripts/stage4_test.py
.venv/bin/python scripts/run_eval.py     # 退出码 0 = 30/30
```

## 4. 数据备份与回滚

```bash
# 每日备份（数据库 + 索引 + 上传原件）
tar -czf /backup/campus-agent-$(date +%Y%m%d).tar.gz \
    /opt/campus-agent/data/app.db /opt/campus-agent/data/faiss /opt/campus-agent/data/uploads

# 代码回滚
cd /opt/campus-agent
git checkout <上一发布 tag>
sudo systemctl restart campus-agent
```

保留期建议 ≥30 天；恢复后必须跑一次三角色登录 + 制度问答 + 申请全流程冒烟。

## 5. 离线复现（评审 / 无外网环境）

```powershell
# 强制使用 mock 供应商与本地哈希嵌入，不连接任何外部接口
$env:LLM_PROVIDER='mock'
$env:EMBEDDING_PROVIDER='local_hash'
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

mock 供应商仅用于离线演示与评测基线，**不可作为生产配置**；真实供应商切换路径见 `.env.example`。

## 6. 已知限制（MVP）

1. 限流为进程内内存实现，仅适用于**单实例**；多实例需 Redis。
2. SQLite 适合单实例低并发；高并发请切 PostgreSQL 并复测 CL-4。
3. 教务系统对接为 **mock 只读数据**（课程/课表/学籍/成绩），生产需替换为真实只读接口。
4. 真实 LLM 供应商下个别脚本的"精确工具序列"断言可能因措辞/路径差异失败，评测口径见 `eval/README.md`。
5. 演示账号与默认口令仅用于验收，生产必须改密或禁用。

## 7. 地址登记表

| 环境 | 地址 | 状态 | 备注 |
| --- | --- | --- | --- |
| 本机演示 | http://127.0.0.1:8000/login | 运行中 | 仅本机可访问 |
| 局域网演示 | http://10.201.33.2:8000/login | 需 `--host 0.0.0.0` + 防火墙放行 | IP 随网络变化，演示前复核 |
| 生产（规划） | https://agent.example.edu.cn | 未上线 | 按第 3 节部署后替换为真实域名 |

> 本文档只登记**当前真实可访问地址**与**生产部署方法**，不宣称系统已完成公网上线。
