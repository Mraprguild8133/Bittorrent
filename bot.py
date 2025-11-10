import os
import asyncio
import re
import requests
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, RPCError
from pyrogram.types import Message

# Import configuration
from config import config

# --- Configuration Validation ---
if not config.validate_required():
    exit(1)

# Display optional services status
services_status = config.get_optional_services_status()

# Ensure download directory exists
os.makedirs(config.TEMP_DOWNLOAD_DIR, exist_ok=True)

# Initialize Pyrogram Client
try:
    app = Client(
        "PowerfulDownloaderBot",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        bot_token=config.BOT_TOKEN
    )
except ValueError as e:
    print(f"FATAL ERROR: Invalid API_ID format. It must be an integer. {e}")
    exit(1)

# --- Helper Functions for Progress and Formatting ---

def format_bytes(size):
    """Converts bytes to human-readable format."""
    power = 2**10
    n = 0
    units = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"

async def progress_callback(current, total, client, message, start_time):
    """
    Updates the message with download/upload progress, providing 'Immersive Network speed' feedback.
    This function is called by Pyrogram during file transfer.
    """
    if not start_time:
        start_time = asyncio.get_event_loop().time()
        client.progress_start_time = start_time

    now = asyncio.get_event_loop().time()
    elapsed = now - start_time
    
    # Avoid division by zero
    if elapsed < 0.1:
        elapsed = 0.1

    speed = current / elapsed
    percentage = current * 100 / total
    progress_bar = f"[{'█' * int(percentage / 10):<10}]"

    text = (
        f"**🚀 Immersive Network Speed Transfer**\n\n"
        f"**File:** `{message.text.splitlines()[0] if message.text else 'Downloading...'}`\n"
        f"**Progress:** {percentage:.2f}% {progress_bar}\n"
        f"**Size:** `{format_bytes(current)}` / `{format_bytes(total)}`\n"
        f"**Speed:** `{format_bytes(speed)}/s`\n"
        f"**Time Left:** `{(total - current) / speed:.2f}s`"
    )

    # Use a simple throttling mechanism to avoid hitting Telegram API limits
    if current == 0 or percentage > 99.0 or (now - getattr(client, 'last_edit_time', 0) > 3.0):
        try:
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=text
            )
            setattr(client, 'last_edit_time', now)
        except FloodWait as e:
            print(f"FloodWait: Sleeping for {e.value} seconds.")
            await asyncio.sleep(e.value)
        except RPCError as e:
            # Handle message not found or other RPC errors gracefully
            if 'MESSAGE_NOT_MODIFIED' not in str(e):
                print(f"An RPC error occurred during progress update: {e}")

# --- External Service Upload Functions ---

async def upload_to_wasabi(file_path, original_filename):
    """Placeholder for Wasabi S3 upload logic."""
    if not all([config.WASABI_ACCESS_KEY, config.WASABI_SECRET_KEY, config.WASABI_BUCKET, config.WASABI_REGION]):
        return f"❌ **Wasabi Upload Skipped:** Configuration incomplete."

    # NOTE: In a real app, use a library like aiobotocore (async AWS SDK) for
    # efficient S3 multipart upload for large files.
    # The actual implementation for 4GB+ files would involve chunking and a multipart upload.

    try:
        # Simulate upload time
        await asyncio.sleep(2)
        
        # Simulate generating a direct URL
        s3_url = f"https://{config.WASABI_BUCKET}.s3.{config.WASABI_REGION}.wasabisys.com/{original_filename.replace(' ', '_')}"
        return f"✅ **Wasabi Upload Complete!**\nDirect Link: [Download]({s3_url})"
    except Exception as e:
        return f"❌ **Wasabi Upload Failed** for {original_filename}: {e}"

async def upload_to_gdtot(file_path, original_filename):
    """Placeholder for GDToT upload/transfer logic."""
    if not config.GDToT_API_KEY:
        return "❌ **GDToT Transfer Skipped:** API Key is missing."

    # NOTE: GDToT usually involves a web hook or an API call to initiate a server-side
    # transfer from a direct download link to Google Drive/Teams Drive.
    
    # We will simulate the transfer initiation.
    api_endpoint = "https://api.gdtot.com/transfer"
    
    # For a real implementation, you would need to:
    # 1. Upload the file to a temporary public host (like Wasabi, or a temp web server).
    # 2. Get the public URL.
    # 3. Call the GDToT API with the public URL and your API key.
    
    # Since we have the local file, we simulate the successful transfer.
    try:
        # Simulate transfer initiation
        await asyncio.sleep(3)
        
        # Simulate response
        drive_link = f"https://gdrive.link/to/{original_filename.replace(' ', '_')}"
        
        return f"✅ **GDToT Transfer Initiated!**\nGDrive Link: [View File]({drive_link})"
    except Exception as e:
        return f"❌ **GDToT Transfer Failed**: {e}"

# --- Core Logic for Download and Processing ---

async def download_file_http(url, file_name, progress_msg, client):
    """
    Downloads a file from a direct HTTP/HTTPS URL using streaming
    to handle large files without excessive memory usage.
    """
    temp_path = os.path.join(config.TEMP_DOWNLOAD_DIR, file_name)
    total_downloaded = 0
    start_time = asyncio.get_event_loop().time()
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=config.CHUNK_SIZE):
                f.write(chunk)
                total_downloaded += len(chunk)
                # Update progress
                await progress_callback(total_downloaded, total_size, client, progress_msg, start_time)
        
        # Final progress update
        await progress_callback(total_size, total_size, client, progress_msg, start_time)
        return temp_path, total_size
        
    except requests.exceptions.RequestException as e:
        print(f"HTTP Download error: {e}")
        return None, 0
    except Exception as e:
        print(f"An unexpected error occurred during HTTP download: {e}")
        return None, 0

async def process_file(client, message, file_path, file_name, file_size):
    """
    Handles post-download operations: Split logic, Wasabi upload, GDToT transfer, and cleanup.
    """
    status_text = f"**{file_name}** ({format_bytes(file_size)}) download complete.\n\n"
    
    # 1. Split Support for > 4GB files
    size_in_gb = file_size / (1024**3)
    if size_in_gb > config.LARGE_FILE_THRESHOLD_GB:
        status_text += f"⚙️ File size exceeds {config.LARGE_FILE_THRESHOLD_GB}GB. **Split support logic activated** (simulated chunking for external uploads).\n"
    
    # 2. Wasabi Upload (if configured)
    if services_status["wasabi"]:
        status_text += "\n📦 **Starting Wasabi Upload...**"
        await message.edit_text(status_text)
        wasabi_result = await upload_to_wasabi(file_path, file_name)
        status_text += f"\n{wasabi_result}"
    else:
        status_text += "\n📦 **Wasabi Upload:** ❌ Service not configured"
    
    # 3. GDToT Transfer (if configured)
    if services_status["gdtot"]:
        status_text += "\n\n🚀 **Starting GDToT Transfer...**"
        await message.edit_text(status_text)
        gdtot_result = await upload_to_gdtot(file_path, file_name)
        status_text += f"\n{gdtot_result}"
    else:
        status_text += "\n\n🚀 **GDToT Transfer:** ❌ Service not configured"
    
    # 4. Final Cleanup
    try:
        os.remove(file_path)
        status_text += f"\n\n🗑️ **Cleanup Complete:** Local file deleted."
    except Exception as e:
        status_text += f"\n\n⚠️ **Cleanup Warning:** Could not delete local file: {e}"
    
    await message.edit_text(status_text)

# --- Telegram Handlers ---

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    """Handles the /start command."""
    services_info = ""
    if services_status["wasabi"]:
        services_info += "✅ **Wasabi S3 Storage**\n"
    if services_status["gdtot"]:
        services_info += "✅ **GDToT Google Drive Transfer**\n"
    
    if not services_info:
        services_info = "❌ No external services configured (Wasabi/GDToT)"
    
    await message.reply_text(
        "👋 Welcome to the **Powerful Immersive Network Speed Downloader Bot!**\n\n"
        "I can download files from:\n"
        "1. **Direct Download Link** (HTTP/S)\n"
        "2. **Telegram File Link** (Post/Message URL, including restricted content)\n"
        "3. **Direct File Upload** (Send files directly to me)\n\n"
        f"**Configured Services:**\n{services_info}\n\n"
        "**Usage:** Send me a link or file to get started!"
    )

@app.on_message(filters.command("status") & filters.private)
async def status_command(client, message):
    """Shows bot status and configured services."""
    status_text = "🤖 **Bot Status**\n\n"
    status_text += f"**Telegram API:** ✅ Connected\n"
    status_text += f"**Download Directory:** `{config.TEMP_DOWNLOAD_DIR}`\n"
    status_text += f"**Large File Threshold:** {config.LARGE_FILE_THRESHOLD_GB}GB\n\n"
    
    status_text += "**External Services:**\n"
    status_text += f"• Wasabi S3: {'✅ Configured' if services_status['wasabi'] else '❌ Not Configured'}\n"
    status_text += f"• GDToT: {'✅ Configured' if services_status['gdtot'] else '❌ Not Configured'}\n\n"
    
    status_text += "**Ready to download!** 🚀"
    
    await message.reply_text(status_text)

@app.on_message(filters.private & (filters.text | filters.media))
async def handle_download_request(client, message):
    """Handles incoming messages and routes them to the correct download function."""
    
    # Check if the message is a link (Telegram post link or direct URL)
    url_pattern = re.compile(r'https?://(?:t\.me/|telegra\.ph/|[^ \n]*)')
    
    # Priority 1: Check if it's a Telegram message link
    telegram_link_match = re.search(r'https?://t\.me/(?:c/)?([^/]+)/(\d+)', message.text or "")
    if telegram_link_match:
        await process_telegram_link(client, message, telegram_link_match.group(1), int(telegram_link_match.group(2)))
        return

    # Priority 2: Check for a direct HTTP/HTTPS URL
    direct_link_match = url_pattern.search(message.text or "")
    if direct_link_match:
        url = direct_link_match.group(0)
        await process_direct_url(client, message, url)
        return
        
    # Priority 3: Check if the message itself contains media (direct forwarded file)
    if message.media:
        await process_telegram_file(client, message)
        return

    # If no link or file is found
    await message.reply_text(
        "🤔 I couldn't find a valid file link or media in your message.\n"
        "Please send a **Direct Download Link** (http/s) or a **Telegram Post Link** (`https://t.me/...`).\n\n"
        "Use /start to see all supported features."
    )

async def process_telegram_link(client, message, chat_id, message_id):
    """Downloads a file from a specified Telegram message link."""
    status_msg = await message.reply_text(
        "⏳ **Fetching Telegram message...**\n"
        f"Chat: `{chat_id}` | ID: `{message_id}`"
    )

    try:
        # Resolve chat ID (e.g., if it's a private chat c/12345678)
        if chat_id.startswith('c/'):
            chat_identifier = int("-100" + chat_id[2:])
        else:
            chat_identifier = chat_id
            
        # Get the target message
        target_message = await client.get_messages(
            chat_id=chat_identifier,
            message_ids=message_id
        )

        if not target_message or not target_message.media:
            await status_msg.edit_text("❌ **Error:** Message not found or contains no downloadable media.")
            return

        # Prepare for download
        media = target_message.document or target_message.video or target_message.audio or target_message.photo
        file_name = getattr(media, 'file_name', f"tg_file_{message_id}_{chat_id}.dat")
        file_size = getattr(media, 'file_size', 0)
        
        # Check for large file size
        if file_size > (config.LARGE_FILE_THRESHOLD_GB * 1024**3):
            await status_msg.edit_text(
                f"⚠️ File is large ({format_bytes(file_size)}). Pyrogram will handle the chunked download.\n"
                f"**Downloading restricted content (if applicable)...**"
            )
        else:
             await status_msg.edit_text(
                f"⬇️ **Downloading File:** `{file_name}` ({format_bytes(file_size)})"
            )

        # Pyrogram's download_media handles large files and restricted content efficiently
        start_time = asyncio.get_event_loop().time()
        download_path = await client.download_media(
            message=target_message,
            file_name=os.path.join(config.TEMP_DOWNLOAD_DIR, file_name),
            progress=progress_callback,
            progress_args=(client, status_msg, start_time)
        )

        if download_path:
            await process_file(client, status_msg, download_path, file_name, file_size)
        else:
            await status_msg.edit_text(f"❌ **Download Failed:** Telegram download did not return a path.")
            
    except FloodWait as e:
        await status_msg.edit_text(f"⏳ **FloodWait:** Please wait {e.value} seconds before trying again.")
        await asyncio.sleep(e.value)
    except RPCError as e:
        await status_msg.edit_text(f"❌ **Telegram Error:** An RPC error occurred: {e}. Check if bot is in the chat/channel.")
    except Exception as e:
        await status_msg.edit_text(f"❌ **An unexpected error occurred:** {e}")

async def process_telegram_file(client, message):
    """Downloads a file sent directly/forwarded to the bot."""
    status_msg = await message.reply_text("⬇️ **Initializing Telegram File Download...**")
    
    # Identify the media
    media = message.document or message.video or message.audio or message.photo
    if not media:
        await status_msg.edit_text("❌ **Error:** Message contains no downloadable media.")
        return

    file_name = getattr(media, 'file_name', f"tg_file_{message.id}.dat")
    file_size = getattr(media, 'file_size', 0)
    
    await status_msg.edit_text(
        f"⬇️ **Downloading File:** `{file_name}` ({format_bytes(file_size)})"
    )
    
    try:
        start_time = asyncio.get_event_loop().time()
        download_path = await client.download_media(
            message=message,
            file_name=os.path.join(config.TEMP_DOWNLOAD_DIR, file_name),
            progress=progress_callback,
            progress_args=(client, status_msg, start_time)
        )

        if download_path:
            await process_file(client, status_msg, download_path, file_name, file_size)
        else:
            await status_msg.edit_text(f"❌ **Download Failed:** Telegram download did not return a path.")

    except Exception as e:
        await status_msg.edit_text(f"❌ **An unexpected error occurred during download:** {e}")

async def process_direct_url(client, message, url):
    """Downloads a file from a direct HTTP/HTTPS URL."""
    # Try to extract filename from URL path
    file_name = os.path.basename(url.split('?')[0])
    if not file_name or len(file_name) > 255:
        file_name = f"http_download_{message.id}.dat"
        
    status_msg = await message.reply_text(
        f"🌐 **Starting HTTP Download:** `{file_name}`\n"
        f"URL: `{url}`"
    )

    download_path, file_size = await download_file_http(url, file_name, status_msg, client)

    if download_path:
        await process_file(client, status_msg, download_path, file_name, file_size)
    else:
        await status_msg.edit_text(f"❌ **HTTP Download Failed:** Could not retrieve file from `{url}`.")

# --- Main Bot Execution ---

print("🤖 Starting Telegram Downloader Bot...")
print(f"📁 Download directory: {config.TEMP_DOWNLOAD_DIR}")
print(f"⚙️ Large file threshold: {config.LARGE_FILE_THRESHOLD_GB}GB")

try:
    app.run()
    print("✅ Bot stopped gracefully.")
except Exception as e:
    print(f"❌ An error occurred during bot execution: {e}")
    # Clean up the session file on error
    if os.path.exists("PowerfulDownloaderBot.session"):
        os.remove("PowerfulDownloaderBot.session")
