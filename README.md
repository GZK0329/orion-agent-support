# 调度组件 API 文档助手

基于 LangChain + RAG + DeepSeek 的内部调度组件接口文档智能问答系统。

---

## 目录

- [调度组件 API 文档助手](#调度组件-api-文档助手)
  - [目录](#目录)
  - [项目背景](#项目背景)
  - [技术栈](#技术栈)
  - [快速开始](#快速开始)
    - [环境要求](#环境要求)
    - [配置](#配置)
    - [启动后端](#启动后端)
    - [启动前端](#启动前端)
    - [导入文档到知识库](#导入文档到知识库)
  - [开发纪要](#开发纪要)
    - [1. 知识库：分块策略演进](#1-知识库分块策略演进)
    - [2. RAG 提示词：从客服到文档助手](#2-rag-提示词从客服到文档助手)
    - [3. 检索多样性：从相似度到 MMR](#3-检索多样性从相似度到-mmr)
    - [4. Embedding 兼容性：自定义客户端](#4-embedding-兼容性自定义客户端)
    - [5. Agent 提示词：JSON 花括号转义](#5-agent-提示词json-花括号转义)
    - [6. 前端代理：Vite 反向代理遗漏](#6-前端代理vite-反向代理遗漏)
    - [7. Demo 示例问答](#7-demo-示例问答)
    - [8. 用户隔离](#8-用户隔离)
    - [9. 管理员权限](#9-管理员权限)
  - [API 概览](#api-概览)
  - [目录结构](#目录结构)

---

## 项目背景

内部调度组件有大量 API 接口文档（Swagger / Markdown），开发同学经常需要查接口地址、参数说明、请求示例。用传统 Wiki 查阅效率低，因此构建了一个基于 RAG 的智能问答助手，用自然语言直接检索文档。

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端框架 | Python 3.11 + FastAPI |
| 大模型 | DeepSeek V4 Flash（`deepseek-v4-flash`） |
| Embedding | BAAI/bge-m3（通过 SiliconFlow API 调用） |
| RAG 引擎 | LangChain 0.3.x + ChromaDB |
| Agent | LangChain `create_openai_tools_agent` |
| 前端 | React 19 + TypeScript + Vite + Tailwind CSS |
| 部署 | Docker Compose + Nginx |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- DeepSeek API Key（[申请](https://platform.deepseek.com)）
- SiliconFlow API Key（[申请](https://cloud.siliconflow.cn)）

### 配置

```bash
cp customer_service_ai/.env.example customer_service_ai/.env
```

编辑 `.env`，填入以下配置：

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-xxx` |
| `EMBEDDING_API_KEY` | SiliconFlow API Key | `sk-xxx` |
| `EMBEDDING_BASE_URL` | Embedding 服务地址 | `https://api.siliconflow.cn/v1` |
| `EMBEDDING_MODEL` | Embedding 模型 | `BAAI/bge-m3` |
| `ADMIN_PASSWORD` | 管理员密码（留空关闭管理功能） | `admin123` |

### 启动后端

```bash
cd customer_service_ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 启动前端

```bash
cd chat-ui
npm install
npm run dev
```

### 导入文档到知识库

把你的调度组件接口文档（`.md` / `.txt` / `.pdf`）放到 `customer_service_ai/data/docs/`，然后执行：

```bash
cd customer_service_ai
python scripts/ingest.py        # 全量重建
# 或
python scripts/ingest.py -i     # 增量更新（推荐日常使用）
```

---

## 开发纪要

### 1. 知识库：分块策略演进

**问题**：API 文档包含大量参数表（每行 4-5 列），初始 `chunk_size=500` 时一张表被切成 3-4 块，导致召回内容残缺，LLM 看到的参数不完整。

**操作**：

- `chunk_size`: 500 → **1500**
- `chunk_overlap`: 100 → **200**
- 分隔符保留 `["\n\n", "\n", "。", "；", " ", ""]`

**依据**：Embedding 模型为 `BAAI/bge-m3`，支持最大 8192 tokens，1500 中文字符远未达到上限，足以容纳一个完整的接口定义（含参数表 + 子结构体说明）。

**效果**：一个接口的请求参数、子 DTO、返回示例基本在一个 chunk 内完成，不再碎片化。

---

### 2. RAG 提示词：从客服到文档助手

**问题**：RAG 链路的 System Prompt 仍是"你是一名专业、友好的智能客服助手"，同时还要求"回答控制在 300 字以内"、"建议联系人工客服"——与 API 文档场景完全不匹配。

**操作**：

- 重写 `app/prompts/customer_service.py`：角色改为"调度组件接口文档助手"
- 去除字数限制和客服话术
- 增加结构化输出格式指导（接口地址、请求参数表、返回参数表、JSON 示例）

**效果**：LLM 输出从客服语气变为结构化 API 文档格式。

---

### 3. 检索多样性：从相似度到 MMR

**问题**：知识库中有 4 个文档，API 接口文档（约 73KB）占总文本量的 80%+。使用默认的 `similarity` 检索时，`top_k=6` 个结果可能全部来自同一个大文件，小文档（如扩缩容方案）的段落被完全淹没，跨文档查询命中率低。

**操作**：

- 检索方式：`similarity` → **`mmr`（最大边际相关性）**
- `top_k`: 6 → **8**
- `fetch_k`: 无 → **30**（候选池）
- `lambda_mult`: 无 → **0.5**（相关性/多样性五五开）

**MMR 原理**：先按相似度召回 `fetch_k` 个候选，再从中选择 `k` 个——每选一个，不仅看它和问题的相似度，还要看它和已选结果的差异度，确保最终结果覆盖不同的内容来源。

**效果**：8 个检索结果来自不同文件的比例显著提升，小文档内容不再被覆盖。

---

### 4. Embedding 兼容性：自定义客户端

**问题**：LangChain 的 `OpenAIEmbeddings` 会向服务商传递 `dimensions`、`user` 等参数。SiliconFlow（兼容 OpenAI 格式但不完全一致）遇到不认识参数时返回错误码 `20015`（`parameter invalid`）。

**操作**：实现 `OpenAICompatibleEmbeddings` 类（`app/services/embedding_service.py`），直接用 `openai` SDK 调用，只传 `model` 和 `input` 两个参数，不做任何多余事情。同时增加 `BATCH_SIZE=20` 分批处理。

---

### 5. Agent 提示词：JSON 花括号转义

**问题**：Agent 的 System Prompt 中包含了 JSON 示例（`{"jobName": "myJob"}`），LangChain 的 `ChatPromptTemplate` 将 `{` `}` 解析为模板占位符，运行时报错 `Input to ChatPromptTemplate is missing variables`。

**操作**：将 System Prompt 中的 `{` `}` 全部翻倍为 `{{` `}}`，LangChain 渲染时自动转回单花括号。

---

### 6. 前端代理：Vite 反向代理遗漏

**问题**：Vite dev proxy 只配置了 `/chat` 路径，未配置 `/documents` 和 `/history`，导致开发模式下文档上传和会话历史请求返回 404。

**操作**：在 `vite.config.ts` 中补充 `/documents`、`/history`、`/demos`、`/auth` 的转发规则。Docker 部署的 `nginx.conf` 同步更新。

---

### 7. Demo 示例问答

**目的**：用户在空状态时能快速了解助手能力，而不必从零开始想问题。

**操作**：

- 后端新增 `app/api/demos.py` → `GET /demos/` 返回 5 个固化的示例问答
- 前端空状态展示可点击的示例卡片，点击自动发送问题给 Agent 实时回答

**示例覆盖**：创建作业计划、查询接口列表、通用状态码、Shell 脚本作业、调度模式配置。

---

### 8. 用户隔离

**目的**：每个用户只能看到自己的对话历史，不受他人干扰。

**操作**：

- 浏览器首次访问时自动生成 `client_id`（UUID），存入 localStorage，后续所有请求携带
- `DBSession` 表新增 `client_id` 列
- `list_sessions` 和 `delete_session` 按 `client_id` 过滤
- 首次启动自动 `ALTER TABLE` 加列（兼容已有数据）

**效果**：不同浏览器 / 清缓存后互不可见历史。

---

### 9. 管理员权限

**目的**：文档上传是运维操作，不应开放给所有普通用户。

**操作**：

- `.env` 新增 `ADMIN_PASSWORD` 配置
- 后端 `POST /auth/login` 验证密码，返回 admin token
- 文档 API（`GET /documents/`、`POST /documents/upload`、`DELETE /documents/{name}`）增加 `X-Admin-Token` 校验
- 前端：未登录用户右上角显示「管理员」按钮，点击弹出密码输入框；登录成功后显示「文档管理」和「退出管理」

**效果**：普通用户无感聊天，管理员登录后可见文档管理入口。

---

## API 概览

| 端点 | 方法 | 说明 | 需管理员 |
|------|------|------|---------|
| `/chat/` | POST | 同步问答 | 否 |
| `/chat/stream` | POST | 流式问答（SSE） | 否 |
| `/history/` | GET | 获取当前用户会话列表 | 否 |
| `/history/{id}` | GET | 获取会话消息 | 否 |
| `/history/{id}` | DELETE | 删除会话 | 否 |
| `/documents/` | GET | 列出文档 | 是 |
| `/documents/upload` | POST | 上传文档 | 是 |
| `/documents/{name}` | DELETE | 删除文档 | 是 |
| `/demos/` | GET | 获取示例问答 | 否 |
| `/auth/login` | POST | 管理员登录 | - |

## 目录结构

```
agent-support/
├── customer_service_ai/        # Python 后端
│   ├── app/
│   │   ├── api/                # API 端点（chat / history / documents / demos / auth）
│   │   ├── agent/              # Agent 编排（LLM + Tool + Prompt）
│   │   ├── models/             # Pydantic Schema + SQLAlchemy ORM
│   │   ├── memory/             # 会话记忆存储（SQLAlchemy）
│   │   ├── prompts/            # System Prompt 模板
│   │   ├── services/           # RAG / LLM / Embedding 服务
│   │   └── tools/              # LangChain Tool（文档查询 / 转人工）
│   ├── data/
│   │   ├── docs/               # 知识库文档源文件
│   │   └── vector_db/          # ChromaDB 向量库
│   └── scripts/
│       └── ingest.py           # 文档导入/增量同步
├── chat-ui/                    # React 前端
│   ├── src/
│   │   ├── api/                # 后端 API 调用
│   │   ├── components/         # UI 组件
│   │   └── types/              # TypeScript 类型定义
│   └── nginx.conf              # 生产部署配置
├── docker-compose.yml          # Docker 编排
└── README.md
```
