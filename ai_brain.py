import time
import re
from database import db
from config import CACHE_TTL, ADMIN_IDS
import logging

logger = logging.getLogger(__name__)

FAST_RESPONSES = {
    r"^(السلام|هلو|هاي|مرحبا|اهلا|هلا|صباح|مساء)$": "اهلاً وسهلاً بك 🌹\nكيف يمكنني مساعدتك؟",
    r"(شكر|شكراً|مشكور|يسلمو|ثانكس)": "اهلاً بك 🌹 دائماً في خدمتكم 💙",
}

# سيتم تعيين app من bot.py
_app = None

def set_app(app):
    global _app
    _app = app

def fast_mode_check(text: str) -> str | None:
    for pattern, response in FAST_RESPONSES.items():
        if re.search(pattern, text.strip(), re.IGNORECASE):
            return response
    return None

async def notify_admin(user_question: str, user_id: int):
    """إرسال السؤال للأدمن في الخاص"""
    if not _app or not ADMIN_IDS:
        return
    for admin_id in ADMIN_IDS:
        try:
            await _app.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"❓ سؤال جديد بدون إجابة:\n\n"
                    f"👤 User ID: {user_id}\n"
                    f"💬 السؤال: {user_question}\n\n"
                    f"أضف الإجابة بالأمر:\n"
                    f"/addinfo"
                )
            )
        except Exception as e:
            logger.error(f"notify_admin error: {e}")

async def get_ai_response(user_question: str, user_id: int = 0) -> tuple:
    start = time.time()

    # 1 Fast Mode
    fast = fast_mode_check(user_question)
    if fast:
        db.log_conversation(user_id, user_question, fast, "fast", time.time()-start)
        return fast, "fast"

    # 2 كاش
    cached = db.get_cache(user_question)
    if cached:
        db.log_conversation(user_id, user_question, cached, "cache", time.time()-start)
        return cached, "cache"

    # 3 قاعدة المعرفة
    knowledge = db.search_knowledge(user_question)

    if knowledge:
        answer = "\n\n".join(knowledge)
        db.set_cache(user_question, answer, CACHE_TTL)
        db.log_conversation(user_id, user_question, answer, "knowledge", time.time()-start)
        return answer, "knowledge"

    # 4 ما في إجابة - أرسل للأدمن
    answer = (
        "اهلاً بك 🌹\n\n"
        "عذراً، لا املك معلومات مؤكدة عن هذا السؤال.\n"
        "سيتم تحويله للإدارة لمراجعته. 💙"
    )
    db.log_unknown(user_id, user_question)
    db.log_conversation(user_id, user_question, answer, "unknown", time.time()-start)
    
    # إرسال السؤال للأدمن في الخاص
    await notify_admin(user_question, user_id)
    
    return answer, "unknown"
