import re
from telegram import Message, ChatPermissions
from telegram.ext import ContextTypes
from config import ADMIN_IDS, BANNED_WORDS, MAX_WARNINGS, SPAM_WINDOW, MAX_MSGS_PER_WINDOW
from database import db
import logging

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"(https?://|www\.|t\.me/(?!me)|bit\.ly|tinyurl)", re.IGNORECASE)
AD_PATTERN = re.compile(r"(للتواصل|للتسجيل|اشترك الآن|استثمر معنا|ربح سريع|قناة جديدة)", re.IGNORECASE)

async def moderate(msg: Message, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    يفحص الرسالة.
    يرجع True إذا تم حذفها (توقف المعالجة).
    """
    if not msg or not msg.from_user:
        return False

    user = msg.from_user
    user_id = user.id
    text = msg.text or ""

    # المشرفون معفيون
    if user_id in ADMIN_IDS:
        return False

    # تحديث بيانات المستخدم
    db.upsert_user(user_id, user.username, user.first_name)

    # فحص الحظر
    if db.is_banned(user_id):
        try:
            await msg.delete()
        except Exception:
            pass
        return True

    # فحص السبام (رسائل كثيرة)
    db.track_msg(user_id, text)
    recent = db.count_recent(user_id, SPAM_WINDOW)
    if recent > MAX_MSGS_PER_WINDOW:
        await _warn_user(msg, context, "إرسال رسائل كثيرة جداً")
        return True

    # فحص الرسائل المتكررة
    repeated = db.count_repeated(user_id, text, SPAM_WINDOW)
    if repeated > 2:
        await _warn_user(msg, context, "رسائل متكررة")
        return True

    # فحص الروابط
    if URL_PATTERN.search(text):
        await _delete_and_notify(msg, context, "روابط خارجية غير مسموحة 🔗")
        return True

    # فحص الإعلانات
    if AD_PATTERN.search(text):
        await _warn_user(msg, context, "محتوى إعلاني غير مسموح")
        return True

    # فحص الكلمات المحظورة
    for word in BANNED_WORDS:
        if word.lower() in text.lower():
            await _warn_user(msg, context, f"كلمة محظورة")
            return True

    return False

async def _delete_and_notify(msg: Message, context: ContextTypes.DEFAULT_TYPE, reason: str):
    try:
        await msg.delete()
        note = await context.bot.send_message(
            chat_id=msg.chat_id,
            text=f"⚠️ تم حذف رسالة بسبب: {reason}"
        )
        # حذف إشعار الحذف بعد 5 ثواني
        import asyncio
        await asyncio.sleep(5)
        await note.delete()
    except Exception as e:
        logger.error(f"Moderation error: {e}")

async def _warn_user(msg: Message, context: ContextTypes.DEFAULT_TYPE, reason: str):
    try:
        await msg.delete()
        user_id = msg.from_user.id
        warnings = db.add_warning(user_id)
        remaining = MAX_WARNINGS - warnings

        if warnings >= MAX_WARNINGS:
            # حظر المستخدم
            db.ban_user(user_id)
            try:
                await context.bot.ban_chat_member(chat_id=msg.chat_id, user_id=user_id)
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=msg.chat_id,
                text=f"🚫 تم حظر المستخدم بسبب تكرار المخالفات."
            )
        else:
            note = await context.bot.send_message(
                chat_id=msg.chat_id,
                text=(
                    f"⚠️ تحذير للمستخدم {msg.from_user.first_name}\n"
                    f"السبب: {reason}\n"
                    f"التحذيرات: {warnings}/{MAX_WARNINGS}\n"
                    f"{'تحذير أخير قبل الحظر! ⛔' if remaining == 1 else ''}"
                )
            )
            import asyncio
            await asyncio.sleep(8)
            try:
                await note.delete()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Warn error: {e}")
