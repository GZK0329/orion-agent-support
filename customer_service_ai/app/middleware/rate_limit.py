"""
限流中间件
基于 slowapi，每个 IP 按接口类型做速率限制
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
