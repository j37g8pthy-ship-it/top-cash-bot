import logging
import re
from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_IDS, GROUP_ID, GROUP_IDS
from database import db
from scheduler import setup_scheduler
from knowledge_base import init_knowledge
from ai_brain import get_ai_response, set_app, conversation_memory

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

LINK_PATTERN = re.compile(r'(https?://|t\.me/|www\.)', re.IGNORECASE)
AD_KEYWORDS = [
    "ربح مضمون", "استثمار مضمون", "انضم الآن", "اشترك الآن",
    "تواصل معي", "للتواصل", "واتساب", "whatsapp",
    "منصة أخرى", "فرصة ذهبية", "ربح سريع",
]

QUESTION_WORDS = [
    "؟", "?",
    "كيف", "شلون", "اشلون", "كيفاش",
    "ما", "ماذا", "شنو", "شو", "وش", "ايش", "إيش",
    "متى", "امتى", "متين", "وقتاش",
    "وين", "أين", "فين",
    "كم", "شكم", "شقد", "قديش",
    "هل", "ليش", "ليه", "لماذا", "علاش",
    "اريد", "أريد", "ابغى", "ابي", "بدي",
    "ممكن", "أقدر", "اقدر",
    "مرحبا", "هلا", "اهلا", "السلام", "هلو", "هاي",
    "انا مشترك", "انا عضو", "انا جديد", "مشترك جديد",
    "سجلت", "اشتركت", "فعلت",
]

warnings_count = {}

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        db.upsert_user(member.id, member.username, member.first_name)
        await update.message.reply_text(
            f"🌹 أهلاً وسهلاً بك {member.first_name} في مجموعة TOP CASH\n\n"
            f"نحن سعداء بانضمامك إلى عائلتنا.\n\n"
            f"📌 يرجى قراءة القوانين والتعليمات المثبتة.\n\n"
            f"نتمنى لك تجربة ناجحة ومربحة 💙\n"
            f"إدارة TOP CASH"
        )
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"👋 عضو جديد انضم!\n\n"
                        f"👤 الاسم: {member.first_name}\n"
                        f"🆔 ID: {member.id}\n"
                        f"🔗 Username: @{member.username or 'لا يوجد'}"
                    )
                )
            except Exception as e:
                logger.error(f"welcome notify: {e}")
        db.log_event("new_member", {"user_id": member.id})

CONGRATS_KEYWORDS = [
    "تم السحب", "وصل السحب", "وصلت الفلوس", "وصل المبلغ",
    "استلمت", "وصلت ارباحي", "وصل الراتب", "وصل ربحي",
    "وصل المكسب", "استلمت السحب", "وصلت المبلغ",
    "تم استلام", "وصل التحويل", "شكرا توب كاش",
    "شكرا top cash", "شكرا للشركة", "شكرا للادارة",
    "تم استلامه", "شكراً للإدارة", "شكرا الادارة",
    "وصل مبلغي", "استلمته", "استلمت مبلغي",
    "سحب ناجح", "تم بنجاح", "الف شكر", "الف مبروك",
    "وصلت الاموال", "استلمت الفلوس", "وصل حسابي",
    "وصلني السحب", "وصل الحوالة", "تم التحويل",
    "استلمت المبلغ",
    "شكرا توب", "شكرا TOP", "TOP CASH شكرا",
    "وصلي الفلوس", "اجاني المبلغ", "اجاني السحب",
    "المبلغ وصل", "الفلوس وصلت", "الراتب وصل",
    "تم وصول السحب", "تم وصول لسحب", "وصول السحب",
    "تم وصول", "تم استلامي", "وصل لحسابي",
    "شكرا شركة", "شكرا للشركه", "شكرا للمصداقيه",
    "المصداقيه المستمره", "سعدين", "سعيدين",
    "شركه توب كاش", "شركة توب كاش", "توب كاش شكرا",
    "نحن سعدين", "نحن سعيدين", "نعمل معكم",
    "بعمل معكم", "بالعمل معكم", "المصداقية",
    "شكرا لسحب", "شكرا للسحب", "شكرا سحب",
    "وصلني", "استلمت السحب", "استلمت الاموال",
]

def is_question(text: str, bot_username: str = None) -> bool:
    text_lower = text.lower().strip()
    if bot_username and f"@{bot_username.lower()}" in text_lower:
        return True
    for word in QUESTION_WORDS:
        if word in ["؟", "?"]:
            if word in text:
                return True
        else:
            pattern = r'(^|\s)' + re.escape(word) + r'($|\s)'
            if re.search(pattern, text_lower):
                return True
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text or not msg.from_user:
        return

    text = msg.text
    user = msg.from_user
    user_id = user.id

    if user_id in ADMIN_IDS:
        return

    bot_username = context.bot.username if context.bot else None
    is_reply_to_bot = False

    # التحقق إذا كانت الرسالة رد على البوت
    if msg.reply_to_message and msg.reply_to_message.from_user:
        replied_user = msg.reply_to_message.from_user
        if replied_user.username == bot_username or replied_user.is_bot:
            is_reply_to_bot = True
        else:
            # رد على عضو آخر → تجاهل
            return

    has_link = bool(LINK_PATTERN.search(text))
    has_ad = any(kw in text for kw in AD_KEYWORDS)

    if has_link or has_ad:
        try:
            await msg.delete()
        except Exception:
            pass

        warnings_count[user_id] = warnings_count.get(user_id, 0) + 1
        count = warnings_count[user_id]

        if count == 1:
            await context.bot.send_message(
                chat_id=msg.chat_id,
                text=f"⚠️ تحذير أول لـ {user.first_name}\nإرسال الروابط والإعلانات ممنوع."
            )
        elif count == 2:
            await context.bot.send_message(
                chat_id=msg.chat_id,
                text=f"⚠️ تحذير ثاني وأخير لـ {user.first_name}\nالمرة القادمة سيتم حظرك."
            )
        elif count >= 3:
            try:
                await context.bot.ban_chat_member(chat_id=msg.chat_id, user_id=user_id)
                await context.bot.send_message(
                    chat_id=msg.chat_id,
                    text=f"🚫 تم حظر {user.first_name} بسبب مخالفة القوانين."
                )
                for admin_id in ADMIN_IDS:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"🚫 تم حظر عضو\n👤 {user.first_name}\n🆔 {user_id}"
                    )
            except Exception as e:
                logger.error(f"ban error: {e}")
        return

    is_congrats = any(kw in text.lower() for kw in CONGRATS_KEYWORDS)
    if is_congrats:
        await msg.reply_text(
            "مبروك على وصول السحب 🎉\n\n"
            "كل سحب هو ثمرة التزامك وعملك الجاد 💪\n"
            "نفخر بكل عضو ملتزم في عائلة TOP CASH 🌹\n\n"
            "💙 إدارة TOP CASH"
        )
        return

    # إذا كان رد على البوت أو له تاريخ محادثة → يرد بدون فحص السؤال
    has_conversation = user_id in conversation_memory and len(conversation_memory[user_id]) > 0

    if not (is_reply_to_bot or has_conversation or is_question(text, bot_username)):
        return

    try:
        answer, source = await get_ai_response(text, user_id)

        # إزالة النجوم والرموز
        answer = answer.replace("**", "").replace("*", "").replace("###", "").replace("##", "").replace("#", "")

        if source in ["knowledge", "claude", "fast", "cache"]:
            await msg.reply_text(answer)
            logger.info(f"✅ رد [{source}] لـ {user.first_name}")

            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=(
                            f"❓ سؤال من عضو [{source}]\n\n"
                            f"👤 الاسم: {user.first_name}\n"
                            f"💬 {text}\n\n"
                            f"📌 تم الرد تلقائياً في المجموعة"
                        )
                    )
                except Exception as e:
                    logger.error(f"admin notify: {e}")
        else:
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=(
                            f"❓ سؤال بدون إجابة\n\n"
                            f"👤 الاسم: {user.first_name}\n"
                            f"🆔 ID: {user_id}\n"
                            f"💬 {text}"
                        )
                    )
                except Exception as e:
                    logger.error(f"unknown notify: {e}")
    except Exception as e:
        logger.error(f"handle_message error: {e}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.photo:
        return
    if msg.from_user and msg.from_user.id in ADMIN_IDS:
        return

    user = msg.from_user
    caption = msg.caption or ""
    is_congrats = any(kw in caption.lower() for kw in CONGRATS_KEYWORDS)

    if is_congrats:
        await msg.reply_text(
            "مبروك على وصول السحب 🎉\n\n"
            "كل سحب هو ثمرة التزامك وعملك الجاد 💪\n"
            "نفخر بكل عضو ملتزم في عائلة TOP CASH 🌹\n\n"
            "💙 إدارة TOP CASH"
        )
    else:
        db.log_task_photo(user.id, user.first_name, user.username or "")
        logger.info(f"📸 صورة مهمة من {user.first_name}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: /broadcast الرسالة")
        return
    text = " ".join(context.args)
    success = 0
    for gid in GROUP_IDS:
        try:
            await context.bot.send_message(chat_id=gid, text=text)
            success += 1
        except Exception as e:
            logger.error(f"broadcast error [{gid}]: {e}")
    await update.message.reply_text(f"✅ تم الإرسال لـ {success}/{len(GROUP_IDS)} مجموعة")

async def members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        msg = "📊 إحصائيات المجموعات\n\n"
        for gid in GROUP_IDS:
            try:
                count = await context.bot.get_chat_member_count(chat_id=gid)
                chat = await context.bot.get_chat(chat_id=gid)
                msg += f"👥 {chat.title}: {count} عضو\n"
            except Exception:
                msg += f"❌ مجموعة {gid}: خطأ\n"
        stats = db.get_stats()
        msg += f"\n💬 أسئلة اليوم: {stats['questions_today']}\n"
        msg += f"❓ بدون إجابة: {stats['unanswered']}"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    error = str(context.error)
    logger.error(f"❌ Error: {error}")
    db.log_error(error)

def main():
    init_knowledge()

    app = Application.builder().token(BOT_TOKEN).build()

    set_app(app)

    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("members", members))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    setup_scheduler(app)

    logger.info(f"🚀 TOP CASH Bot Started! - {len(GROUP_IDS)} مجموعات")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        read_timeout=30,
        write_timeout=30,
        connect_timeout=30,
        pool_timeout=30,
    )

if __name__ == "__main__":
    main()
