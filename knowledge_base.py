from database import db
import sqlite3, os

DATA = [
    ("السحب كيف السحب طريقة السحب اسحب", "💸 السحب في TOP CASH:\n📅 أيام السحب: الأحد إلى الخميس\n⚡ السحب الفوري: 5 دقائق - عمولة 35%\n🕒 السحب العادي: 72 ساعة - عمولة 10%\n📌 تأكد من صحة بيانات محفظتك.", "مالي"),
    ("TOP 2 top2 ربح top-2", "🥈 باقة TOP-2:\n💳 150$\n💰 ربح يومي: 6$\n📅 شهري: 180$\n📈 سنوي: 2190$\n🎁 إحالة: 15$", "مستويات"),
    ("TOP 1 top1 ربح top-1", "🥉 باقة TOP-1:\n💳 75$\n💰 ربح يومي: 3$\n📅 شهري: 90$\n📈 سنوي: 1095$\n🎁 إحالة: 7.5$", "مستويات"),
    ("TOP 3 top3 ربح top-3", "🥇 باقة TOP-3:\n💳 300$\n💰 ربح يومي: 12$\n📅 شهري: 360$\n📈 سنوي: 4380$\n🎁 إحالة: 30$", "مستويات"),
    ("الباقات الاشتراك المستويات", "💎 باقات TOP CASH:\n🥉 TOP-1: 75$\n🥈 TOP-2: 150$\n🥇 TOP-3: 300$", "مستويات"),
    ("مكافأة الإحالة", "🎁 الإحالة:\nTOP-1: 7.5$\nTOP-2: 15$\nTOP-3: 30$", "مكافآت"),
    ("مهمة الفيديو", "🎬 مهمة الفيديو: انشر فيديو عن TOP CASH، إذا وصل 100,000 مشاهدة تحصل على 10$.", "مهام"),
    ("وقت الدوام ساعات", "⏰ الدوام: 11 صباحاً - 9 مساءً بتوقيت العراق 🇮🇶", "عام"),
    ("الارباح ربح كم اكسب", "💰 الأرباح:\nTOP-1: 3$ يومياً\nTOP-2: 6$ يومياً\nTOP-3: 12$ يومياً", "مالي"),
]

def init_knowledge():
    conn = sqlite3.connect("top_cash.db")
    conn.execute("DELETE FROM knowledge WHERE source='system'")
    conn.commit()
    for q, a, cat in DATA:
        conn.execute("INSERT INTO knowledge (question,answer,category,source) VALUES (?,?,?,?)", (q,a,cat,"system"))
    conn.commit()
    conn.close()
    print(f"✅ تم تحميل {len(DATA)} معلومة")
