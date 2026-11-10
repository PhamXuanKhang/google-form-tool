"""In-memory cache for uploaded answer rows, keyed by short upload ids."""

import threading
import time
import uuid

from app.config import Config


_upload_cache = {}
_upload_cache_lock = threading.RLock()


def _cleanup_expired_upload_cache(now: float = None) -> None:
    now = now or time.monotonic()
    ttl = Config.UPLOAD_CACHE_TTL_SECONDS
    with _upload_cache_lock:
        expired_ids = [
            upload_id
            for upload_id, entry in _upload_cache.items()
            if now - entry["created_at"] > ttl
        ]
        for upload_id in expired_ids:
            _upload_cache.pop(upload_id, None)


def store_uploaded_responses(responses_list):
    _cleanup_expired_upload_cache()
    with _upload_cache_lock:
        if len(_upload_cache) >= Config.UPLOAD_CACHE_MAX_ENTRIES:
            return None
        upload_id = uuid.uuid4().hex[:12]
        while upload_id in _upload_cache:
            upload_id = uuid.uuid4().hex[:12]
        _upload_cache[upload_id] = {
            "responses": responses_list,
            "created_at": time.monotonic(),
        }
        return upload_id


def get_cached_upload(upload_id: str):
    _cleanup_expired_upload_cache()
    with _upload_cache_lock:
        entry = _upload_cache.get(upload_id)
        if not entry:
            return None
        return entry["responses"]


def delete_cached_upload(upload_id: str) -> None:
    if not upload_id:
        return
    with _upload_cache_lock:
        _upload_cache.pop(upload_id, None)
