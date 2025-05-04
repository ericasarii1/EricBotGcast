from pyrogram import Client, filters

app = Client("anti_gcast_bot", bot_token="TOKEN_KAMU", api_id=12345, api_hash="HASH_KAMU")

GCAST_IDS = [-1001234567890, 777000, 123456789]  # contoh ID gcast spammer

@app.on_message(filters.group)
def delete_gcast_messages(client, message):
    if message.from_user and message.from_user.id in GCAST_IDS:
        message.delete()

app.run()
