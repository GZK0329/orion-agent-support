"""
项目配置管理
使用 Pydantic Settings，类似 Spring Boot 的 @ConfigurationProperties
读取顺序：环境变量 > .env 文件 > 默认值
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM 配置
    deepseek_api_key: str
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-v4-flash"
    llm_temperature: float = 0.7

    # Embedding 配置（DeepSeek 暂无 Embedding API，使用 OpenAI 兼容接口）
    embedding_api_key: str
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"

    # 向量库配置
    vector_db_path: str = "./data/vector_db"
    collection_name: str = "scheduling_kb"

    # 检索配置
    retrieval_top_k: int = 8
    retrieval_fetch_k: int = 30  # MMR 候选池大小
    retrieval_lambda_mult: float = 0.5  # MMR 多样性系数
    retrieval_rerank_top_k: int = 5  # 经过 Reranker 精排后保留的文档数
    retrieval_rerank_candidate_k: int = 20  # 送入 Reranker 的候选文档数

    # Hybrid Search 配置（BM25 + 向量检索融合）
    hybrid_search_enabled: bool = True  # 启用混合搜索
    hybrid_search_alpha: float = 0.3  # BM25 权重（1-alpha 为向量权重），设为 0 则纯向量，1 则纯 BM25
    hybrid_search_fetch_k: int = 40  # 每种搜索方式拉取的候选数
    hybrid_search_rrf_k: int = 60  # RRF 融合常数

    # Embedding 回退配置
    embedding_fallback_api_key: str = ""  # 回退 Embedding API 密钥，为空则跳过回退
    embedding_fallback_base_url: str = "https://api.openai.com/v1"
    embedding_fallback_model: str = "text-embedding-3-small"

    # Reranker 配置（使用与 Embedding 相同的 API 提供商）
    reranker_api_key: str = ""  # 默认复用 embedding_api_key
    reranker_base_url: str = ""  # 默认复用 embedding_base_url
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    # 缓存配置
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 缓存秒数
    cache_max_entries: int = 200

    # 置信度配置
    confidence_threshold: float = 0.5  # 低于此值标注"仅供参考"

    # 对话上下文配置
    context_max_tokens: int = 8000  # 聊天历史最大 token 数，超出后截断最旧消息

    # 数据库配置（默认 SQLite 零配置，部署可换 PostgreSQL）
    database_url: str = "sqlite:///./data/chat.db"

    # Redis 配置（任务队列 + 限流存储）
    redis_url: str = "redis://localhost:6379/0"

    # 限流配置
    rate_limit_chat: str = "30/minute"  # /chat 接口
    rate_limit_chat_stream: str = "10/minute"  # /chat/stream 接口
    rate_limit_documents: str = "5/minute"  # /documents 接口
    rate_limit_config: str = "10/minute"  # /config 接口

    # JWT 配置
    jwt_secret: str = ""  # 空则自动生成
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    # 管理员密码（为空则不开启管理员功能）
    admin_password: str = ""

    # 服务配置
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    @property
    def vector_db_dir(self) -> Path:
        return Path(self.vector_db_path).resolve()


# 全局配置实例
settings = Settings()
