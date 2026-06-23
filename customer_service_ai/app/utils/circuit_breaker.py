"""
断路器
对 LLM / Reranker API 调用做熔断保护，连续失败超阈值后快速降级
"""
import pybreaker
from loguru import logger

llm_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
)
llm_breaker.add_excluded_exception(TimeoutError)

reranker_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=30,
)
reranker_breaker.add_excluded_exception(TimeoutError)


class LogListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logger.warning(f"断路器 {cb.name}: {old_state} -> {new_state}")


llm_breaker.add_listener(LogListener())
reranker_breaker.add_listener(LogListener())
