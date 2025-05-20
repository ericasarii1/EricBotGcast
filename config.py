from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
import asyncio

API_ID = 123456
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"

LOG_CHANNEL_ID = -1001234567890
AUTO_BAN = False
AUTO_MUTE = True
MUTE_DURATION = 3600
WHITELIST_BOTS = [777000, 123456789]

# Pemilik dan sudo
OWNER_ID = 123456789  # Ganti dengan ID kamu
SUDO_USERS = {123456789, 987654321}  # Tambahkan ID lain jika perlu

GCAST_KEYWORDS = ["gcast", "broadcast", "global message", "siaran", "pesan global", "/gcast"]

# Database sementara
gmute_list = set()
gban_list = set()

app = Client("antigcast_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Filter untuk owner dan sudo
def is_sudo():
    return filters.user([OWNER_ID, *SUDO_USERS])

# Auto mute/ban
@app.on_message(filters.group & filters.user(lambda _, __, msg: msg.from_user.id in gmute_list or msg.from_user.id in gban_list))
async def enforce_gmute_gban(client: Client, message: Message):
    user_id = message.from_user.id
    try:
        if user_id in gban_list:
            await client.ban_chat_member(message.chat.id, user_id)
            await message.reply(f"{message.from_user.mention} telah dibanned karena masuk daftar *GBAN*.")
        elif user_id in gmute_list:
            await client.restrict_chat_member(
                message.chat.id,
                user_id,
                permissions=ChatPermissions(),
                until_date=int(message.date.timestamp()) + MUTE_DURATION
            )
            await message.reply(f"{message.from_user.mention} telah dimute otomatis karena masuk daftar *GMUTE*.")
    except Exception as e:
        print(f"Gagal enforce gmute/gban: {e}")

# Anti-Gcast
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
                await message.reply(f"Bot {message.from_user.mention} diblokir karena gcast.")
            except Exception as e:
                print(f"Gagal ban bot: {e}")
        elif AUTO_MUTE:
            try:
                await client.restrict_chat_member(
                    message.chat.id,
                    message.from_user.id,
                    permissions=ChatPermissions(),
                    until_date=int(message.date.timestamp()) + MUTE_DURATION
                )
                await message.reply(
                    f"Bot {message.from_user.mention} dimute selama {MUTE_DURATION // 60} menit karena gcast."
                )
            except Exception as e:
                print(f"Gagal mute bot: {e}")

# Perintah GMUTE / GBAN khusus sudo/owner
@app.on_message(filters.command(["gmute", "ungmute", "gban", "ungban"]) & (filters.private | filters.group) & is_sudo())
async def handle_g_commands(client, message):
    if len(message.command) < 2:
        return await message.reply("Gunakan format: `/gmute <user_id>`", quote=True)

    action = message.command[0].lower()
    try:
        user_id = int(message.command[1])
        if action == "gmute":
            gmute_list.add(user_id)
            await message.reply(f"User `{user_id}` telah ditambahkan ke daftar *GMUTE*.")
        elif action == "ungmute":
            gmute_list.discard(user_id)
            await message.reply(f"User `{user_id}` telah dihapus dari daftar *GMUTE*.")
        elif action == "gban":
            gban_list.add(user_id)
            await message.reply(f"User `{user_id}` telah ditambahkan ke daftar *GBAN*.")
        elif action == "ungban":
            gban_list.discard(user_id)
            await message.reply(f"User `{user_id}` telah dihapus dari daftar *GBAN*.")
    except Exception as e:
        await message.reply(f"Gagal: {e}")

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "Bot Anti-Gcast Aktif!\n"
        "Saya akan menghapus dan membisukan atau memblokir bot yang mengirim pesan global (gcast).\n\n"
        "Perintah:\n"
        "/gmute <id>\n/ungmute <id>\n/gban <id>\n/ungban <id>\n\n"
        f"Owner: <code>{OWNER_ID}</code>\n"
        f"Sudo: {', '.join(str(x) for x in SUDO_USERS)}"
    )

app.run()
