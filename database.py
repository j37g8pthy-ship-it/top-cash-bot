import sqlite3
import json
import os
import shutil
from datetime import datetime, date
from config import DB_PATH, BACKUP_DIR
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    hits INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'admin',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS user_memory (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_seen TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    subscription_level TEXT DEFAULT 'none',
                    warnings INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    notes TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    question TEXT,
                    answer TEXT,
                    source TEXT DEFAULT 'ai',
                    response_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS response_cache (
                    question_hash TEXT PRIMARY KEY,
                    question TEXT,
                    answer TEXT,
                    hits INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS unknown_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    question TEXT,
                    answered INTEGER DEFAULT 0,
                    admin_answer TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error TEXT,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS message_track (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    msg_text TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        logger.info("✅ Database ready")

    def add_knowledge(self, question: str, answer: str, category: str = "general", source: str = "admin"):
        with self._conn() as c:
            c.execute("INSERT INTO knowledge (question, answer, category, source) VALUES (?,?,?,?)",
                      (question, answer, category, source))

    def update_knowledge(self, kid: int, question: str, answer: str):
        with self._conn() as c:
            c.execute("UPDATE knowledge SET question=?, answer=? WHERE id=?", (question, answer, kid))

    def delete_knowledge(self, kid: int):
        with self._conn() as c:
            c.execute("DELETE FROM knowledge WHERE id=?", (kid,))

    def search_knowledge(self, query: str, limit: int = 1) -> list:
        """بحث ذكي - يلقى أدق إجابة"""
        with self._conn() as c:
            rows = c.execute("SELECT id, question, answer, hits FROM knowledge").fetchall()

            scored = []
            query_words = [w for w in query.split() if len(w) > 2]

            for row in rows:
                score = 0
                q = row["question"].lower()

                for word in query_words:
                    w = word.lower()
                    if w in q:
                        score += 10
                    elif len(w) >= 4 and w[:4] in q:
                        score += 5
                    elif len(w) >= 3 and w[:3] in q:
                        score += 3

                if score > 0:
                    scored.append((score, row["id"], row["answer"]))

            if not scored:
                return []

            scored.sort(reverse=True)
            best_score = scored[0][0]

            results = []
            for score, rid, answer in scored:
                if score == best_score:
                    results.append(answer)
                    c.execute("UPDATE knowledge SET hits=hits+1 WHERE id=?", (rid,))

            return results[:limit]

    def get_all_knowledge(self) -> list:
        with self._conn() as c:
            return c.execute("SELECT * FROM knowledge ORDER BY category, created_at").fetchall()

    def upsert_user(self, user_id: int, username: str = None, first_name: str = None):
        with self._conn() as c:
            exists = c.execute("SELECT user_id FROM user_memory WHERE user_id=?", (user_id,)).fetchone()
            if exists:
                c.execute("""UPDATE user_memory SET username=?, first_name=?,
                             last_seen=CURRENT_TIMESTAMP, message_count=message_count+1
                             WHERE user_id=?""", (username, first_name, user_id))
            else:
                c.execute("""INSERT INTO user_memory (user_id, username, first_name, last_seen, message_count)
                             VALUES (?,?,?,CURRENT_TIMESTAMP,1)""", (user_id, username, first_name))

    def get_user(self, user_id: int) -> dict:
        with self._conn() as c:
            row = c.execute("SELECT * FROM user_memory WHERE user_id=?", (user_id,)).fetchone()
            return dict(row) if row else {}

    def add_warning(self, user_id: int) -> int:
        with self._conn() as c:
            c.execute("UPDATE user_memory SET warnings=warnings+1 WHERE user_id=?", (user_id,))
            row = c.execute("SELECT warnings FROM user_memory WHERE user_id=?", (user_id,)).fetchone()
            return row["warnings"] if row else 0

    def ban_user(self, user_id: int):
        with self._conn() as c:
            c.execute("UPDATE user_memory SET is_banned=1 WHERE user_id=?", (user_id,))

    def unban_user(self, user_id: int):
        with self._conn() as c:
            c.execute("UPDATE user_memory SET is_banned=0, warnings=0 WHERE user_id=?", (user_id,))

    def is_banned(self, user_id: int) -> bool:
        with self._conn() as c:
            row = c.execute("SELECT is_banned FROM user_memory WHERE user_id=?", (user_id,)).fetchone()
            return bool(row["is_banned"]) if row else False

    def set_subscription(self, user_id: int, level: str):
        with self._conn() as c:
            c.execute("UPDATE user_memory SET subscription_level=? WHERE user_id=?", (level, user_id))

    def get_cache(self, question: str) -> str | None:
        import hashlib
        qhash = hashlib.md5(question.encode()).hexdigest()
        with self._conn() as c:
            row = c.execute("""SELECT answer FROM response_cache
                               WHERE question_hash=? AND expires_at > CURRENT_TIMESTAMP""", (qhash,)).fetchone()
            if row:
                c.execute("UPDATE response_cache SET hits=hits+1 WHERE question_hash=?", (qhash,))
                return row["answer"]
        return None

    def set_cache(self, question: str, answer: str, ttl: int = 3600):
        import hashlib
        qhash = hashlib.md5(question.encode()).hexdigest()
        with self._conn() as c:
            c.execute("""INSERT OR REPLACE INTO response_cache
                         (question_hash, question, answer, expires_at)
                         VALUES (?, ?, ?, datetime('now', ? || ' seconds'))""",
                      (qhash, question, answer, str(ttl)))

    def log_conversation(self, user_id: int, question: str, answer: str,
                          source: str = "ai", response_time: float = 0):
        with self._conn() as c:
            c.execute("""INSERT INTO conversations (user_id, question, answer, source, response_time)
                         VALUES (?,?,?,?,?)""", (user_id, question, answer, source, response_time))

    def log_unknown(self, user_id: int, question: str):
        with self._conn() as c:
            c.execute("INSERT INTO unknown_questions (user_id, question) VALUES (?,?)", (user_id, question))

    def answer_unknown(self, qid: int, answer: str):
        with self._conn() as c:
            c.execute("UPDATE unknown_questions SET answered=1, admin_answer=? WHERE id=?", (answer, qid))

    def get_unknowns(self, limit: int = 10) -> list:
        with self._conn() as c:
            return c.execute("""SELECT * FROM unknown_questions WHERE answered=0
                                ORDER BY created_at DESC LIMIT ?""", (limit,)).fetchall()

    def track_msg(self, user_id: int, text: str):
        with self._conn() as c:
            c.execute("INSERT INTO message_track (user_id, msg_text) VALUES (?,?)", (user_id, text))

    def count_recent(self, user_id: int, window: int) -> int:
        with self._conn() as c:
            row = c.execute("""SELECT COUNT(*) as cnt FROM message_track
                               WHERE user_id=? AND sent_at > datetime('now', ? || ' seconds')""",
                            (user_id, f"-{window}")).fetchone()
            return row["cnt"] if row else 0

    def count_repeated(self, user_id: int, text: str, window: int) -> int:
        with self._conn() as c:
            row = c.execute("""SELECT COUNT(*) as cnt FROM message_track
                               WHERE user_id=? AND msg_text=?
                               AND sent_at > datetime('now', ? || ' seconds')""",
                            (user_id, text, f"-{window}")).fetchone()
            return row["cnt"] if row else 0

    def get_stats(self) -> dict:
        today = date.today().isoformat()
        with self._conn() as c:
            total_users = c.execute("SELECT COUNT(*) as n FROM user_memory").fetchone()["n"]
            active_today = c.execute("""SELECT COUNT(DISTINCT user_id) as n FROM conversations
                                        WHERE DATE(created_at)=?""", (today,)).fetchone()["n"]
            questions_today = c.execute("""SELECT COUNT(*) as n FROM conversations
                                           WHERE DATE(created_at)=?""", (today,)).fetchone()["n"]
            cache_hits = c.execute("SELECT SUM(hits) as n FROM response_cache").fetchone()["n"] or 0
            top_q = c.execute("""SELECT question, COUNT(*) as cnt FROM conversations
                                  WHERE DATE(created_at)=?
                                  GROUP BY question ORDER BY cnt DESC LIMIT 1""", (today,)).fetchone()
            unknowns = c.execute("SELECT COUNT(*) as n FROM unknown_questions WHERE answered=0").fetchone()["n"]
            top_knowledge = c.execute("""SELECT question, hits FROM knowledge
                                          ORDER BY hits DESC LIMIT 3""").fetchall()
        return {
            "total_users": total_users,
            "active_today": active_today,
            "questions_today": questions_today,
            "cache_hits": cache_hits,
            "top_question": top_q["question"][:60] if top_q else "لا يوجد",
            "unanswered": unknowns,
            "top_knowledge": [(r["question"], r["hits"]) for r in top_knowledge],
        }

    def log_event(self, etype: str, data: dict = {}):
        with self._conn() as c:
            c.execute("INSERT INTO events (type, data) VALUES (?,?)",
                      (etype, json.dumps(data, ensure_ascii=False)))

    def log_error(self, error: str, context: str = ""):
        with self._conn() as c:
            c.execute("INSERT INTO errors (error, context) VALUES (?,?)", (error, context))

    def backup(self) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(BACKUP_DIR, f"backup_{ts}.db")
        shutil.copy2(DB_PATH, path)
        return path

db = Database()
