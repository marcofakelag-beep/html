#!/bin/bash
echo "========================================"
echo " HUNTER PROXY - Status"
echo "========================================"
pids=$(pgrep -f "hunter_proxy.py")
[ -n "$pids" ] && echo "  [ON]  Proxy 8884  (PID: $pids)" || echo "  [OFF] Proxy 8884"
pids=$(pgrep -f "bot_control.py")
[ -n "$pids" ] && echo "  [ON]  Bot         (PID: $pids)" || echo "  [OFF] Bot"
echo "========================================"
