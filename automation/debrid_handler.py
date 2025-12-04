"""
Debrid-Link API Handler
"""
import httpx
import asyncio
from typing import Optional, Dict
from .config import DEBRID_API_KEY, DEBRID_API_URL


class DebridHandler:
    def __init__(self):
        self.api_key = DEBRID_API_KEY
        self.api_url = DEBRID_API_URL
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
    
    async def add_magnet(self, magnet_link: str) -> Optional[str]:
        """
        Add magnet to Debrid-Link
        Returns: torrent_id if successful
        """
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.api_url}/seedbox/add",
                    headers=self.headers,
                    data={"url": magnet_link}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        torrent_id = data.get("value", {}).get("id")
                        print(f"✅ Magnet added to Debrid: {torrent_id}")
                        return torrent_id
                
                print(f"❌ Debrid add failed: {response.text}")
                return None
        
        except Exception as e:
            print(f"❌ Debrid add error: {e}")
            return None
    
    async def get_torrent_status(self, torrent_id: str) -> Dict:
        """Check torrent download status"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.api_url}/seedbox/list",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    torrents = data.get("value", [])
                    
                    for torrent in torrents:
                        if str(torrent.get("id")) == str(torrent_id):
                            return {
                                "status": torrent.get("status"),
                                "progress": torrent.get("downloadPercent", 0),
                                "name": torrent.get("name"),
                                "size": torrent.get("totalSize")
                            }
        except Exception as e:
            print(f"❌ Status check error: {e}")
        
        return {"status": "error", "progress": 0}
    
    async def wait_for_download(self, torrent_id: str, max_wait_minutes: int = 30) -> Optional[str]:
        """
        Wait for torrent to finish downloading
        Returns: direct download link
        """
        max_attempts = max_wait_minutes * 2  # Check every 30 seconds
        
        for attempt in range(max_attempts):
            status = await self.get_torrent_status(torrent_id)
            
            if status['status'] == 'downloaded':
                # Get direct link
                link = await self.get_download_link(torrent_id)
                return link
            
            elif status['status'] == 'error':
                print(f"❌ Torrent failed: {torrent_id}")
                return None
            
            # Still downloading
            progress = status.get('progress', 0)
            print(f"⏳ Downloading: {progress}%")
            await asyncio.sleep(30)  # Wait 30 seconds
        
        print(f"⏰ Download timeout: {torrent_id}")
        return None
    
    async def get_download_link(self, torrent_id: str) -> Optional[str]:
        """Get direct download link from completed torrent"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.api_url}/seedbox/{torrent_id}/files",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    files = data.get("value", [])
                    
                    if files:
                        # Get the largest file (usually the movie)
                        largest_file = max(files, key=lambda x: x.get('size', 0))
                        download_url = largest_file.get('downloadUrl')
                        print(f"✅ Got direct link: {download_url[:50]}...")
                        return download_url
        
        except Exception as e:
            print(f"❌ Get link error: {e}")
        
        return None
