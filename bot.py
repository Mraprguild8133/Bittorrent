import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, RPCError

# Import configuration
from config import config

# External library imports
try:
    import boto3
    from botocore.config import Config
except ImportError:
    print("Please install required libraries: pip install pyrogram tgcrypto boto3")
    exit(1)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Pyrogram Client Initialization ---
app = Client(
    "media_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# --- Wasabi Client Setup ---
def initialize_wasabi_client():
    """Initialize Wasabi client if credentials are provided."""
    if not all([config.WASABI_ACCESS_KEY, config.WASABI_SECRET_KEY, config.WASABI_BUCKET]):
        logger.warning("Wasabi credentials incomplete. Upload features disabled.")
        return None
    
    try:
        s3_config = Config(
            region_name=config.WASABI_REGION,
            signature_version='s3v4',
        )
        
        client = boto3.client(
            's3',
            endpoint_url=f"https://s3.{config.WASABI_REGION}.wasabisys.com",
            aws_access_key_id=config.WASABI_ACCESS_KEY,
            aws_secret_access_key=config.WASABI_SECRET_KEY,
            config=s3_config
        )
        logger.info(f"Wasabi client initialized for bucket: {config.WASABI_BUCKET}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Wasabi client: {e}")
        return None

WASABI_CLIENT = initialize_wasabi_client()

# --- Helper Functions ---
async def progress_callback(current, total, client, message, start_time):
    """Updates the message with download/upload progress."""
    try:
        percentage = (current / total) * 100
        speed = current / (asyncio.get_event_loop().time() - start_time) if current > 0 else 0
        
        text = (
            f"**Progress:** {current / (1024 * 1024):.2f} MB / {total / (1024 * 1024):.2f} MB\n"
            f"**Percentage:** {percentage:.1f}%\n"
            f"**Speed:** {speed / (1024 * 1024):.2f} MB/s"
        )
        
        await client.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.id,
            text=text
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except RPCError:
        pass

def validate_file_size(file_size: int) -> bool:
    """Check if file size is within limits."""
    max_size_bytes = config.MAX_FILE_SIZE * 1024 * 1024
    return file_size <= max_size_bytes

async def upload_to_wasabi(client: Client, chat_id: int, file_path: str):
    """Uploads a local file to Wasabi bucket."""
    if not WASABI_CLIENT:
        await client.send_message(chat_id, "❌ Wasabi upload is disabled due to missing credentials.")
        return

    wasabi_key = f"uploads/{os.path.basename(file_path)}"
    
    try:
        status_msg = await client.send_message(chat_id, f"**Starting upload to Wasabi:** `{wasabi_key}`...")
        
        def sync_upload():
            WASABI_CLIENT.upload_file(
                file_path, 
                config.WASABI_BUCKET, 
                wasabi_key,
                ExtraArgs={'ACL': 'public-read'}  # Make files publicly accessible
            )

        await asyncio.get_event_loop().run_in_executor(None, sync_upload)

        wasabi_url = f"https://s3.{config.WASABI_REGION}.wasabisys.com/{config.WASABI_BUCKET}/{wasabi_key}"
        
        await status_msg.edit_text(
            f"✅ **Upload Complete!**\n"
            f"**File:** `{os.path.basename(file_path)}`\n"
            f"**Direct Link:** [Download]({wasabi_url})"
        )

    except Exception as e:
        await client.send_message(chat_id, f"❌ Wasabi Upload Failed: `{e}`")
    finally:
        # Clean up local file
        if os.path.exists(file_path):
            os.remove(file_path)

# --- Bot Command Handlers ---
@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handles the /start command."""
    features = [
        "✅ Download restricted content",
        "✅ Convert videos (MP4/MKV)",
        "✅ Mirror to Wasabi cloud storage",
        "✅ Custom file naming",
        "✅ Progress tracking"
    ]
    
    await message.reply_text(
        "👋 **Welcome to Media Handler Bot!**\n\n"
        "**Available Features:**\n" + "\n".join(features) + "\n\n"
        "**Commands:**\n"
        "• `/download [url]` - Download from links\n"
        "• `/convert mp4` - Convert replied video\n"
        "• `/mirror` - Upload to Wasabi\n\n"
        f"**User ID:** `{message.from_user.id}`"
    )

@app.on_message(filters.command("mirror") & filters.reply)
async def mirror_command(client: Client, message: Message):
    """Mirror replied file to Wasabi."""
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply_text("❌ Please reply to a file to mirror it.")
        return

    # Extract file information
    if message.reply_to_message.video:
        file_id = message.reply_to_message.video.file_id
        file_size = message.reply_to_message.video.file_size
    elif message.reply_to_message.document:
        file_id = message.reply_to_message.document.file_id
        file_size = message.reply_to_message.document.file_size
    else:
        await message.reply_text("❌ Unsupported media type.")
        return

    # Validate file size
    if not validate_file_size(file_size):
        await message.reply_text(
            f"❌ File too large. Max size: {config.MAX_FILE_SIZE}MB"
        )
        return

    # Download and upload
    await handle_download_and_process(client, message, file_id)

async def handle_download_and_process(client: Client, message: Message, file_id: str):
    """Download file and upload to Wasabi."""
    os.makedirs(config.DOWNLOAD_PATH, exist_ok=True)
    
    status_msg = await client.send_message(message.chat.id, "⬇️ **Starting download...**")
    start_time = asyncio.get_event_loop().time()
    
    try:
        local_path = await client.download_media(
            file_id,
            file_name=config.DOWNLOAD_PATH,
            progress=progress_callback,
            progress_args=(client, status_msg, start_time)
        )
        
        if local_path:
            await status_msg.edit_text(f"✅ **Download Complete!**\nStarting upload...")
            await upload_to_wasabi(client, message.chat.id, local_path)
        else:
            await status_msg.edit_text("❌ Download failed.")
            
    except Exception as e:
        logger.error(f"Processing error: {e}")
        await status_msg.edit_text(f"❌ **Error:** {str(e)}")

# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Starting Media Handler Bot...")
    logger.info(f"Download path: {config.DOWNLOAD_PATH}")
    logger.info(f"Max file size: {config.MAX_FILE_SIZE}MB")
    logger.info(f"Wasabi enabled: {WASABI_CLIENT is not None}")
    
    app.run()
