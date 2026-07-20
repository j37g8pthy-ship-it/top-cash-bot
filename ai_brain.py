import time
import re
import os
import logging
import httpx
from database import db
from config import CACHE_TTL, ADMIN_IDS

logger = logging.getLogger(__name__)

# مفتاح Claude API من Railway Variables
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-5"

# ردود سريعة
FAST_RESPONSES = {
    r"^(السلام|هلو|هاي|مرحبا|اهلا|هلا|صباح|مساء)$": "اهلاً وسهلاً بك 🌹\nكيف يمكنني مساعدتك؟",
    r"(شكر|شكراً|مشكور|يسلمو|ثانكس)": "اهلاً بك 🌹 دائماً في خدمتكم 💙",
}

# System Prompt - شخصية البوت
SYSTEM_PROMPT = """أنت مدير خدمة عملاء محترف في منصة استثمار رقمي تُدعى TOP CASH.

مهمتك:
- الرد على أسئلة الأعضاء باللغة العربية الفصحى
- الحفاظ على لهجة رسمية ومهنية دائماً
- الإجابة بشكل مباشر وواضح
- استخدام الإيموجي بشكل معتدل ومهني

معلومات عن المنصة:
- الباقات: TOP-1 (75$)، TOP-2 (150$)، TOP-3 (300$)
- الأرباح اليومية: 3$، 6$، 12$ حسب الباقة
- السحب: الأحد إلى الخميس فقط
- شبكات السحب: Binance و OKX
- ساعات الدوام: 11 صباحاً - 9 مساءً بتوقيت العراق
- طرق الدفع: Paylogine و BNB
- عجلة الحظ: 3 فرص مجانية للأعضاء الجدد
- الإحالة: مكافآت تصل إلى 30$
- الترقية متاحة في أي وقت
- بعد 6 أشهر يُرجع مبلغ الاشتراك القديم

قواعد مهمة:
- لا تخترع معلومات غير موجودة
- إذا كنت لا تعرف الإجابة قل: "للتفاصيل الدقيقة يرجى التواصل مع مديرك المباشر"
- كن مختصراً ومباشراً
- ختم الرسائل بـ: 💙 إدارة TOP CASH
- لا تستخدم اللهجات العامية أبداً"""

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

async def ask_claude(question: str) -> str | None:
    """طلب رد من Claude AI"""
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
                    "max_tokens": 1000,
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
    """إرسال السؤال للأدمن في الخاص"""
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

    # 4 Claude AI - محاولة الرد بالذكاء الاصطناعي
    ai_answer = await ask_claude(user_question)
    if ai_answer:
        db.set_cache(user_question, ai_answer, CACHE_TTL)
        db.log_conversation(user_id, user_question, ai_answer, "claude", time.time()-start)
        # إرسال نسخة للأدمن للاطلاع
        await notify_admin(user_question, user_id)
        return ai_answer, "claude"

    # 5 ما في إجابة - أرسل للأدمن
    answer = (
        "أهلاً بك 🌹\n\n"
        "شكراً لتواصلك معنا. سيتم الرد على استفسارك من قبل الإدارة قريباً.\n\n"
        "💙 إدارة TOP CASH"
    )
    db.log_unknown(user_id, user_question)
    db.log_conversation(user_id, user_question, answer, "unknown", time.time()-start)
    await notify_admin(user_question, user_id)
    return answer, "unknown"
