<div align="center">

# 调度组件智能文档助手

**用自然语言查询调度系统接口文档** · 基于 RAG + DeepSeek + LangChain

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=fff)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=fff)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?logo=langchain&logoColor=fff)](https://langchain.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=fff)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[快速开始](#rocket-快速开始) · [功能特性](#sparkles-功能特性) · [技术架构](#building_construction-技术架构) · [检索流水线](#zap-检索流水线) · [API 文档](#open_book-api-文档) · [开发指南](#wrench-开发指南) · [项目亮点](#star-项目亮点) · [技术难点](#fire-技术难点)

</div>

---

## :bulb: 项目简介

为调度组件（公司内部自研的定时任务调度系统）提供智能文档问答服务。用户用中文自然语言提问，系统自动检索接口文档并生成结构化回答（接口地址、参数表、JSON 示例），解决"接口文档难查、参数描述难懂、新人上手慢"的痛点。

> ⚠️ 本项目中的「调度组件」「调度系统」均特指**公司内部自研的调度组件**，与 XXL-Job、Quartz、Elastic-Job 等开源框架无关。

---

## :rocket: 快速开始

### Docker 一键部署（推荐）

```bash
# 1. 配置 API Key
cp customer_service_ai/.env.example customer_service_ai/.env
# 编辑 .env 填入 DEEPSEEK_API_KEY 和 EMBEDDING_API_KEY

# 2. 构建并启动
./start.sh

# 3. 初始化知识库（上传文档后也可在 UI 中点"重新向量化"）
./start.sh ingest
```

打开 `http://localhost:8083`，点击右上角「管理员」→ 输入密码 →「文档管理」→ 上传调度组件文档 →「重新向量化」。

### 本地开发

```bash
# 后端
cd customer_service_ai
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端（另开终端）
cd chat-ui
npm install
npm run dev
```

打开 `http://localhost:5173`。

---

## :sparkles: 功能特性

| 功能 | 描述 |
|------|------|
| **自然语言查接口** | 用中文提问直接检索调度组件 API 文档，无需翻文档找接口 |
| **三阶检索流水线** | MultiQuery 查询重写 → MMR 多样性粗排 → Reranker 精排，检索命中率达 ~90% |
| **真流式输出** | 基于 `astream_events` 的 token-by-token SSE 流式，首 token 延迟 ~2s |
| **结构化回答** | 接口地址、请求参数表、返回参数表、JSON 示例自动格式化呈现 |
| **防幻觉护栏** | System Prompt 显式隔离开源框架知识 + few-shot 工具调用示例 |
| **RAG 量化评测** | 30 条 Golden QA + 评测脚本，检索策略变更可一键回归验证 |
| **用户反馈闭环** | 👍/👎 反馈收集 + 错误日志自动记录，管理员后台可查 |
| **管理员权限** | 文档上传/删除/重建仅管理员可见，普通用户无感聊天 |
| **用户隔离** | 每浏览器独立会话历史，互不可见 |
| **响应缓存** | 相同问题 1h 内直接返回缓存，不走 LLM，省钱又快 |

---

## :building_construction: 技术架构

```
┌──────────────┐      ┌──────────────────────────────────────────┐
│  浏览器       │      │  FastAPI 后端                             │
│  React 19     │─────▶│                                          │
│  Tailwind     │      │  ┌─────────┐  ┌──────────────────────┐  │
│  SSE 真流式   │◀─────│  │ Agent   │──│ RAG Service           │  │
│  Markdown 渲染│      │  │LangChain│  │ MultiQuery → MMR      │  │
│  反馈 👍/👎   │      │  │ 2 Tools │  │ → Reranker → Cache    │  │
└──────────────┘      │  └─────────┘  └─────────┬────────────┘  │
                      │                          │               │
                      │  ┌──────────┐  ┌────────▼─────────┐     │
                      │  │ Session  │  │  ChromaDB        │     │
                      │  │ Store    │  │  (向量库)         │     │
                      │  │ async DB │  └────────┬─────────┘     │
                      │  └──────────┘            │               │
                      │              ┌───────────▼───────────┐   │
                      │              │ Embedding (bge-m3)    │   │
                      │              │ Reranker (bge-reranker)│  │
                      │              └───────────┬───────────┘   │
                      │              ┌───────────▼───────────┐   │
                      │              │ LLM (DeepSeek V4)     │   │
                      │              └───────────────────────┘   │
                      └──────────────────────────────────────────┘
```

### 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| **前端** | React 19 + TypeScript + Tailwind CSS + Vite | SSE 流式渲染、Markdown 参数表格、反馈 UI |
| **Web 框架** | FastAPI 0.115 + Uvicorn | 异步 API、SSE 流式、全局异常处理 |
| **Agent 框架** | LangChain 0.3 | OpenAI Tools Agent、`astream_events` 真流式 |
| **检索** | MultiQueryRetriever + MMR + Cross-encoder Reranker | 三阶检索流水线 |
| **向量库** | ChromaDB | 轻量级本地向量存储 |
| **LLM** | DeepSeek V4 Flash | OpenAI 兼容 API |
| **Embedding** | BAAI/bge-m3 (SiliconFlow) | 8192 tokens 上下文，中英双语 |
| **Reranker** | BAAI/bge-reranker-v2-m3 | Cross-encoder 精排 |
| **数据库** | SQLite (async) / PostgreSQL | 会话、消息、反馈、错误日志 |
| **日志** | Loguru | 结构化日志 + request_id 全链路追踪 |

### 关键流程

```
用户提问
    │
    ▼
Agent (few-shot 引导 → 调用 search_documentation)
    │
    ▼
MultiQueryRetriever (LLM 生成 3 个中文改写 + 原问题 → 4 路并行)
    │
    ▼ (每路)
MMR 粗排 (fetch_k=50, lambda_mult=0.5, k=20)
    │
    ▼
合并去重 → Reranker 精排 (top-20 → top-5)
    │
    ▼
LLM 基于精排结果生成结构化回答 (参数表 + JSON 示例)
    │
    ▼
缓存命中？→ 直接返回 : → 存入 LRU 缓存 (TTL=1h)
```

---

## :zap: 检索流水线

### 三阶检索策略

针对调度组件文档**中英文术语混用**（用户问中文"怎么创建作业计划"，文档接口名为英文 `saveCommonJobPlan`）的语义鸿沟，构建三阶检索流水线：

| 阶段 | 策略 | 作用 |
|------|------|------|
| **1. 查询重写** | MultiQueryRetriever：LLM 生成 3 个中文搜索词 + 注入领域接口名种子词 | 桥接中英语义鸿沟，多角度覆盖 |
| **2. 粗排** | MMR（Maximal Marginal Relevance）：`fetch_k=50, lambda_mult=0.5` | 多样性优先，避免大文档吞噬小文档 |
| **3. 精排** | Cross-encoder Reranker：`bge-reranker-v2-m3`，top-20→5 | 语义相关性精准排序 |

### 防幻觉护栏

- System Prompt 显式声明"调度组件 ≠ XXL-Job/Quartz/Elastic-Job"
- 5 条 few-shot 示例教 Agent 正确调用 `search_documentation`
- RAG Prompt 强制"必须严格基于参考资料回答，不要编造接口信息"

### RAG 量化评测

```bash
cd customer_service_ai
source .venv/bin/activate
python scripts/eval_rag.py
```

基于 30 条 Golden QA（覆盖接口查询/概念解释/故障排查/配置操作），输出关键词召回率和文档达标率，每次检索策略变更可一键回归验证。

---

## :open_book: API 文档

| 端点 | 方法 | 说明 | 需管理员 |
|------|------|------|---------|
| `/chat/stream` | POST | 流式问答（主入口，SSE 真流式） | 否 |
| `/chat/` | POST | 同步问答 | 否 |
| `/history/` | GET | 当前用户的会话列表 | 否 |
| `/history/{id}` | GET | 会话消息列表 | 否 |
| `/history/{id}` | DELETE | 删除会话 | 否 |
| `/demos/` | GET | 示例问答 | 否 |
| `/feedback/` | POST | 提交 👍/👎 反馈 | 否 |
| `/auth/login` | POST | 管理员登录 | - |
| `/documents/` | GET | 文档列表 | 是 |
| `/documents/upload` | POST | 上传文档（自动导入向量库） | 是 |
| `/documents/reindex` | POST | 全量重建向量库 | 是 |
| `/documents/{name}` | DELETE | 删除文档 | 是 |
| `/error-logs/` | GET | 错误日志列表 | 是 |

---

## :wrench: 开发指南

### 环境要求

- Python 3.11+
- Node.js 18+
- Docker 20+（部署用）

### 配置说明

```bash
cp customer_service_ai/.env.example customer_service_ai/.env
```

| 环境变量 | 必填 | 说明 |
|----------|------|------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API Key |
| `EMBEDDING_API_KEY` | ✅ | Embedding API Key（SiliconFlow 等） |
| `EMBEDDING_BASE_URL` | | Embedding 服务地址 |
| `EMBEDDING_MODEL` | | Embedding 模型，默认 `text-embedding-3-small` |
| `RERANKER_MODEL` | | Reranker 模型，默认 `BAAI/bge-reranker-v2-m3` |
| `RETRIEVAL_RERANK_TOP_K` | | 精排后保留文档数，默认 5 |
| `CACHE_ENABLED` | | 响应缓存开关，默认 `true` |
| `CACHE_TTL` | | 缓存秒数，默认 3600 |
| `DATABASE_URL` | | 数据库连接，默认 SQLite |
| `ADMIN_PASSWORD` | | 管理员密码，留空则关闭管理功能 |

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
```

### 部署

```bash
./start.sh              # 构建并启动
./start.sh down         # 停止
./start.sh logs         # 查看日志
./start.sh export       # 导出 tar 包（内网部署）
./start.sh push-registry # 推送到内网镜像仓库
./start.sh status       # 查看状态
```

---

## :file_folder: 目录结构

```
agent-support/
├── customer_service_ai/            # Python 后端
│   ├── app/
│   │   ├── api/                    # FastAPI 路由（chat/history/documents/feedback/auth）
│   │   ├── agent/                  # Agent 编排（LangChain AgentExecutor + 真流式）
│   │   ├── services/               # 核心服务
│   │   │   ├── rag_service.py      #   三阶检索 + 缓存
│   │   │   ├── reranker_service.py #   Cross-encoder 精排
│   │   │   ├── llm_service.py      #   DeepSeek LLM
│   │   │   └── embedding_service.py#   bge-m3 Embedding
│   │   ├── tools/                  # LangChain Tool（search_documentation / transfer_to_human）
│   │   ├── prompts/                # Prompt 模板（防幻觉护栏 + few-shot）
│   │   ├── models/                 # SQLAlchemy ORM + Pydantic DTO
│   │   ├── memory/                 # 异步会话存储
│   │   ├── middleware.py           # RequestId 中间件
│   │   ├── utils/retry.py          # Tenacity 重试装饰器
│   │   ├── config.py               # Pydantic Settings
│   │   ├── database.py             # 异步 SQLAlchemy 引擎
│   │   └── main.py                 # FastAPI 入口 + 全局异常处理
│   ├── data/
│   │   ├── docs/                   # 文档源文件（.gitignore）
│   │   ├── vector_db/              # ChromaDB 向量库（.gitignore）
│   │   └── logs/                   # 滚动日志（.gitignore）
│   ├── scripts/
│   │   ├── ingest.py               # 文档导入（增量 + 全量）
│   │   └── eval_rag.py             # RAG 检索质量评测
│   ├── tests/                      # pytest 测试 + Golden QA 集
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── chat-ui/                        # React 前端
│   ├── src/
│   │   ├── api/                    # 后端 API 调用（SSE 流式解析）
│   │   ├── components/             # UI 组件（ChatBubble / DocManager / LoginModal）
│   │   ├── types/                  # TypeScript 类型定义
│   │   └── App.tsx                 # 主应用
│   ├── nginx.conf                  # 生产反向代理
│   ├── Dockerfile
│   └── vite.config.ts              # Vite 配置（dev proxy）
├── docker-compose.yml
├── start.sh                        # 一键部署脚本
└── README.md
```

---

## :star: 项目亮点

- **三阶检索流水线与领域 Prompt 工程**：针对调度组件文档中英文术语混用（用户问中文"怎么创建作业计划"，文档接口名为英文 `saveCommonJobPlan`）的语义鸿沟，构建 MultiQuery 查询重写（LLM 生成 3 个多角度中文搜索词 + 注入领域接口名/核心概念种子词）→ MMR 多样性粗排（候选池 20 篇）→ Cross-encoder Reranker 精排（top-20→5）三阶检索链路；System Prompt 内嵌防幻觉护栏（显式声明"调度组件 ≠ XXL-Job/Quartz"）+ 5 条 few-shot 工具调用示例，显著降低事实性幻觉与开源框架混淆问题。

- **RAG 量化评测体系与 Golden Set 驱动迭代**：在原型阶段即引入 30 条调度场景 Golden QA 集（覆盖接口查询/概念解释/故障排查/配置操作），配套 `eval_rag.py` 评测脚本量化关键词召回率与文档达标率，每次检索策略变更可一键回归验证，将"改了检索不知道变好还是变坏"的黑盒调优转化为数据驱动的可度量迭代。

- **真流式 Agent 与全链路可观测**：从"等完整答案再逐字吐"的假流式升级为基于 `AgentExecutor.astream_events(version="v2")` 的真 token-by-token 流式，过滤工具调用阶段 token 只发送最终回答，首 token 延迟从 10s+ 降至 ~2s；结合 loguru 结构化日志 + RequestIdMiddleware 全链路 request_id 注入 + 按日滚动文件日志，线上问题可基于请求 ID 精确回溯完整调用轨迹。

- **错误日志 + 用户反馈闭环**：自动捕获 LLM/Embedding 调用失败写入 `ErrorLog` 表（含 session_id、问题原文、错误信息、来源标识），管理员后台可查；前端 👍/👎 反馈写入 `MessageFeedback` 表，形成"badcase 发现 → 检索策略调优 → Golden Set 验证"的持续改进闭环。

- **异步 DB 改造与基础设施加固**：将 SQLAlchemy 从同步改为全异步（`aiosqlite` + `async_sessionmaker`），`session_store` 全方法异步化，释放 FastAPI 事件循环避免 SSE 流式期间阻塞；补齐 `pytest-asyncio` 测试体系（20 条测试覆盖 session/chat/documents/feedback/history）、tenacity 重试（LLM/Embedding 指数退避）、Agent 限步防死循环（`max_iterations=5`）、全局异常兜底统一 ErrorResponse。

- **安全加固与生产就绪**：修复路径穿越漏洞（`Path.resolve()` + `is_relative_to()` 校验）、`.env` 排除出 Docker 镜像层、nginx 补全 `/feedback/` 和 `/error-logs/` 反向代理路由；部署工具 `start.sh` 处理 ARM→x86 交叉构建、QEMU 代理清理、三种内网部署路径（tar/scp/registry），适配内网无外网环境的交付约束。

---

## :fire: 技术难点

- **中英语义对齐**：用户自然语言提问为中文，知识库接口文档为英文标识符 + 中文描述的混合体，MultiQuery 改写依赖 LLM 的翻译直觉，每次检索多一次 LLM 调用，延迟与准确率的平衡是持续挑战。

- **幻觉防控是军备竞赛**：调度组件术语（作业计划、分片、工作流）与 XXL-Job/Quartz 等开源框架高度重叠，DeepSeek 容易"张冠李戴"，每次模型版本更新都需重新验证防幻觉护栏是否仍然有效。

- **RAG 评测只能靠代理指标**：当前 `eval_rag.py` 测量的是关键词在检索文档中的召回率，而非最终回答的正确性；检索命中关键词但 LLM 误读参数表格仍可能产生错误回答，真正的端到端评测需要 LLM-as-judge 或人工标注，成本高且有噪声。

- **检索延迟与用户体验的矛盾**：MultiQuery（额外 LLM 调用 ~3s）+ Reranker（HTTP 调用 ~1s）+ 最终生成（~5s），整条链路 10-15s；真流式虽降低了首 token 延迟，但工具调用阶段用户仍在等待，需在前端用"正在查询文档…"等占位提示缓解感知延迟。

- **无状态部署 vs 有状态向量库**：ChromaDB 为文件级存储，Docker volume 挂载，水平扩展需迁移至服务化向量数据库（Qdrant/Milvus）；当前架构隐式假设单副本部署，与高可用要求存在张力。

---

## :hammer: 开发纪要

> 记录开发过程中遇到的关键问题、解法与效果。

### 检索命中率优化（40% → 90%）

**背景**：初始部署后用户反馈"问接口查不到"、"回答不完整"，分析日志发现：
- 500 字符分块把一张参数表切成 3-4 块，LLM 看到的上下文残缺
- 3 个检索结果太少，且全部来自同一个大文件
- 用户用中文问"怎么创建作业计划"，但文档写的是英文接口名，语义对不上
- 模型偶尔混入 XXL-Job 等外部知识回答

**操作**（按依赖顺序）：

| # | 操作 | 变更 |
|---|------|------|
| 0 | **Embedding 模型换型**——原 `text-embedding-3-small`（512 tokens）是分块上限瓶颈 | 切换到 `BAAI/bge-m3`，8192 tokens，为增大分块扫清障碍 |
| 1 | **分块策略调整**——`chunk_size` 500→1500, `overlap` 100→200 | 一个接口定义落在一个 chunk 内，不再碎片化 |
| 2 | **检索量提升**——`top_k` 3→8，`fetch_k=30` 候选池 | LLM 获得 8 段上下文 vs 之前 3 段，信息量 2.7× |
| 3 | **相似度→MMR**——`lambda_mult=0.5` 多样性权重 50% | 结果均匀分布在不同文档，不再被大文件淹没 |
| 4 | **查询改写**——`MultiQueryRetriever` 生成 3 个中文改写 + 原问题 | 自动补上 `jobPlan`、`createJob` 等接口名 |
| 5 | **Agent few-shot**——5 条搜索查询示例 | Agent 学会将自然语言转化为精准工具调用 |
| 6 | **RAG prompt 强化**——"必须严格基于参考资料回答" | 杜绝 LLM 混入开源框架知识 |
| 7 | **Reranker 精排**——Cross-encoder top-20→5 | 语义相关性精准排序，进一步提升准确率 |

**效果**：有效召回率从 ~40% 提升至 ~90%，跨文档覆盖从 ~20% 提升至 ~70%。

---

## :scroll: License

[MIT](LICENSE)
