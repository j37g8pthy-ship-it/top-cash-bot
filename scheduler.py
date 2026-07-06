from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import asyncio
import random
from datetime import datetime
from telegram import ChatPermissions
from config import GROUP_ID, TIMEZONE, OPEN_HOUR, OPEN_MINUTE, CLOSE_HOUR, CLOSE_MINUTE, WARNING_MINUTES, ADMIN_IDS
from database import db
import logging

logger = logging.getLogger(__name__)
tz = pytz.timezone(TIMEZONE)

# ===== رسائل تحفيزية عشوائية =====
MOTIVATIONAL_MESSAGES = [
    "🌟 النجاح لا يأتي من الحظ، بل من العمل والالتزام اليومي.\n\nابدأ يومك بطاقة إيجابية وأنجز مهامك! 💙",
    "💪 كل يوم تلتزم فيه هو خطوة نحو هدفك.\n\nلا تتوقف، الفريق يحتاجك! 🌹",
    "🎯 الفرق بين الناجح وغيره هو الاستمرارية.\n\nاستمر ولا تستسلم! 💙",
    "⭐ أصغر خطوة تقوم بها اليوم تصنع فرقاً كبيراً في الغد.\n\nأنجز مهامك الآن! 🌟",
    "🚀 الالتزام اليومي هو سر بناء الفريق الناجح.\n\nتذكر: فريقك يراقبك ويتعلم منك! 💙",
    "💡 من يعمل في صمت اليوم، يتحدث بنجاحه غداً.\n\nواصل العمل! 🌹",
    "🌈 كل عضو تدعوه اليوم قد يكون قائد الغد.\n\nلا تضيع الفرصة! 💙",
    "🔥 الحماس يبدأ... لكن الالتزام هو الذي يصل.\n\nكن من الملتزمين! 💪",
    "💎 قيمتك تزداد كلما زاد التزامك وفريقك.\n\nاستثمر في نفسك كل يوم! 🌟",
    "🌙 نهاية كل يوم سؤال: هل أنجزت ما خططت له؟\n\nاجعل الإجابة دائماً: نعم! 💙",
]

# ===== رسائل الختام الأسبوعي =====
WEEKLY_CLOSING = [
    "🌟 ختام أسبوع مميز!\n\nشكراً لكل عضو التزم وعمل بجد هذا الأسبوع.\nكل خطوة قمت بها اقتربت من هدفك.\n\nاستعدوا لأسبوع جديد مليء بالنجاح! 💙\n\nإدارة TOP CASH",
    "💙 أسبوع مر وأنتم في تقدم مستمر!\n\nالالتزام هو مفتاح النجاح، واستمراركم دليل على عزيمتكم.\n\nنتمنى لكم نهاية أسبوع سعيدة وبداية جديدة موفقة! 🌹\n\nإدارة TOP CASH",
    "🎯 أسبوع من العمل والتعلم!\n\nلكل من التزم بمهامه وساعد فريقه، أنتم الفرق الحقيقي.\n\nاستريحوا وعودوا بطاقة مضاعفة! 💪\n\nإدارة TOP CASH",
]

async def open_group(app):
    try:
        await app.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions=ChatPermissions(can_send_messages=True)
        )
        # رسالة تحفيزية عشوائية مع الفتح
        motivational = random.choice(MOTIVATIONAL_MESSAGES)
        await app.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                "🌞 صباح الخير أعضاء TOP CASH\n\n"
                "تم فتح الدردشة لهذا اليوم.\n\n"
                f"{motivational}\n\n"
                "💙 إدارة TOP CASH"
            )
        )
        db.log_event("group_opened")
    except Exception as e:
        logger.error(f"open_group: {e}")

async def pre_close_warning(app):
    try:
        await app.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                f"⏰ تنبيه\n\n"
                f"سيتم إغلاق الدردشة بعد {WARNING_MINUTES} دقائق.\n\n"
                f"إذا كان لديكم أي استفسار يرجى إرساله الآن.\n\n"
                f"شكراً لكم. 💙"
            )
        )
    except Exception as e:
        logger.error(f"pre_close: {e}")

async def close_group(app):
    try:
        await app.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await app.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                "🌙 انتهى الدوام الرسمي لهذا اليوم.\n\n"
                "تم إغلاق الدردشة، وسيتم فتحها غداً الساعة 11:00 صباحاً.\n\n"
                "شاكرين تعاونكم.\n"
                "نتمنى لكم مساءً سعيداً.\n\n"
                "💙 إدارة TOP CASH"
            )
        )
        db.log_event("group_closed")
    except Exception as e:
        logger.error(f"close_group: {e}")

async def meeting_reminder(app):
    try:
        now = datetime.now(tz)
        if now.weekday() in [4, 5]:
            return
        await app.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                "🔔 تذكير\n\n"
                "سيبدأ الاجتماع اليومي الليلة الساعة 10:00 مساءً بتوقيت العراق.\n\n"
                "نرجو من الجميع الحضور والاستعداد.\n\n"
                "💙 إدارة TOP CASH"
            )
        )
    except Exception as e:
        logger.error(f"meeting_reminder: {e}")

async def send_daily_meeting(app):
    try:
        from meetings import MEETINGS
        now = datetime.now(tz)
        if now.weekday() in [4, 5]:
            return
        date_str = now.strftime("%Y-%m-%d")
        if date_str not in MEETINGS:
            logger.info(f"لا يوجد اجتماع لتاريخ {date_str}")
            return
        messages = MEETINGS[date_str]
        for i, msg in enumerate(messages):
            await app.bot.send_message(chat_id=GROUP_ID, text=msg)
            if i < len(messages) - 1:
                await asyncio.sleep(30)
        logger.info(f"✅ تم إرسال اجتماع {date_str}")
    except Exception as e:
        logger.error(f"send_daily_meeting: {e}")

async def tasks_reminder(app):
    try:
        await app.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                "📋 تذكير بالمهام اليومية\n\n"
                "🔔 لا تنسوا إتمام مهامكم اليومية!\n\n"
                "✅ تأكدوا من:\n"
                "• إتمام جميع المهام المطلوبة.\n"
                "• إرسال صور الإنجاز.\n"
                "• متابعة آخر التحديثات.\n\n"
                "💙 إدارة TOP CASH"
            )
        )
    except Exception as e:
        logger.error(f"tasks_reminder: {e}")

async def weekly_closing(app):
    """ختام أسبوعي كل خميس 8 مساءً"""
    try:
        msg = random.choice(WEEKLY_CLOSING)
        await app.bot.send_message(chat_id=GROUP_ID, text=msg)
    except Exception as e:
        logger.error(f"weekly_closing: {e}")

async def friday_greeting(app):
    """تهنئة جمعة مباركة"""
    try:
        await app.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                "🕌 جمعة مباركة على جميع أعضاء TOP CASH\n\n"
                "تقبل الله منا ومنكم صالح الأعمال.\n\n"
                "نتمنى لكم جمعة مباركة وإجازة سعيدة. 🌹\n\n"
                "💙 إدارة TOP CASH"
            )
        )
    except Exception as e:
        logger.error(f"friday_greeting: {e}")

async def sunday_reminder(app):
    """تذكير أسبوعي كل أحد"""
    try:
        await app.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                "🌟 أهلاً بكم في أسبوع جديد!\n\n"
                "مع بداية كل أسبوع، ضع لنفسك هدفاً واضحاً:\n\n"
                "🎯 كم عضواً ستضيف هذا الأسبوع؟\n"
                "📋 هل ستلتزم بمهامك يومياً؟\n"
                "💪 هل ستتابع فريقك وتدعمه؟\n\n"
                "النجاح يبدأ بقرار، والقرار يبدأ الآن!\n\n"
                "💙 إدارة TOP CASH"
            )
        )
    except Exception as e:
        logger.error(f"sunday_reminder: {e}")

async def daily_stats(app):
    """إحصائيات يومية للأدمن"""
    try:
        stats = db.get_stats()
        msg = (
            f"📊 إحصائيات اليوم\n\n"
            f"👥 إجمالي الأعضاء: {stats['total_users']}\n"
            f"💬 أسئلة اليوم: {stats['questions_today']}\n"
            f"❓ أسئلة بدون إجابة: {stats['unanswered']}\n\n"
            f"💙 TOP CASH Bot"
        )
        for admin_id in ADMIN_IDS:
            await app.bot.send_message(chat_id=admin_id, text=msg)
    except Exception as e:
        logger.error(f"daily_stats: {e}")

async def daily_backup(app):
    try:
        path = db.backup()
        if ADMIN_IDS:
            await app.bot.send_document(
                chat_id=ADMIN_IDS[0],
                document=open(path, "rb"),
                caption="💾 النسخة الاحتياطية اليومية"
            )
    except Exception as e:
        logger.error(f"backup: {e}")

def setup_scheduler(app):
    scheduler = AsyncIOScheduler(timezone=tz)

    # فتح المجموعة - 11:00 صباحاً
    scheduler.add_job(open_group, CronTrigger(hour=OPEN_HOUR, minute=OPEN_MINUTE, timezone=tz), args=[app])

    # إغلاق المجموعة - 9:00 مساءً
    scheduler.add_job(close_group, CronTrigger(hour=CLOSE_HOUR, minute=CLOSE_MINUTE, timezone=tz), args=[app])

    # تحذير قبل الإغلاق
    wh = CLOSE_HOUR if CLOSE_MINUTE - WARNING_MINUTES >= 0 else CLOSE_HOUR - 1
    wm = (CLOSE_MINUTE - WARNING_MINUTES) % 60
    scheduler.add_job(pre_close_warning, CronTrigger(hour=wh, minute=wm, timezone=tz), args=[app])

    # تذكير المهام - 2:00 ظهراً
    scheduler.add_job(tasks_reminder, CronTrigger(hour=14, minute=0, timezone=tz), args=[app])

    # تذكير الاجتماع - 3:00 ظهراً (عدا الجمعة والسبت)
    scheduler.add_job(meeting_reminder, CronTrigger(hour=15, minute=0, day_of_week='sun-thu', timezone=tz), args=[app])

    # إرسال الاجتماع - 10:00 مساءً (عدا الجمعة والسبت)
    scheduler.add_job(send_daily_meeting, CronTrigger(hour=22, minute=0, day_of_week='sun-thu', timezone=tz), args=[app])

    # ختام أسبوعي - الخميس 8:00 مساءً
    scheduler.add_job(weekly_closing, CronTrigger(hour=20, minute=0, day_of_week='thu', timezone=tz), args=[app])

    # تهنئة الجمعة - 10:00 صباحاً
    scheduler.add_job(friday_greeting, CronTrigger(hour=10, minute=0, day_of_week='fri', timezone=tz), args=[app])

    # تذكير أسبوعي - الأحد 11:30 صباحاً
    scheduler.add_job(sunday_reminder, CronTrigger(hour=11, minute=30, day_of_week='sun', timezone=tz), args=[app])

    # إحصائيات يومية للأدمن - 9:30 مساءً
    scheduler.add_job(daily_stats, CronTrigger(hour=21, minute=30, timezone=tz), args=[app])

    # نسخة احتياطية - منتصف الليل
    scheduler.add_job(daily_backup, CronTrigger(hour=0, minute=0, timezone=tz), args=[app])

    scheduler.start()
    logger.info("✅ Scheduler started")
