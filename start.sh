#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# 加载 .env 中的变量（如 REGISTRY_URL）
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

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

# 在 Mac 本地原生编译前端（避免 QEMU 下 npm 崩溃）
_build_frontend() {
  echo "🏗️  编译前端（本地原生）..."
  cd chat-ui
  npm install --silent
  npm run build
  cd ..
  echo "✅ 前端编译完成"
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
    _build_frontend
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
      _build_frontend
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
    _build_frontend
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
  export)
    _build_frontend
    _clear_docker_proxy
    echo "📦 构建镜像并导出 tar..."
    docker compose build
    _restore_docker_proxy
    mkdir -p /tmp/agent-support-images
    docker save "${REGISTRY_URL:-}agent-support-backend:latest" -o /tmp/agent-support-images/backend.tar
    docker save "${REGISTRY_URL:-}agent-support-frontend:latest" -o /tmp/agent-support-images/frontend.tar
    echo "✅ 已导出："
    ls -lh /tmp/agent-support-images/
    echo ""
    echo "部署到开发服务器（二选一）："
    echo ""
    echo "  方式 A — 上传服务："
    echo "    服务器: python3 upload_server.py 8080 /opt/agent-support"
    echo "    浏览器访问 http://server-ip:8080 上传 backend.tar、frontend.tar、docker-compose.yml、.env"
    echo "    然后 ssh 登录服务器: cd /opt/agent-support && docker load -i backend.tar && docker load -i frontend.tar && docker compose up -d"
    echo ""
    echo "  方式 B — scp："
    echo "    scp -r /tmp/agent-support-images user@server:/tmp/"
    echo "    scp docker-compose.yml customer_service_ai/.env user@server:/opt/agent-support/"
    echo "    ssh user@server"
    echo "    docker load -i /tmp/agent-support-images/backend.tar"
    echo "    docker load -i /tmp/agent-support-images/frontend.tar"
    echo "    cd /opt/agent-support && docker compose up -d"
    echo ""
    echo "  方式 C — 内网 registry："
    echo "    .env 中设置 REGISTRY_URL=<your-registry>:5000/"
    echo "    ./start.sh push-registry"
    ;;
  push-registry)
    if [ -z "${REGISTRY_URL:-}" ]; then
      echo "❌ 请先在 .env 中设置 REGISTRY_URL，例如："
      echo "   REGISTRY_URL=10.0.0.1:5000/"
      exit 1
    fi
    _build_frontend
    _clear_docker_proxy
    echo "🚀 构建并推送镜像到 ${REGISTRY_URL}..."
    docker compose build
    docker push "${REGISTRY_URL}agent-support-backend:latest"
    docker push "${REGISTRY_URL}agent-support-frontend:latest"
    _restore_docker_proxy
    echo "✅ 推送完成！"
    echo ""
    echo "开发服务器上操作："
    echo "  1. 确保 /etc/docker/daemon.json 配置了 insecure-registries: [\"${REGISTRY_URL%/}\"]"
    echo "  2. 上传 docker-compose.yml 和 customer_service_ai/.env 到 /opt/agent-support/"
    echo "  3. cd /opt/agent-support && docker compose up -d"
    ;;
  dev)
    echo "🚀 启动本地开发环境..."
    echo ""
    set +e

    # 清理旧后端进程
    OLD_PIDS=$(lsof -ti :8000 -sTCP:LISTEN 2>/dev/null) || true
    if [ -n "$OLD_PIDS" ]; then
      echo "⚠️  端口 8000 已被占用，正在清理旧进程 (PID: $OLD_PIDS)..."
      kill $OLD_PIDS 2>/dev/null
      sleep 1
      # 如果没杀掉，强制 kill
      STILL=$(lsof -ti :8000 -sTCP:LISTEN 2>/dev/null) || true
      if [ -n "$STILL" ]; then
        kill -9 $STILL 2>/dev/null || true
      fi
    fi

    # 后端: 创建 venv + 安装依赖 + 启动
    BACKEND_DIR="customer_service_ai"
    if [ ! -d "$BACKEND_DIR/.venv" ]; then
      echo "📦 创建 Python venv..."
      python3 -m venv "$BACKEND_DIR/.venv"
    fi
    echo "📦 安装 Python 依赖..."
    "$BACKEND_DIR/.venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt" --quiet
    echo "🟢 启动后端 (uvicorn --reload :8000)..."
    PREV_DIR=$(pwd)
    cd "$BACKEND_DIR"
    .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd "$PREV_DIR"

    # 等待后端就绪
    for i in $(seq 1 10); do
      if curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
        break
      fi
      sleep 1
    done
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
      echo "❌ 后端启动失败，请检查端口冲突"
      exit 1
    fi

    # 前端: 安装依赖 + 启动
    echo "🟢 启动前端 (Vite dev server :5173)..."
    cd chat-ui
    npm install --silent
    npm run dev &
    FRONTEND_PID=$!
    cd ..

    echo ""
    echo "✅ 本地开发环境已启动"
    echo "   后端: http://localhost:8000  (热重载)"
    echo "   前端: http://localhost:5173  (热重载，API 代理到 8000)"
    echo ""
    echo "按 Ctrl+C 停止"

    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo ''; echo '🛑 已停止'; exit" SIGINT SIGTERM
    wait
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
  echo "  dev       本地开发环境（uvicorn --reload + Vite dev server）"
  echo "  export    构建并导出 tar，供服务器 docker load"
  echo "  push-registry  推送到 .env 中 REGISTRY_URL 指定的内网仓库"
    ;;
esac
