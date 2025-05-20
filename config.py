from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
import asyncio

API_ID = 123456
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"

# Konfigurasi
LOG_CHANNEL_ID = -1001234567890   # Ganti dengan ID channel log kamu
AUTO_BAN = False                  # Kalau True, bot akan diban
AUTO_MUTE = True                  # Kalau True, bot akan dimute
MUTE_DURATION = 3600             # Durasi mute dalam detik (3600 = 1 jam)
WHITELIST_BOTS = [777000, 123456789]  # Bot yang diabaikan

GCAST_KEYWORDS = ["gcast", "broadcast", "global message", "siaran", "pesan global", "/gcast"]

app = Client("antigcast_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.group & filters.bot)
async def anti_gcast(client: Client, message: Message):
    if message.from_user.id in WHITELIST_BOTS:
        return

    text = message.text or message.caption or ""
    if any(keyword in text.lower() for keyword in GCAST_KEYWORDS):
        try:
            await message.delete()
        except Exception as e:
            print(f"Gagal menghapus pesan: {e}")

        log_text = (
            f"🚫 <b>Gcast Detected</b>\n"
            f"<b>Grup:</b> {message.chat.title} (`{message.chat.id}`)\n"
            f"<b>Bot:</b> {message.from_user.mention} (`{message.from_user.id}`)\n"
            f"<b>Pesan:</b> <code>{text[:100]}</code>"
        )
        try:
            await client.send_message(LOG_CHANNEL_ID, log_text, parse_mode="html")
        except Exception as e:
            print(f"Gagal mengirim log: {e}")

        if AUTO_BAN:
            try:
                await client.ban_chat_member(message.chat.id, message.from_user.id)
                await client.send_message(message.chat.id, f"Bot {message.from_user.mention} diblokir karena gcast.")
            except Exception as e:
                print(f"Gagal ban bot: {e}")
        elif AUTO_MUTE:
            try:
                await client.restrict_chat_member(
                    message.chat.id,
                    message.from_user.id,
                    permissions=ChatPermissions(),  # Tidak ada izin
                    until_date=int(message.date.timestamp()) + MUTE_DURATION
                )
                await client.send_message(
                    message.chat.id,
                    f"Bot {message.from_user.mention} dimute selama {MUTE_DURATION // 60} menit karena gcast."
                )
            except Exception as e:
                print(f"Gagal mute bot: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply("Bot Anti-Gcast Aktif!\nSaya akan menghapus dan membisukan atau memblokir bot yang mengirim pesan global (gcast).")

app.run()
