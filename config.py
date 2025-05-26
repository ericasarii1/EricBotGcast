from pyrogram import Client, filters
from pyrogram.types import ChatPermissions
from pymongo import MongoClient
import time

# KONFIGURASI BOT
API_ID = 23746013
API_HASH = ""
BOT_TOKEN = ""
MONGO_URI = ""

# ROLE YANG BOLEH PAKAI PERINTAH
SUDO_USERS = [7742582171]
SUPPORT_USERS = [7742582171]
WHITELIST = [7742582171]
OWNER_ID = 7742582171
OWNER_USERNAME = "rezreza_asarii"

# KONEKSI BOT & DATABASE
bot = Client("global_protection_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = MongoClient(MONGO_URI)
db = mongo["global_protect"]
users = db["users"]
activity = db["activity"]

# CEK IZIN
def is_authorized(user_id):
    return user_id in SUDO_USERS or user_id in SUPPORT_USERS or user_id in WHITELIST

# FUNGSI AMAN AMBIL TARGET
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
        return await msg.reply("Balas pesan pengguna atau berikan user_id.")
    if msg.command[0] == "gmute":
        users.update_one({"_id": target}, {"$set": {"gmute": True}}, upsert=True)
        await msg.reply("Pengguna dimute secara global.")
    else:
        users.update_one({"_id": target}, {"$unset": {"gmute": ""}})
        await msg.reply("Mute global dilepas.")

# GKICK / UNGKICK
@bot.on_message(filters.command(["gkick", "ungkick"]))
async def handle_gkick(_, msg):
    if not is_authorized(msg.from_user.id):
        return
    target = get_target_user(msg)
    if not target:
        return await msg.reply("Balas pesan pengguna atau berikan user_id.")
    if msg.command[0] == "gkick":
        users.update_one({"_id": target}, {"$set": {"gkick": True}}, upsert=True)
        if msg.chat.type != "private":
            await msg.chat.kick_member(target)
        await msg.reply("Pengguna dikick secara global.")
    else:
        users.update_one({"_id": target}, {"$unset": {"gkick": ""}})
        await msg.reply("Kick global dilepas.")

# GBAN / UNGBAN
@bot.on_message(filters.command(["gban", "ungban"]))
async def handle_gban(_, msg):
    if not is_authorized(msg.from_user.id):
        return
    target = get_target_user(msg)
    if not target:
        return await msg.reply("Balas pesan pengguna atau berikan user_id.")
    if msg.command[0] == "gban":
        users.update_one({"_id": target}, {"$set": {"gban": True}}, upsert=True)
        if msg.chat.type != "private":
            await msg.chat.ban_member(target)
        await msg.reply("Pengguna dibanned secara global.")
    else:
        users.update_one({"_id": target}, {"$unset": {"gban": ""}})
        await msg.reply("Ban global dilepas.")

# CEK SAAT USER MENGIRIM PESAN (RESTRIKSI GLOBAL)
@bot.on_message(filters.group)
async def enforce_restrictions(_, msg):
    user_id = msg.from_user.id
    data = users.find_one({"_id": user_id})
    if not data:
        return
    try:
        if data.get("gban"):
            await msg.chat.ban_member(user_id)
        elif data.get("gkick"):
            await msg.chat.kick_member(user_id)
        elif data.get("gmute"):
            await msg.chat.restrict_member(user_id, ChatPermissions(can_send_messages=False))
    except Exception:
        pass

# ANTI GCAST DENGAN PILIHAN AKSI: GMUTE / GKICK / GBAN
@bot.on_message(filters.group & ~filters.service)
async def detect_gcast_user(_, msg):
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

        activity.update_one(
            {"_id": user_id},
            {"$set": {"chats": list(chats), "timestamps": timestamps}},
            upsert=True
        )

        if len(chats) >= 5:
            # GANTI PILIHAN DI BAWAH SESUAI AKSI YANG DIINGINKAN:
            users.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "gban": False,
                        "gmute": True,
                        "gkick": False
                    }
                },
                upsert=True
            )
            try:
                await msg.chat.ban_member(user_id)
            except: pass
            try:
                await bot.send_message(
                    OWNER_ID,
                    f"User {msg.from_user.mention} (`{user_id}`) terdeteksi GCAST. Aksi: GBAN, GMUTE, GKICK telah diterapkan."
                )
            except: pass
    else:
        activity.insert_one({"_id": user_id, "chats": [chat_id], "timestamps": [now]})

# ANTI CHANNEL SENDER (FORWARD DARI CHANNEL)
@bot.on_message(filters.group)
async def block_channel_sender(_, msg):
    if msg.sender_chat and msg.sender_chat.type == "channel":
        try:
            await msg.delete()
            await msg.chat.ban_sender_chat(msg.sender_chat.id)
            await bot.send_message(
                OWNER_ID,
                f"Channel [{msg.sender_chat.title}](https://t.me/{msg.sender_chat.username}) diblokir dari grup {msg.chat.title} karena kirim pesan via sender_chat."
            )
        except Exception:
            pass

# ANTI BOT MASUK GRUP
@bot.on_chat_member_updated()
async def block_bot_join(_, event):
    if event.new_chat_member.user.is_bot and event.new_chat_member.user.id != (await bot.get_me()).id:
        try:
            await bot.kick_chat_member(event.chat.id, event.new_chat_member.user.id)
            await bot.send_message(
                OWNER_ID,
                f"Bot @{event.new_chat_member.user.username or event.new_chat_member.user.first_name} dikick dari grup {event.chat.title}."
            )
        except:
            pass

# CEK USER MASUK GRUP UNTUK GBAN/GMUTE/GKICK
@bot.on_chat_member_updated()
async def on_user_join(_, event):
    if event.new_chat_member.status != "member":
        return
    user_id = event.new_chat_member.user.id
    data = users.find_one({"_id": user_id})
    if not data:
        return
    try:
        if data.get("gban"):
            await bot.ban_chat_member(event.chat.id, user_id)
        elif data.get("gkick"):
            await bot.kick_chat_member(event.chat.id, user_id)
        elif data.get("gmute"):
            await bot.restrict_chat_member(event.chat.id, user_id, ChatPermissions(can_send_messages=False))
    except Exception:
        pass

# START DAN HELP COMMAND
@bot.on_message(filters.command("start") & filters.private)
async def start(_, msg):
    await msg.reply("Halo! Saya adalah Emilia bot AntiGcast proteksi global Yang Bertema Anime Dari Re:Zero Yang Sekarang Menjaga Keamanan Di Grup Ovanime Indonesia.")

@bot.on_message(filters.command("help") & filters.private)
async def help_command(_, msg):
    await msg.reply("Perintah hanya tersedia untuk admin dan terbatas fungsinya.")

bot.run()
