import time
from pyrogram import Client
from pyrogram.types import Message

class Progress:
    def __init__(self, client: Client, message: Message, operation: str):
        self.client = client
        self.message = message
        self.operation = operation
        self.start_time = time.time()
        self.last_update = 0
        self.update_interval = 1  # Update every 1 second
    
    async def update_progress(self, current, total):
        """Update progress message"""
        current_time = time.time()
        
        # Throttle updates to avoid rate limiting
        if current_time - self.last_update < self.update_interval and current != total:
            return
        
        self.last_update = current_time
        
        percentage = (current / total) * 100
        speed = current / (current_time - self.start_time) if current_time > self.start_time else 0
        elapsed = current_time - self.start_time
        eta = (total - current) / speed if speed > 0 else 0
        
        # Format sizes
        def format_size(size):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.2f} {unit}"
                size /= 1024.0
            return f"{size:.2f} TB"
        
        # Format time
        def format_time(seconds):
            if seconds < 60:
                return f"{seconds:.0f}s"
            elif seconds < 3600:
                return f"{seconds/60:.0f}m {seconds%60:.0f}s"
            else:
                return f"{seconds/3600:.0f}h {(seconds%3600)/60:.0f}m"
        
        progress_bar = self._create_progress_bar(percentage)
        
        text = (
            f"**{self.operation} Progress**\n\n"
            f"{progress_bar} {percentage:.1f}%\n\n"
            f"**Size:** {format_size(current)} / {format_size(total)}\n"
            f"**Speed:** {format_size(speed)}/s\n"
            f"**ETA:** {format_time(eta)}\n"
            f"**Elapsed:** {format_time(elapsed)}"
        )
        
        try:
            await self.message.edit_text(text)
        except Exception:
            pass  # Ignore edit errors
    
    def _create_progress_bar(self, percentage, length=20):
        """Create a visual progress bar"""
        filled = int(length * percentage / 100)
        empty = length - filled
        return "█" * filled + "░" * empty
