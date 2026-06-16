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
    collection_name: str = "customer_service_kb"

    # 检索配置
    retrieval_top_k: int = 3

    # 业务 API 配置（为空时 Tool 使用 mock 数据）
    order_api_url: str = ""
    logistics_api_url: str = ""
    return_api_url: str = ""

    # 服务配置
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    @property
    def vector_db_dir(self) -> Path:
        return Path(self.vector_db_path).resolve()


# 全局配置实例
settings = Settings()
