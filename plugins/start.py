from pyrogram import Client, filters
from pyrogram.types import Message
from vars import API_ID, API_HASH, BOT_TOKEN

@Client.on_message(filters.command(["start", "help"]))
async def start_command(client: Client, message: Message):
    user = message.from_user
    help_text = f"""
<b>👋 Hello {user.mention}!</b>

🤖 <b>I'm Your File Uploader Bot</b>

<b>📚 Available Commands:</b>
• /start - Show this help message
• /upload - Upload files to Telegram
• /wasabi_upload - Upload files to Wasabi Cloud
• /wasabi_files - List files in Wasabi bucket
• /stop - Stop current task
• /ping - Check bot status

<b>🚀 How to Use:</b>
1. Send /upload or /wasabi_upload
2. Upload a TXT file with download links
3. Follow the interactive steps
4. Wait for files to be processed

<b>📁 Supported Links:</b>
• Google Drive links
• YouTube videos
• Direct download links
• PDF files
• Video files

<b>⚡ Features:</b>
• Multiple quality options
• Custom captions
• Thumbnail support
• Progress tracking
• Stop/resume functionality

<code>Made with ❤️ by @VJ_Botz</code>
"""
    await message.reply_text(help_text)

@Client.on_message(filters.command("ping"))
async def ping_command(client: Client, message: Message):
    import time
    start = time.time()
    msg = await message.reply_text("🏓 **Pinging...**")
    end = time.time()
    await msg.edit(f"🏓 **Pong!**\n`{round((end - start) * 1000, 2)} ms`")

@Client.on_message(filters.command("about"))
async def about_command(client: Client, message: Message):
    about_text = """
<b>🤖 About This Bot</b>

<b>📝 Description:</b>
A powerful file uploader bot that can download files from links in TXT files and upload them to Telegram or Wasabi Cloud Storage.

<b>🛠️ Technical Details:</b>
• Built with Pyrogram
• Supports multiple file types
• Cloud storage integration
• Progress tracking
• Error handling

<b>🔧 Developer:</b>
• YouTube: @Tech_VJ
• Telegram: @KingVJ01
• Channel: @VJ_Botz

<b>💡 Source Code:</b>
Available on GitHub

<code>Version 2.0</code>
"""
    await message.reply_text(about_text)
