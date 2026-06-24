# 调度组件智能文档助手 — 全量功能交付 PR

> **分支:** `feat-improve-rag` → `master`
> **变更:** 61 files · +3,305 / −647 lines · 3 commits
> **状态:** ✅ 已构建 & 已测试 & 已部署验证

---

## 概述

从原型阶段（单检索 + 假流式）升级为具备**生产级可观测性、弹性容错、混合检索增强、全链路安全防护**的智能问答系统。

---

## 变更列表

### Phase 1 — 基础设施加固

| 变更 | 文件 |
|------|------|
| Pytest 测试体系（24 条用例） | `tests/` |
| Loguru 结构化日志 + RequestId 链路追踪 | `app/middleware/` |
| 全局异常处理（统一 ErrorResponse + request_id） | `app/main.py` |
| Tenacity 重试（LLM / Embedding 指数退避） | `app/utils/retry.py` |
| 异步 DB（aiosqlite + async_sessionmaker） | `app/database.py` |
| Agent 限步防死循环（max_iterations=5） | `app/agent/agent_service.py` |
| CI/CD pipeline（GitHub Actions） | `.github/workflows/ci.yml` |

### Phase 2+3 — 检索质量升级 & 体验优化

| 变更 | 文件 |
|------|------|
| MultiQuery 查询重写（LLM 生成 3 变体 + 原问题） | `app/services/rag_service.py` |
| MMR 多样性粗排（lambda_mult=0.5） | `app/services/rag_service.py` |
| Reranker 精排（bge-reranker-v2-m3） | `app/services/reranker_service.py` |
| 响应缓存（LRU + TTL 3600s） | `app/services/rag_service.py` |
| RAG 量化评测（30 条 Golden QA） | `scripts/eval_rag.py`, `tests/golden_set.json` |
| 真流式（astream_events v2，智能过滤中间 token） | `app/agent/agent_service.py` |
| 配置热重载（AgentConfig DB 表 + 30s 缓存） | `app/services/config_service.py`, `app/api/config.py` |
| 对话摘要 + 上下文恢复 | `app/memory/session_store.py` |
| CI/CD 完善 + README 重写 | 全域 |

### Phase 4 — 生产加固

| 变更 | 文件 |
|------|------|
| **限流（slowapi）** — 按 IP 分接口限流 | `app/middleware/rate_limit.py` |
| **熔断（pybreaker）** — LLM / Reranker 独立熔断 | `app/utils/circuit_breaker.py` |
| **JWT 鉴权** — Access (30min) + Refresh (7d) Token | `app/api/auth.py` |
| **Celery 异步任务** — Redis broker，对话摘要生成 | `app/celery_app.py`, `app/tasks/summary_task.py` |
| **健康检查** — `/health` DB/向量库/LLM 状态 | `app/api/health.py` |
| **优雅停机** — 关闭 httpx + DB + FTS5 | `app/main.py` |
| **审计日志** — 管理员操作全程记录 | `app/models/db_models.py` |

### Phase 5 — 检索增强

| 变更 | 文件 |
|------|------|
| **Hybrid Search** — FTS5 BM25 + 向量检索 RRF 融合 | `app/services/fts_service.py`, `app/services/rag_service.py` |
| **Embedding 回退** — primary → fallback → zero-vector | `app/services/embedding_service.py` |
| **知识库版本管理** — create / list / rollback | `app/models/db_models.py`, `app/api/documents.py` |

### 前端重构

| 变更 | 文件 |
|------|------|
| Dark/geek 主题（#07080e 底色、紫色渐变） | `index.css`, `tailwind.config.js` |
| lucide-react 图标替换 CLI `$` 前缀 | `App.tsx`, `ChatBubble.tsx`, `DocManager.tsx`, `LoginModal.tsx` |
| 全界面中文化 | 所有组件 |
| 流式渲染 + Markdown 表格适配 | `MarkdownRender.tsx` |
| Nginx 动态 DNS 解析（resolver + proxy_pass 变量） | `nginx.conf` |
| 新示例问题（历史指标重跑） | `app/api/demos.py` |

---

## 关键设计决策

### 检索流水线：四阶融合

```
MultiQuery(4 queries) → Hybrid Search (Vector + FTS5 BM25 → RRF)
  → Reranker (top-20→5) → LLM Generation + Confidence Labeling
```

**为什么 RRF 替代 MMR？** MMR 由 ChromaDB 内置实现，与自定义 Hybrid Search 不兼容。RRF 公式 `score(d) = 1/(k+rank_v(d)) + 1/(k+rank_b(d))` 无需额外向量计算，兼顾精确性和多样性。

**为什么 FTS5？** SQLite 内置，零额外依赖。`porter unicode61` 分词器支持中文 + 英文词干，WAL 模式支持并发读。

### 多级容错体系

```
Tenacity Retry → Pybreaker → Fallback Provider → Zero-Vector Degradation → Error Log
```

每一层都是独立可选的，失败不会级联。Celery 和 Redis 也是可选的——无 Redis 时核心聊天功能完全不受影响。

### 版本管理：元数据优先

知识库版本仅记录文件清单和 chunk 数，不复制 ChromaDB 数据。回滚是切换 `is_active` 标记，实际回溯需手动 reindex。这是权衡存储成本和功能粒度的决定——对于文档数量 < 100 的场景，reindex 耗时 < 5s，完全可接受。

### Embedding 回退：仅浪费

`EMBEDDING_FALLBACK_API_KEY` 为空时 `get_embedding_model()` 直接返回 primary provider，零开销。配置后才激活 `EmbeddingFallback` 包装器。

---

## 验证结果

### 本地测试

```bash
# 后端
pytest tests/ -v    # 24 tests passed
uvicorn app.main:app --reload --port 8000

# 前端
npm run build       # tsc + vite build 通过
npm run dev
```

### Docker 验证

```bash
docker compose build   # 后端 + 前端镜像构建成功
docker compose up -d   # 4 服务全部启动
curl http://localhost:8000/health  # 200 OK

# 流式问答
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"如何创建作业计划"}'  # SSE 正常 stream

# 文档重建 + 版本管理
curl -X POST http://localhost:8000/documents/reindex \
  -H "X-Admin-Token: <token>"  # 返回 version_id
curl http://localhost:8000/documents/versions \
  -H "X-Admin-Token: <token>"  # 列出版本
```

### 检索质量

有效召回率 ~90%（基于 30 条 Golden QA 评测），跨文档覆盖 ~70%。

---

## 风险与待确认

| 风险 | 影响 | 缓解 |
|------|------|------|
| ChromaDB 无内置用户认证 | 内网环境安全 | Nginx 反向代理 + IP 白名单 |
| FTS5 索引与 ChromaDB 需保持同步 | 数据不一致 | `delete_by_source()` 和 `add_documents()` 始终双写 |
| 版本回滚不自动重建索引 | 版本元数据和实际索引不匹配 | README 已注明需手动 reindex |
| 💡 Docker Desktop 代理问题 | Mac 无法 pull 外部镜像 | `start.sh` 自动清理代理 env，Redis 镜像需手动 load |

---

## 后续规划

1. **OpenTelemetry 链路追踪** + Prometheus 指标
2. **Hybrid Search 参数自动调优**（基于 Golden QA 反馈）
3. **Makefile** 统一命令 + pre-commit hooks
4. **Helm chart** K8s 部署清单
5. **函数调用 / Tool-use** 结构化输出
