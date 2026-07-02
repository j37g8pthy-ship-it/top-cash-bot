import logging
import time
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_IDS
from ai_brain import get_ai_response
from moderation import moderate
from database import db
from scheduler import setup_scheduler
from admin import register_admin_handlers
from knowledge_base import init_knowledge

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== ترحيب بالأعضاء الجدد =====
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        db.upsert_user(member.id, member.username, member.first_name)
        await update.message.reply_text(
            f"🌹 أهلاً وسهلاً بك {member.first_name} في مجموعة TOP CASH\n\n"
            f"نحن سعداء بانضمامك إلى عائلتنا.\n\n"
            f"📌 يرجى قراءة القوانين والتعليمات المثبتة.\n"
            f"💬 يمكنك سؤالي عن أي شيء يخص المنصة.\n\n"
            f"نتمنى لك تجربة ناجحة ومربحة 💙\n"
            f"إدارة TOP CASH"
        )
        db.log_event("new_member", {"user_id": member.id})

# ===== معالجة الرسائل =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text or not msg.from_user:
        return

    text = msg.text
    user = msg.from_user
    user_id = user.id

    # ===== الإشراف والحماية =====
    deleted = await moderate(msg, context)
    if deleted:
        return

    # ===== تحديد إذا البوت يجب يرد =====
    is_question = any(c in text for c in ["؟", "?", "كيف", "ماهو", "ما هو", "وين", "شلون", "متى", "هل", "ليش", "ماذا", "اريد", "أريد"])
    is_mention = context.bot.username and f"@{context.bot.username}" in text
    is_reply_to_bot = (msg.reply_to_message and msg.reply_to_message.from_user
                       and msg.reply_to_message.from_user.is_bot)
    is_admin = user_id in ADMIN_IDS

    if not (is_question or is_mention or is_reply_to_bot or is_admin):
        return

    # ===== الحصول على الرد =====
    try:
        answer, source = await get_ai_response(text, user_id)
        await msg.reply_text(answer)
        logger.info(f"✅ Replied [{source}] to {user.first_name}: {text[:50]}")
    except Exception as e:
        logger.error(f"❌ handle_message error: {e}")
        await msg.reply_text(
            "أهلاً بك 🌹\n\n"
            "عذرًا، حدث خطأ مؤقت. يرجى المحاولة مجدداً. 💙"
        )

# ===== معالجة الصور =====
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.photo:
        return
    photo = msg.photo[-1]
    if photo.file_size < 15000:
        await msg.reply_text(
            "⚠️ الصورة غير واضحة أو صغيرة جداً.\n"
            "يرجى إعادة إرسال صورة الإنجاز بجودة أفضل. 📸"
        )
    else:
        await msg.reply_text(
            "✅ تم استلام صورة الإنجاز!\n"
            "شكراً لك، ستتم المراجعة من قِبل الإدارة. 💙"
        )

# ===== معالجة الأخطاء =====
async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    error = str(context.error)
    logger.error(f"❌ Error: {error}")
    db.log_error(error)
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"⚠️ خطأ في البوت:\n{error[:300]}"
            )
        except Exception:
            pass

# ===== تشغيل البوت =====
def main():
    # تهيئة قاعدة المعرفة
    init_knowledge()

    app = Application.builder().token(BOT_TOKEN).build()

    # تسجيل المعالجات
    register_admin_handlers(app)

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    setup_scheduler(app)

    logger.info("🚀 TOP CASH AI v2 Started!")
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