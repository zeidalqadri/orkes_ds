#!/bin/bash
set -euo pipefail

BOT_NAME="arbos-orkes_ds"
LAUNCH_SCRIPT="/home/the_bomb/orkes_ds/.arbos-launch.sh"
WORK_DIR="/home/the_bomb/orkes_ds"
ENV_FILE="$WORK_DIR/.env"
LOG="/tmp/check-bot.log"

set -a
source "$ENV_FILE" 2>/dev/null || { echo "$(date -u +%FT%T) ERROR: cannot source $ENV_FILE" >> "$LOG"; exit 1; }
set +a

STATUS=$(pm2 status "$BOT_NAME" 2>/dev/null | grep -cE "$BOT_NAME.*online" || true)

if [ "$STATUS" -eq 0 ]; then
    echo "$(date -u +%FT%T) $BOT_NAME DOWN — restarting" >> "$LOG"
    rm -f "$WORK_DIR/context/.bot.lock"
    cd "$WORK_DIR"
    pm2 start "$LAUNCH_SCRIPT" --name "$BOT_NAME" 2>&1 >> "$LOG"
    pm2 save 2>&1 >> "$LOG"
    MSG="⚠️ arbos-orkes_ds was DOWN — auto-restarted at $(date -u +%d-%H:%M UTC)"
    curl -s -X POST "https://api.telegram.org/bot$TAU_BOT_TOKEN/sendMessage" \
        -d "chat_id=$TELEGRAM_OWNER_ID" \
        -d "text=$MSG" > /dev/null 2>&1
else
    echo "$(date -u +%FT%T) $BOT_NAME OK" >> "$LOG"
fi
