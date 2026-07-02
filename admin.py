from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from config import ADMIN_IDS, GROUP_ID
from database import db
import logging

logger = logging.getLogger(__name__)

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper

# ===== لوحة التحكم الرئيسية =====
@admin_only
async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
         InlineKeyboardButton("👥 المستخدمين", callback_data="users")],
        [InlineKeyboardButton("📚 قاعدة المعرفة", callback_data="knowledge"),
         InlineKeyboardButton("❓ أسئلة معلقة", callback_data="unknowns")],
        [InlineKeyboardButton("🔓 فتح المجموعة", callback_data="open"),
         InlineKeyboardButton("🔒 إغلاق المجموعة", callback_data="close")],
        [InlineKeyboardButton("💾 نسخة احتياطية", callback_data="backup"),
         InlineKeyboardButton("📢 إرسال إعلان", callback_data="announce")],
    ]
    await update.message.reply_text(
        "🎛️ لوحة تحكم TOP CASH AI\n\nاختر الخيار المطلوب:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== الإحصائيات =====
@admin_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = db.get_stats()
    top_k = "\n".join([f"  • {q} ({h} مرة)" for q, h in stats["top_knowledge"]]) or "  لا يوجد"
    text = (
        f"📊 إحصائيات TOP CASH AI\n"
        f"{'─'*30}\n"
        f"👥 إجمالي المستخدمين: {stats['total_users']}\n"
        f"🟢 نشطون اليوم: {stats['active_today']}\n"
        f"❓ أسئلة اليوم: {stats['questions_today']}\n"
        f"⚡ كاش الردود: {stats['cache_hits']} ضربة\n"
        f"🔥 أكثر سؤال: {stats['top_question']}\n"
        f"⏳ أسئلة معلقة: {stats['unanswered']}\n"
        f"{'─'*30}\n"
        f"📚 أكثر معلومات طُلبت:\n{top_k}"
    )
    await update.message.reply_text(text)

# ===== الإعلانات =====
@admin_only
async def cmd_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: /announce [نص الإعلان]")
        return
    text = " ".join(context.args)
    msg = (
        f"📢 إعلان رسمي\n"
        f"{'─'*25}\n\n"
        f"{text}\n\n"
        f"{'─'*25}\n"
        f"💙 إدارة TOP CASH"
    )
    await context.bot.send_message(chat_id=GROUP_ID, text=msg)
    await update.message.reply_text("✅ تم إرسال الإعلان")

# ===== إرسال رسالة جماعية =====
@admin_only
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: /broadcast [الرسالة]")
        return
    text = " ".join(context.args)
    users = db.get_all_knowledge()  # نرسل للمجموعة فقط
    await context.bot.send_message(chat_id=GROUP_ID, text=f"📣 رسالة جماعية:\n\n{text}")
    await update.message.reply_text("✅ تم الإرسال")

# ===== فتح/إغلاق المجموعة =====
@admin_only
async def cmd_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import ChatPermissions
    await context.bot.set_chat_permissions(
        chat_id=GROUP_ID,
        permissions=ChatPermissions(can_send_messages=True)
    )
    await context.bot.send_message(
        chat_id=GROUP_ID,
        text=(
            "🌞 صباح الخير أعضاء TOP CASH\n\n"
            "تم فتح الدردشة لهذا اليوم.\n\n"
            "يمكنكم الآن:\n"
            "• طرح جميع استفساراتكم.\n"
            "• مشاركة إنجازاتكم.\n"
            "• متابعة آخر الإعلانات.\n\n"
            "نتمنى لكم يوماً مليئاً بالنجاح والأرباح.\n\n"
            "💙 إدارة TOP CASH"
        )
    )
    await update.message.reply_text("✅ تم فتح المجموعة")

@admin_only
async def cmd_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import ChatPermissions
    await context.bot.set_chat_permissions(
        chat_id=GROUP_ID,
        permissions=ChatPermissions(can_send_messages=False)
    )
    await context.bot.send_message(
        chat_id=GROUP_ID,
        text=(
            "🌙 انتهى الدوام الرسمي لهذا اليوم.\n\n"
            "تم إغلاق الدردشة، وسيتم فتحها غداً الساعة 11:00 صباحاً.\n\n"
            "شاكرين تعاونكم.\n"
            "نتمنى لكم مساءً سعيداً.\n\n"
            "💙 إدارة TOP CASH"
        )
    )
    await update.message.reply_text("✅ تم إغلاق المجموعة")

# ===== قاعدة المعرفة =====
@admin_only
async def cmd_addinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: /addinfo [سؤال] | [جواب]")
        return
    full = " ".join(context.args)
    if "|" not in full:
        await update.message.reply_text("⚠️ افصل السؤال عن الجواب بـ |")
        return
    q, a = full.split("|", 1)
    db.add_knowledge(q.strip(), a.strip())
    await update.message.reply_text(f"✅ تمت الإضافة!\nسؤال: {q.strip()[:50]}")

@admin_only
async def cmd_listinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = db.get_all_knowledge()
    if not items:
        await update.message.reply_text("قاعدة المعرفة فارغة")
        return
    text = "📚 قاعدة المعرفة:\n\n"
    for item in items[:15]:
        text += f"#{item['id']} [{item['category']}] {item['question'][:40]}\n"
    await update.message.reply_text(text)

@admin_only
async def cmd_delinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: /delinfo [رقم المعلومة]")
        return
    try:
        kid = int(context.args[0])
        db.delete_knowledge(kid)
        await update.message.reply_text(f"✅ تم حذف المعلومة #{kid}")
    except ValueError:
        await update.message.reply_text("⚠️ أدخل رقماً صحيحاً")

# ===== الأسئلة المعلقة =====
@admin_only
async def cmd_unknowns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = db.get_unknowns(10)
    if not questions:
        await update.message.reply_text("✅ لا توجد أسئلة معلقة")
        return
    text = "❓ أسئلة لم يجد البوت إجابة لها:\n\n"
    for q in questions:
        text += f"#{q['id']} - {q['question'][:60]}\n"
    text += "\nللإجابة: /answer [رقم] | [الإجابة]"
    await update.message.reply_text(text)

@admin_only
async def cmd_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: /answer [رقم] | [الإجابة]")
        return
    full = " ".join(context.args)
    if "|" not in full:
        await update.message.reply_text("⚠️ افصل الرقم عن الإجابة بـ |")
        return
    num, ans = full.split("|", 1)
    try:
        qid = int(num.strip())
        db.answer_unknown(qid, ans.strip())
        db.add_knowledge(f"سؤال #{qid}", ans.strip(), "من الإدارة")
        await update.message.reply_text(f"✅ تمت الإجابة وحفظها في قاعدة المعرفة")
    except ValueError:
        await update.message.reply_text("⚠️ رقم غير صحيح")

# ===== إدارة المستخدمين =====
@admin_only
async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ رد على رسالة المستخدم")
        return
    user = update.message.reply_to_message.from_user
    warnings = db.add_warning(user.id)
    await update.message.reply_text(f"⚠️ تحذير لـ {user.first_name} ({warnings}/{3})")

@admin_only
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ رد على رسالة المستخدم")
        return
    user = update.message.reply_to_message.from_user
    db.ban_user(user.id)
    try:
        await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user.id)
    except Exception:
        pass
    await update.message.reply_text(f"🚫 تم حظر {user.first_name}")

@admin_only
async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: /unban [user_id]")
        return
    uid = int(context.args[0])
    db.unban_user(uid)
    try:
        await context.bot.unban_chat_member(chat_id=GROUP_ID, user_id=uid)
    except Exception:
        pass
    await update.message.reply_text(f"✅ تم رفع الحظر عن {uid}")

@admin_only
async def cmd_userinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ رد على رسالة المستخدم")
        return
    user = update.message.reply_to_message.from_user
    info = db.get_user(user.id)
    if not info:
        await update.message.reply_text("المستخدم غير موجود في قاعدة البيانات")
        return
    text = (
        f"👤 معلومات المستخدم:\n"
        f"الاسم: {info.get('first_name', 'غير معروف')}\n"
        f"يوزر: @{info.get('username', 'لا يوجد')}\n"
        f"ID: {info.get('user_id')}\n"
        f"رسائل: {info.get('message_count', 0)}\n"
        f"تحذيرات: {info.get('warnings', 0)}/3\n"
        f"محظور: {'نعم 🚫' if info.get('is_banned') else 'لا ✅'}\n"
        f"مستوى الاشتراك: {info.get('subscription_level', 'none')}\n"
        f"انضم: {info.get('joined_at', 'غير معروف')}"
    )
    await update.message.reply_text(text)

@admin_only
async def cmd_setlevel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not context.args:
        await update.message.reply_text("الاستخدام: /setlevel [top1/top2/top3] - رد على رسالة المستخدم")
        return
    user = update.message.reply_to_message.from_user
    level = context.args[0].lower()
    db.set_subscription(user.id, level)
    await update.message.reply_text(f"✅ تم تعيين مستوى {user.first_name} إلى {level}")

# ===== النسخة الاحتياطية =====
@admin_only
async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = db.backup()
    await update.message.reply_document(
        document=open(path, "rb"),
        filename=path.split("/")[-1].split("\\")[-1],
        caption="💾 نسخة احتياطية - TOP CASH AI"
    )

# ===== Callback للوحة التحكم =====
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id

    if data == "stats":
        stats = db.get_stats()
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"📊 إحصائيات:\n"
                f"👥 مستخدمين: {stats['total_users']}\n"
                f"🟢 نشطون اليوم: {stats['active_today']}\n"
                f"❓ أسئلة اليوم: {stats['questions_today']}\n"
                f"⏳ معلقة: {stats['unanswered']}"
            )
        )
    elif data == "unknowns":
        questions = db.get_unknowns(10)
        if not questions:
            await context.bot.send_message(chat_id=chat_id, text="✅ لا توجد أسئلة معلقة")
        else:
            text = "❓ أسئلة لم يجد البوت إجابة لها:\n\n"
            for q in questions:
                text += f"#{q['id']} - {q['question'][:60]}\n"
            text += "\nللإجابة: /answer [رقم] | [الإجابة]"
            await context.bot.send_message(chat_id=chat_id, text=text)
    elif data == "knowledge":
        items = db.get_all_knowledge()
        if not items:
            await context.bot.send_message(chat_id=chat_id, text="قاعدة المعرفة فارغة\nاستخدم: /addinfo [سؤال] | [جواب]")
        else:
            text = "📚 قاعدة المعرفة:\n\n"
            for item in items[:15]:
                text += f"#{item['id']} {item['question'][:40]}\n"
            await context.bot.send_message(chat_id=chat_id, text=text)
    elif data == "backup":
        path = db.backup()
        await context.bot.send_document(
            chat_id=chat_id,
            document=open(path, "rb"),
            caption="💾 نسخة احتياطية - TOP CASH AI"
        )
    elif data == "open":
        from telegram import ChatPermissions
        await context.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions=ChatPermissions(can_send_messages=True)
        )
        await context.bot.send_message(chat_id=GROUP_ID, text=(
            "🌞 صباح الخير أعضاء TOP CASH\n\n"
            "تم فتح الدردشة لهذا اليوم.\n\n"
            "💙 إدارة TOP CASH"
        ))
        await context.bot.send_message(chat_id=chat_id, text="✅ تم فتح المجموعة")
    elif data == "close":
        from telegram import ChatPermissions
        await context.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await context.bot.send_message(chat_id=GROUP_ID, text=(
            "🌙 انتهى الدوام الرسمي لهذا اليوم.\n\n"
            "تم إغلاق الدردشة، وسيتم فتحها غداً الساعة 11:00 صباحاً.\n\n"
            "💙 إدارة TOP CASH"
        ))
        await context.bot.send_message(chat_id=chat_id, text="✅ تم إغلاق المجموعة")
    elif data == "announce":
        await context.bot.send_message(
            chat_id=chat_id,
            text="📢 لإرسال إعلان استخدم:\n/announce [نص الإعلان]"
        )
    elif data == "users":
        stats = db.get_stats()
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"👥 إجمالي المستخدمين: {stats['total_users']}\n🟢 نشطون اليوم: {stats['active_today']}"
        )

def register_admin_handlers(app):
    from telegram.ext import CommandHandler, CallbackQueryHandler
    app.add_handler(CommandHandler("panel", cmd_panel))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("announce", cmd_announce))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("open", cmd_open))
    app.add_handler(CommandHandler("close", cmd_close))
    app.add_handler(CommandHandler("addinfo", cmd_addinfo))
    app.add_handler(CommandHandler("listinfo", cmd_listinfo))
    app.add_handler(CommandHandler("delinfo", cmd_delinfo))
    app.add_handler(CommandHandler("unknowns", cmd_unknowns))
    app.add_handler(CommandHandler("answer", cmd_answer))
    app.add_handler(CommandHandler("warn", cmd_warn))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("userinfo", cmd_userinfo))
    app.add_handler(CommandHandler("setlevel", cmd_setlevel))
    app.add_handler(CommandHandler("backup", cmd_backup))
    app.add_handler(CallbackQueryHandler(handle_callback))