<div align="center">

# 调度组件智能文档助手

**用自然语言查询调度系统接口文档** · 基于 RAG + Hybrid Search + DeepSeek + LangChain

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=fff)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=fff)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?logo=langchain&logoColor=fff)](https://langchain.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=fff)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[快速开始](#rocket-快速开始) · [功能特性](#sparkles-功能特性) · [技术架构](#building_construction-技术架构) · [检索流水线](#zap-检索流水线) · [API 文档](#open_book-api-文档) · [配置说明](#gear-配置说明) · [开发指南](#wrench-开发指南) · [设计亮点](#star-设计亮点)

</div>

---

## :bulb: 项目简介

为调度组件（公司内部自研的定时任务调度系统）提供智能文档问答服务。用户用中文自然语言提问，系统自动检索接口文档并生成结构化回答（接口地址、参数表、JSON 示例），解决「接口文档难查、参数描述难懂、新人上手慢」的痛点。

> ⚠️ 本项目中的「调度组件」「调度系统」均特指**公司内部自研的调度组件**，与 XXL-Job、Quartz、Elastic-Job 等开源框架无关。

---

## :rocket: 快速开始

### Docker 一键部署（推荐）

```bash
# 1. 克隆项目
git clone <repo-url> && cd agent-support

# 2. 配置 API Key
cp customer_service_ai/.env.example customer_service_ai/.env
# 编辑 .env，填入：
#   DEEPSEEK_API_KEY=<你的 DeepSeek Key>
#   EMBEDDING_API_KEY=<你的 Embedding Key>
#   ADMIN_PASSWORD=<管理员密码>

# 3. 构建并启动（前端 + 后端 + Redis + Worker）
./start.sh

# 4. 初始化知识库（首次部署）
./start.sh ingest
```

打开 `http://localhost:8083` 即可使用。点击右上角「管理员」→ 输入密码 →「文档管理」→ 上传调度组件文档（.txt/.md/.pdf）→「重建索引」。

### 本地开发

```bash
# 后端
cd customer_service_ai
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端（另开终端）
cd chat-ui
npm install
npm run dev
```

打开 `http://localhost:5173`（Vite dev proxy 自动转发 API 到 8000 端口）。

### 内网部署

```bash
./start.sh export         # 导出 x86 镜像 tar 包到 /tmp/
./start.sh push-registry  # 推送到内网镜像仓库（需配置 REGISTRY_URL）
```

---

## :sparkles: 功能特性

### 核心问答

| 功能 | 描述 |
|------|------|
| **自然语言查接口** | 中文提问直接检索调度组件 API 文档，返回接口地址 + 参数表 + JSON 示例 |
| **真流式输出** | 基于 `astream_events v2` 的 token-by-token SSE 流式，首 token 延迟 ~2s |
| **多轮对话** | 对话摘要自动注入上下文，支持连续追问 |
| **示例引导** | 首页展示 6 个常见问题示例，点击即问 |

### 检索引擎

| 功能 | 描述 |
|------|------|
| **Hybrid Search** | FTS5 BM25 关键词检索 + 向量语义检索，RRF 融合排序 |
| **MultiQuery 查询重写** | LLM 从多角度生成 3 个查询变体 + 原问题 = 4 路并行检索 |
| **Reranker 精排** | Cross-encoder (`bge-reranker-v2-m3`) 语义精排 top-5 |
| **置信度标注** | Reranker 评分 < 0.5 自动标注「仅供参考」 |
| **响应缓存** | 相同问题 1h 内命中缓存直接返回，跳过 LLM 调用 |

### 管理后台

| 功能 | 描述 |
|------|------|
| **JWT 鉴权** | Access Token (30min) + Refresh Token (7d)，支持旧 Token 兼容 |
| **文档管理** | 上传 / 删除 / 全量重建，支持 .txt / .md / .pdf |
| **知识库版本管理** | 每次重建自动创建版本，支持列表和回滚 |
| **配置热重载** | Prompt / 阈值 / 检索参数在线修改，无需重启 |
| **用户反馈闭环** | 👍/👎 反馈收集 + 错误日志自动记录 |
| **审计日志** | 管理员操作（文档上传 / 配置修改）全程记录 |

### 生产加固

| 功能 | 描述 |
|------|------|
| **限流** | slowapi 按 IP 限流：聊天 30/min、流式 10/min、文档 5/min |
| **熔断** | pybreaker：LLM 连续失败 5 次 / Reranker 连续失败 3 次自动熔断 |
| **重试** | tenacity 指数退避（1-10s），仅重试网络类异常 |
| **Embedding 回退** | 主 Embedding 不可用时自动切换备用 provider |
| **健康检查** | `GET /health` 返回 DB / 向量库 / LLM 组件状态 + 延迟 |
| **优雅停机** | 关闭 HTTPX 客户端 + DB 引擎 + FTS5 连接 |
| **请求链路追踪** | RequestId 中间件注入 `X-Request-ID` 全链路日志关联 |
| **异步任务队列** | Celery + Redis 异步生成对话摘要，不阻塞主流程 |

---

## :building_construction: 技术架构

```
┌──────────────┐      ┌──────────────────────────────────────────────────┐
│  浏览器       │      │  Nginx (8083)                                    │
│  React 19     │─────▶│  ├── /          → 静态 SPA                       │
│  Tailwind     │      │  └── /chat/ ...  → 反代后端 (8000)               │
│  SSE 真流式   │◀─────│      (proxy_pass + resolver 动态 DNS)            │
│  Markdown 渲染│      └──────────────────┬───────────────────────────────┘
│  反馈 👍/👎   │                         │                               │
└──────────────┘                         ▼                               │
                       ┌──────────────────────────────────────────────────┐
                       │  FastAPI 后端 (8000)                              │
                       │                                                   │
                       │  ┌──────────┐  ┌──────────────────────────────┐  │
                       │  │ Agent    │  │ RAG Service                   │  │
                       │  │LangChain │──│ MultiQuery → Hybrid Search   │  │
                       │  │ 2 Tools  │  │ (Vector + BM25 → RRF)        │  │
                       │  └──────────┘  │ → Reranker → Cache            │  │
                       │                └──────────┬───────────────────┘  │
                       │  ┌──────────┐             │                      │
                       │  │ Session  │  ┌──────────▼──────────┐          │
                       │  │ Store    │  │  ChromaDB (向量库)   │          │
                       │  │ async DB │  │  + FTS5 (BM25 索引)  │          │
                       │  └──────────┘  └──────────┬──────────┘          │
                       │                           │                      │
                       │  ┌──────────┐  ┌──────────▼──────────┐          │
                       │  │ Limiter  │  │ Embedding (bge-m3)   │          │
                       │  │ Breaker  │  │ + Fallback Provider  │          │
                       │  │ JWT Auth │  │ Reranker (cross-enc) │          │
                       │  └──────────┘  │ LLM (DeepSeek V4)    │          │
                       │                └─────────────────────┘          │
                       └──────────────────────────────────────────────────┘
                                    │
                       ┌────────────┴───────────┐
                       │  Celery Worker          │
                       │  (异步生成对话摘要)       │
                       └────────────┬───────────┘
                                    │
                       ┌────────────▼───────────┐
                       │  Redis                  │
                       │  (Celery broker + 限流)  │
                       └────────────────────────┘
```

### 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| **前端** | React 19 + TypeScript + Tailwind CSS + Vite + lucide-react | SSE 流式渲染、Markdown 参数表格、暗色主题 |
| **Web 框架** | FastAPI 0.115 + Uvicorn | 异步 API、SSE 流式、全局异常处理 |
| **Agent 框架** | LangChain 0.3 | OpenAI Tools Agent、`astream_events` 真流式 |
| **检索引擎** | MultiQuery + Hybrid Search (Vector + FTS5 BM25) + RRF + Reranker | 四阶检索流水线 |
| **向量库** | ChromaDB | 轻量级本地向量存储 |
| **全文索引** | SQLite FTS5 | BM25 关键词检索，`porter unicode61` 分词 |
| **LLM** | DeepSeek V4 Flash | OpenAI 兼容 API |
| **Embedding** | BAAI/bge-m3 (SiliconFlow) | 8192 tokens 上下文，中英双语，支持多级回退 |
| **Reranker** | BAAI/bge-reranker-v2-m3 | Cross-encoder 精排 |
| **数据库** | SQLite (async aiosqlite) / PostgreSQL | 会话、消息、反馈、错误日志、配置、版本、审计 |
| **任务队列** | Celery + Redis | 异步对话摘要生成 |
| **限流** | slowapi | 按 IP 分接口限流 |
| **熔断** | pybreaker | LLM / Reranker 独立熔断 |
| **鉴权** | PyJWT (HS256) | Access + Refresh Token |
| **日志** | Loguru | 结构化日志 + request_id 全链路追踪 + 按日滚动 |

---

## :zap: 检索流水线

### 四阶检索策略

针对调度组件文档**中英文术语混用**（用户问中文「怎么创建作业计划」，文档接口名为英文 `saveCommonJobPlan`）的语义鸿沟，构建四阶检索流水线：

```
用户提问
    │
    ▼
1. MultiQuery 查询重写（LLM 生成 3 个中文变体 + 原问题 → 4 路并行）
    │
    ▼ (每路)
2. Hybrid Search 混合检索
   ├── 向量相似度检索（ChromaDB, fetch_k=40）
   └── BM25 关键词检索（FTS5, fetch_k=40）
         │
         ▼
   RRF 融合排序（Reciprocal Rank Fusion, k=60）
    │
    ▼
3. 去重合并 → Reranker 精排（Cross-encoder, top-20 → top-5）
    │
    ▼
4. LLM 基于精排结果生成结构化回答（参数表 + JSON 示例）
    │
    ▼
   置信度 < 0.5？→ 标注「仅供参考」 : → 正常返回
    │
    ▼
   缓存写入（LRU, TTL=1h, max=200）
```

| 阶段 | 策略 | 作用 |
|------|------|------|
| **1. 查询重写** | MultiQueryRetriever：LLM 生成 3 个中文搜索词 + 注入领域接口名种子词 | 桥接中英语义鸿沟，多角度覆盖 |
| **2. 混合检索** | FTS5 BM25 + 向量相似度，RRF 融合 | 关键词精确匹配 + 语义泛化双保险 |
| **3. 精排** | Cross-encoder Reranker：`bge-reranker-v2-m3`，top-20→5 | 语义相关性精准排序 |
| **4. 生成** | Stuff Documents Chain + 防幻觉 Prompt | 严格基于检索结果回答，不编造 |

### RRF 融合公式

```
score(d) = 1 / (k + rank_vector(d)) + 1 / (k + rank_bm25(d))
```

- `k` = 60（RRF 常数，平滑排名影响）
- `alpha` = 0.3（BM25 权重，`1-alpha` = 0.7 为向量权重）
- 可通过 `HYBRID_SEARCH_ALPHA` 调节：0 = 纯向量，1 = 纯 BM25

### 防幻觉护栏

- System Prompt 显式声明「调度组件 ≠ XXL-Job / Quartz / Elastic-Job」
- 5 条 few-shot 示例教 Agent 正确调用 `search_documentation`
- RAG Prompt 强制「必须严格基于参考资料回答，不要编造接口信息」

### RAG 量化评测

```bash
cd customer_service_ai
source .venv/bin/activate
python scripts/eval_rag.py
```

基于 30 条 Golden QA（覆盖接口查询 / 概念解释 / 故障排查 / 配置操作），输出关键词召回率和文档达标率，每次检索策略变更可一键回归验证。

---

## :open_book: API 文档

### 用户接口

| 端点 | 方法 | 说明 | 鉴权 | 限流 |
|------|------|------|------|------|
| `/chat/stream` | POST | 流式问答（SSE 真流式，主入口） | — | 10/min |
| `/chat/` | POST | 同步问答 | — | 30/min |
| `/history/` | GET | 当前用户会话列表 | — | — |
| `/history/{id}` | GET / DELETE | 会话消息列表 / 删除会话 | — | — |
| `/demos/` | GET | 示例问答 | — | — |
| `/feedback/` | POST | 提交 👍/👎 反馈 | — | — |
| `/health` | GET | 健康检查（DB / 向量库 / LLM 状态） | — | — |

### 管理员接口

| 端点 | 方法 | 说明 | 鉴权 | 限流 |
|------|------|------|------|------|
| `/auth/login` | POST | 管理员登录 → JWT Token | — | — |
| `/auth/refresh` | POST | 刷新 JWT Token | Refresh Token | — |
| `/documents/` | GET | 文档列表 | Admin | 5/min |
| `/documents/upload` | POST | 上传文档（自动导入向量库 + FTS5） | Admin | 5/min |
| `/documents/reindex` | POST | 全量重建（自动创建版本） | Admin | 5/min |
| `/documents/{filename}` | DELETE | 删除文档 | Admin | 5/min |
| `/documents/versions` | GET | 知识库版本列表 | Admin | — |
| `/documents/versions/{id}/rollback` | POST | 回滚到指定版本 | Admin | — |
| `/config/` | GET / PUT | 读取 / 修改运行时配置 | Admin | 10/min |
| `/config/reload` | POST | 清除配置缓存（热重载） | Admin | 10/min |
| `/feedback/` | GET | 反馈列表 | Admin | — |
| `/error-logs/` | GET | 错误日志列表 | Admin | — |

---

## :gear: 配置说明

```bash
cp customer_service_ai/.env.example customer_service_ai/.env
```

### 必填配置

| 环境变量 | 说明 |
|----------|------|
| `DEEPSEEK_API_KEY` | DeepSeek LLM API Key |
| `EMBEDDING_API_KEY` | Embedding API Key（SiliconFlow / OpenAI 等） |
| `ADMIN_PASSWORD` | 管理员登录密码，留空则关闭管理功能 |

### 检索配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `RETRIEVAL_RERANK_TOP_K` | 5 | Reranker 精排后保留文档数 |
| `RETRIEVAL_RERANK_CANDIDATE_K` | 20 | 送入 Reranker 的候选文档数 |
| `HYBRID_SEARCH_ENABLED` | true | 启用混合搜索 |
| `HYBRID_SEARCH_ALPHA` | 0.3 | BM25 权重（0=纯向量, 1=纯 BM25） |
| `CONFIDENCE_THRESHOLD` | 0.5 | 低于此值标注「仅供参考」 |

### Embedding 回退（可选）

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `EMBEDDING_FALLBACK_API_KEY` | (空) | 备用 Embedding Key，为空则不启用回退 |
| `EMBEDDING_FALLBACK_BASE_URL` | `https://api.openai.com/v1` | 备用 Embedding 端点 |
| `EMBEDDING_FALLBACK_MODEL` | `text-embedding-3-small` | 备用 Embedding 模型 |

### 基础设施

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DATABASE_URL` | `sqlite:///./data/chat.db` | 数据库（支持 PostgreSQL） |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis（Celery + 限流），为空则跳过异步任务 |
| `CACHE_ENABLED` | true | 响应缓存开关 |
| `CACHE_TTL` | 3600 | 缓存秒数 |
| `JWT_SECRET` | (空) | JWT 密钥，为空则自动生成 |

完整配置见 [`.env.example`](customer_service_ai/.env.example)。

---

## :wrench: 开发指南

### 环境要求

- Python 3.11+
- Node.js 18+
- Docker 20+（部署用）

### 运行测试

```bash
cd customer_service_ai
source .venv/bin/activate
python -m pytest tests/ -v
```

### 文档导入

```bash
# 全量重建（基于 data/docs/ 下所有文档）
./start.sh ingest

# 或通过 API
curl -X POST http://localhost:8000/documents/reindex \
  -H "X-Admin-Token: <your-token>"

# 增量导入
cd customer_service_ai
python scripts/ingest.py --incremental
```

### 部署命令

```bash
./start.sh                # 构建并启动全部服务
./start.sh dev            # 本地开发模式（uvicorn --reload + Vite）
./start.sh down           # 停止
./start.sh logs           # 查看日志
./start.sh status         # 查看状态
./start.sh rebuild        # 重新构建镜像
./start.sh export         # 导出 tar 包（内网部署）
./start.sh push-registry  # 推送到内网镜像仓库
```

### 知识库版本管理

```bash
# 列出所有版本
curl http://localhost:8000/documents/versions \
  -H "X-Admin-Token: <token>"

# 回滚到版本 #1
curl -X POST http://localhost:8000/documents/versions/1/rollback \
  -H "X-Admin-Token: <token>"
```

---

## :file_folder: 目录结构

```
agent-support/
├── customer_service_ai/              # Python 后端
│   ├── app/
│   │   ├── api/                      # FastAPI 路由
│   │   │   ├── chat.py               #   同步/流式问答
│   │   │   ├── auth.py               #   JWT 鉴权
│   │   │   ├── documents.py          #   文档管理 + 版本管理
│   │   │   ├── health.py             #   健康检查
│   │   │   ├── history.py            #   会话历史
│   │   │   ├── feedback.py           #   用户反馈
│   │   │   ├── config.py             #   配置热重载
│   │   │   ├── demos.py              #   示例问答
│   │   │   └── error_logs.py         #   错误日志
│   │   ├── agent/                    # Agent 编排（LangChain + 真流式）
│   │   ├── services/                 # 核心服务
│   │   │   ├── rag_service.py        #   四阶检索 + 缓存 + 版本管理
│   │   │   ├── fts_service.py        #   FTS5 BM25 全文检索
│   │   │   ├── embedding_service.py  #   Embedding + 多级回退
│   │   │   ├── reranker_service.py   #   Cross-encoder 精排
│   │   │   ├── llm_service.py        #   DeepSeek LLM
│   │   │   └── config_service.py     #   配置热重载
│   │   ├── tasks/                    # Celery 异步任务
│   │   │   └── summary_task.py       #   对话摘要生成
│   │   ├── middleware/               # 中间件
│   │   │   ├── __init__.py           #   RequestId
│   │   │   └── rate_limit.py         #   限流
│   │   ├── tools/                    # LangChain Tool
│   │   ├── prompts/                  # Prompt 模板（防幻觉 + few-shot）
│   │   ├── models/                   # SQLAlchemy ORM + Pydantic DTO
│   │   ├── utils/                    # 重试 + 熔断
│   │   ├── config.py                 # Pydantic Settings
│   │   ├── database.py               # 异步 SQLAlchemy 引擎
│   │   └── main.py                   # FastAPI 入口 + 优雅停机
│   ├── scripts/                      # 文档导入 + RAG 评测 + CLI 问答
│   ├── tests/                        # pytest 测试 + Golden QA 集
│   └── requirements.txt
├── chat-ui/                          # React 前端
│   ├── src/
│   │   ├── api/                      # SSE 流式解析 + API 调用
│   │   ├── components/               # ChatBubble / DocManager / LoginModal
│   │   └── App.tsx
│   ├── nginx.conf                    # 反向代理 + 动态 DNS
│   └── Dockerfile
├── docker-compose.yml                # 4 服务：backend / worker / redis / frontend
├── docker-compose.x86.yml            # x86 交叉构建 override
├── start.sh                          # 一键部署脚本
└── README.md
```

---

## :star: 设计亮点

### 1. 四阶检索流水线：Hybrid Search + RRF 融合

针对调度组件文档中英文术语混用的语义鸿沟，构建 **MultiQuery 查询重写 → Hybrid Search (Vector + BM25) → Reranker 精排 → 防幻觉生成** 四阶检索链路：

- **MultiQuery**：LLM 生成 3 个多角度中文搜索词 + 注入领域接口名种子词，桥接「中文提问 vs 英文接口名」的语义鸿沟
- **Hybrid Search**：FTS5 BM25 关键词精确匹配 + 向量语义泛化检索，通过 RRF（Reciprocal Rank Fusion）融合排序，兼顾精确性和召回率
- **Reranker**：Cross-encoder `bge-reranker-v2-m3` 精排 top-20→5，语义相关性精准排序
- **防幻觉**：System Prompt 显式声明「≠ XXL-Job / Quartz」+ 5 条 few-shot 示例 + RAG Prompt 强制「严格基于参考资料回答」

有效召回率从 ~40% 提升至 ~90%，跨文档覆盖从 ~20% 提升至 ~70%。

### 2. 多级容错与优雅降级

构建 **重试 → 熔断 → 回退 → 降级** 四层容错体系，任何一层失败都不会导致服务完全不可用：

- **重试**（tenacity）：LLM / Embedding 调用指数退避重试，仅重试网络类异常
- **熔断**（pybreaker）：LLM 连续失败 5 次 / Reranker 连续失败 3 次自动熔断，30s 后半开试探
- **Embedding 回退**：主 provider 不可用时自动切换备用 provider，全部失败返回零向量（配合置信度阈值兜底）
- **Reranker 降级**：熔断或 API 不可用时返回 MMR 排序结果，不中断检索
- **Celery 可选**：Redis 不可用时跳过异步摘要生成，不影响主聊天流程

### 3. 知识库版本管理

每次全量重建自动创建版本记录（文件清单 MD5 + chunk 数 + 描述），支持列表和一键回滚。管理员可在 UI 或 API 中查看历史版本并切换活跃版本，无需重新上传文档。

### 4. 真流式 Agent 与全链路可观测

从「等完整答案再逐字吐」的假流式升级为基于 `astream_events v2` 的真 token-by-token 流式，智能过滤工具调用阶段 token 只发送最终回答，首 token 延迟从 10s+ 降至 ~2s。结合 Loguru 结构化日志 + RequestId 全链路追踪 + 按日滚动文件日志，线上问题可基于请求 ID 精确回溯完整调用轨迹。

### 5. 生产就绪的运维体系

- **健康检查**：`GET /health` 返回 DB / 向量库 / LLM 组件状态 + 延迟，可用于 K8s 探针
- **限流**：slowapi 按 IP 分接口限流，防止恶意调用
- **JWT 鉴权**：Access + Refresh Token 机制，支持旧 Token 平滑迁移
- **配置热重载**：Prompt / 阈值 / 检索参数在线修改，30s 内存缓存 + 手动刷新
- **优雅停机**：关闭 HTTPX 客户端 + DB 引擎 + FTS5 连接，防止数据损坏
- **路径安全**：`Path.resolve()` + `is_relative_to()` 防止路径穿越攻击

### 6. RAG 量化评测驱动迭代

在原型阶段即引入 30 条调度场景 Golden QA 集，配套 `eval_rag.py` 评测脚本量化关键词召回率与文档达标率，每次检索策略变更可一键回归验证，将「改了检索不知道变好还是变坏」的黑盒调优转化为数据驱动的可度量迭代。

---

## :scroll: License

[MIT](LICENSE)
