import asyncio
import time
import re
from groq import Groq
from database import db
from config import GROQ_API_KEY, GEMINI_API_KEY, MAX_RETRIES, RETRY_DELAY, CACHE_TTL
import logging

logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY)

gemini_model = None
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-2.0-flash-lite")
        logger.info("✅ Gemini loaded")
    except Exception as e:
        logger.warning(f"⚠️ Gemini غير متوفر: {e}")

SYSTEM_PROMPT = """أنت TOP CASH AI، موظف دعم رسمي لمنصة TOP CASH.

قواعد صارمة:
1. ترد باللغة العربية أو اللهجة العراقية.
2. تبدأ دائماً بـ: أهلاً بك 🌹
3. إذا وُجدت معلومات في قاعدة المعرفة استخدمها مباشرة ولا تتجاهلها أبداً.
4. إذا لم تعرف قل: عذرًا، لا أملك معلومات مؤكدة. سيتم تحويل سؤالك للإدارة.
5. لا تخترع أرقاماً أو معلومات.
6. ردودك مختصرة وواضحة."""

FAST_RESPONSES = {
    r"^(السلام|هلو|هاي|مرحبا|أهلا|هلا|صباح|مساء)": "أهلاً وسهلاً بك 🌹\nكيف يمكنني مساعدتك؟",
    r"(شكر|شكراً|مشكور|يسلمو|ثانكس)": "أهلاً بك 🌹 دائماً في خدمتكم 💙",
}

def fast_mode_check(text: str) -> str | None:
    for pattern, response in FAST_RESPONSES.items():
        if re.search(pattern, text, re.IGNORECASE):
            return response
    return None

async def call_groq(messages: list) -> str:
    for attempt in range(MAX_RETRIES):
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=400,
                temperature=0.5,
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise e

async def call_gemini(prompt: str) -> str:
    if not gemini_model:
        raise Exception("Gemini not configured")
    response = gemini_model.generate_content(prompt)
    return response.text

async def get_ai_response(user_question: str, user_id: int = 0) -> tuple:
    start = time.time()

    # 1️⃣ Fast Mode
    fast = fast_mode_check(user_question)
    if fast:
        db.log_conversation(user_id, user_question, fast, "fast", time.time()-start)
        return fast, "fast"

    # 2️⃣ كاش
    cached = db.get_cache(user_question)
    if cached:
        db.log_conversation(user_id, user_question, cached, "cache", time.time()-start)
        return cached, "cache"

    # 3️⃣ قاعدة المعرفة - البحث المباشر
    knowledge = db.search_knowledge(user_question)
    
    if knowledge:
        context = "معلومات من قاعدة البيانات:\n" + "\n".join(knowledge)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{context}\n\nسؤال العضو: {user_question}\n\nأجب بأسلوبك الخاص مستخدماً المعلومات أعلاه فقط ولا تضف أي أرقام أو معلومات من عندك."}
        ]
    else:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"سؤال العضو: {user_question}"}
        ]

    # 4️⃣ Groq
    try:
        answer = await call_groq(messages)
        db.set_cache(user_question, answer, CACHE_TTL)
        db.log_conversation(user_id, user_question, answer, "groq", time.time()-start)
        if "لا أملك" in answer or "سيتم تحويل" in answer:
            db.log_unknown(user_id, user_question)
        return answer, "groq"
    except Exception as groq_error:
        logger.warning(f"⚠️ Groq failed: {groq_error}")

    # 5️⃣ Gemini Fallback
    try:
        context = "\n".join(knowledge) if knowledge else ""
        full_prompt = f"{SYSTEM_PROMPT}\n\n{context}\n\nسؤال: {user_question}"
        answer = await call_gemini(full_prompt)
        db.set_cache(user_question, answer, CACHE_TTL)
        db.log_conversation(user_id, user_question, answer, "gemini", time.time()-start)
        return answer, "gemini"
    except Exception as e:
        logger.error(f"❌ All AI failed: {e}")

    # 6️⃣ Fallback
    fallback = "أهلاً بك 🌹\nعذرًا، النظام مشغول حالياً. يرجى المحاولة بعد دقيقة. 💙"
    return fallback, "fallback"
