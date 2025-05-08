from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime
import sqlite3

# === CONFIG (Langsung dalam file) ===
API_ID = 12345678  # Ganti dengan API ID kamu
API_HASH = "abcd1234efgh5678"  # Ganti dengan API HASH kamu
BOT_TOKEN = "123456789:ABCDEF_BOT_TOKEN_HERE"
LOG_CHANNEL_ID = -1001234567890  # Ganti dengan channel log kamu
SUDO_USERS = [123456789]  # ID kamu atau sudo lainnya

# === Inisialisasi Bot ===
app = Client("anti-gcast-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# === Setup Database ===
conn = sqlite3.connect("anti_gcast.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS gban (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS gmute (user_id INTEGER PRIMARY KEY)")
conn.commit()

# === Keyword GCAST ===
GCAST_KEYWORDS = [
    "t.me/", "gcast", "join grup", "joinchannel", "broadcast", "grup baru", "channel telegram"
]

# === Fungsi Logging ===
def utc_now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

async def log(client, text):
    try:
        await client.send_message(LOG_CHANNEL_ID, f"{text}\n\n🕒 {utc_now()}")
    except Exception as e:
        print(f"[Log Error] {e}")

# === Command /start dan /help ===
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await message.reply("Halo! Saya bot Anti-GCAST. Gunakan /help untuk melihat fitur.")

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message):
    await message.reply(
        "**Fitur Anti-GCAST Bot:**\n\n"
        "- Deteksi otomatis spam seperti `t.me/`, `gcast`, dll\n"
        "- `/gban` & `/gmute`: Blokir pengguna secara global (SUDO only)\n"
        "- Otomatis kick user yg masuk jika di-GBAN\n"
        "- Otomatis hapus pesan user yang di-GMUTE\n"
        "- Semua aksi dicatat ke channel log"
    )

# === GBAN ===
@app.on_message(filters.command("gban") & filters.user(SUDO_USERS))
async def gban_cmd(client, message):
    user = message.reply_to_message.from_user if message.reply_to_message else None
    if not user:
        return await message.reply("Balas pesan user untuk GBAN.")
    cursor.execute("INSERT OR IGNORE INTO gban VALUES (?)", (user.id,))
    conn.commit()
    await message.reply(f"{user.mention} telah di-GBAN.")
    await log(client, f"🔨 GBAN\n👤 {user.mention} (`{user.id}`)\n👮 Oleh: {message.from_user.mention}")

# === UNGBAN ===
@app.on_message(filters.command("ungban") & filters.user(SUDO_USERS))
async def ungban_cmd(client, message):
    user = message.reply_to_message.from_user if message.reply_to_message else None
    if not user:
        return await message.reply("Balas pesan user untuk UNGBAN.")
    cursor.execute("DELETE FROM gban WHERE user_id = ?", (user.id,))
    conn.commit()
    await message.reply(f"{user.mention} telah di-UNGBAN.")
    await log(client, f"✅ UNGBAN\n👤 {user.mention} (`{user.id}`)\n👮 Oleh: {message.from_user.mention}")

# === GMUTE ===
@app.on_message(filters.command("gmute") & filters.user(SUDO_USERS))
async def gmute_cmd(client, message):
    user = message.reply_to_message.from_user if message.reply_to_message else None
    if not user:
        return await message.reply("Balas pesan user untuk GMUTE.")
    cursor.execute("INSERT OR IGNORE INTO gmute VALUES (?)", (user.id,))
    conn.commit()
    await message.reply(f"{user.mention} telah di-GMUTE.")
    await log(client, f"🔇 GMUTE\n👤 {user.mention} (`{user.id}`)\n👮 Oleh: {message.from_user.mention}")

# === UNGMUTE ===
@app.on_message(filters.command("ungmute") & filters.user(SUDO_USERS))
async def ungmute_cmd(client, message):
    user = message.reply_to_message.from_user if message.reply_to_message else None
    if not user:
        return await message.reply("Balas pesan user untuk UNGMUTE.")
    cursor.execute("DELETE FROM gmute WHERE user_id = ?", (user.id,))
    conn.commit()
    await message.reply(f"{user.mention} telah di-UNGMUTE.")
    await log(client, f"✅ UNGMUTE\n👤 {user.mention} (`{user.id}`)\n👮 Oleh: {message.from_user.mention}")

# === Enforcer Otomatis ===
@app.on_message(filters.group)
async def enforcement(client, message: Message):
    user = message.from_user
    if not user:
        return

    # GBAN Enforce
    cursor.execute("SELECT 1 FROM gban WHERE user_id = ?", (user.id,))
    if cursor.fetchone():
        try:
            await message.chat.ban_member(user.id)
            await log(client, f"🚫 Auto-Kick GBAN\n👤 {user.mention} (`{user.id}`)\n📍 Grup: {message.chat.title}")
        except Exception: pass
        return

    # GMUTE Enforce
    cursor.execute("SELECT 1 FROM gmute WHERE user_id = ?", (user.id,))
    if cursor.fetchone():
        try:
            await message.delete()
            await log(client, f"🚫 Auto-Hapus GMUTE\n👤 {user.mention} (`{user.id}`)\n📍 Grup: {message.chat.title}")
        except Exception: pass
        return

    # Anti-GCAST
    if message.text:
        for kw in GCAST_KEYWORDS:
            if kw in message.text.lower():
                try:
                    await message.delete()
                    await message.chat.ban_member(user.id)
                    await log(client, f"🚨 GCAST Detected\n👤 {user.mention} (`{user.id}`)\n📍 Grup: {message.chat.title}")
                except Exception: pass
                break

# === Start Bot ===
print("Bot Anti-GCAST aktif...")
app.run()
