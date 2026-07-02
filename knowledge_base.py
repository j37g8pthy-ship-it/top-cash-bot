"""
قاعدة معرفة TOP CASH - أضف معلومات المنصة الحقيقية هنا
"""
from database import db

KNOWLEDGE = {
    "top1": {
        "category": "مستويات",
        "question": "TOP 1 ما هو",
        "answer": "📌 TOP 1 - المستوى الأول:\n[أضف تفاصيل TOP 1 هنا]"
    },
    "top2": {
        "category": "مستويات",
        "question": "TOP 2 ما هو",
        "answer": "📌 TOP 2 - المستوى الثاني:\n[أضف تفاصيل TOP 2 هنا]"
    },
    "top3": {
        "category": "مستويات",
        "question": "TOP 3 ما هو",
        "answer": "📌 TOP 3 - المستوى الثالث:\n[أضف تفاصيل TOP 3 هنا]"
    },
    "withdrawal": {
        "category": "مالي",
        "question": "كيف السحب طريقة السحب",
        "answer": (
            "💰 طريقة السحب:\n"
            "• الحد الأدنى: [المبلغ]\n"
            "• مدة المعالجة: [المدة]\n"
            "• الطريقة: [زين كاش / كي كارد]\n"
            "[أضف تفاصيل السحب هنا]"
        )
    },
    "deposit": {
        "category": "مالي",
        "question": "كيف الإيداع طريقة الإيداع",
        "answer": "💳 طريقة الإيداع:\n[أضف تفاصيل الإيداع هنا]"
    },
    "profits": {
        "category": "مالي",
        "question": "الأرباح كيف الربح",
        "answer": "📈 نظام الأرباح:\n[أضف تفاصيل الأرباح هنا]"
    },
    "tasks": {
        "category": "مهام",
        "question": "المهام اليومية",
        "answer": "✅ المهام اليومية:\n[أضف تفاصيل المهام هنا]"
    },
    "upgrade": {
        "category": "ترقية",
        "question": "الترقية كيف أترقى",
        "answer": "⬆️ نظام الترقية:\n[أضف شروط الترقية هنا]"
    },
    "rules": {
        "category": "قوانين",
        "question": "القوانين والتعليمات",
        "answer": "📜 قوانين المنصة:\n[أضف القوانين هنا]"
    },
}

def init_knowledge():
    """تهيئة قاعدة المعرفة الأساسية عند أول تشغيل"""
    existing = db.get_all_knowledge()
    if not existing:
        for key, item in KNOWLEDGE.items():
            db.add_knowledge(
                question=item["question"],
                answer=item["answer"],
                category=item["category"],
                source="system"
            )
        print("✅ تم تهيئة قاعدة المعرفة الأساسية")

def load_pdf(pdf_path: str, category: str = "وثائق"):
    """تحميل معرفة من PDF"""
    try:
        import PyPDF2
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = "".join(p.extract_text() for p in reader.pages)
        name = os.path.basename(pdf_path)
        db.add_knowledge(f"محتوى {name}", text, category, "pdf")
        return True
    except Exception as e:
        print(f"❌ خطأ في تحميل PDF: {e}")
        return False
