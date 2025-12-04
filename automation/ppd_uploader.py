"""
PPD/PPV Website Remote Upload Handler
"""
import httpx
from typing import Optional, Dict
from .config import PPD_API_KEY, PPD_API_URL


class PPDUploader:
    def __init__(self):
        self.api_key = PPD_API_KEY
        self.api_url = PPD_API_URL
    
    async def remote_upload(self, direct_link: str, filename: str) -> Optional[Dict]:
        """
        Upload file to PPD site via remote URL
        Returns: watch_url and download_url
        """
        try:
            # Note: Each PPD site has different API endpoints
            # This is a generic example - adjust for your specific PPD site
            
            payload = {
                "api_key": self.api_key,
                "url": direct_link,
                "filename": filename
            }
            
            async with httpx.AsyncClient(timeout=300) as client:  # 5 min timeout
                response = await client.post(
                    f"{self.api_url}/remote_upload",
                    data=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        file_id = data.get("file_id")
                        
                        return {
                            "watch_url": f"{self.api_url}/watch/{file_id}",
                            "download_url": f"{self.api_url}/download/{file_id}",
                            "file_id": file_id
                        }
                
                print(f"❌ PPD upload failed: {response.text}")
                return None
        
        except Exception as e:
            print(f"❌ PPD upload error: {e}")
            return None
    
    async def check_upload_status(self, file_id: str) -> Dict:
        """Check if remote upload is complete"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.api_url}/file/{file_id}/status",
                    params={"api_key": self.api_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": data.get("status"),  # pending/complete/error
                        "progress": data.get("progress", 0)
                    }
        except Exception as e:
            print(f"❌ Status check error: {e}")
        
        return {"status": "error", "progress": 0}


# Alternative: For sites without remote upload API
class ManualPPDHelper:
    """
    If your PPD site doesn't have API, this helps you upload manually
    It will download from Debrid and save locally, then you can upload
    """
    
    async def download_from_debrid(self, direct_link: str, save_path: str) -> bool:
        """Download file from Debrid link to local storage"""
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream('GET', direct_link) as response:
                    response.raise_for_status()
                    
                    with open(save_path, 'wb') as f:
                        total = 0
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            total += len(chunk)
                            if total % (10 * 1024 * 1024) == 0:  # Every 10MB
                                print(f"Downloaded: {total / (1024*1024):.1f} MB")
                    
                    print(f"✅ Download complete: {save_path}")
                    return True
        
        except Exception as e:
            print(f"❌ Download error: {e}")
            return False
