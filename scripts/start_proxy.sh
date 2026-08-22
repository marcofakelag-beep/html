#!/bin/bash
export HUNTER_BASE_DIR=/home/runner/hunter
export HUNTER_DB_PATH=/home/runner/hunter/uids.json
export HUNTER_LOG_DIR=/home/runner/hunter/logs
echo "[HUNTER] Starting Proxy on port 8884..."
mitmdump -p 8884 --set proxyauth=HUNTER:HUNTER --set block_global=false --ssl-insecure -s /home/runner/hunter/scripts/hunter_proxy.py
