# verification_tokens.py

import secrets
from datetime import datetime
from typing import Optional, Dict, Any

from db import get_db


async def create_verification_token(session_id: str, next_url: str) -> str:
    """
    Create a one-time verification token linked to a session + target URL.
    Used to auto-verify when the user returns from the shortlink.
    """
    token = secrets.token_urlsafe(16)
    db = get_db()
    if db is None:
        return token

    await db["verify_tokens"].insert_one(
        {
            "token": token,
            "session_id": session_id,
            "next": next_url,
            "created_at": datetime.utcnow(),
        }
    )
    return token


async def use_verification_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Look up token and delete it (one-time use).
    Returns the document or None if not found.
    """
    db = get_db()
    if db is None:
        return None

    col = db["verify_tokens"]
    doc = await col.find_one({"token": token})
    if not doc:
        return None

    await col.delete_one({"_id": doc["_id"]})
    return doc
