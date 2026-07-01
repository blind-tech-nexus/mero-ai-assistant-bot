import edge_tts
import asyncio
from typing import Optional
from config import DEFAULT_TTS_VOICE

MICROSOFT_VOICES_CACHE: list[dict] = []
MICROSOFT_VOICES_CACHE_TIMESTAMP: float = 0
CACHE_TTL = 3600

async def fetch_microsoft_voices() -> list[dict]:
    global MICROSOFT_VOICES_CACHE, MICROSOFT_VOICES_CACHE_TIMESTAMP
    import time
    current_time = time.time()
    if MICROSOFT_VOICES_CACHE and (current_time - MICROSOFT_VOICES_CACHE_TIMESTAMP) < CACHE_TTL:
        return MICROSOFT_VOICES_CACHE
    try:
        voices = await edge_tts.list_voices()
        sorted_voices = sorted(voices, key=lambda v: (v.get("Locale", ""), v.get("Gender", ""), v.get("ShortName", "")))
        formatted = [{"name": v.get("ShortName"), "language": v.get("Locale"), "gender": v.get("Gender")} for v in sorted_voices]
        MICROSOFT_VOICES_CACHE = formatted
        MICROSOFT_VOICES_CACHE_TIMESTAMP = current_time
        return formatted
    except Exception:
        return MICROSOFT_VOICES_CACHE or []

async def generate_tts(text: str, voice: str = DEFAULT_TTS_VOICE) -> Optional[bytes]:
    try:
        communicate = edge_tts.Communicate(text, voice)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        return audio_bytes if audio_bytes else None
    except Exception:
        return None