import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from config import config
from torrent_client import qbit_client
from file_handler import file_handler

# Initialize Pyrogram client
app = Client(
    "qbit_leecher_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Start command
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    welcome_text = """
🤖 **qBit Leecher Bot**

A high-speed Telegram bot for torrent operations with 4GB file support!

**Available Commands:**
• /start - Show this message
• /add_torrent - Add torrent from file or magnet
• /list_torrents - Show active torrents
• /help - Show help message

**Features:**
✅ 4GB file support
✅ Real-time progress
✅ qBittorrent integration
✅ Fast async operations
    """
    
    await message.reply_text(welcome_text)

# Add torrent command
@app.on_message(filters.command("add_torrent"))
async def add_torrent_command(client, message: Message):
    if message.reply_to_message and message.reply_to_message.document:
        # Torrent file
        torrent_file = message.reply_to_message.document
        if not torrent_file.file_name.endswith('.torrent'):
            await message.reply_text("❌ Please send a .torrent file")
            return
        
        status_msg = await message.reply_text("📥 Downloading torrent file...")
        
        # Download torrent file
        torrent_path = await file_handler.download_file(
            client, status_msg, 
            message.reply_to_message.document, 
            f"temp_{torrent_file.file_name}"
        )
        
        if torrent_path:
            await status_msg.edit_text("🔗 Adding torrent to qBittorrent...")
            
            # Read torrent file content
            async with aiofiles.open(torrent_path, 'rb') as f:
                torrent_content = await f.read()
            
            # Add to qBittorrent
            success, result = await qbit_client.add_torrent(torrent_content)
            
            # Cleanup
            file_handler.cleanup_file(torrent_path)
            
            if success:
                await status_msg.edit_text("✅ Torrent added successfully!")
            else:
                await status_msg.edit_text(f"❌ {result}")
    
    elif len(message.command) > 1:
        # Magnet link
        magnet_link = message.text.split(" ", 1)[1]
        
        if not magnet_link.startswith("magnet:"):
            await message.reply_text("❌ Please provide a valid magnet link")
            return
        
        status_msg = await message.reply_text("🔗 Adding magnet link...")
        success, result = await qbit_client.add_torrent(magnet_link)
        
        if success:
            await status_msg.edit_text("✅ Magnet link added successfully!")
        else:
            await status_msg.edit_text(f"❌ {result}")
    
    else:
        await message.reply_text("""
**Usage:**
• Reply to a .torrent file with `/add_torrent`
• Or send `/add_torrent magnet_link`
        """)

# List torrents command
@app.on_message(filters.command("list_torrents"))
async def list_torrents_command(client, message: Message):
    status_msg = await message.reply_text("🔄 Fetching torrents...")
    
    try:
        torrents = await qbit_client.get_torrents()
        
        if not torrents:
            await status_msg.edit_text("📭 No active torrents")
            return
        
        torrent_list = "**Active Torrents:**\n\n"
        
        for i, torrent in enumerate(torrents[:10], 1):  # Show first 10
            progress = (torrent['progress'] * 100)
            status = "⏸️" if torrent['state'] == 'paused' else "▶️" if progress < 100 else "✅"
            
            torrent_list += (
                f"{i}. **{torrent['name']}** {status}\n"
                f"   📊 {progress:.1f}% | ⬇️ {torrent['dlspeed']/1024:.1f} KB/s\n"
                f"   📦 {file_handler._format_size(torrent['size'])}\n\n"
            )
        
        if len(torrents) > 10:
            torrent_list += f"... and {len(torrents) - 10} more torrents"
        
        await status_msg.edit_text(torrent_list)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error fetching torrents: {str(e)}")

# Handle document files for direct upload
@app.on_message(filters.document & filters.private)
async def handle_document(client, message: Message):
    # Check if user wants to add torrent
    if message.document.file_name and message.document.file_name.endswith('.torrent'):
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Add Torrent", callback_data=f"add_torrent_{message.id}")
        ]])
        await message.reply_text(
            "📥 **Torrent File Detected**\n\nClick the button below to add this torrent to qBittorrent:",
            reply_markup=keyboard
        )
    else:
        # Regular file upload with progress
        status_msg = await message.reply_text("📥 Starting download...")
        
        downloaded_file = await file_handler.download_file(
            client, status_msg, message.document, message.document.file_name
        )
        
        if downloaded_file:
            # File is already in downloads, we could process it here
            pass

# Callback query handler
@app.on_callback_query()
async def handle_callback(client, callback_query):
    data = callback_query.data
    
    if data.startswith("add_torrent_"):
        message_id = int(data.split("_")[2])
        original_message = await client.get_messages(
            callback_query.message.chat.id,
            message_id
        )
        
        if original_message and original_message.document:
            await callback_query.message.edit_text("📥 Processing torrent file...")
            await add_torrent_command(client, original_message)

# Help command
@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    help_text = """
🆘 **Help Guide**

**Adding Torrents:**
1. Send a .torrent file and reply with `/add_torrent`
2. Or send `/add_torrent your_magnet_link_here`

**Managing Torrents:**
• `/list_torrents` - View active downloads
• Files are automatically managed by qBittorrent

**File Upload:**
• Send any file to upload it with progress tracking
• Maximum file size: 4GB

**Need Help?**
Check qBittorrent Web UI for detailed management.
    """
    
    await message.reply_text(help_text)

# Initialize and start bot
async def main():
    # Connect to qBittorrent
    await qbit_client.connect()
    
    # Start the bot
    print("🚀 Starting qBit Leecher Bot...")
    await app.start()
    print("✅ Bot started successfully!")
    
    # Keep running
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
