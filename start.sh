#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

DOCKER_CONFIG="$HOME/.docker/config.json"

# 构建时临时清除 Docker Desktop 全局代理，避免阻断容器内网络
_clear_docker_proxy() {
  if [ -f "$DOCKER_CONFIG" ]; then
    python3 -c "
import json
with open('$DOCKER_CONFIG') as f:
    cfg = json.load(f)
saved = cfg.pop('proxies', None)
if saved:
    with open('$DOCKER_CONFIG', 'w') as f:
        json.dump(cfg, f, indent=2)
    import os
    with open('/tmp/.docker_proxy_backup', 'w') as f:
        json.dump(saved, f)
    print('Docker proxy cleared')
" 2>&1 || true
  fi
}

_restore_docker_proxy() {
  if [ -f "/tmp/.docker_proxy_backup" ]; then
    python3 -c "
import json
with open('$DOCKER_CONFIG') as f:
    cfg = json.load(f)
with open('/tmp/.docker_proxy_backup') as f:
    proxy = json.load(f)
cfg['proxies'] = proxy
with open('$DOCKER_CONFIG', 'w') as f:
    json.dump(cfg, f, indent=2)
print('Docker proxy restored')
" 2>&1 || true
    rm -f /tmp/.docker_proxy_backup
  fi
}

CMD="${1:-up}"

trap _restore_docker_proxy EXIT

case "$CMD" in
  up)
    _clear_docker_proxy
    echo "🚀 构建并启动调度组件助手..."
    docker compose build
    docker compose up -d
    _restore_docker_proxy
    echo "✅ 启动完成！浏览器打开 http://localhost"
    echo ""
    echo "首次使用请执行以下操作初始化知识库："
    echo "  方式 A：管理员登录 → 文档管理 → 点「重新向量化」"
    echo "  方式 B：./start.sh ingest"
    ;;
  down)
    echo "🛑 停止服务..."
    docker compose down
    echo "✅ 已停止"
    ;;
  restart)
    if docker compose ps --quiet 2>/dev/null | grep -q .; then
      echo "🔄 重启服务..."
      docker compose restart
      echo "✅ 已重启"
    else
      _clear_docker_proxy
      echo "⚠️  没有运行中的容器，直接启动..."
      docker compose build
      docker compose up -d
      _restore_docker_proxy
      echo "✅ 启动完成！浏览器打开 http://localhost"
    fi
    ;;
  logs)
    docker compose logs -f
    ;;
  ingest)
    echo "📚 初始化知识库（从 data/docs/ 构建向量库）..."
    docker compose exec backend python scripts/ingest.py
    echo "✅ 知识库初始化完成"
    ;;
  rebuild)
    _clear_docker_proxy
    echo "🏗️  重建镜像并启动..."
    docker compose build --no-cache
    docker compose up -d
    _restore_docker_proxy
    echo "✅ 完成"
    ;;
  status)
    docker compose ps
    ;;
  shell)
    docker compose exec backend /bin/bash
    ;;
  *)
    echo "用法: ./start.sh [命令]"
    echo ""
    echo "命令:"
    echo "  up        构建并启动（默认）"
    echo "  down      停止服务"
    echo "  restart   重启服务"
    echo "  logs      查看日志"
    echo "  ingest    初始化知识库"
    echo "  rebuild   强制重建镜像并启动"
    echo "  status    查看服务状态"
    echo "  shell     进入后端容器"
    ;;
esac
