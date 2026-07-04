import sqlite3
import os

DATA = [
    ("سحب اسحب طريقة السحب withdraw",
     "💸 السحب في TOP CASH:\n📅 أيام السحب: الأحد إلى الخميس\n⚡ السحب الفوري: 5 دقائق - عمولة 35%\n🕒 السحب العادي: 72 ساعة - عمولة 10%\n📌 تأكد من صحة بيانات محفظتك.",
     "مالي"),

    ("top1 TOP1 الأول",
     "🥉 باقة TOP-1:\n💳 سعر الاشتراك: 75$\n💰 ربح يومي: 3$\n📅 شهري: 90$\n📈 سنوي: 1095$",
     "مستويات"),

    ("top2 TOP2 الثاني",
     "🥈 باقة TOP-2:\n💳 سعر الاشتراك: 150$\n💰 ربح يومي: 6$\n📅 شهري: 180$\n📈 سنوي: 2190$",
     "مستويات"),

    ("top3 TOP3 الثالث",
     "🥇 باقة TOP-3:\n💳 سعر الاشتراك: 300$\n💰 ربح يومي: 12$\n📅 شهري: 360$\n📈 سنوي: 4380$",
     "مستويات"),

    ("باقات مستويات سعر اشتراك packages",
     "💎 باقات TOP CASH:\n🥉 TOP-1: 75$\n🥈 TOP-2: 150$\n🥇 TOP-3: 300$\nتبدأ الأرباح بعد التفعيل مباشرة.",
     "مستويات"),

    ("ربح يومي أرباح اكسب profit daily",
     "💰 الأرباح اليومية:\n🥉 TOP-1: 3$\n🥈 TOP-2: 6$\n🥇 TOP-3: 12$\nتُحتسب يومياً بعد التفعيل.",
     "مالي"),

    ("مكافأة إحالة احالة دعوة referral",
     "🎁 مكافآت الإحالة:\n\n🥉 اشتراكك TOP-1:\n• أي إحالة = 7.5$\n\n🥈 اشتراكك TOP-2:\n• إحالة TOP-1 = 7.5$\n• إحالة TOP-2/TOP-3 = 15$\n\n🥇 اشتراكك TOP-3:\n• إحالة TOP-1 = 7.5$\n• إحالة TOP-2 = 15$\n• إحالة TOP-3 = 30$\n\n📌 تُمنح عند تسجيل وتفعيل الاشتراك.",
     "مكافآت"),

    ("دخل سلبي شو ما passive فريق team مستوى ABC نسبة كيف",
     "📊 الدخل السلبي من الفريق في TOP CASH:\n• المستوى A = 3% من أرباحهم اليومية\n• المستوى B = 2%\n• المستوى C = 1%\n\nكلما توسع فريقك زادت أرباحك تلقائياً 💰",
     "مكافآت"),

    ("فيديو مشاهدات مهمة video views task",
     "🎬 مهمة الفيديو:\nانشر فيديو يروج لـ TOP CASH.\nإذا وصل 100,000 مشاهدة تحصل على 10$.\nأرسل صورة من حسابك مع ID للإدارة.",
     "مهام"),

    ("دوام ساعات وقت فتح غلق time hours",
     "⏰ ساعات الدوام:\n• الفتح: 11:00 صباحاً\n• الإغلاق: 9:00 مساءً\nبتوقيت العراق 🇮🇶",
     "عام"),
]

def init_knowledge():
    db_path = os.getenv("DB_PATH", "top_cash.db")
    conn = sqlite3.connect(db_path)
    
    # مسح system وإعادة تحميل دائماً
    conn.execute("DELETE FROM knowledge WHERE source='system'")
    conn.execute("DELETE FROM response_cache")
    
    for question, answer, category in DATA:
        conn.execute(
            "INSERT INTO knowledge (question,answer,category,source) VALUES (?,?,?,?)",
            (question, answer, category, "system")
        )
    conn.commit()
    conn.close()
    print(f"✅ تم تحميل {len(DATA)} معلومة")
