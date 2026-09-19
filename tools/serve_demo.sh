#!/usr/bin/env bash
# 起本地演示环境：CAP 服务(4004) + 注入 mock 认证的小代理(4005)。
# 用法: bash tools/serve_demo.sh [start|stop|status]
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMO="$ROOT/project-code/demo-node"
LOG="$ROOT/work/evidence"
mkdir -p "$LOG"
export PATH="$(dirname "$(npx -y node@22 -p process.execPath)"):$PATH"

start() {
  if ! curl -s -o /dev/null "http://localhost:4004/odata/v4/book-order/\$metadata"; then
    echo "starting cds server (4004)…"
    ( cd "$DEMO" && nohup npm start > "$LOG/03_server.log" 2>&1 & )
    for i in $(seq 1 20); do
      sleep 1
      curl -s -o /dev/null "http://localhost:4004/odata/v4/book-order/\$metadata" && break
    done
  fi
  if ! curl -s -o /dev/null "http://localhost:4005/book-orders/webapp/index.html"; then
    echo "starting dev-proxy (4005)…"
    ( cd "$DEMO" && nohup node test/dev-proxy.js > "$LOG/06_proxy.log" 2>&1 & )
    sleep 2
  fi
  status
}

stop() {
  pkill -f cds-serve || true
  pkill -f "test/dev-proxy.js" || true
  sleep 1
  echo "stopped"
}

status() {
  printf '  CAP 4004  : %s\n' "$(curl -s -o /dev/null -w '%{http_code}' -u alice:alice http://localhost:4004/odata/v4/book-order/BookOrders)"
  printf '  proxy 4005: %s\n' "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:4005/book-orders/webapp/index.html)"
  printf '  app URL   : http://localhost:4005/book-orders/webapp/index.html\n'
}

case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  status) status ;;
  *) echo "usage: $0 [start|stop|status]"; exit 2 ;;
esac
