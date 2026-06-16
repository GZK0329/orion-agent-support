# 智能客服助手（LangChain + RAG + DeepSeek）

一个简单的智能客服 Demo，基于：
- **LangChain** 编排 LLM 调用
- **RAG** 检索增强生成，让回答基于你的文档
- **DeepSeek** 作为对话大模型
- **ChromaDB** 作为本地向量数据库
- **FastAPI** 提供 Web API

## 项目结构

```
customer_service_ai/
├── app/                      # 应用核心代码
│   ├── api/chat.py           # /chat 接口
│   ├── config.py             # 配置管理
│   ├── main.py               # FastAPI 入口
│   ├── models/schemas.py     # 请求/响应模型
│   ├── prompts/              # Prompt 模板
│   └── services/             # 业务服务层
│       ├── llm_service.py    # DeepSeek LLM
│       ├── embedding_service.py  # Embedding 模型
│       └── rag_service.py    # RAG 检索+生成
├── data/
│   └── docs/                 # 放你的知识库文档
├── scripts/
│   ├── ingest.py             # 导入文档到向量库
│   └── ask.py                # 命令行问答测试
├── .env.example              # 环境变量示例
└── requirements.txt          # Python 依赖
```

## 快速开始

### 1. 准备环境

```bash
# 创建虚拟环境（项目根目录）
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp customer_service_ai/.env.example customer_service_ai/.env
```

编辑 `customer_service_ai/.env`，填入：

```env
# DeepSeek 对话模型（必填）
# 官方模型名见：https://platform.deepseek.com/api-docs/zh-cn/quick_start/model_capabilities
# 当前推荐：deepseek-v4-flash / deepseek-v4-pro
# 注意：base_url 没有 /v1 后缀
DEEPSEEK_API_KEY=your_deepseek_api_key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash

# Embedding 模型（必填，DeepSeek 暂无 Embedding API）
# 方案 1：OpenAI
EMBEDDING_API_KEY=your_openai_api_key
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small

# 方案 2：硅基流动（国内推荐，更便宜）
# EMBEDDING_API_KEY=your_siliconflow_key
# EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
# EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
```

### 3. 放入知识库文档

把你的文档放到 `customer_service_ai/data/docs/`，支持 `.txt`、`.md`、`.pdf`。

项目已自带一份 `sample_faq.txt` 示例文档，可直接测试。

### 4. 导入文档到向量库

```bash
cd customer_service_ai
source ../.venv/bin/activate
python scripts/ingest.py
```

### 5. 启动 API 服务

```bash
cd customer_service_ai
source ../.venv/bin/activate
uvicorn app.main:app --reload
```

服务启动后访问：
- 健康检查：http://127.0.0.1:8000/
- API 文档：http://127.0.0.1:8000/docs

### 6. 测试对话

**方式一：命令行**

```bash
cd customer_service_ai
source ../.venv/bin/activate
python scripts/ask.py
```

**方式二：curl**

```bash
curl -X POST "http://127.0.0.1:8000/chat/" \
  -H "Content-Type: application/json" \
  -d '{"question": "支持 7 天无理由退货吗？"}'
```

## 关键设计说明

1. **为什么 DeepSeek 用 OpenAI 兼容方式调用？**
   DeepSeek 的 API 完全兼容 OpenAI SDK，所以使用 `langchain-openai` 的 `ChatOpenAI`，只需替换 `base_url` 和 `api_key`。
   注意：DeepSeek 官方 `base_url` 是 `https://api.deepseek.com`（没有 `/v1`），模型名当前推荐 `deepseek-v4-flash` 或 `deepseek-v4-pro`，`deepseek-chat` 将于 2026/07/24 弃用。

2. **Embedding 怎么配？**
   DeepSeek 目前不提供 Embedding 接口。推荐：
   - OpenAI：`text-embedding-3-small`
   - 硅基流动：`BAAI/bge-large-zh-v1.5`

3. **向量库存在哪里？**
   默认存在 `customer_service_ai/data/vector_db/`，ChromaDB 本地持久化。

## 下一步可扩展

- [ ] 接入 MySQL/Redis 保存对话历史
- [ ] 增加 Agent + 工具（查订单、查物流、转人工）
- [ ] 用 Milvus/Pinecone 替换本地 ChromaDB
- [ ] 接入 Streamlit/Gradio 做管理后台
- [ ] 增加单元测试和异常监控
