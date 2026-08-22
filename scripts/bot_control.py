import json, time, os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

TOKEN          = os.environ.get("8682600876:AAHqI8k8IoCFP_wsUWaKvmtMU3SRdBv2FuM
", "")
ADMIN_ID       = int(os.environ.get("HUNTER_ADMIN_ID", "8347981047"))
UIDS_JSON_FILE = os.environ.get("HUNTER_DB_PATH", "/opt/hunter/uids.json")
TEMP_DATA: dict = {}

DURATION_PRESETS = {
    "dur_1h":  ("1 Hour",    3_600),
    "dur_1d":  ("1 Day",    86_400),
    "dur_7d":  ("7 Days",  604_800),
    "dur_30d": ("30 Days", 2_592_000),
}

def load_db():
    if not os.path.exists(UIDS_JSON_FILE): return {}
    try:
        with open(UIDS_JSON_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_db(data):
    with open(UIDS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def format_date(ts):
    if not ts or ts == 0: return "—"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

def get_stats(db):
    now = time.time()
    active = expired = blocked = 0
    for u in db.values():
        if u.get("status") == "blocked": blocked += 1
        elif u.get("status") == "active":
            (active if u.get("expires_at", 0) > now else expired).__class__  # dummy
            if u.get("expires_at", 0) > now: active += 1
            else: expired += 1
    return len(db), active, expired, blocked

def get_user_status_label(user):
    now = time.time()
    if user.get("status") == "blocked": return "🚫 Banned"
    if user.get("status") == "active":
        if user.get("expires_at", 0) > now:
            rem = user["expires_at"] - now
            return f"✅ Active ({int(rem//86400)}d {int((rem%86400)//3600)}h left)"
        return "⏰ Expired"
    return "❔ Not Registered"

def main_menu_keyboard(db):
    total, active, expired, blocked = get_stats(db)
    text = (
        "<b>⚡ HUNTER Control Panel</b>\n"
        "<i>@EVANNxCHEAT</i>\n\n"
        "<b>📊 Statistics</b>\n"
        f"🔢 Total   : <code>{total}</code>\n"
        f"✅ Active  : <code>{active}</code>\n"
        f"⏰ Expired : <code>{expired}</code>\n"
        f"🚫 Banned  : <code>{blocked}</code>\n\n"
        "Send a <b>numeric ID</b> to manage it."
    )
    keyboard = [
        [InlineKeyboardButton("➕  Add / Manage ID", callback_data="add_new")],
        [
            InlineKeyboardButton("✅ Active",  callback_data="list_active"),
            InlineKeyboardButton("⏰ Expired", callback_data="list_expired"),
            InlineKeyboardButton("🚫 Banned",  callback_data="list_blocked"),
        ],
        [InlineKeyboardButton("📋  View All IDs", callback_data="list_all")],
        [InlineKeyboardButton("🔄  Refresh", callback_data="refresh")],
    ]
    return text, InlineKeyboardMarkup(keyboard)

def id_management_keyboard(uid, is_banned):
    ban_btn = (
        InlineKeyboardButton("✅  Unban Account", callback_data="dur_unblock")
        if is_banned else
        InlineKeyboardButton("🚫  Ban Account", callback_data="dur_block")
    )
    keyboard = [
        [InlineKeyboardButton("⚡  1 Hour", callback_data="dur_1h"),
         InlineKeyboardButton("📅  1 Day",  callback_data="dur_1d")],
        [InlineKeyboardButton("📆  7 Days", callback_data="dur_7d"),
         InlineKeyboardButton("🗓️  30 Days",callback_data="dur_30d")],
        [InlineKeyboardButton("⚙️  Custom Duration", callback_data="dur_custom")],
        [ban_btn, InlineKeyboardButton("🗑️  Delete", callback_data="dur_delete")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied.")
        return
    db = load_db()
    text, markup = main_menu_keyboard(db)
    await update.message.reply_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    db = load_db()
    total, active, expired, blocked = get_stats(db)
    await update.message.reply_text(
        f"📊 <b>Stats</b>\nTotal: {total} | Active: {active} | Expired: {expired} | Banned: {blocked}",
        parse_mode=ParseMode.HTML,
    )

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("Usage: /search <ID>"); return
    uid = context.args[0]
    db = load_db()
    if uid not in db:
        await update.message.reply_text(f"❔ ID <code>{uid}</code> not found.", parse_mode=ParseMode.HTML); return
    user = db[uid]
    label = get_user_status_label(user)
    await update.message.reply_text(
        f"🆔 <code>{uid}</code>\nStatus: {label}\nExpires: {format_date(user.get('expires_at',0))}",
        parse_mode=ParseMode.HTML,
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    text  = update.message.text.strip()
    admin = update.effective_user.id
    state = TEMP_DATA.get(admin, {}).get("action")

    if state == "waiting_time":
        uid = TEMP_DATA[admin].get("uid")
        text_lower = text.lower()
        try:
            if text_lower.endswith("m"):   secs = int(text_lower[:-1]) * 60
            elif text_lower.endswith("h"): secs = int(text_lower[:-1]) * 3600
            elif text_lower.endswith("d"): secs = int(text_lower[:-1]) * 86400
            else:                          secs = int(text_lower) * 3600
        except ValueError:
            await update.message.reply_text("⚠️ Invalid format. Use: 30m / 6h / 14d"); return
        expire = time.time() + secs
        db = load_db()
        db[uid] = {"status": "active", "expires_at": expire}
        save_db(db)
        TEMP_DATA.pop(admin, None)
        await update.message.reply_text(
            f"✅ <b>Activated</b>\n🆔 <code>{uid}</code>\n📅 Expires: <code>{format_date(expire)}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if text.isdigit():
        uid = text
        db  = load_db()
        user = db.get(uid, {})
        is_banned = user.get("status") == "blocked"
        label = get_user_status_label(user)
        TEMP_DATA[admin] = {"uid": uid}
        await update.message.reply_text(
            f"🆔 <b>ID:</b> <code>{uid}</code>\n📌 Status: {label}\n📅 Expires: {format_date(user.get('expires_at',0))}",
            reply_markup=id_management_keyboard(uid, is_banned),
            parse_mode=ParseMode.HTML,
        )
        return

    await update.message.reply_text("⚠️ Please send a <b>numeric ID</b>.", parse_mode=ParseMode.HTML)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    data     = query.data
    admin_id = update.effective_user.id
    await query.answer()
    db = load_db()

    if data in ("back_to_start", "refresh"):
        TEMP_DATA.pop(admin_id, None)
        text, markup = main_menu_keyboard(db)
        await query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
        return

    if data == "add_new":
        await query.edit_message_text(
            "🆕 <b>Register / Manage ID</b>\n\nSend the numeric account ID:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="back_to_start")]]),
        )
        return

    if data.startswith("list_"):
        now    = time.time()
        flt    = data[5:]
        lines  = []
        for uid, info in db.items():
            s = info.get("status",""); exp = info.get("expires_at",0)
            is_active  = s=="active" and exp>now
            is_expired = s=="active" and exp<=now
            is_blocked = s=="blocked"
            if flt=="active"  and not is_active:  continue
            if flt=="expired" and not is_expired: continue
            if flt=="blocked" and not is_blocked: continue
            icon   = "✅" if is_active else ("⏰" if is_expired else "🚫")
            lines.append(f"{icon} <code>{uid}</code>  |  {format_date(exp)}")
        header = {"all":"All","active":"Active","expired":"Expired","blocked":"Banned"}
        body   = "\n".join(lines) if lines else "— No records —"
        text   = f"<b>📋 {header.get(flt,flt)} Accounts</b>\n\n{body}"
        if len(text) > 4000: text = text[:3990] + "\n…"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]))
        return

    if data.startswith("dur_"):
        if admin_id not in TEMP_DATA or "uid" not in TEMP_DATA[admin_id]:
            await query.edit_message_text("⚠️ Session expired.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="back_to_start")]])); return
        uid      = TEMP_DATA[admin_id]["uid"]
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="back_to_start")]])

        if data == "dur_block":
            db[uid] = {"status":"blocked","expires_at":0}; save_db(db)
            await query.edit_message_text(f"🚫 <b>Banned</b>\n🆔 <code>{uid}</code>", parse_mode=ParseMode.HTML, reply_markup=back_btn)
        elif data == "dur_unblock":
            expire = time.time()+3600; db[uid]={"status":"active","expires_at":expire}; save_db(db)
            await query.edit_message_text(f"✅ <b>Unbanned</b>\n🆔 <code>{uid}</code>\n📅 {format_date(expire)}", parse_mode=ParseMode.HTML, reply_markup=back_btn)
        elif data == "dur_delete":
            db.pop(uid,None); save_db(db)
            await query.edit_message_text(f"🗑️ <b>Deleted</b>\n🆔 <code>{uid}</code>", parse_mode=ParseMode.HTML, reply_markup=back_btn)
        elif data == "dur_custom":
            TEMP_DATA[admin_id]["action"] = "waiting_time"
            await query.edit_message_text(
                f"⚙️ <b>Custom Duration</b>\n🆔 <code>{uid}</code>\n\n<code>30m</code> / <code>6h</code> / <code>14d</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="back_to_start")]]))
        elif data in DURATION_PRESETS:
            label, secs = DURATION_PRESETS[data]
            expire = time.time()+secs; db[uid]={"status":"active","expires_at":expire}; save_db(db)
            await query.edit_message_text(
                f"✅ <b>Activated</b>\n🆔 <code>{uid}</code>\n⏱️ {label}\n📅 {format_date(expire)}",
                parse_mode=ParseMode.HTML, reply_markup=back_btn)

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: Set HUNTER_BOT_TOKEN"); exit(1)
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("stats",  cmd_stats))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("🚀 HUNTER Bot running... (@EVANNxCHEAT)")
    app.run_polling(drop_pending_updates=True)
