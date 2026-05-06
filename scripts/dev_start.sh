#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
CONDA_BIN="${CONDA_BIN:-/home/will/miniconda3/bin/conda}"
CONDA_ENV="${CONDA_ENV:-pest_detect}"
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_MANAGED_BY_SCRIPT=1

if [[ ! -x "$CONDA_BIN" ]]; then
  echo "未找到 conda 可执行文件: $CONDA_BIN"
  echo "可通过 CONDA_BIN 覆盖，例如：CONDA_BIN=/path/to/conda ./scripts/dev_start.sh"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "未找到 npm，请先安装 Node.js/npm。"
  exit 1
fi

if ! command -v redis-server >/dev/null 2>&1; then
  echo "未找到 redis-server，请先安装 Redis（Ubuntu/Debian: sudo apt install redis-server -y）。"
  exit 1
fi

# 防止当前 shell 残留的旧 Conda 变量污染 conda run 行为
unset CONDA_EXE CONDA_PYTHON_EXE CONDA_SHLVL _CE_CONDA _CE_M

if [[ "$CONDA_ENV" == */* ]]; then
  if [[ ! -d "$CONDA_ENV" ]]; then
    echo "指定的 Conda 环境路径不存在: $CONDA_ENV"
    exit 1
  fi
  CONDA_ENV_FLAG=(-p "$CONDA_ENV")
else
  if ! "$CONDA_BIN" env list | awk '{print $1}' | grep -Fxq "$CONDA_ENV"; then
    echo "Conda 环境不存在: $CONDA_ENV"
    echo "当前 $CONDA_BIN 可见环境："
    "$CONDA_BIN" env list || true
    echo
    echo "可通过以下方式覆盖："
    echo "1) CONDA_BIN=/path/to/conda ./scripts/dev_start.sh"
    echo "2) CONDA_ENV=/path/to/env ./scripts/dev_start.sh"
    exit 1
  fi
  CONDA_ENV_FLAG=(-n "$CONDA_ENV")
fi

cleanup() {
  echo
  echo "正在停止开发服务..."
  kill "${FRONTEND_PID:-0}" "${BACKEND_PID:-0}" "${CELERY_PID:-0}" "${REDIS_PID:-0}" >/dev/null 2>&1 || true
  wait "${FRONTEND_PID:-0}" "${BACKEND_PID:-0}" "${CELERY_PID:-0}" "${REDIS_PID:-0}" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

if command -v redis-cli >/dev/null 2>&1 && redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
  echo "检测到已有 Redis 运行，复用: redis://$REDIS_HOST:$REDIS_PORT/0"
  REDIS_MANAGED_BY_SCRIPT=0
  REDIS_PID=0
else
  echo "启动 Redis: redis://$REDIS_HOST:$REDIS_PORT/0"
  (
    exec redis-server --bind "$REDIS_HOST" --port "$REDIS_PORT" --save "" --appendonly no
  ) &
  REDIS_PID=$!
fi

echo "启动 Celery Worker"
(
  cd "$BACKEND_DIR"
  exec "$CONDA_BIN" run "${CONDA_ENV_FLAG[@]}" celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO --pool=threads --concurrency=1
) &
CELERY_PID=$!

echo "启动后端: http://$BACKEND_HOST:$BACKEND_PORT"
(
  cd "$BACKEND_DIR"
  exec "$CONDA_BIN" run "${CONDA_ENV_FLAG[@]}" python3 -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

echo "启动前端: http://$FRONTEND_HOST:$FRONTEND_PORT"
(
  cd "$FRONTEND_DIR"
  exec npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

echo "服务启动中，按 Ctrl+C 停止。"

sleep 3
if [[ "$REDIS_MANAGED_BY_SCRIPT" == "1" ]]; then
  if ! kill -0 "$REDIS_PID" >/dev/null 2>&1; then
    echo "Redis 启动失败。"
    exit 1
  fi
fi
if ! kill -0 "$CELERY_PID" >/dev/null 2>&1; then
  echo "Celery Worker 启动失败。"
  exit 1
fi
if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
  echo "后端启动失败。"
  exit 1
fi
if ! kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
  echo "前端启动失败。"
  exit 1
fi

echo "全部服务已启动：Frontend($FRONTEND_PORT) / Backend($BACKEND_PORT) / Redis($REDIS_PORT) / Celery(worker)"

wait "$REDIS_PID" "$CELERY_PID" "$BACKEND_PID" "$FRONTEND_PID"
