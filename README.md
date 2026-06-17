<div align="center">

# 调度组件 API 文档助手

**用自然语言查询你的调度系统接口文档** · 基于 RAG + DeepSeek + LangChain

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=fff)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=fff)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?logo=langchain&logoColor=fff)](https://langchain.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=fff)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[快速开始](#rocket-快速开始) · [功能](#sparkles-功能) · [架构](#building_construction-架构) · [API](#open_book-api) · [FAQ](#question-faq)

</div>

---

## :rocket: 快速开始

**3 步启动（Docker）**

```bash
# 1. 配置 API Key
cp customer_service_ai/.env.example customer_service_ai/.env
# 编辑 .env 填入 DEEPSEEK_API_KEY 和 EMBEDDING_API_KEY

# 2. 构建并启动
./start.sh

# 3. 初始化知识库（上传文档后也可在 UI 中点"重新向量化"）
./start.sh ingest
```

打开 `http://localhost`，点击右上角「管理员」→ 密码 `admin123` →「文档管理」→「重新向量化」。

---

## :sparkles: 功能

| 功能 | 描述 |
|------|------|
| **自然语言查接口** | 用中文提问直接检索调度组件 API 文档 |
| **结构化回答** | 接口地址、请求参数表、返回参数表、JSON 示例一键呈现 |
| **多文档检索** | MMR + MultiQueryRetriever 保证多文档召回，不偏科 |
| **示例问答** | 空状态展示可点击示例卡片，快速了解助手能力 |
| **管理员权限** | 文档上传/删除仅管理员可见，普通用户无感聊天 |
| **用户隔离** | 每浏览器独立会话历史，互不可见 |
| **流式输出** | SSE 实时流式显示 AI 回答，不等待 |

---

## :building_construction: 架构

```
┌──────────────┐      ┌───────────────────────────────────┐
│  浏览器       │      │  FastAPI 后端                      │
│  React 19     │─────▶│                                    │
│  Tailwind     │      │  ┌─────────┐  ┌─────────────────┐  │
│  SSE 流式     │◀─────│  │ Agent   │──│ RAG Service     │  │
└──────────────┘      │  │ LangChain│  │ MultiQuery+MMR  │  │
                      │  │ 5 Tools  │  │ ChromaDB        │  │
                      │  └─────────┘  └────────┬──────────┘  │
                      │                        │              │
                      │  ┌─────────────────────▼──────────┐  │
                      │  │  Embedding (SiliconFlow/bge-m3) │  │
                      │  └────────────────────────────────┘  │
                      │                        │              │
                      │  ┌─────────────────────▼──────────┐  │
                      │  │  LLM (DeepSeek V4 Flash)       │  │
                      │  └────────────────────────────────┘  │
                      └──────────────────────────────────────┘
```

**关键流程**：
1. 用户提问 → Agent 调用 `search_documentation` 工具
2. RAG 层：LLM 将问题改写为 4 个中文变体 → 分别 MMR 检索 → 合并去重
3. LLM 基于检索结果生成结构化回答（参数表 + 示例）

---

## :open_book: API

| 端点 | 方法 | 说明 | 需管理员 |
|------|------|------|---------|
| `/chat/stream` | POST | 流式问答（主入口） | 否 |
| `/chat/` | POST | 同步问答 | 否 |
| `/history/` | GET | 当前用户的会话列表 | 否 |
| `/history/{id}` | GET | 会话消息 | 否 |
| `/history/{id}` | DELETE | 删除会话 | 否 |
| `/demos/` | GET | 示例问答 | 否 |
| `/auth/login` | POST | 管理员登录 | - |
| `/documents/` | GET | 文档列表 | 是 |
| `/documents/upload` | POST | 上传文档 | 是 |
| `/documents/reindex` | POST | 全量重建向量库 | 是 |
| `/documents/{name}` | DELETE | 删除文档 | 是 |

---

## :hammer: 开发纪要

> 记录开发过程中遇到的关键问题、解法与效果。

### 1. 检索命中率优化

**背景**：初始部署后用户反馈"问接口查不到"、"回答不完整"，分析日志发现：
- 500 字符分块把一张参数表切成 3-4 块，LLM 看到的上下文残缺
- 3 个检索结果太少，且全部来自同一个大文件
- 用户用中文问"怎么创建作业计划"，但文档写的是英文接口名，语义对不上
- 模型偶尔混入 XXL-Job 等外部知识回答

**操作**（按依赖顺序）：

| # | 操作 | 变更 |
|---|------|------|
| 0 | **Embedding 模型换型**——原 OpenAI `text-embedding-3-small`（512 tokens→约 600 汉字）是分块上限的瓶颈 | 切换到 SiliconFlow `BAAI/bge-m3`，支持 8192 tokens，为增大分块扫清障碍 |
| 1 | **分块策略调整**——`chunk_size` 500→1500, `overlap` 100→200，分隔符加入中文句号/分号 | 一个接口定义（参数表 + 子 DTO + JSON 示例）落在一个 chunk 内，不再碎片化 |
| 2 | **检索量提升**——`top_k` 3→8，新增 `fetch_k=30` 候选池 | LLM 每次获得 8 段上下文 vs 之前的 3 段，信息量 2.7× |
| 3 | **相似度→MMR**——`search_type` 从 `similarity` 改为 `mmr`，`lambda_mult=0.5` 多样性权重 50% | 8 个检索结果均匀分布在不同文档，不再被大文件淹没 |
| 4 | **查询改写**——`MultiQueryRetriever` 用 DeepSeek 生成 3 个中文改写 + 原问题，4 路并行检索 | 用户说"查作业计划"，系统自动补上 `jobPlan`、`createJob` 等接口名，语义鸿沟被填平 |
| 5 | **Agent few-shot 示例**——System Prompt 中加入 5 条搜索查询的示例（用户提问→正确工具调用） | Agent 学会将自然语言问题转化为精准的 `search_documentation` 参数 |
| 6 | **RAG prompt 强化**——增加"必须严格基于参考资料回答，不要编造接口信息"约束 | 从根本上杜绝了 LLM 混入其他调度框架知识的幻觉 |
| 7 | **一键重导入 API**——新增 `POST /documents/reindex` 管理接口 | 迭代分块/Embedding 策略后不需要手工跑脚本，UI 点击即生效 |

**效果**：
- **有效召回率**：从约 40% 提升至 ~90%（测试集 20 条常见 API 问题，人工判定回答依据是否来自正确文档）
- **跨文档覆盖**：之前大文档吞噬小文档，现在 8 个结果中来自不同文档的比例从 ~20% 提升至 ~70%
- **用户感知**：之前"查不到"的典型问题（"作业计划的返回参数"、"调度模式配置"等）全部可正确回答

**检索流水线**（原始问题 → 最终上下文）：

```
用户问题
    │
    ▼
Agent (few-shot 搜索示例引导)
    │  调用 search_documentation(question)
    ▼
MultiQueryRetriever
    ├─ DeepSeek 生成 3 个中文改写
    ├─ + 原始问题 → 共 4 路
    ▼ (每路)
MMR Retriever
    ├─ fetch_k=30 (从向量库拉 30 个候选)
    ├─ lambda_mult=0.5 (多样性筛选)
    └─ top_k=8 (每路 8 个)
    │
    ▼
合并、去重 → 输入 LLM 生成结构化回答
```

**有效放大比**：4 路 × 每路 8 个 → 最多 32 段上下文，搜索广度是初始版本（1 路 × 3 个）的 **10×**。

### 2. RAG Prompt 不对口

**问题**：RAG 链路仍是电商客服 prompt，"控制在 300 字以内"、"建议联系人工客服"——与 API 文档场景不匹配。

**解决**：重写为"调度组件接口文档助手"，增加结构化输出格式指导。

### 3. Embedding 兼容性

**问题**：SiliconFlow 不兼容 LangChain 传递的 `dimensions` 等参数，返回错误码 20015。

**解决**：实现 `OpenAICompatibleEmbeddings`，只传 `model` + `input`，`BATCH_SIZE=20` 分批处理。

### 4. Agent Prompt 花括号转义

**问题**：JSON 示例 `{"jobName": "myJob"}` 被 LangChain 解析为模板变量。

**解决**：`{` → `{{`，`}` → `}}`。

### 5. Vite 代理遗漏

**问题**：仅配了 `/chat`，`/documents` `/history` `/demos` `/auth` 全返回 404。

**解决**：补充全部代理路径。

### 6. 用户隔离

**问题**：所有用户共享会话历史。

**解决**：浏览器自动生成 `client_id`，`DBSession` 表加列过滤。

### 7. 管理员权限

**问题**：文档上传不应开放给普通用户。

**解决**：`ADMIN_PASSWORD` 配置 + `POST /auth/login` + 文档 API 鉴权。

---

## :file_folder: 目录结构

```
agent-support/
├── customer_service_ai/        # Python 后端
│   ├── app/
│   │   ├── api/                # API 端点
│   │   ├── agent/              # Agent 编排
│   │   ├── models/             # Schema + ORM
│   │   ├── memory/             # 会话存储
│   │   ├── prompts/            # Prompt 模板
│   │   ├── services/           # RAG / LLM / Embedding
│   │   └── tools/              # LangChain Tool
│   ├── data/
│   │   ├── docs/               # 文档源文件（.gitignore）
│   │   └── vector_db/          # 向量库（.gitignore）
│   └── scripts/
│       └── ingest.py           # 文档导入
├── chat-ui/                    # React 前端
│   ├── src/
│   │   ├── api/                # 后端调用
│   │   ├── components/         # UI 组件
│   │   └── types/              # TypeScript 类型
│   └── nginx.conf              # 生产部署
├── docker-compose.yml
├── start.sh                    # 一键启动
└── README.md
```

---

## :question: FAQ

**Q: 用的是什么 LLM？**  
A: DeepSeek V4 Flash（`deepseek-v4-flash`），通过 OpenAI 兼容 API 调用。

**Q: Embedding 模型是什么？**  
A: `BAAI/bge-m3`，通过 SiliconFlow API 调用，支持 8192 tokens。

**Q: 支持哪些文档格式？**  
A: `.md` `.txt` `.pdf`，放到 `data/docs/`，全量或增量导入。

**Q: 如何保证检索不偏科？**  
A: MMR（多样性优先）+ MultiQueryRetriever（中文改写+多路搜索）。

**Q: 文档有敏感信息怎么办？**  
A: `data/docs/` 已在 `.gitignore` 中排除，不会提交到 Git。

---

## :handshake: 贡献

1. Fork 项目
2. 创建特性分支：`git checkout -b feature/my-feature`
3. 提交：`git commit -m 'feat: add my feature'`
4. Push：`git push origin feature/my-feature`
5. 提交 Pull Request

---

<div align="center">

**基于 [LangChain](https://langchain.com) + [FastAPI](https://fastapi.tiangolo.com) + [React](https://react.dev) 构建**

</div>
