import base64
from api import call_gemini_raw, normalize_mime_type

TRANSCRIBE_PROMPT = (
    "Transcribe the uploaded audio exactly in its original language. "
    "Do not summarize. Do not translate. Return only the transcript text."
)

async def transcribe_audio_inline(audio_bytes: bytes, mime_type: str, chat_id: int) -> tuple[str | None, str | None]:
    mime_type = normalize_mime_type(mime_type)
    encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
    
    parts = [
        {"inlineData": {"mimeType": mime_type, "data": encoded_audio}},
        {"text": TRANSCRIBE_PROMPT}
    ]
    
    text = await call_gemini_raw(chat_id, parts, "You are an audio transcriber.")
    if not text or text in ("No response received from AI.", "Failed to parse AI response."):
        return None, "Empty transcription result or failed to parse"
    return text.strip(), None