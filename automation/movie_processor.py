"""
Main Movie Automation Processor
Orchestrates the entire workflow
"""
import asyncio
import httpx
from datetime import datetime
from typing import Optional, Dict
from bson import ObjectId

from .tamilmv_scraper import TamilMVScraper
from .debrid_handler import DebridHandler
from .poster_fetcher import PosterFetcher
from .ppd_uploader import PPDUploader
from .config import AUTO_NOTIFY_ADMIN, ADMIN_TELEGRAM_ID

from db import get_db


class MovieProcessor:
    def __init__(self):
        self.scraper = TamilMVScraper()
        self.debrid = DebridHandler()
        self.poster_fetcher = PosterFetcher()
        self.ppd = PPDUploader()
    
    async def process_single_movie(
        self, 
        magnet_link: str, 
        movie_title: str,
        year: Optional[int] = None
    ) -> Dict:
        """
        Process a single movie through the complete pipeline
        Returns: result dict with success status and movie_id
        """
        result = {
            "success": False,
            "movie_id": None,
            "status": "Starting...",
            "selected_quality": None,
            "selection_type": None,
            "errors": []
        }
        
        try:
            # STEP 1: Add magnet to Debrid
            print(f"\n🎬 Processing: {movie_title}")
            print("📥 Step 1: Adding to Debrid...")
            result["status"] = "Adding to Debrid"
            
            torrent_id = await self.debrid.add_magnet(magnet_link)
            if not torrent_id:
                result["errors"].append("Failed to add magnet to Debrid")
                return result
            
            # STEP 2: Wait for download (parallel with poster fetch)
            print("⏳ Step 2: Waiting for download...")
            result["status"] = "Downloading from Debrid"
            
            # Run download wait and poster fetch in parallel
            download_task = self.debrid.wait_for_download(torrent_id)
            poster_task = self.poster_fetcher.search_movie(movie_title, year)
            
            direct_link, poster_data = await asyncio.gather(
                download_task,
                poster_task
            )
            
            if not direct_link:
                result["errors"].append("Debrid download failed or timeout")
                return result
            
            # STEP 3: Upload to PPD site
            print("📤 Step 3: Uploading to PPD...")
            result["status"] = "Uploading to PPD site"
            
            ppd_result = await self.ppd.remote_upload(
                direct_link,
                f"{movie_title}_{year or 2024}.mkv"
            )
            
            if not ppd_result:
                result["errors"].append("PPD upload failed")
                return result
            
            # STEP 4: Download poster if available
            poster_url = None
            poster_path = None
            
            if poster_data and poster_data.get("poster_url"):
                print("🖼️ Step 4: Downloading poster...")
                poster_bytes = await self.poster_fetcher.download_poster(
                    poster_data["poster_url"]
                )
                
                if poster_bytes:
                    # Upload to Telegram via your existing API
                    poster_path = await self._upload_poster_to_telegram(
                        poster_bytes,
                        movie_title,
                        poster_data.get("overview", "")
                    )
            
            # STEP 5: Save to MongoDB
            print("💾 Step 5: Saving to database...")
            result["status"] = "Saving to database"
            
            movie_id = await self._save_to_database(
                title=movie_title,
                year=year,
                watch_url=ppd_result["watch_url"],
                download_url=ppd_result["download_url"],
                poster_path=poster_path,
                description=poster_data.get("overview") if poster_data else "",
                rating=poster_data.get("rating") if poster_data else None
            )
            
            if movie_id:
                result["success"] = True
                result["movie_id"] = movie_id
                result["status"] = "Complete!"
                result["selected_quality"] = "1080p"  # You can extract from magnet
                print(f"✅ SUCCESS! Movie ID: {movie_id}")
                
                # Send admin notification
                if AUTO_NOTIFY_ADMIN:
                    await self._notify_admin_success(movie_title, movie_id)
            
            return result
        
        except Exception as e:
            result["errors"].append(f"Unexpected error: {str(e)}")
            print(f"❌ Process error: {e}")
            return result
    
    async def _upload_poster_to_telegram(
        self, 
        poster_bytes: bytes, 
        title: str,
        description: str
    ) -> Optional[str]:
        """Upload poster to Telegram channel via your existing API"""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                files = {
                    "image": (f"{title}_poster.jpg", poster_bytes, "image/jpeg")
                }
                data = {
                    "movie_title": title,
                    "description": description[:200]  # Limit description
                }
                
                response = await client.post(
                    "http://127.0.0.1:8000/api/poster/upload",
                    data=data,
                    files=files
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        return result.get("url")
        
        except Exception as e:
            print(f"⚠️ Poster upload error: {e}")
        
        return None
    
    async def _save_to_database(
        self,
        title: str,
        year: Optional[int],
        watch_url: str,
        download_url: str,
        poster_path: Optional[str],
        description: str,
        rating: Optional[float]
    ) -> Optional[str]:
        """Save movie to MongoDB using your existing structure"""
        try:
            db = get_db()
            if not db:
                print("❌ MongoDB not connected")
                return None
            
            movie_doc = {
                "title": title,
                "year": year,
                "language": "Tamil",  # Default, can be detected from filename
                "languages": ["Tamil"],
                "audio_languages": ["Tamil"],
                "quality": "HD \\ 1080P",
                "category": "",  # Can be extracted from TMDb genres
                "watch_url": watch_url,
                "download_url": download_url,
                "poster_path": poster_path,
                "description": description,
                "rating": rating,
                "created_at": datetime.utcnow(),
                "auto_added": True,  # Flag to identify auto-added movies
                "trending": True  # Show in trending section
            }
            
            # Use upsert to prevent duplicates
            result = await db["movies"].update_one(
                {"title": title, "year": year},
                {"$set": movie_doc},
                upsert=True
            )
            
            if result.upserted_id:
                return str(result.upserted_id)
            else:
                # Movie already existed, get its ID
                existing = await db["movies"].find_one({"title": title, "year": year})
                return str(existing["_id"]) if existing else None
        
        except Exception as e:
            print(f"❌ Database save error: {e}")
            return None
    
    async def _notify_admin_success(self, title: str, movie_id: str):
        """Send success notification to admin via Telegram"""
        if not ADMIN_TELEGRAM_ID:
            return
        
        try:
            from config import BOT_TOKEN
            
            message = (
                f"✅ <b>Movie Auto-Added!</b>\n\n"
                f"🎬 <b>Title:</b> {title}\n"
                f"🆔 <b>ID:</b> {movie_id}\n"
                f"⏱️ <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}\n"
                f"🔗 <b>View:</b> yoursite.com/movie/{movie_id}"
            )
            
            async with httpx.AsyncClient(timeout=30) as client:
                await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": ADMIN_TELEGRAM_ID,
                        "text": message,
                        "parse_mode": "HTML"
                    }
                )
        except Exception as e:
            print(f"⚠️ Notification error: {e}")
    
    async def auto_scan_tamilmv(self, limit: int = 10) -> Dict:
        """
        Automatically scan TamilMV and process new movies
        Returns: summary of processed movies
        """
        summary = {
            "scanned": 0,
            "added": 0,
            "skipped": 0,
            "failed": 0,
            "movies": []
        }
        
        try:
            print("\n🔍 Scanning TamilMV for new movies...")
            
            # Get latest movies
            movies = await self.scraper.get_latest_movies(limit)
            summary["scanned"] = len(movies)
            
            db = get_db()
            
            for movie in movies:
                # Check if already in database
                existing = await db["movies"].find_one({
                    "title": movie["title"],
                    "year": movie["year"]
                })
                
                if existing:
                    print(f"⏭️ Skip: {movie['title']} (already exists)")
                    summary["skipped"] += 1
                    continue
                
                # Get torrent links
                torrents = await self.scraper.get_torrent_links(movie["topic_url"])
                
                if not torrents:
                    print(f"❌ No torrents found: {movie['title']}")
                    summary["failed"] += 1
                    continue
                
                # Select best torrent
                best_torrent = self.scraper.select_best_torrent(torrents)
                
                if not best_torrent:
                    print(f"⚠️ No suitable quality: {movie['title']}")
                    summary["skipped"] += 1
                    continue
                
                print(f"\n✅ Selected: {best_torrent['title']} ({best_torrent['size_gb']}GB)")
                
                # Process movie
                result = await self.process_single_movie(
                    magnet_link=best_torrent["magnet"],
                    movie_title=movie["title"],
                    year=movie["year"]
                )
                
                if result["success"]:
                    summary["added"] += 1
                    summary["movies"].append({
                        "title": movie["title"],
                        "movie_id": result["movie_id"],
                        "quality": best_torrent["title"]
                    })
                else:
                    summary["failed"] += 1
                
                # Small delay to avoid overwhelming services
                await asyncio.sleep(5)
            
            print(f"\n📊 SUMMARY: Scanned={summary['scanned']}, Added={summary['added']}, Skipped={summary['skipped']}, Failed={summary['failed']}")
            
            return summary
        
        except Exception as e:
            print(f"❌ Auto-scan error: {e}")
            return summary
