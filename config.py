import os

# ========== البوت ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ========== المجموعة الرئيسية ==========
GROUP_ID = int(os.getenv("GROUP_ID", "-1005319609296"))

# ========== 10 مجموعات ==========
def _get_groups():
    groups = [GROUP_ID]
    for i in range(2, 11):
        g = os.getenv(f"GROUP_ID_{i}", "")
        if g.strip():
            groups.append(int(g.strip()))
    return groups

GROUP_IDS = _get_groups()

# ========== الأدمن الرئيسي ==========
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))

# ========== 3 أدمن ==========
def _get_admins():
    admins = list(ADMIN_IDS)
    for i in range(2, 4):
        a = os.getenv(f"ADMIN_ID_{i}", "")
        if a.strip():
            admins.append(int(a.strip()))
    return list(set(admins))

ALL_ADMINS = _get_admins()

# ========== التوقيت ==========
TIMEZONE = "Asia/Baghdad"
OPEN_HOUR, OPEN_MINUTE = 11, 0
CLOSE_HOUR, CLOSE_MINUTE = 21, 0
WARNING_MINUTES = 10

# ========== الأداء ==========
CACHE_TTL = 3600
MAX_RETRIES = 3
RETRY_DELAY = 2
FAST_MODE_THRESHOLD = 0.85

# ========== الحماية ==========
BANNED_WORDS = ["سبام", "spam"]
MAX_WARNINGS = 3
SPAM_WINDOW = 60
MAX_MSGS_PER_WINDOW = 5

# ========== قاعدة البيانات ==========
DB_PATH = "top_cash.db"
BACKUP_DIR = "backups"
