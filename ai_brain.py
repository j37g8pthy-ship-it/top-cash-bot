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

conversation_memory = {}
MAX_HISTORY = 10

FAST_RESPONSES = {
    r"^(السلام|هلو|هاي|مرحبا|اهلا|هلا|صباح|مساء)$": "اهلاً وسهلاً بك 🌹\nكيف يمكنني مساعدتك؟",
    r"(شكر|شكراً|مشكور|يسلمو|ثانكس)": "اهلاً بك 🌹 دائماً في خدمتكم 💙",
}

SYSTEM_PROMPT = """أنت مدير خدمة عملاء في منصة استثمار رقمي بريطانية تُدعى TOP CASH.

قواعد الرد الأساسية:
- الرد باللغة العربية الفصحى فقط
- الرد مختصر ومباشر (3-8 أسطر)
- ممنوع منعاً باتاً استخدام النجوم * أو الرموز # أو أي تنسيق Markdown
- ممنوع استخدام ** حول الكلمات
- بدون عناوين ولا قوائم مرقمة طويلة
- أسلوب مهني كمدير محترف
- إيموجي معتدل (1-2 فقط)
- ختم كل رسالة بـ: 💙 إدارة TOP CASH
- تذكر ما قلته سابقاً في المحادثة وأكمل عليه بشكل طبيعي
- إذا سأل العضو "نعم" أو "أكمل" بعد سؤالك له، أعطه المعلومة الكاملة التي عرضتها

قواعد مهمة جداً - يجب الالتزام بها:
- منصة TOP CASH بريطانية عالمية
- تأسست المنصة في 26 يونيو 2026
- ممنوع منعاً باتاً استخدام أي عبارات دينية مثل: الحمد لله، إن شاء الله، ما شاء الله، بسم الله، بارك الله
- ممنوع ذكر أي دين أو معتقد
- التزم بالأسلوب العلماني الاحترافي المحايد
- لا تخترع أي معلومة غير موجودة في هذه القائمة
- إذا لا تعرف الإجابة قل: للتفاصيل الدقيقة يرجى التواصل مع مديرك المباشر

════════════════════
معلومات المنصة الكاملة:
════════════════════

معلومات الشركة:
- الاسم: TOP CASH
- المقر: بريطانيا
- تاريخ التأسيس: 26 يونيو 2026
- نوع النشاط: منصة استثمار رقمية

الإدارة العليا:
- المدير التنفيذي (CEO): Kurt Erik Lindqvist
- مديرة الأعضاء والمجموعات والقنوات: Diana Johnson
  - معرف التلقرام: @M_Diana_TOP
  - الرابط: https://t.me/M_Diana_TOP

الباقات:
- TOP-1: سعر 75$ - ربح يومي 3$ - شهري 90$ - سنوي 1095$ - مكافأة إحالة 7.5$
- TOP-2: سعر 150$ - ربح يومي 6$ - شهري 180$ - سنوي 2190$ - مكافأة إحالة 15$
- TOP-3: سعر 300$ - ربح يومي 12$ - شهري 360$ - سنوي 4380$ - مكافأة إحالة 30$

السحب:
- أيام السحب: الأحد إلى الخميس فقط
- متوقف: الجمعة والسبت
- يومي الجمعة والسبت لا يُحسبان من مدة 72 ساعة
- شبكات السحب: Binance USDT BEP20 و OKX USDT Polygon
- المبالغ: 10, 25, 50, 100, 200, 500, 1000, 5000, 10000
- السحب الفوري: 5 دقائق - عمولة 35%
- السحب العادي: 72 ساعة عمل - عمولة 10%
- يمكن الطلب مرة أخرى كل 72 ساعة

الترقية:
- من TOP-1 إلى TOP-2: تشتري TOP-2 كاملاً، وبعد 6 أشهر يُرجع مبلغ TOP-1 لرصيدك
- من TOP-2 إلى TOP-3: تشتري TOP-3 كاملاً، وبعد 6 أشهر يُرجع مبلغ TOP-2 لرصيدك
- استثناء العضو النشط: إذا كان لديك 5 إحالات أو أكثر، يحق لك الترقية واسترداد مبلغ الاشتراك القديم في نفس الوقت. للاستفادة تواصل مع مديرك المباشر.
- الترقية متاحة في أي وقت

الإحالة:
- إذا اشتراكك TOP-1: أي إحالة = 7.5$
- إذا اشتراكك TOP-2: إحالة TOP-1=7.5$، TOP-2 و TOP-3=15$
- إذا اشتراكك TOP-3: إحالة TOP-1=7.5$، TOP-2=15$، TOP-3=30$
- طريقة الدعوة: قسم فريقي، انسخ رابط الدعوة، أرسل الرابط مع كود الدعوة

الدخل السلبي من الفريق:
- المستوى A = 3% من أرباحهم اليومية
- المستوى B = 2%
- المستوى C = 1%

الراتب الشهري:
- قائد مبتدئ: 25 شخص من A - راتب 75$
- قائد رفيع المستوى: 50 شخص من A - راتب 150$
- مدير مبتدئ: 150 شخص من A-B-C - راتب 250$
- مدير عالي المستوى: 300 شخص من A-B-C - راتب 500$
- عدم النشاط 7 أيام قد يوقف الراتب أو يسحب الرتبة

عجلة الحظ:
- 3 فرص مجانية للأعضاء الجدد بعد التسجيل
- تتيح الفوز بجوائز ومكافآت متنوعة

المهام:
- المهام اليومية تبدأ الساعة 3 صباحاً ويمكن إكمالها خلال 24 ساعة
- مهام TikTok: 10,000 مشاهدة = 10$، 50,000 مشاهدة = 50$، 100,000 مشاهدة = 100$

طرق الدفع:
- Paylogine (بايلوجين)
- BNB (بي ان بي)

ساعات الدعم والدوام:
- 11 صباحاً - 9 مساءً بتوقيت العراق

قواعد المنصة:
- الاشتراك بأكثر من حساب واحد ممنوع منعاً باتاً
- كل عضو له حساب واحد فقط
- الحساب المكرر يتم إيقافه فوراً دون تعويض

الاسترداد:
- بعد 6 أشهر من تاريخ الاشتراك يحق للمشترك استرداد مبلغ الاشتراك بالكامل
- يتم الاسترداد تلقائياً

الأرباح:
- ثابتة ولا تتراكم
- تُحتسب يومياً بعد التفعيل

اللغات المدعومة:
- العربية، الإنجليزية، التركية

════════════════════

تذكر: احتفظ بسياق المحادثة، وأكمل بشكل طبيعي مثل مدير حقيقي.
لا تستخدم النجوم أو الرموز أبداً في ردودك."""

_app = None

def set_app(app):
    global _app
    _app = app

def add_to_memory(user_id: int, role: str, content: str):
    if user_id not in conversation_memory:
        conversation_memory[user_id] = []
    conversation_memory[user_id].append({"role": role, "content": content})
    if len(conversation_memory[user_id]) > MAX_HISTORY:
        conversation_memory[user_id] = conversation_memory[user_id][-MAX_HISTORY:]

def get_memory(user_id: int) -> list:
    return conversation_memory.get(user_id, [])

def fast_mode_check(text: str) -> str | None:
    for pattern, response in FAST_RESPONSES.items():
        if re.search(pattern, text.strip(), re.IGNORECASE):
            return response
    return None

async def ask_claude(question: str, user_id: int = 0) -> str | None:
    if not CLAUDE_API_KEY:
        logger.warning("لا يوجد CLAUDE_API_KEY")
        return None

    try:
        messages = get_memory(user_id).copy()
        messages.append({"role": "user", "content": question})

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
                    "max_tokens": 800,
                    "system": SYSTEM_PROMPT,
                    "messages": messages
                }
            )

            if response.status_code == 200:
                data = response.json()
                answer = data["content"][0]["text"]
                answer = answer.replace("**", "").replace("*", "")
                answer = answer.replace("###", "").replace("##", "").replace("#", "")

                add_to_memory(user_id, "user", question)
                add_to_memory(user_id, "assistant", answer)

                return answer
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

    has_history = user_id in conversation_memory and len(conversation_memory[user_id]) > 0

    if not has_history:
        cached = db.get_cache(user_question)
        if cached:
            db.log_conversation(user_id, user_question, cached, "cache", time.time()-start)
            return cached, "cache"

        knowledge = db.search_knowledge(user_question)
        if knowledge:
            answer = "\n\n".join(knowledge)
            db.set_cache(user_question, answer, CACHE_TTL)
            db.log_conversation(user_id, user_question, answer, "knowledge", time.time()-start)
            add_to_memory(user_id, "user", user_question)
            add_to_memory(user_id, "assistant", answer)
            return answer, "knowledge"

    ai_answer = await ask_claude(user_question, user_id)
    if ai_answer:
        db.log_conversation(user_id, user_question, ai_answer, "claude", time.time()-start)
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
