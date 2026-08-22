"""
HUNTER Proxy - EVANN Injection Method
Request hook: serves modified game files (cache_res, assetindexer, fileinfo)
Response hook: login detection + UID validation via protobuf
"""
import os
import json
import time
import logging
from mitmproxy import http, ctx

# ─── Configuration ───────────────────────────────────────────
BASE_DIR   = os.environ.get("HUNTER_BASE_DIR", "/opt/hunter")
DATA_DIR   = os.path.join(BASE_DIR, "data", "HUNTER")
DB_PATH    = os.environ.get("HUNTER_DB_PATH",  os.path.join(BASE_DIR, "uids.json"))
LOG_DIR    = os.environ.get("HUNTER_LOG_DIR",  os.path.join(BASE_DIR, "logs"))
LOG_PREFIX = "【HUNTER】"

# EVANN-style intercept patterns (request hook)
INTERCEPT_PATTERNS = ["cache_res", "fileinfo"]

# Anti-cheat patterns to block (EVANN method)
ANTICHEAT_PATTERNS = [
    "CheckHackBehavior", "anticheat",
    "GetMatchmakingBlacklist", "antijuda",
]

# Protected login hosts (hunter method)
PROTECTED_HOSTS = [
    "loginbp.ggpolarbear.com",
    "clientbp.ggpolarbear.com",
    "gate.ggpolarbear.com",
]
LOGIN_KEYWORD = "majorlogin"

# In-game messages
MSG_SUCCESS      = "[00FF88]✅ Authentication Successful\n[FFFFFF]HUNTER is active.\n[00FFFF]⚡ @EVANNxCHEAT"
MSG_BANNED       = "[FF0000]⛔ Access Revoked\n[FFFFFF]Your account is banned.\n[FFAA00]Contact: [00FFFF]@EVANNxCHEAT"
MSG_EXPIRED      = "[FF8800]⏰ Subscription Expired\n[FFFFFF]Renew now: [00FFFF]@EVANNxCHEAT"
MSG_NOT_FOUND    = "[FF6600]🔒 Not Registered\n[FFFFFF]Get access: [00FFFF]@EVANNxCHEAT"

# ─── Logging ─────────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "hunter_proxy.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("hunter")

# ─── File cache (EVANN method) ───────────────────────────────
FILE_CACHE = {}
current_uid = None  # UID detected from last login

def load_files():
    if not os.path.exists(DATA_DIR):
        log.error(f"Data dir not found: {DATA_DIR}")
        return
    for pattern in INTERCEPT_PATTERNS:
        for name in [pattern, pattern + ".txt", pattern + ".bin"]:
            path = os.path.join(DATA_DIR, name)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    raw = f.read()
                try:
                    text = raw.decode("ascii").strip()
                    clean = text.replace(" ", "").replace("\n", "").replace("\r", "")
                    if all(c in "0123456789abcdefABCDEF" for c in clean) and len(clean) > 10:
                        binary = bytes.fromhex(clean)
                        FILE_CACHE[pattern] = binary
                        ctx.log.info(f"{LOG_PREFIX} Loaded {pattern}: {len(raw)} hex → {len(binary)} binary bytes")
                        break
                except (UnicodeDecodeError, ValueError):
                    pass
                FILE_CACHE[pattern] = raw
                ctx.log.info(f"{LOG_PREFIX} Loaded {pattern}: {len(raw)} binary bytes")
                break
    ctx.log.info(f"{LOG_PREFIX} Files ready: {list(FILE_CACHE.keys())}")

# ─── UID Database ─────────────────────────────────────────────
def load_db():
    if not os.path.exists(DB_PATH):
        return {}
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def get_auth_status(uid):
    if not uid:
        return "NOT_FOUND"
    db = load_db()
    if uid not in db:
        return "NOT_FOUND"
    user = db[uid]
    status = user.get("status", "")
    if status == "blocked":
        return "BANNED"
    if status == "active":
        return "ACTIVE" if user.get("expires_at", 0) > time.time() else "EXPIRED"
    return "NOT_FOUND"

# ─── Protobuf helpers (hunter method) ────────────────────────
def _decode_varint(data, pos):
    result, shift = 0, 0
    while pos < len(data):
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80): break
        shift += 7
    return result, pos

def extract_uid(proto_bytes):
    try:
        pos = 0
        while pos < len(proto_bytes):
            tag, pos = _decode_varint(proto_bytes, pos)
            field_num = tag >> 3
            wire_type = tag & 0x7
            if field_num == 1 and wire_type == 0:
                value, pos = _decode_varint(proto_bytes, pos)
                return str(value)
            elif wire_type == 0:
                _, pos = _decode_varint(proto_bytes, pos)
            elif wire_type == 2:
                length, pos = _decode_varint(proto_bytes, pos)
                pos += length
            elif wire_type == 5:
                pos += 4
            else:
                pos += 8
    except Exception:
        pass
    return None

def make_block_response(flow, message, status=400):
    flow.response = http.Response.make(
        status,
        message.encode("utf-8"),
        {"Content-Type": "text/plain; charset=utf-8"},
    )

# ─── Proxy Addon ─────────────────────────────────────────────
class HunterProxy:

    def load(self, loader):
        ctx.log.info(f"{LOG_PREFIX} Proxy starting...")
        load_files()
        ctx.log.info(f"{LOG_PREFIX} Ready on port {ctx.options.listen_port}")

    def request(self, flow: http.HTTPFlow):
        url = flow.request.pretty_url
        url_lower = url.lower()

        # ── Block anti-cheat (EVANN method) ──────────────────
        for pattern in ANTICHEAT_PATTERNS:
            if pattern.lower() in url_lower:
                flow.response = http.Response.make(200, b"{}", {"Content-Type": "application/json"})
                ctx.log.info(f"[BLOCK anticheat] {url}")
                log.info(f"BLOCK_ANTICHEAT: {url}")
                return

        # ── Serve modified files (EVANN method) ──────────────
        for pattern in INTERCEPT_PATTERNS:
            if pattern.lower() in url_lower:
                data = FILE_CACHE.get(pattern)
                if data:
                    flow.response = http.Response.make(
                        200, data,
                        {
                            "Content-Type": "application/octet-stream",
                            "Content-Length": str(len(data)),
                            "Connection": "close",
                        },
                    )
                    ctx.log.info(f"[INJECT {pattern}] {len(data)} bytes → {url}")
                    log.info(f"INJECT_{pattern.upper()}: {url}")
                else:
                    ctx.log.warn(f"[MISSING {pattern}] No file loaded")
                return

    def response(self, flow: http.HTTPFlow):
        global current_uid
        url = flow.request.pretty_url.lower()

        # ── Login detection (hunter method) ──────────────────
        if LOGIN_KEYWORD in url:
            if flow.response.status_code != 200:
                return
            uid = extract_uid(flow.response.content)
            if not uid:
                ctx.log.warn(f"{LOG_PREFIX} Login detected but UID not parsed")
                return

            current_uid = uid
            status = get_auth_status(uid)

            ctx.log.info(f"\n{'═'*45}")
            ctx.log.info(f"  {LOG_PREFIX} UID: {uid}  |  Status: {status}")
            ctx.log.info(f"{'═'*45}")
            log.info(f"LOGIN UID={uid} STATUS={status}")

            msg_map = {
                "ACTIVE":    (MSG_SUCCESS,   200),
                "BANNED":    (MSG_BANNED,    400),
                "EXPIRED":   (MSG_EXPIRED,   400),
                "NOT_FOUND": (MSG_NOT_FOUND, 400),
            }
            message, code = msg_map.get(status, (MSG_NOT_FOUND, 400))
            flow.response.status_code = code
            flow.response.content = message.encode("utf-8")
            flow.response.headers["Content-Type"] = "text/plain; charset=utf-8"
            return

        # ── Protect game hosts (hunter method) ───────────────
        if any(host in url for host in PROTECTED_HOSTS):
            if not current_uid:
                make_block_response(flow, MSG_NOT_FOUND)
                ctx.log.warn(f"{LOG_PREFIX} [BLOCK] No UID — {url}")
                return
            status = get_auth_status(current_uid)
            if status == "ACTIVE":
                ctx.log.info(f"{LOG_PREFIX} [ALLOW] UID {current_uid} — {url}")
            else:
                msg = {"BANNED": MSG_BANNED, "EXPIRED": MSG_EXPIRED}.get(status, MSG_NOT_FOUND)
                make_block_response(flow, msg)
                ctx.log.warn(f"{LOG_PREFIX} [BLOCK {status}] UID {current_uid} — {url}")


addons = [HunterProxy()]
