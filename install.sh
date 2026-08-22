#!/bin/bash
echo "========================================"
echo "  HUNTER PROXY - Installer"
echo "========================================"
mkdir -p /home/runner/hunter/{scripts,data/HUNTER,logs,certs}

echo "[1/3] Copying files..."
cp scripts/*.py   /home/runner/hunter/scripts/
cp scripts/*.sh   /home/runner/hunter/scripts/
cp -r data/HUNTER/* /home/runner/hunter/data/HUNTER/ 2>/dev/null || true
cp uids.json /home/runner/hunter/ 2>/dev/null || echo '{}' > /home/runner/hunter/uids.json
chmod +x /home/runner/hunter/scripts/*.sh

echo "[2/3] Installing dependencies..."
pip install mitmproxy python-telegram-bot requests --quiet

echo "[3/3] Done!"
echo ""
echo "Set env vars then run:"
echo "  HUNTER_BOT_TOKEN=<token> HUNTER_ADMIN_ID=<id> bash /home/runner/hunter/scripts/start_all.sh"
