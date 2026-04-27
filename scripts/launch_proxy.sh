#!/usr/bin/env bash
# Launch the deepseek-cursor-proxy alongside the bot.
# The proxy intercepts API calls from opencode → DeepSeek and caches
# reasoning_content, preventing 400 errors on tool-call turns.
#
# Usage:
#   ./launch_proxy.sh [--port 9000] [--model deepseek-v4-pro]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROXY_DIR="$SCRIPT_DIR/repos/deepseek-cursor-proxy"

cd "$PROXY_DIR"

# Start proxy in background, capture PID
uv run deepseek-cursor-proxy --no-ngrok "$@" &
PROXY_PID=$!
echo "proxy pid=$PROXY_PID listening on http://127.0.0.1:9000/v1"

# Save PID for cleanup
echo "$PROXY_PID" > /tmp/deepseek-cursor-proxy.pid

# Wait for interrupt
trap "kill $PROXY_PID 2>/dev/null; rm -f /tmp/deepseek-cursor-proxy.pid" EXIT
wait $PROXY_PID
