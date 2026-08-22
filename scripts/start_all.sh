#!/bin/bash
echo "========================================"
echo " HUNTER PROXY - Starting Services"
echo "========================================"
HUNTER_BASE_DIR=/home/runner/hunter
HUNTER_DB_PATH=$HUNTER_BASE_DIR/uids.json
HUNTER_LOG_DIR=$HUNTER_BASE_DIR/logs

echo "[1/2] Starting Proxy Port 8884..."
HUNTER_BASE_DIR=$HUNTER_BASE_DIR HUNTER_DB_PATH=$HUNTER_DB_PATH HUNTER_LOG_DIR=$HUNTER_LOG_DIR \
mitmdump -p 8884 --set proxyauth=HUNTER:HUNTER --set block_global=false --ssl-insecure \
-s $HUNTER_BASE_DIR/scripts/hunter_proxy.py > $HUNTER_LOG_DIR/proxy.out 2>&1 &
sleep 2

echo "[2/2] Starting Bot..."
HUNTER_DB_PATH=$HUNTER_DB_PATH HUNTER_LOG_DIR=$HUNTER_LOG_DIR \
python3 $HUNTER_BASE_DIR/scripts/bot_control.py > $HUNTER_LOG_DIR/bot.out 2>&1 &

echo "Done! Check status: bash /home/runner/hunter/scripts/status.sh"
