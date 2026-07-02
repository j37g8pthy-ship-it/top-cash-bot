from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from telegram import ChatPermissions
from telegram.ext import Application
from config import GROUP_ID, TIMEZONE, OPEN_HOUR, OPEN_MINUTE, CLOSE_HOUR, CLOSE_MINUTE, WARNING_MINUTES, ADMIN_IDS
from database import db
import logging

logger = logging.getLogger(__name__)
tz = pytz.timezone(TIMEZONE)

async def open_group(app):
    try:
        await app.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions=ChatPermissions(can_send_messages=True)
        )
        await app.bot.send_message(chat_id=GROUP_ID, text=(
            "🌞 صباح الخير أعضاء TOP CASH\n\n"
            "تم فتح الدردشة لهذا اليوم.\n\n"
            "يمكنكم الآن:\n"
            "• طرح جميع استفساراتكم.\n"
            "• مشاركة إنجازاتكم.\n"
            "• متابعة آخر الإعلانات.\n\n"
            "نتمنى لكم يوماً مليئاً بالنجاح والأرباح.\n\n"
            "💙 إدارة TOP CASH"
        ))
        db.log_event("group_opened")
    except Exception as e:
        logger.error(f"open_group: {e}")

async def pre_close_warning(app):
    try:
        await app.bot.send_message(chat_id=GROUP_ID, text=(
            f"⏰ تنبيه\n\n"
            f"سيتم إغلاق الدردشة بعد {WARNING_MINUTES} دقائق.\n\n"
            f"إذا كان لديكم أي استفسار يرجى إرساله الآن.\n\n"
            f"شكراً لكم. 💙"
        ))
    except Exception as e:
        logger.error(f"pre_close: {e}")

async def close_group(app):
    try:
        await app.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await app.bot.send_message(chat_id=GROUP_ID, text=(
            "🌙 انتهى الدوام الرسمي لهذا اليوم.\n\n"
            "تم إغلاق الدردشة، وسيتم فتحها غداً الساعة 11:00 صباحاً.\n\n"
            "شاكرين تعاونكم.\n"
            "نتمنى لكم مساءً سعيداً.\n\n"
            "💙 إدارة TOP CASH"
        ))
        db.log_event("group_closed")
    except Exception as e:
        logger.error(f"close_group: {e}")

async def tasks_reminder(app):
    try:
        await app.bot.send_message(chat_id=GROUP_ID, text=(
            "📋 تذكير بالمهام اليومية\n\n"
            "🔔 لا تنسوا إتمام مهامكم اليومية!\n\n"
            "✅ تأكدوا من:\n"
            "• إتمام جميع المهام المطلوبة.\n"
            "• إرسال صور الإنجاز.\n"
            "• متابعة آخر التحديثات.\n\n"
            "💙 إدارة TOP CASH"
        ))
    except Exception as e:
        logger.error(f"tasks_reminder: {e}")

async def daily_backup(app):
    try:
        path = db.backup()
        if ADMIN_IDS:
            await app.bot.send_document(
                chat_id=ADMIN_IDS[0],
                document=open(path, "rb"),
                caption="💾 النسخة الاحتياطية اليومية - TOP CASH AI"
            )
    except Exception as e:
        logger.error(f"backup: {e}")

def setup_scheduler(app):
    scheduler = AsyncIOScheduler(timezone=tz)

    scheduler.add_job(open_group, CronTrigger(hour=OPEN_HOUR, minute=OPEN_MINUTE, timezone=tz), args=[app])
    scheduler.add_job(close_group, CronTrigger(hour=CLOSE_HOUR, minute=CLOSE_MINUTE, timezone=tz), args=[app])

    wh = CLOSE_HOUR if CLOSE_MINUTE - WARNING_MINUTES >= 0 else CLOSE_HOUR - 1
    wm = (CLOSE_MINUTE - WARNING_MINUTES) % 60
    scheduler.add_job(pre_close_warning, CronTrigger(hour=wh, minute=wm, timezone=tz), args=[app])
    scheduler.add_job(tasks_reminder, CronTrigger(hour=14, minute=0, timezone=tz), args=[app])
    scheduler.add_job(daily_backup, CronTrigger(hour=0, minute=0, timezone=tz), args=[app])

    scheduler.start()
    logger.info("✅ Scheduler started")