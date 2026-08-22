#!/bin/bash
export HUNTER_BOT_TOKEN="${HUNTER_BOT_TOKEN}"
export HUNTER_ADMIN_ID="${HUNTER_ADMIN_ID}"
export HUNTER_DB_PATH=/home/runner/hunter/uids.json
export HUNTER_LOG_DIR=/home/runner/hunter/logs
echo "[HUNTER] Starting Bot..."
python3 /home/runner/hunter/scripts/bot_control.py
