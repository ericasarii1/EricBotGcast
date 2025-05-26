from pyrogram import Client, filters
from pyrogram.types import ChatPermissions
from pymongo import MongoClient
import time
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# KONFIGURASI BOT
API_ID = 23746013
API_HASH = ""
BOT_TOKEN = ""
MONGO_URI = ""
LOG_CHANNEL = -1002690553118

# ROLE
SUDO_USERS = [7742582171, 7881514020]
SUPPORT_USERS = [7742582171, 7881514020]
WHITELIST = [7742582171, 7881514020]
OWNER_ID = 7742582171

# KONEKSI BOT & DB
bot = Client("global_protection_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = MongoClient(MONGO_URI)
db = mongo["global_protect"]
users = db["users"]
activity = db["activity"]
groups = db["groups"]

# LOG
async def log_to_channel(text):
    try:
        await bot.send_message(LOG_CHANNEL, text)
    except:
        pass

# CEK IZIN
def is_authorized(user_id):
    return user_id in SUDO_USERS or user_id in SUPPORT_USERS or user_id in WHITELIST

# AMBIL TARGET
def get_target_user(msg):
    if msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user.id
    elif len(msg.command) > 1:
        try:
            return int(msg.command[1])
        except ValueError:
            return None
    return None

# GMUTE / UNGMUTE
@bot.on_message(filters.command(["gmute", "ungmute"]))
async def handle_gmute(_, msg):
    if not is_authorized(msg.from_user.id):
        return
    target = get_target_user(msg)
    if not target:
        return await msg.reply("Balas pesan atau kirim user ID.")
    if msg.command[0] == "gmute":
        users.update_one({"_id": target}, {"$set": {"gmute": True}}, upsert=True)
        await msg.reply("Pengguna dimute global.")
        await log_to_channel(f"[GMUTE] `{target}` oleh `{msg.from_user.id}`.")
    else:
        users.update_one({"_id": target}, {"$unset": {"gmute": ""}})
        await msg.reply("Mute global dicabut.")
        await log_to_channel(f"[UNGMUTE] `{target}` oleh `{msg.from_user.id}`.")

# GBAN / UNGBAN
@bot.on_message(filters.command(["gban", "ungban"]))
async def handle_gban(_, msg):
    if not is_authorized(msg.from_user.id):
        return
    target = get_target_user(msg)
    if not target:
        return await msg.reply("Balas pesan atau kirim user ID.")
    if msg.command[0] == "gban":
        users.update_one({"_id": target}, {"$set": {"gban": True}}, upsert=True)
        group_ids = groups.distinct("_id")
        for group_id in group_ids:
            try:
                await bot.ban_chat_member(group_id, target)
            except:
                pass
        await msg.reply("Pengguna dibanned global.")
        await log_to_channel(f"[GBAN] `{target}` oleh `{msg.from_user.id}`.")
    else:
        users.update_one({"_id": target}, {"$unset": {"gban": ""}})
        await msg.reply("Ban global dicabut.")
        await log_to_channel(f"[UNGBAN] `{target}` oleh `{msg.from_user.id}`.")

# MODERASI PESAN
@bot.on_message(filters.group)
async def enforce_restrictions(_, msg):
    if not msg.from_user:
        return
    user_id = msg.from_user.id
    data = users.find_one({"_id": user_id})
    if not data:
        return
    try:
        if data.get("gban"):
            await bot.ban_chat_member(msg.chat.id, user_id)
            await log_to_channel(f"[ENFORCE] `{user_id}` dibanned di `{msg.chat.title}`.")
        elif data.get("gmute"):
            await bot.restrict_chat_member(msg.chat.id, user_id, ChatPermissions(can_send_messages=False))
            await log_to_channel(f"[ENFORCE] `{user_id}` dimute di `{msg.chat.title}`.")
    except:
        pass

# DETEKSI GCAST
@bot.on_message(filters.group & ~filters.service)
async def detect_gcast(_, msg):
    if not msg.from_user or msg.sender_chat:
        return
    user_id = msg.from_user.id
    chat_id = msg.chat.id
    now = int(time.time())

    recent = activity.find_one({"_id": user_id})
    if recent:
        chats = set(recent.get("chats", []))
        timestamps = [t for t in recent.get("timestamps", []) if now - t < 60]
        chats.add(chat_id)
        timestamps.append(now)
        activity.update_one({"_id": user_id}, {"$set": {"chats": list(chats), "timestamps": timestamps}})
        if len(chats) >= 5:
            users.update_one({"_id": user_id}, {"$set": {"gmute": True}}, upsert=True)
            try:
                await bot.ban_chat_member(chat_id, user_id)
            except:
                pass
            await log_to_channel(f"[GCAST DETECTED] `{user_id}` di `{msg.chat.title}`.")
            try:
                await bot.send_message(OWNER_ID, f"User {msg.from_user.mention} (`{user_id}`) GMUTE karena GCAST.")
            except:
                pass
    else:
        activity.insert_one({"_id": user_id, "chats": [chat_id], "timestamps": [now]})

# BLOKIR CHANNEL SENDER
@bot.on_message(filters.group)
async def block_channel_sender(_, msg):
    if msg.sender_chat and msg.sender_chat.type == "channel":
        try:
            await msg.delete()
            await msg.chat.ban_sender_chat(msg.sender_chat.id)
            await log_to_channel(f"[CHANNEL BLOCKED] `{msg.sender_chat.title}` di `{msg.chat.title}`.")
            await bot.send_message(OWNER_ID, f"Channel `{msg.sender_chat.title}` diblok dari `{msg.chat.title}`.")
        except:
            pass

# HANDLER UPDATE MEMBER (Gabungan)
@bot.on_chat_member_updated()
async def chat_member_handler(_, event):
    try:
        bot_id = (await bot.get_me()).id
        user = event.new_chat_member.user
        chat_id = event.chat.id

        # Jika bot baru masuk ke grup
        if user.id == bot_id:
            groups.update_one({"_id": chat_id}, {"$set": {"title": event.chat.title}}, upsert=True)

        # Jika bot lain masuk grup
        elif user.is_bot:
            await bot.kick_chat_member(chat_id, user.id)
            await log_to_channel(f"[ANTI BOT] `{user.first_name}` dikick dari `{event.chat.title}`.")
            try:
                await bot.send_message(OWNER_ID, f"Bot @{user.username or user.first_name} dikick dari grup `{event.chat.title}`.")
            except:
                pass

        # User biasa join, cek hukuman
        elif event.new_chat_member.status == "member":
            data = users.find_one({"_id": user.id})
            if not data:
                return
            if data.get("gban"):
                await bot.ban_chat_member(chat_id, user.id)
            elif data.get("gmute"):
                await bot.restrict_chat_member(chat_id, user.id, ChatPermissions(can_send_messages=False))
            await log_to_channel(f"[AUTO JOIN ACTION] `{user.id}` dikenai hukuman di `{event.chat.title}`.")
    except:
        pass

# START DAN HELP
@bot.on_message(filters.command("start") & filters.private)
async def start(_, msg):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Tambahkan Bot", url="https://t.me/emiliarezero_robot?startgroup=true")],
            [
                InlineKeyboardButton("👥 Support Group", url="https://t.me/Grup_Ovanime_Indo"),
                InlineKeyboardButton("📢 Channel Updates", url="https://t.me/TE_Team_Official")
            ]
        ]
    )
    await msg.reply(
        "Halo! Saya adalah Emilia bot proteksi global bertema anime Re:Zero. Gunakan saya untuk melindungi grup kamu dari spam dan GCAST!",
        reply_markup=keyboard
    )

@bot.on_message(filters.command("help") & filters.private)
async def help(_, msg):
    await msg.reply("Perintah tersedia untuk admin. Gunakan dengan bijak.")

# JALANKAN BOT
bot.run()
