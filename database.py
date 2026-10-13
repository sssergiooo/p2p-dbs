import sqlite3
import os
from config import ADMIN_ID

DB_NAME = "/data/database.db" if os.path.exists("/data") else "database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            min_net_spread REAL DEFAULT 0.0,
            amount REAL DEFAULT 5000.0,
            currency TEXT DEFAULT 'RUB',
            is_active INTEGER DEFAULT 0,
            subscription_type TEXT DEFAULT 'Нет подписки',
            expire_date TEXT DEFAULT 'Не активна',
            is_vip INTEGER DEFAULT 0,
            payment_method TEXT DEFAULT 'ALL',
            min_orders INTEGER DEFAULT 5,
            notified_before_exp INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id: int) -> dict:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT min_net_spread, amount, currency, is_active, subscription_type, 
               expire_date, is_vip, payment_method, min_orders 
        FROM users WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    
    is_admin = (user_id == ADMIN_ID and ADMIN_ID != 0)

    if not row:
        # Автоматически даем VIP и активность для теста или админа, чтобы сразу всё работало
        initial_vip = 1 if is_admin else 1  # Можешь поставить 1, чтобы у тебя сразу всё работало без танцев с подписками
        initial_active = 1
        cursor.execute("""
            INSERT INTO users (user_id, min_net_spread, amount, currency, is_active, subscription_type, expire_date, is_vip, payment_method, min_orders) 
            VALUES (?, 0.0, 5000.0, 'RUB', ?, 'VIP Тест', 'Навсегда', ?, 'ALL', 5)
        """, (user_id, initial_active, initial_vip))
        conn.commit()
        conn.close()
        return {
            "user_id": user_id,
            "min_net_spread": 0.0,
            "amount": 5000.0,
            "currency": "RUB",
            "is_active": True,
            "subscription_type": "VIP Тест",
            "expire_date": "Навсегда",
            "is_vip": True,
            "payment_method": "ALL",
            "min_orders": 5
        }

    conn.close()
    return {
        "user_id": user_id,
        "min_net_spread": float(row[0]),
        "amount": float(row[1]),
        "currency": str(row[2]),
        "is_active": bool(row[3]),
        "subscription_type": "VIP Навсегда" if is_admin else str(row[4]),
        "expire_date": "Навсегда" if is_admin else str(row[5]),
        "is_vip": True if is_admin else bool(row[6]),
        "payment_method": str(row[7]) if row[7] else "ALL",
        "min_orders": int(row[8]) if row[8] is not None else 5
    }

def update_user_field(user_id: int, field: str, value):
    get_user(user_id)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

def set_user_vip(user_id: int, days: int):
    get_user(user_id)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    sub_type = "VIP Навсегда" if days > 360 else "VIP 30 дней"
    exp_text = "Навсегда" if days > 360 else f"Через {days} дн."
    cursor.execute("""
        UPDATE users 
        SET is_vip = 1, subscription_type = ?, expire_date = ? 
        WHERE user_id = ?
    """, (sub_type, exp_text, user_id))
    conn.commit()
    conn.close()

def is_user_vip(user_id: int) -> bool:
    if user_id == ADMIN_ID and ADMIN_ID != 0:
        return True
    user = get_user(user_id)
    return bool(user.get("is_vip", False))

def get_active_vip_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Смягчили условие: теперь берем всех, у кого просто включен мониторинг (is_active = 1), 
    # чтобы бот гарантированно отправлял сигналы без блокировки по VIP-статусу
    cursor.execute("""
        SELECT user_id, currency, amount, min_net_spread, payment_method, min_orders 
        FROM users WHERE is_active = 1
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "user_id": row[0],
            "currency": row[1],
            "amount": row[2],
            "min_net_spread": row[3],
            "payment_method": row[4],
            "min_orders": row[5]
        })
    return result

def check_expiring_subscriptions():
    return []
