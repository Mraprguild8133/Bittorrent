import os
import aiofiles
import asyncio
from pathlib import Path
from config import config
from progress import Progress

class FileHandler:
    def __init__(self):
        self.download_path = Path(config.DOWNLOAD_PATH)
        self.upload_path = Path(config.UPLOAD_PATH)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories"""
        self.download_path.mkdir(exist_ok=True)
        self.upload_path.mkdir(exist_ok=True)
    
    async def download_file(self, client, message, file_id, filename):
        """Download file from Telegram with progress"""
        download_path = self.download_path / filename
        
        progress = Progress(client, message, "Downloading")
        
        try:
            file = await client.download_media(
                message=file_id,
                file_name=str(download_path),
                progress=progress.update_progress,
                progress_args=(client, message, "Downloading")
            )
            
            if file:
                file_size = os.path.getsize(file)
                await message.edit_text(f"✅ Download completed!\n**File:** {filename}\n**Size:** {self._format_size(file_size)}")
                return file
            else:
                await message.edit_text("❌ Download failed!")
                return None
                
        except Exception as e:
            await message.edit_text(f"❌ Download error: {str(e)}")
            return None
    
    async def upload_file(self, client, message, file_path, caption=""):
        """Upload file to Telegram with progress"""
        progress = Progress(client, message, "Uploading")
        
        try:
            file_size = os.path.getsize(file_path)
            
            if file_size > config.MAX_FILE_SIZE:
                await message.edit_text(f"❌ File too large! Max size: {self._format_size(config.MAX_FILE_SIZE)}")
                return False
            
            await client.send_document(
                chat_id=message.chat.id,
                document=str(file_path),
                caption=caption,
                progress=progress.update_progress,
                progress_args=(client, message, "Uploading")
            )
            
            await message.delete()  # Delete progress message
            return True
            
        except Exception as e:
            await message.edit_text(f"❌ Upload error: {str(e)}")
            return False
    
    def _format_size(self, size):
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def cleanup_file(self, file_path):
        """Remove temporary file"""
        try:
            os.remove(file_path)
        except Exception:
            pass

file_handler = FileHandler()
