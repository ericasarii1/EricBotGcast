from pyrogram import Client, filters
from pyrogram.types import ChatPermissions
from pymongo import MongoClient

# KONFIGURASI BOT
API_ID = 23746013
API_HASH = "c4c86f53aac9b29f7fa28d5ba953be44"
BOT_TOKEN = "7939007449:AAFppmG4KC-rRI1Qjh6z-Qnrk2Wky2hqsvM"
MONGO_URI = "mongodb+srv://NangKu077220:NangKu177221@musikdb.yntjfg7.mongodb.net/?retryWrites=true&w=majority&appName=musikdb"

# ROLE YANG BOLEH PAKAI PERINTAH
SUDO_USERS = [7742582171]
SUPPORT_USERS = [7742582171]
WHITELIST = [7742582171]

# KONEKSI BOT & DATABASE
bot = Client("global_protection_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = MongoClient(MONGO_URI)
db = mongo["global_protect"]
users = db["users"]

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

# CEK SAAT USER MENGIRIM PESAN
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

# CEK SAAT USER MASUK GRUP
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

bot.run()
