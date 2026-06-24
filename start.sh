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

# 判断是否在 ARM Mac 上
_IS_ARM=false
if [[ "$(uname -m)" == "arm64" ]]; then
  _IS_ARM=true
fi

DC_FILES=("-f" "docker-compose.yml")
# 主动要求 x86 构建时（如推送到 x86 服务器），加上 x86 override
if [ "${FORCE_X86:-}" == "true" ] || [ "$1" == "push-registry" ]; then
  DC_FILES+=("-f" "docker-compose.x86.yml")
fi

_DC="docker compose ${DC_FILES[*]}"

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
  up|up-x86)
    if [ "$CMD" == "up-x86" ]; then
      FORCE_X86=true
    fi
    _build_frontend
    _clear_docker_proxy
    echo "🚀 构建并启动..."
    if [ "${FORCE_X86:-false}" == "true" ]; then
      echo "   架构: x86 (linux/amd64)"
      docker compose -f docker-compose.yml -f docker-compose.x86.yml build
      docker compose -f docker-compose.yml -f docker-compose.x86.yml up -d
    else
      echo "   架构: 自动 (本机架构)"
      docker compose build
      docker compose up -d
    fi
    _restore_docker_proxy
    echo "✅ 启动完成！浏览器打开 http://localhost:8083"
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
      echo "✅ 启动完成！浏览器打开 http://localhost:8083"
    fi
    ;;
  logs)
    docker compose logs -f
    ;;
  ingest)
    echo "📚 初始化知识库..."
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
  dev)
    echo "🚀 启动本地开发环境..."
    echo ""
    set +e

    OLD_PIDS=$(lsof -ti :8000 -sTCP:LISTEN 2>/dev/null) || true
    if [ -n "$OLD_PIDS" ]; then
      echo "⚠️  端口 8000 已被占用，正在清理旧进程 (PID: $OLD_PIDS)..."
      kill $OLD_PIDS 2>/dev/null
      sleep 1
      STILL=$(lsof -ti :8000 -sTCP:LISTEN 2>/dev/null) || true
      if [ -n "$STILL" ]; then
        kill -9 $STILL 2>/dev/null || true
      fi
    fi

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
  export)
    _build_frontend
    _clear_docker_proxy
    echo "📦 构建 x86 镜像并导出 tar..."
    docker compose -f docker-compose.yml -f docker-compose.x86.yml build
    _restore_docker_proxy
    mkdir -p /tmp/agent-support-images
    # 确保第三方依赖镜像为 x86 架构
    docker pull --platform linux/amd64 bitnami/redis:latest 2>&1 | tail -3
    # 导出所有服务镜像（含 redis 等第三方镜像）
    docker save \
      "${REGISTRY_URL:-}agent-support-backend:latest" \
      "${REGISTRY_URL:-}agent-support-frontend:latest" \
      bitnami/redis:latest \
      -o /tmp/agent-support-images/all-images.tar
    echo "✅ 已导出："
    ls -lh /tmp/agent-support-images/
    echo ""
    echo "部署到服务器："
    echo ""
    echo "  scp /tmp/agent-support-images/all-images.tar user@server:/tmp/"
    echo "  scp docker-compose.yml docker-compose.x86.yml customer_service_ai/.env user@server:/opt/agent-support/"
    echo "  ssh user@server"
    echo "  docker load -i /tmp/all-images.tar"
    echo "  cd /opt/agent-support && docker compose -f docker-compose.yml -f docker-compose.x86.yml up -d"
    ;;
  push-registry)
    if [ -z "${REGISTRY_URL:-}" ]; then
      echo "❌ 请先在 .env 中设置 REGISTRY_URL，例如："
      echo "   REGISTRY_URL=10.0.0.1:5000/"
      exit 1
    fi
    _build_frontend
    _clear_docker_proxy
    echo "🚀 构建 x86 镜像并推送到 ${REGISTRY_URL}..."
    docker compose -f docker-compose.yml -f docker-compose.x86.yml build
    # 推送自建镜像
    docker push "${REGISTRY_URL}agent-support-backend:latest"
    docker push "${REGISTRY_URL}agent-support-frontend:latest"
    # 推送第三方依赖镜像（确保 x86 架构）
    docker pull --platform linux/amd64 bitnami/redis:latest 2>&1 | tail -1
    docker tag bitnami/redis:latest "${REGISTRY_URL}bitnami/redis:latest" 2>/dev/null || true
    docker push "${REGISTRY_URL}bitnami/redis:latest" 2>/dev/null || echo "⚠️  bitnami/redis 推送失败"
    _restore_docker_proxy
    echo "✅ 推送完成！"
    echo ""
    echo "服务器操作："
    echo "  1. daemon.json 配置 insecure-registries: [\"${REGISTRY_URL%/}\"]"
    echo "  2. 修改 docker-compose.yml，将 redis 镜像改为 ${REGISTRY_URL}bitnami/redis:latest"
    echo "  3. 上传 docker-compose.yml 和 .env 到 /opt/agent-support/"
    echo "  4. cd /opt/agent-support && docker compose up -d"
    ;;
  *)
    echo "用法: ./start.sh [命令]"
    echo ""
    echo "命令:"
    echo "  up / up-x86  构建并启动（up 自动本机架构，up-x86 强制 x86）"
    echo "  down         停止服务"
    echo "  restart      重启服务"
    echo "  logs         查看日志"
    echo "  ingest       初始化知识库"
    echo "  rebuild      强制重建镜像并启动"
    echo "  status       查看服务状态"
    echo "  shell        进入后端容器"
    echo "  dev          本地开发环境（uvicorn --reload + Vite dev server）"
    echo "  export       构建 x86 镜像并导出 tar"
    echo "  push-registry 推送到 .env 中 REGISTRY_URL 指定的内网仓库"
    echo ""
    echo "示例:"
    echo "  ./start.sh               # Mac: 构建 ARM 并启动 / 服务器: 构建 x86 并启动"
    echo "  ./start.sh up-x86        # 强制 x86（在 Mac 上构建给服务器用）"
    echo "  ./start.sh dev           # 本地热重载开发"
    echo "  ./start.sh push-registry # 构建 x86 并推送到 registry"
    ;;
esac
