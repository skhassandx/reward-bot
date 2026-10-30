"""সিম্পল SQLite ডেটাবেজ লেয়ার (aiosqlite)।"""
import time
import aiosqlite
from config import Config


async def init_db():
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            ref_by INTEGER DEFAULT 0,
            balance_usd_micro INTEGER DEFAULT 0,
            created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS tasks(
            user_id INTEGER,
            task_type TEXT,
            amount_usd_micro INTEGER,
            ts INTEGER
        );
        CREATE TABLE IF NOT EXISTS withdrawals(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            token TEXT,
            address TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending',
            ts INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id, ts);
        """)
        await db.commit()


def usd_to_micro(usd: float) -> int:
    return int(round(usd * 1_000_000))


def micro_to_usd(micro: int) -> float:
    return micro / 1_000_000


async def add_user(user_id: int, ref_by: int = 0):
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users(user_id, ref_by, created_at) VALUES(?,?,?)",
            (user_id, ref_by, int(time.time())))
        await db.commit()


async def credit(user_id: int, usd: float):
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance_usd_micro = balance_usd_micro + ? WHERE user_id = ?",
            (usd_to_micro(usd), user_id))
        await db.commit()


async def get_balance(user_id: int) -> float:
    async with aiosqlite.connect(Config.DB_PATH) as db:
        cur = await db.execute(
            "SELECT balance_usd_micro FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return micro_to_usd(row[0]) if row else 0.0


async def get_ref_by(user_id: int) -> int:
    async with aiosqlite.connect(Config.DB_PATH) as db:
        cur = await db.execute(
            "SELECT ref_by FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else 0


async def get_ref_count(user_id: int) -> int:
    async with aiosqlite.connect(Config.DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM users WHERE ref_by = ?", (user_id,))
        row = await cur.fetchone()
        return row[0]


async def last_task_ts(user_id: int, task_type: str) -> int:
    async with aiosqlite.connect(Config.DB_PATH) as db:
        cur = await db.execute(
            "SELECT MAX(ts) FROM tasks WHERE user_id = ? AND task_type = ?",
            (user_id, task_type))
        row = await cur.fetchone()
        return row[0] or 0


async def log_task(user_id: int, task_type: str, usd: float):
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute(
            "INSERT INTO tasks(user_id, task_type, amount_usd_micro, ts) VALUES(?,?,?,?)",
            (user_id, task_type, usd_to_micro(usd), int(time.time())))
        await db.commit()


async def create_withdrawal(user_id: int, token: str, address: str, amount: float):
    async with aiosqlite.connect(Config.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO withdrawals(user_id, token, address, amount, ts)
               VALUES(?,?,?,?,?)""",
            (user_id, token.upper(), address, amount, int(time.time())))
        await db.commit()
        return cur.lastrowid


async def get_pending_withdrawals():
    async with aiosqlite.connect(Config.DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, user_id, token, address, amount FROM withdrawals WHERE status='pending'")
        return await cur.fetchall()


async def set_withdrawal_status(wid: int, status: str):
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute("UPDATE withdrawals SET status=? WHERE id=?",
                         (status, wid))
        await db.commit()


async def deduct_balance(user_id: int, usd: float):
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance_usd_micro = MAX(0, balance_usd_micro - ?) WHERE user_id = ?",
            (usd_to_micro(usd), user_id))
        await db.commit()


async def stats():
    async with aiosqlite.connect(Config.DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(balance_usd_micro),0) FROM users")
        users, bal = await cur.fetchone()
        cur = await db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM withdrawals WHERE status='paid'")
        paid = await cur.fetchone()
        return users, micro_to_usd(bal), paid[0]
