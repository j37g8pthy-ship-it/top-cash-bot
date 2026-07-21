from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import asyncio
import random
from datetime import datetime
from telegram import ChatPermissions
from config import GROUP_ID, GROUP_IDS, TIMEZONE, OPEN_HOUR, OPEN_MINUTE, CLOSE_HOUR, CLOSE_MINUTE, WARNING_MINUTES, ADMIN_IDS
from database import db
import logging

logger = logging.getLogger(__name__)
tz = pytz.timezone(TIMEZONE)

MOTIVATIONAL_MESSAGES = [
    "🌟 النجاح لا يأتي من الحظ، بل من العمل والالتزام اليومي.\n\nابدأ يومك بطاقة إيجابية وأنجز مهامك! 💙",
    "💪 كل يوم تلتزم فيه هو خطوة نحو هدفك.\n\nلا تتوقف، الفريق يحتاجك! 🌹",
    "🎯 الفرق بين الناجح وغيره هو الاستمرارية.\n\nاستمر ولا تستسلم! 💙",
    "⭐ أصغر خطوة تقوم بها اليوم تصنع فرقاً كبيراً في الغد.\n\nأنجز مهامك الآن! 🌟",
    "🚀 الالتزام اليومي هو سر بناء الفريق الناجح.\n\nتذكر: فريقك يراقبك ويتعلم منك! 💙",
    "💡 من يعمل في صمت اليوم، يتحدث بنجاحه غداً.\n\nواصل العمل! 🌹",
    "💫 كل عضو تدعوه اليوم قد يكون قائد الغد.\n\nلا تضيع الفرصة! 💙",
    "🔥 الحماس يبدأ... لكن الالتزام هو الذي يصل.\n\nكن من الملتزمين! 💪",
    "💎 قيمتك تزداد كلما زاد التزامك وفريقك.\n\nاستثمر في نفسك كل يوم! 🌟",
    "🌙 نهاية كل يوم سؤال: هل أنجزت ما خططت له؟\n\nاجعل الإجابة دائماً: نعم! 💙",
]

WEEKLY_CLOSING = [
    "🌟 ختام أسبوع مميز!\n\nشكراً لكل عضو التزم وعمل بجد هذا الأسبوع.\nكل خطوة قمت بها اقتربت من هدفك.\n\nاستعدوا لأسبوع جديد مليء بالنجاح! 💙\n\nإدارة TOP CASH",
    "💙 أسبوع مر وأنتم في تقدم مستمر!\n\nالالتزام هو مفتاح النجاح، واستمراركم دليل على عزيمتكم.\n\nنتمنى لكم نهاية أسبوع سعيدة وبداية جديدة موفقة! 🌹\n\nإدارة TOP CASH",
    "🎯 أسبوع من العمل والتعلم!\n\nلكل من التزم بمهامه وساعد فريقه، أنتم الفرق الحقيقي.\n\nاستريحوا وعودوا بطاقة مضاعفة! 💪\n\nإدارة TOP CASH",
]

async def send_to_all(app, text):
    for gid in GROUP_IDS:
        try:
            await app.bot.send_message(chat_id=gid, text=text)
        except Exception as e:
            logger.error(f"send_to_all error [{gid}]: {e}")

async def open_all_groups(app):
    for gid in GROUP_IDS:
        try:
            await app.bot.set_chat_permissions(
                chat_id=gid,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_photos=True,
                    can_send_videos=True,
                    can_send_documents=True,
                    can_send_voice_notes=True,
                    can_send_video_notes=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                )
            )
        except Exception as e:
            logger.error(f"open_group error [{gid}]: {e}")
    motivational = random.choice(MOTIVATIONAL_MESSAGES)
    await send_to_all(app,
        "🌞 صباح الخير أعضاء TOP CASH\n\n"
        "تم فتح الدردشة لهذا اليوم.\n\n"
        f"{motivational}\n\n"
        "💙 إدارة TOP CASH"
    )
    db.log_event("groups_opened")

async def pre_close_warning(app):
    await send_to_all(app,
        f"⏰ تنبيه\n\n"
        f"سيتم إغلاق الدردشة بعد {WARNING_MINUTES} دقائق.\n\n"
        f"إذا كان لديكم أي استفسار يرجى إرساله الآن.\n\n"
        f"شكراً لكم. 💙"
    )

async def close_all_groups(app):
    for gid in GROUP_IDS:
        try:
            await app.bot.set_chat_permissions(
                chat_id=gid,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_photos=False,
                    can_send_videos=False,
                    can_send_documents=False,
                    can_send_voice_notes=False,
                    can_send_video_notes=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                )
            )
        except Exception as e:
            logger.error(f"close_group error [{gid}]: {e}")
    await send_to_all(app,
        "🌙 انتهى الدوام الرسمي لهذا اليوم.\n\n"
        "تم إغلاق الدردشة، وسيتم فتحها غداً الساعة 11:00 صباحاً.\n\n"
        "شاكرين تعاونكم.\n"
        "نتمنى لكم مساءً سعيداً.\n\n"
        "💙 إدارة TOP CASH"
    )
    db.log_event("groups_closed")

async def meeting_reminder(app):
    now = datetime.now(tz)
    if now.weekday() in [4, 5]:
        return
    await send_to_all(app,
        "🔔 تذكير\n\n"
        "سيبدأ الاجتماع اليومي الليلة الساعة 10:00 مساءً بتوقيت العراق.\n\n"
        "نرجو من الجميع الحضور والاستعداد.\n\n"
        "💙 إدارة TOP CASH"
    )

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
            for gid in GROUP_IDS:
                try:
                    await app.bot.send_message(chat_id=gid, text=msg)
                except Exception as e:
                    logger.error(f"meeting error [{gid}]: {e}")
            if i < len(messages) - 1:
                await asyncio.sleep(30)
        logger.info(f"✅ تم إرسال اجتماع {date_str}")
    except Exception as e:
        logger.error(f"send_daily_meeting: {e}")

async def tasks_reminder(app):
    await send_to_all(app,
        "📋 تذكير بالمهام اليومية\n\n"
        "🔔 لا تنسوا إتمام مهامكم اليومية!\n\n"
        "✅ تأكدوا من:\n"
        "• إتمام جميع المهام المطلوبة.\n"
        "• إرسال صور الإنجاز.\n"
        "• متابعة آخر التحديثات.\n\n"
        "💙 إدارة TOP CASH"
    )

async def weekly_closing(app):
    msg = random.choice(WEEKLY_CLOSING)
    await send_to_all(app, msg)

async def sunday_reminder(app):
    await send_to_all(app,
        "🌟 أهلاً بكم في أسبوع جديد!\n\n"
        "مع بداية كل أسبوع، ضع لنفسك هدفاً واضحاً:\n\n"
        "🎯 كم عضواً ستضيف هذا الأسبوع؟\n"
        "📋 هل ستلتزم بمهامك يومياً؟\n"
        "💪 هل ستتابع فريقك وتدعمه؟\n\n"
        "النجاح يبدأ بقرار، والقرار يبدأ الآن!\n\n"
        "💙 إدارة TOP CASH"
    )

async def daily_stats(app):
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

async def send_tasks_report(app):
    try:
        members_done = db.get_task_photos()
        if members_done:
            names = "\n".join([f"✅ {name}" for name in members_done])
            msg = (
                f"📸 تقرير المهام اليومية\n\n"
                f"عدد من أرسل صور المهام: {len(members_done)}\n\n"
                f"{names}\n\n"
                f"💙 TOP CASH Bot"
            )
        else:
            msg = (
                f"📸 تقرير المهام اليومية\n\n"
                f"⚠️ لم يرسل أي عضو صورة مهمة حتى الآن!\n\n"
                f"💙 TOP CASH Bot"
            )
        for admin_id in ADMIN_IDS:
            await app.bot.send_message(chat_id=admin_id, text=msg)
    except Exception as e:
        logger.error(f"send_tasks_report: {e}")

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

    scheduler.add_job(open_all_groups, CronTrigger(hour=OPEN_HOUR, minute=OPEN_MINUTE, timezone=tz), args=[app])
    scheduler.add_job(close_all_groups, CronTrigger(hour=CLOSE_HOUR, minute=CLOSE_MINUTE, timezone=tz), args=[app])
    wh = CLOSE_HOUR if CLOSE_MINUTE - WARNING_MINUTES >= 0 else CLOSE_HOUR - 1
    wm = (CLOSE_MINUTE - WARNING_MINUTES) % 60
    scheduler.add_job(pre_close_warning, CronTrigger(hour=wh, minute=wm, timezone=tz), args=[app])
    scheduler.add_job(tasks_reminder, CronTrigger(hour=14, minute=0, timezone=tz), args=[app])
    scheduler.add_job(meeting_reminder, CronTrigger(hour=15, minute=0, day_of_week='0,1,2,3,4', timezone=tz), args=[app])
    scheduler.add_job(send_daily_meeting, CronTrigger(hour=22, minute=0, day_of_week='0,1,2,3,4', timezone=tz), args=[app])
    scheduler.add_job(weekly_closing, CronTrigger(hour=20, minute=0, day_of_week='4', timezone=tz), args=[app])
    scheduler.add_job(sunday_reminder, CronTrigger(hour=11, minute=30, day_of_week='0', timezone=tz), args=[app])
    scheduler.add_job(daily_stats, CronTrigger(hour=21, minute=30, timezone=tz), args=[app])
    scheduler.add_job(send_tasks_report, CronTrigger(hour=21, minute=0, timezone=tz), args=[app])
    scheduler.add_job(daily_backup, CronTrigger(hour=0, minute=0, timezone=tz), args=[app])

    scheduler.start()
    logger.info(f"✅ Scheduler started - {len(GROUP_IDS)} مجموعات")
