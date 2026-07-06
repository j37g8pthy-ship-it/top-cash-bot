import time
import re
from database import db
from config import CACHE_TTL
import logging

logger = logging.getLogger(__name__)

FAST_RESPONSES = {
    r"^(السلام|هلو|هاي|مرحبا|اهلا|هلا|صباح|مساء)$": "اهلاً وسهلاً بك 🌹\nكيف يمكنني مساعدتك؟",
    r"(شكر|شكراً|مشكور|يسلمو|ثانكس)": "اهلاً بك 🌹 دائماً في خدمتكم 💙",
}

def fast_mode_check(text: str) -> str | None:
    for pattern, response in FAST_RESPONSES.items():
        if re.search(pattern, text.strip(), re.IGNORECASE):
            return response
    return None

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
        answer = "اهلاً بك 🌹\n\n" + "\n\n".join(knowledge)
        db.set_cache(user_question, answer, CACHE_TTL)
        db.log_conversation(user_id, user_question, answer, "knowledge", time.time()-start)
        return answer, "knowledge"

    # 4 ما في إجابة
    answer = (
        "اهلاً بك 🌹\n\n"
        "عذراً، لا املك معلومات مؤكدة عن هذا السؤال.\n"
        "سيتم تحويله للإدارة لمراجعته. 💙"
    )
    db.log_unknown(user_id, user_question)
    db.log_conversation(user_id, user_question, answer, "unknown", time.time()-start)
    return answer, "unknown"
