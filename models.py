from pydantic import BaseModel
from typing import Optional


class MovieCreate(BaseModel):
    title: str
    year: Optional[int] = None
    language: Optional[str] = None
    quality: Optional[str] = None
    category: Optional[str] = None  # e.g. "Action", "Comedy", "Tamil", etc.
    is_multi_dubbed: bool = False

    watch_url: str  # Lulu / streaming link
    download_url: Optional[str] = None  # direct download / secondary link
    poster_url: Optional[str] = None  # image URL (later: Telegram / CDN)
