"""
database/db.py — PostgreSQL connection pool and schema initialization
"""

import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=os.getenv("DATABASE_URL"),
            sslmode="disable",
        )
    return _pool


def get_conn():
    return get_pool().getconn()


def release_conn(conn):
    get_pool().putconn(conn)


def init_db():
    """Create all tables if they don't exist."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    id              SERIAL PRIMARY KEY,
                    member_id       VARCHAR(20) UNIQUE NOT NULL,   -- e.g. LU90-001
                    telegram_id     BIGINT UNIQUE NOT NULL,
                    username        VARCHAR(100),
                    full_name       VARCHAR(200),
                    registered_at   TIMESTAMPTZ DEFAULT NOW(),
                    current_streak  INT DEFAULT 0,
                    longest_streak  INT DEFAULT 0,
                    total_days      INT DEFAULT 0
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_logs (
                    id              SERIAL PRIMARY KEY,
                    member_id       VARCHAR(20) NOT NULL REFERENCES members(member_id),
                    telegram_id     BIGINT NOT NULL,
                    day_number      INT NOT NULL,                  -- 1..90
                    log_date        DATE NOT NULL,
                    plan_text       TEXT NOT NULL,
                    progress_text   TEXT,
                    proof_file_id   VARCHAR(300),                  -- Telegram file_id
                    proof_type      VARCHAR(20),                   -- 'photo' | 'document' | 'text'
                    plan_submitted_at   TIMESTAMPTZ,
                    progress_submitted_at TIMESTAMPTZ,
                    UNIQUE(member_id, log_date)
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_logs_date
                ON daily_logs(log_date);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_logs_member
                ON daily_logs(member_id);
            """)

        conn.commit()
        print("✅ Database initialized successfully.")
    finally:
        release_conn(conn)