import asyncio
import aiohttp
from qbittorrent import Client
from config import config

class QBitTorrentClient:
    def __init__(self):
        self.client = None
        self.connected = False
    
    async def connect(self):
        """Connect to qBittorrent Web UI"""
        try:
            self.client = Client(config.QBIT_HOST)
            self.client.login(config.QBIT_USERNAME, config.QBIT_PASSWORD)
            self.connected = True
            print("✅ Connected to qBittorrent")
        except Exception as e:
            print(f"❌ Failed to connect to qBittorrent: {e}")
            self.connected = False
    
    async def add_torrent(self, torrent_content, category="telegram"):
        """Add torrent from file content or magnet link"""
        if not self.connected:
            await self.connect()
        
        try:
            # Try as magnet link first
            if torrent_content.startswith("magnet:"):
                self.client.download_from_link(torrent_content, category=category)
            else:
                # Assume it's torrent file content
                self.client.download_from_file(torrent_content, category=category)
            
            return True, "Torrent added successfully"
        except Exception as e:
            return False, f"Failed to add torrent: {e}"
    
    async def get_torrents(self):
        """Get list of all torrents"""
        if not self.connected:
            await self.connect()
        
        return self.client.torrents()
    
    async def get_torrent_info(self, hash):
        """Get detailed info about a torrent"""
        if not self.connected:
            await self.connect()
        
        return self.client.get_torrent(hash)
    
    async def pause_torrent(self, hash):
        """Pause a torrent"""
        if not self.connected:
            await self.connect()
        
        self.client.pause(hash)
    
    async def resume_torrent(self, hash):
        """Resume a torrent"""
        if not self.connected:
            await self.connect()
        
        self.client.resume(hash)
    
    async def delete_torrent(self, hash, delete_files=False):
        """Delete a torrent"""
        if not self.connected:
            await self.connect()
        
        self.client.delete(hash, delete_files=delete_files)

# Global instance
qbit_client = QBitTorrentClient()
