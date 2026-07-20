import time
import re
import os
import logging
import httpx
from database import db
from config import CACHE_TTL, ADMIN_IDS

logger = logging.getLogger(__name__)

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-5"

FAST_RESPONSES = {
    r"^(السلام|هلو|هاي|مرحبا|اهلا|هلا|صباح|مساء)$": "اهلاً وسهلاً بك 🌹\nكيف يمكنني مساعدتك؟",
    r"(شكر|شكراً|مشكور|يسلمو|ثانكس)": "اهلاً بك 🌹 دائماً في خدمتكم 💙",
}

SYSTEM_PROMPT = """أنت مدير خدمة عملاء في منصة TOP CASH.

قواعد الرد:
- الرد باللغة العربية الفصحى فقط
- الرد مختصر ومباشر (3-5 أسطر كحد أقصى)
- لا تستخدم النجوم * أو الرموز # أو أي تنسيق Markdown
- لا تستخدم العناوين ولا القوائم المرقمة الطويلة
- الرد بأسلوب مهني كمدير محترف
- استخدم الإيموجي بشكل معتدل (رمز واحد أو اثنين)
- ختم الرسالة بـ: 💙 إدارة TOP CASH

معلومات المنصة:
- الباقات: TOP-1 بسعر 75$ (ربح 3$ يومياً)، TOP-2 بسعر 150$ (ربح 6$ يومياً)، TOP-3 بسعر 300$ (ربح 12$ يومياً)
- السحب: الأحد إلى الخميس فقط، عبر Binance و OKX
- ساعات الدوام: 11 صباحاً - 9 مساءً بتوقيت العراق
- طرق الدفع: Paylogine و BNB
- عجلة الحظ: 3 فرص مجانية للأعضاء الجدد
- الإحالة: مكافآت تصل إلى 30$
- الترقية متاحة في أي وقت
- بعد 6 أشهر يُرجع مبلغ الاشتراك القديم

إذا كنت لا تعرف الإجابة قل: للتفاصيل الدقيقة يرجى التواصل مع مديرك المباشر."""

_app = None

def set_app(app):
    global _app
    _app = app

def fast_mode_check(text: str) -> str | None:
    for pattern, response in FAST_RESPONSES.items():
        if re.search(pattern, text.strip(), re.IGNORECASE):
            return response
    return None

async def ask_claude(question: str) -> str | None:
    if not CLAUDE_API_KEY:
        logger.warning("لا يوجد CLAUDE_API_KEY")
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": 500,
                    "system": SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": question}
                    ]
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data["content"][0]["text"]
            else:
                logger.error(f"Claude API error: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        logger.error(f"Claude API exception: {e}")
        return None

async def notify_admin(user_question: str, user_id: int):
    if not _app or not ADMIN_IDS:
        return
    for admin_id in ADMIN_IDS:
        try:
            await _app.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"❓ سؤال جديد:\n\n"
                    f"👤 User ID: {user_id}\n"
                    f"💬 السؤال: {user_question}"
                )
            )
        except Exception as e:
            logger.error(f"notify_admin error: {e}")

async def get_ai_response(user_question: str, user_id: int = 0) -> tuple:
    start = time.time()

    fast = fast_mode_check(user_question)
    if fast:
        db.log_conversation(user_id, user_question, fast, "fast", time.time()-start)
        return fast, "fast"

    cached = db.get_cache(user_question)
    if cached:
        db.log_conversation(user_id, user_question, cached, "cache", time.time()-start)
        return cached, "cache"

    knowledge = db.search_knowledge(user_question)
    if knowledge:
        answer = "\n\n".join(knowledge)
        db.set_cache(user_question, answer, CACHE_TTL)
        db.log_conversation(user_id, user_question, answer, "knowledge", time.time()-start)
        return answer, "knowledge"

    ai_answer = await ask_claude(user_question)
    if ai_answer:
        db.set_cache(user_question, ai_answer, CACHE_TTL)
        db.log_conversation(user_id, user_question, ai_answer, "claude", time.time()-start)
        await notify_admin(user_question, user_id)
        return ai_answer, "claude"

    answer = (
        "أهلاً بك 🌹\n\n"
        "شكراً لتواصلك معنا. سيتم الرد على استفسارك من قبل الإدارة قريباً.\n\n"
        "💙 إدارة TOP CASH"
    )
    db.log_unknown(user_id, user_question)
    db.log_conversation(user_id, user_question, answer, "unknown", time.time()-start)
    await notify_admin(user_question, user_id)
    return answer, "unknown"
