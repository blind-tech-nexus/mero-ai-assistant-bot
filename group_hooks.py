import re
from typing import Optional
from config import BOT_USERNAME, BOT_MENTION_ALIASES


def is_group_chat(message: dict) -> bool:
    chat_type = (message.get("chat") or {}).get("type", "")
    return chat_type in {"group", "supergroup"}


def extract_group_prompt(message: dict) -> Optional[str]:
    """Return cleaned prompt only when the bot is explicitly mentioned or replied to in a group message."""
    text = (message.get("text") or message.get("caption") or "").strip()
    
    # Check if this is a reply to our bot
    reply_to = message.get("reply_to_message")
    is_reply_to_bot = False
    if reply_to:
        from_user = reply_to.get("from") or {}
        bot_username = (BOT_USERNAME or "").lower().lstrip("@")
        if from_user.get("is_bot") and from_user.get("username", "").lower() == bot_username:
            is_reply_to_bot = True

    # Build alias set: always include "ai" plus configured aliases
    aliases = {"ai"}
    for a in BOT_MENTION_ALIASES:
        if a:
            aliases.add(a.lower().lstrip("@"))
    if BOT_USERNAME:
        aliases.add(BOT_USERNAME.lower().lstrip("@"))

    # Check if any alias is mentioned in the text
    mentioned_alias = None
    for alias in aliases:
        pattern = rf"@\b{re.escape(alias)}\b"
        if re.search(pattern, text, flags=re.IGNORECASE):
            mentioned_alias = alias
            break

    if not mentioned_alias and not is_reply_to_bot:
        return None

    # If mentioned, strip the mention from the text
    cleaned_text = text
    if mentioned_alias:
        pattern = rf"\s*@{re.escape(mentioned_alias)}\b[\s,:-]*"
        cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE).strip()

    return cleaned_text or "Describe this" if (message.get("photo") or message.get("document")) else (cleaned_text or None)
