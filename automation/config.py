"""
Automation Configuration
Use environment variables for all secrets.
"""

import os

# ========== DEBRID SERVICE (legacy, optional) ==========
DEBRID_API_KEY = os.getenv("DEBRID_API_KEY", "")
DEBRID_API_URL = os.getenv("DEBRID_API_URL", "https://debrid-link.com/api/v2")

# ========== SEEDR (current leech engine) ==========
SEEDR_EMAIL = os.getenv("SEEDR_EMAIL", "")
SEEDR_PASSWORD = os.getenv("SEEDR_PASSWORD", "")
SEEDR_BASE_URL = os.getenv("SEEDR_BASE_URL", "https://www.seedr.cc")

# ========== PPV: LuluStream ==========
LULU_API_KEY = os.getenv("LULU_API_KEY", "")  # from LuluStream “API URL” field (key part)
LULU_API_BASE = os.getenv("LULU_API_BASE", "https://lulustream.com/api")  # adjust if they give a different base

# ========== PPD: DropGalaxy ==========
# If DropGalaxy gives a full API URL containing your token, paste it to DG_API_URL.
DG_API_URL = os.getenv("DG_API_URL", "")
DG_API_KEY = os.getenv("DG_API_KEY", "")  # keep optional in case they require a separate key

# ========== GENERIC PPD (backward compatible) ==========
PPD_API_KEY = os.getenv("PPD_API_KEY", "")
PPD_API_URL = os.getenv("PPD_API_URL", "")  # e.g., https://krakenfiles.com/api

# ========== TMDB SETTINGS ==========
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_API_URL = os.getenv("TMDB_API_URL", "https://api.themoviedb.org/3")

# ========== TAMILMV SCRAPER SETTINGS ==========
TAMILMV_BASE_URL = os.getenv("TAMILMV_BASE_URL", "https://tamilmv.re")
TAMILMV_LATEST_URL = os.getenv(
    "TAMILMV_LATEST_URL",
    f"{TAMILMV_BASE_URL}/index.php?/forums/forum/8-tamil-dubbed-movies/",
)

# ========== FILE SELECTION RULES ==========
SELECTION_RULES = {
    "optimal": {"quality": "1080p", "min_size_gb": 1.0, "max_size_gb": 3.0, "priority": 1},
    "fallback_1080p": {"quality": "1080p", "min_size_gb": 0.5, "max_size_gb": 15.0, "priority": 2},
    "fallback_720p": {"quality": "720p", "min_size_gb": 1.0, "max_size_gb": 5.0, "require_keywords": ["HQ"], "priority": 3},
    "blacklist": ["CAM", "TC", "Telesync", "480p", "4K", "2160p", "HDCAM"],
    "prefer": ["WEB-DL", "BluRay", "HQ.HDRip", "WEBRip"],
}

# ========== AUTOMATION SETTINGS ==========
AUTO_RETRY_FAILED = True
AUTO_NOTIFY_ADMIN = True
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "1"))  # 1 to fit Seedr 3GB
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "30"))

# ========== TELEGRAM NOTIFICATION ==========
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "")
