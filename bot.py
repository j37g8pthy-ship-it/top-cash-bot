import logging
import re
from telegram import Update, ChatPermissions
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_IDS, GROUP_ID, GROUP_IDS
from database import db
from scheduler import setup_scheduler
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

# ===== فلترة الروابط =====
LINK_PATTERN = re.compile(r'(https?://|t\.me/|www\.)', re.IGNORECASE)
AD_KEYWORDS = [
    "ربح مضمون", "استثمار مضمون", "انضم الآن", "اشترك الآن",
    "تواصل معي", "للتواصل", "واتساب", "whatsapp",
    "منصة أخرى", "فرصة ذهبية", "ربح سريع",
]

# ===== تتبع التحذيرات =====
warnings_count = {}

# ===== تتبع صور المهام =====
tasks_photos = {}

# ===== ترحيب بالأعضاء الجدد =====
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

# ===== كلمات التهنئة =====
CONGRATS_KEYWORDS = [
    "تم السحب", "وصل السحب", "وصلت الفلوس", "وصل المبلغ",
    "استلمت", "وصلت ارباحي", "وصل الراتب", "وصل ربحي",
    "وصل المكسب", "استلمت السحب", "وصلت المبلغ",
    "تم استلام", "وصل التحويل", "شكرا توب كاش",
    "شكرا top cash", "شكرا للشركة", "شكرا للادارة",
]

# ===== معالجة الرسائل =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text or not msg.from_user:
        return

    text = msg.text
    user = msg.from_user
    user_id = user.id

    if user_id in ADMIN_IDS:
        return

    # فلترة الروابط والإعلانات
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

    # فحص كلمات التهنئة
    is_congrats = any(kw in text.lower() for kw in CONGRATS_KEYWORDS)
    if is_congrats:
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"🎉 تهنئة سحب!\n\n"
                        f"👤 الاسم: {user.first_name}\n"
                        f"🆔 ID: {user_id}\n"
                        f"💬 الرسالة: {text}\n\n"
                        f"انسخ التهنئة وأرسلها في المجموعة 💙"
                    )
                )
            except Exception as e:
                logger.error(f"congrats notify: {e}")
        return

    # البحث عن إجابة وإرسالها للأدمن
    knowledge = db.search_knowledge(text)

    if knowledge:
        answer = "\n\n".join(knowledge)
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"❓ سؤال من عضو\n\n"
                        f"👤 الاسم: {user.first_name}\n"
                        f"💬 {text}"
                    )
                )
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=answer
                )
            except Exception as e:
                logger.error(f"answer notify: {e}")
    else:
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"❓ سؤال بدون إجابة\n\n"
                        f"👤 الاسم: {user.first_name}\n"
                        f"🆔 ID: {user_id}\n"
                        f"💬 {text}\n\n"
                        f"⚠️ لا يوجد جواب في قاعدة البيانات"
                    )
                )
            except Exception as e:
                logger.error(f"unknown notify: {e}")

# ===== معالجة الصور =====
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
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"🎉 صورة سحب!\n\n"
                        f"👤 {user.first_name}\n"
                        f"🆔 {user.id}\n"
                        f"💬 {caption}\n\n"
                        f"انسخ التهنئة وأرسلها في المجموعة 💙"
                    )
                )
            except Exception as e:
                logger.error(f"photo notify: {e}")
    else:
        from datetime import date
        today = date.today().isoformat()
        if today not in tasks_photos:
            tasks_photos[today] = []
        ids = [x["id"] for x in tasks_photos[today]]
        if user.id not in ids:
            tasks_photos[today].append({
                "id": user.id,
                "name": user.first_name,
                "username": user.username or ""
            })
        logger.info(f"📸 صورة مهمة من {user.first_name}")

# ===== أمر /broadcast للأدمن =====
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

# ===== أمر /members للأدمن =====
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

# ===== معالجة الأخطاء =====
async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    error = str(context.error)
    logger.error(f"❌ Error: {error}")
    db.log_error(error)

# ===== تشغيل البوت =====
def main():
    init_knowledge()

    app = Application.builder().token(BOT_TOKEN).build()

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
