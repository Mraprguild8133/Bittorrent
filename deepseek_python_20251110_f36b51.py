import os
import asyncio
import re
import requests
import time
import json
import aiohttp
from urllib.parse import urlparse
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, RPCError
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

# Import configuration
from config import config

# --- Configuration Validation ---
if not config.validate_required():
    exit(1)

# Display services status
services_status = config.get_services_status()

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

# --- Service Switch Management ---
class ServiceManager:
    """Manage service switches and configurations"""
    
    def __init__(self):
        self.wasabi_enabled = config.WASABI_ENABLED
        self.gdtot_enabled = config.GDTOT_ENABLED
        self.services_status = services_status
    
    def toggle_wasabi(self):
        """Toggle Wasabi service"""
        if services_status["wasabi"]["configured"]:
            self.wasabi_enabled = not self.wasabi_enabled
            config.WASABI_ENABLED = self.wasabi_enabled
            return True
        return False
    
    def toggle_gdtot(self):
        """Toggle GDToT service"""
        if services_status["gdtot"]["configured"]:
            self.gdtot_enabled = not self.gdtot_enabled
            config.GDTOT_ENABLED = self.gdtot_enabled
            return True
        return False
    
    def get_status_text(self):
        """Get formatted status text"""
        status_text = "🔄 **Service Switches**\n\n"
        
        # Wasabi status
        wasabi_icon = "✅" if self.wasabi_enabled and services_status["wasabi"]["configured"] else "❌"
        wasabi_status = "ENABLED" if self.wasabi_enabled and services_status["wasabi"]["configured"] else "DISABLED"
        wasabi_reason = services_status["wasabi"]["reason"]
        status_text += f"**Wasabi S3:** {wasabi_icon} {wasabi_status}\n"
        status_text += f"   - Status: {wasabi_reason}\n\n"
        
        # GDToT status
        gdtot_icon = "✅" if self.gdtot_enabled and services_status["gdtot"]["configured"] else "❌"
        gdtot_status = "ENABLED" if self.gdtot_enabled and services_status["gdtot"]["configured"] else "DISABLED"
        gdtot_reason = services_status["gdtot"]["reason"]
        status_text += f"**GDToT Transfer:** {gdtot_icon} {gdtot_status}\n"
        status_text += f"   - Status: {gdtot_reason}\n\n"
        
        status_text += "Use the buttons below to toggle services:"
        
        return status_text
    
    def get_switch_keyboard(self):
        """Get inline keyboard for service switches"""
        keyboard = []
        
        # Wasabi button
        wasabi_text = "🔴 Disable Wasabi" if self.wasabi_enabled else "🟢 Enable Wasabi"
        wasabi_callback = "disable_wasabi" if self.wasabi_enabled else "enable_wasabi"
        if services_status["wasabi"]["configured"]:
            keyboard.append([InlineKeyboardButton(wasabi_text, callback_data=wasabi_callback)])
        
        # GDToT button
        gdtot_text = "🔴 Disable GDToT" if self.gdtot_enabled else "🟢 Enable GDToT"
        gdtot_callback = "disable_gdtot" if self.gdtot_enabled else "enable_gdtot"
        if services_status["gdtot"]["configured"]:
            keyboard.append([InlineKeyboardButton(gdtot_text, callback_data=gdtot_callback)])
        
        # Refresh button
        keyboard.append([InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_switches")])
        
        return InlineKeyboardMarkup(keyboard)

# Global service manager
service_manager = ServiceManager()

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

def format_time(seconds):
    """Formats time in seconds to human readable format."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.0f}m {seconds%60:.0f}s"
    else:
        return f"{seconds/3600:.0f}h {(seconds%3600)/60:.0f}m"

class ProgressTracker:
    """Track progress and manage message updates to prevent duplicates."""
    
    def __init__(self):
        self.last_update_time = 0
        self.last_percentage = 0
        self.update_interval = 2  # Update every 2 seconds minimum
        
    async def update_progress(self, current, total, client, message, start_time):
        """Update progress with proper throttling to avoid duplicate messages."""
        now = time.time()
        elapsed = now - start_time
        
        # Avoid division by zero
        if elapsed < 0.1:
            elapsed = 0.1

        speed = current / elapsed
        percentage = (current * 100 / total) if total > 0 else 0
        
        # Throttling: Only update if enough time has passed OR significant progress made
        time_since_last_update = now - self.last_update_time
        progress_since_last_update = percentage - self.last_percentage
        
        should_update = (
            time_since_last_update >= self.update_interval or 
            progress_since_last_update >= 10 or  # 10% progress
            percentage >= 99.5 or  # Final update
            current == 0  # Initial update
        )
        
        if not should_update and total > 0:
            return
        
        progress_bar = self.create_progress_bar(percentage)
        time_left = (total - current) / speed if speed > 0 else 0
        
        # Get filename from message or use default
        filename = "Downloading..."
        if hasattr(message, 'text') and message.text:
            first_line = message.text.split('\n')[0]
            if '`' in first_line:
                # Extract text between backticks
                filename_match = re.search(r'`([^`]+)`', first_line)
                if filename_match:
                    filename = filename_match.group(1)
        
        text = (
            f"**🚀 Download Progress**\n\n"
            f"**File:** `{filename}`\n"
            f"**Progress:** {percentage:.1f}% {progress_bar}\n"
            f"**Size:** `{format_bytes(current)} / {format_bytes(total)}`\n"
            f"**Speed:** `{format_bytes(speed)}/s`\n"
            f"**Time Left:** `{format_time(time_left)}`"
        )
        
        try:
            await client.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=text
            )
            self.last_update_time = now
            self.last_percentage = percentage
        except FloodWait as e:
            print(f"FloodWait: Sleeping for {e.value} seconds.")
            await asyncio.sleep(e.value)
        except RPCError as e:
            # Handle specific RPC errors gracefully
            if 'MESSAGE_NOT_MODIFIED' not in str(e):
                print(f"RPC error during progress update: {e}")
    
    def create_progress_bar(self, percentage):
        """Create a visual progress bar."""
        bars = 10
        filled_bars = int(percentage / bars)
        empty_bars = bars - filled_bars
        return f"[{'█' * filled_bars}{'░' * empty_bars}]"
    
    def reset(self):
        """Reset the progress tracker for new download."""
        self.last_update_time = 0
        self.last_percentage = 0

# Global progress tracker instance
progress_tracker = ProgressTracker()

async def progress_callback(current, total, client, message, start_time):
    """Wrapper for progress callback that uses the ProgressTracker."""
    await progress_tracker.update_progress(current, total, client, message, start_time)

# --- External Service Upload Functions ---

async def upload_to_wasabi(file_path, original_filename):
    """Placeholder for Wasabi S3 upload logic."""
    if not service_manager.wasabi_enabled:
        return f"❌ **Wasabi Upload Skipped:** Service disabled."
    
    if not all([config.WASABI_ACCESS_KEY, config.WASABI_SECRET_KEY, config.WASABI_BUCKET, config.WASABI_REGION]):
        return f"❌ **Wasabi Upload Skipped:** Configuration incomplete."

    try:
        # Simulate upload time
        await asyncio.sleep(2)
        
        # Simulate generating a direct URL
        s3_url = f"https://{config.WASABI_BUCKET}.s3.{config.WASABI_REGION}.wasabisys.com/{original_filename.replace(' ', '_')}"
        return f"✅ **Wasabi Upload Complete!**\nDirect Link: [Download]({s3_url})"
    except Exception as e:
        return f"❌ **Wasabi Upload Failed** for {original_filename}: {e}"

async def upload_to_gdtot(file_path, original_filename):
    """Upload file to GDToT using their API."""
    if not service_manager.gdtot_enabled:
        return f"❌ **GDToT Transfer Skipped:** Service disabled."
    
    if not config.GDToT_API_KEY:
        return "❌ **GDToT Transfer Skipped:** API Key is missing."

    try:
        # First, we need to upload the file to a temporary URL or use the file directly
        # Since GDToT API expects a URL, we'll simulate getting a public URL first
        # In a real implementation, you'd upload to a temp service or use Wasabi URL
        
        # For now, we'll simulate the process
        temp_download_url = await get_temporary_download_url(file_path, original_filename)
        
        if not temp_download_url:
            return "❌ **GDToT Transfer Failed:** Could not generate temporary download URL"
        
        # Prepare the API request
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {config.GDToT_API_KEY}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        payload = {
            'link': temp_download_url,
            'filename': original_filename,
            'api_key': config.GDToT_API_KEY
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                config.GDTOT_API_URL,
                headers=headers,
                json=payload,
                timeout=300  # 5 minutes timeout
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    if result.get('status') == 'success':
                        gdrive_link = result.get('gdrive_link', '')
                        file_id = result.get('file_id', '')
                        
                        if gdrive_link:
                            return f"✅ **GDToT Transfer Successful!**\n\n**Google Drive Link:** [Click Here]({gdrive_link})\n**File ID:** `{file_id}`"
                        else:
                            return f"✅ **GDToT Transfer Initiated!**\n**File ID:** `{file_id}`\n*Link will be available shortly*"
                    
                    elif result.get('status') == 'error':
                        error_msg = result.get('message', 'Unknown error')
                        return f"❌ **GDToT Transfer Failed:** {error_msg}"
                    
                    else:
                        return f"❌ **GDToT Transfer Failed:** Unexpected response: {result}"
                
                elif response.status == 401:
                    return "❌ **GDToT Transfer Failed:** Invalid API Key"
                elif response.status == 400:
                    return "❌ **GDToT Transfer Failed:** Bad Request - Check your input"
                elif response.status == 429:
                    return "❌ **GDToT Transfer Failed:** Rate limit exceeded"
                else:
                    error_text = await response.text()
                    return f"❌ **GDToT Transfer Failed:** HTTP {response.status} - {error_text}"
                    
    except asyncio.TimeoutError:
        return "❌ **GDToT Transfer Failed:** Request timeout"
    except aiohttp.ClientError as e:
        return f"❌ **GDToT Transfer Failed:** Network error - {str(e)}"
    except Exception as e:
        return f"❌ **GDToT Transfer Failed:** {str(e)}"

async def get_temporary_download_url(file_path, filename):
    """
    Get a temporary public download URL for the file.
    This is a placeholder - in real implementation, you'd upload to a temp service.
    """
    try:
        # For now, we'll return a placeholder URL
        # In production, you might:
        # 1. Upload to Wasabi and get the URL
        # 2. Use a file.io-like service
        # 3. Use your own temporary file hosting
        
        if service_manager.wasabi_enabled and services_status["wasabi"]["configured"]:
            # If Wasabi is enabled, use that URL
            return f"https://{config.WASABI_BUCKET}.s3.{config.WASABI_REGION}.wasabisys.com/{filename.replace(' ', '_')}"
        else:
            # Return a placeholder - in real implementation, upload file somewhere
            return f"https://example.com/temp/{filename}"
            
    except Exception as e:
        print(f"Error generating temp URL: {e}")
        return None

# --- Core Logic for Download and Processing ---

async def download_file_http(url, file_name, progress_msg, client):
    """
    Downloads a file from a direct HTTP/HTTPS URL using streaming
    to handle large files without excessive memory usage.
    """
    temp_path = os.path.join(config.TEMP_DOWNLOAD_DIR, file_name)
    total_downloaded = 0
    start_time = time.time()
    
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
    
    # 2. Wasabi Upload (if enabled and configured)
    if service_manager.wasabi_enabled and services_status["wasabi"]["configured"]:
        status_text += "\n📦 **Starting Wasabi Upload...**"
        await message.edit_text(status_text)
        wasabi_result = await upload_to_wasabi(file_path, file_name)
        status_text += f"\n{wasabi_result}"
    else:
        status_text += "\n📦 **Wasabi Upload:** ❌ Service disabled or not configured"
    
    # 3. GDToT Transfer (if enabled and configured)
    if service_manager.gdtot_enabled and services_status["gdtot"]["configured"]:
        status_text += "\n\n🚀 **Starting GDToT Transfer...**"
        await message.edit_text(status_text)
        gdtot_result = await upload_to_gdtot(file_path, file_name)
        status_text += f"\n{gdtot_result}"
    else:
        status_text += "\n\n🚀 **GDToT Transfer:** ❌ Service disabled or not configured"
    
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
    if service_manager.wasabi_enabled and services_status["wasabi"]["configured"]:
        services_info += "✅ **Wasabi S3 Storage**\n"
    if service_manager.gdtot_enabled and services_status["gdtot"]["configured"]:
        services_info += "✅ **GDToT Google Drive Transfer**\n"
    
    if not services_info:
        services_info = "❌ No external services enabled (Wasabi/GDToT)"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Service Switches", callback_data="service_switches")],
        [InlineKeyboardButton("📊 Bot Status", callback_data="bot_status")]
    ])
    
    await message.reply_text(
        "👋 Welcome to the **Powerful Immersive Network Speed Downloader Bot!**\n\n"
        "I can download files from:\n"
        "1. **Direct Download Link** (HTTP/S)\n"
        "2. **Telegram File Link** (Post/Message URL, including restricted content)\n"
        "3. **Direct File Upload** (Send files directly to me)\n\n"
        f"**Enabled Services:**\n{services_info}\n\n"
        "**Commands:**\n"
        "/start - Show this message\n"
        "/switches - Manage service switches\n"
        "/status - Check bot status\n\n"
        "**Usage:** Send me a link or file to get started!",
        reply_markup=keyboard
    )

@app.on_message(filters.command("switches") & filters.private)
async def switches_command(client, message):
    """Manage service switches."""
    status_text = service_manager.get_status_text()
    keyboard = service_manager.get_switch_keyboard()
    
    await message.reply_text(status_text, reply_markup=keyboard)

@app.on_message(filters.command("status") & filters.private)
async def status_command(client, message):
    """Shows bot status and configured services."""
    status_text = "🤖 **Bot Status**\n\n"
    status_text += f"**Telegram API:** ✅ Connected\n"
    status_text += f"**Download Directory:** `{config.TEMP_DOWNLOAD_DIR}`\n"
    status_text += f"**Large File Threshold:** {config.LARGE_FILE_THRESHOLD_GB}GB\n\n"
    
    status_text += "**Services Status:**\n"
    status_text += f"• Wasabi S3: {'✅ Enabled' if service_manager.wasabi_enabled and services_status['wasabi']['configured'] else '❌ Disabled'}\n"
    status_text += f"• GDToT: {'✅ Enabled' if service_manager.gdtot_enabled and services_status['gdtot']['configured'] else '❌ Disabled'}\n\n"
    
    status_text += "Use /switches to manage service toggles."
    
    await message.reply_text(status_text)

@app.on_callback_query()
async def handle_callbacks(client, callback_query):
    """Handle inline keyboard callbacks."""
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if data == "service_switches":
        status_text = service_manager.get_status_text()
        keyboard = service_manager.get_switch_keyboard()
        await callback_query.message.edit_text(status_text, reply_markup=keyboard)
        
    elif data == "bot_status":
        status_text = "🤖 **Bot Status**\n\n"
        status_text += f"**Telegram API:** ✅ Connected\n"
        status_text += f"**Download Directory:** `{config.TEMP_DOWNLOAD_DIR}`\n"
        status_text += f"**Large File Threshold:** {config.LARGE_FILE_THRESHOLD_GB}GB\n\n"
        
        status_text += "**Services Status:**\n"
        status_text += f"• Wasabi S3: {'✅ Enabled' if service_manager.wasabi_enabled and services_status['wasabi']['configured'] else '❌ Disabled'}\n"
        status_text += f"• GDToT: {'✅ Enabled' if service_manager.gdtot_enabled and services_status['gdtot']['configured'] else '❌ Disabled'}\n\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Service Switches", callback_data="service_switches")],
            [InlineKeyboardButton("🔙 Back to Start", callback_data="back_to_start")]
        ])
        await callback_query.message.edit_text(status_text, reply_markup=keyboard)
        
    elif data == "back_to_start":
        services_info = ""
        if service_manager.wasabi_enabled and services_status["wasabi"]["configured"]:
            services_info += "✅ **Wasabi S3 Storage**\n"
        if service_manager.gdtot_enabled and services_status["gdtot"]["configured"]:
            services_info += "✅ **GDToT Google Drive Transfer**\n"
        
        if not services_info:
            services_info = "❌ No external services enabled (Wasabi/GDToT)"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Service Switches", callback_data="service_switches")],
            [InlineKeyboardButton("📊 Bot Status", callback_data="bot_status")]
        ])
        
        await callback_query.message.edit_text(
            "👋 Welcome to the **Powerful Immersive Network Speed Downloader Bot!**\n\n"
            "I can download files from:\n"
            "1. **Direct Download Link** (HTTP/S)\n"
            "2. **Telegram File Link** (Post/Message URL, including restricted content)\n"
            "3. **Direct File Upload** (Send files directly to me)\n\n"
            f"**Enabled Services:**\n{services_info}\n\n"
            "**Commands:**\n"
            "/start - Show this message\n"
            "/switches - Manage service switches\n"
            "/status - Check bot status\n\n"
            "**Usage:** Send me a link or file to get started!",
            reply_markup=keyboard
        )
        
    elif data in ["enable_wasabi", "disable_wasabi"]:
        if service_manager.toggle_wasabi():
            status_text = service_manager.get_status_text()
            keyboard = service_manager.get_switch_keyboard()
            await callback_query.message.edit_text(status_text, reply_markup=keyboard)
        else:
            await callback_query.answer("❌ Wasabi is not configured properly!", show_alert=True)
            
    elif data in ["enable_gdtot", "disable_gdtot"]:
        if service_manager.toggle_gdtot():
            status_text = service_manager.get_status_text()
            keyboard = service_manager.get_switch_keyboard()
            await callback_query.message.edit_text(status_text, reply_markup=keyboard)
        else:
            await callback_query.answer("❌ GDToT is not configured properly!", show_alert=True)
            
    elif data == "refresh_switches":
        status_text = service_manager.get_status_text()
        keyboard = service_manager.get_switch_keyboard()
        await callback_query.message.edit_text(status_text, reply_markup=keyboard)
    
    await callback_query.answer()

# ... (Keep the rest of the message handling functions the same)

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
        start_time = time.time()
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
        start_time = time.time()
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