"""
database/queries.py — All SQL query helpers used by handlers
"""

from datetime import date, timedelta
from database.db import get_conn, release_conn


# ─────────────────────────────────────────────
#  Members
# ─────────────────────────────────────────────

def get_member_by_telegram_id(telegram_id: int) -> dict | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM members WHERE telegram_id = %s",
                (telegram_id,)
            )
            row = cur.fetchone()
            if row:
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
            return None
    finally:
        release_conn(conn)


def get_member_by_member_id(member_id: str) -> dict | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM members WHERE member_id = %s",
                (member_id.upper(),)
            )
            row = cur.fetchone()
            if row:
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
            return None
    finally:
        release_conn(conn)


def register_member(member_id: str, telegram_id: int, username: str, full_name: str) -> bool:
    """Returns True if newly registered, False if already exists."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO members (member_id, telegram_id, username, full_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                (member_id.upper(), telegram_id, username, full_name)
            )
            result = cur.fetchone()
        conn.commit()
        return result is not None
    finally:
        release_conn(conn)


def get_all_members() -> list[dict]:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM members ORDER BY current_streak DESC, total_days DESC"
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        release_conn(conn)


def update_streak(member_id: str, new_streak: int, longest: int, total: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE members
                SET current_streak = %s,
                    longest_streak = %s,
                    total_days = %s
                WHERE member_id = %s
                """,
                (new_streak, longest, total, member_id)
            )
        conn.commit()
    finally:
        release_conn(conn)


# ─────────────────────────────────────────────
#  Daily Logs
# ─────────────────────────────────────────────

def get_log_for_today(member_id: str, today: date) -> dict | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM daily_logs WHERE member_id = %s AND log_date = %s",
                (member_id, today)
            )
            row = cur.fetchone()
            if row:
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
            return None
    finally:
        release_conn(conn)


def submit_plan(member_id: str, telegram_id: int, day_number: int,
                log_date: date, plan_text: str) -> bool:
    """Insert a new daily log with the plan. Returns True on success."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO daily_logs
                    (member_id, telegram_id, day_number, log_date, plan_text, plan_submitted_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (member_id, log_date) DO NOTHING
                RETURNING id
                """,
                (member_id, telegram_id, day_number, log_date, plan_text)
            )
            result = cur.fetchone()
        conn.commit()
        return result is not None
    finally:
        release_conn(conn)


def submit_progress(member_id: str, log_date: date, progress_text: str,
                    proof_file_id: str | None, proof_type: str | None):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE daily_logs
                SET progress_text = %s,
                    proof_file_id = %s,
                    proof_type = %s,
                    progress_submitted_at = NOW()
                WHERE member_id = %s AND log_date = %s
                """,
                (progress_text, proof_file_id, proof_type, member_id, log_date)
            )
        conn.commit()
    finally:
        release_conn(conn)


def get_members_without_log_today(today: date) -> list[dict]:
    """Return all members who haven't submitted a plan today."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT m.*
                FROM members m
                LEFT JOIN daily_logs dl
                    ON dl.member_id = m.member_id AND dl.log_date = %s
                WHERE dl.id IS NULL
                """,
                (today,)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        release_conn(conn)


def get_members_without_progress_today(today: date) -> list[dict]:
    """Return members who submitted plan but not progress."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT m.*
                FROM members m
                INNER JOIN daily_logs dl
                    ON dl.member_id = m.member_id AND dl.log_date = %s
                WHERE dl.progress_text IS NULL
                """,
                (today,)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        release_conn(conn)


def get_leaderboard_with_today_status(today: date) -> list[dict]:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    m.member_id,
                    m.full_name,
                    m.current_streak,
                    m.longest_streak,
                    m.total_days,
                    CASE WHEN dl.id IS NOT NULL THEN TRUE ELSE FALSE END AS logged_today
                FROM members m
                LEFT JOIN daily_logs dl
                    ON dl.member_id = m.member_id AND dl.log_date = %s
                ORDER BY m.current_streak DESC, m.total_days DESC
                """,
                (today,)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        release_conn(conn)


def reset_streaks_for_missed(yesterday: date):
    """Reset streak to 0 for members who missed yesterday."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE members
                SET current_streak = 0
                WHERE member_id NOT IN (
                    SELECT DISTINCT member_id FROM daily_logs WHERE log_date = %s
                )
                """,
                (yesterday,)
            )
        conn.commit()
    finally:
        release_conn(conn)


def delete_log_for_today(member_id: str, today: date):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM daily_logs WHERE member_id = %s AND log_date = %s",
                (member_id, today)
            )
        conn.commit()
    finally:
        release_conn(conn)


# ─────────────────────────────────────────────
#  Proof Files (supports multiple photos/documents per submission)
# ─────────────────────────────────────────────

def get_daily_log_id(member_id: str, log_date: date) -> int | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM daily_logs WHERE member_id = %s AND log_date = %s",
                (member_id, log_date)
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        release_conn(conn)


def add_proof_file(daily_log_id: int, file_id: str, file_type: str):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO proof_files (daily_log_id, file_id, file_type)
                VALUES (%s, %s, %s)
                """,
                (daily_log_id, file_id, file_type)
            )
        conn.commit()
    finally:
        release_conn(conn)


def get_proof_files(daily_log_id: int) -> list[dict]:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT file_id, file_type FROM proof_files WHERE daily_log_id = %s ORDER BY id",
                (daily_log_id,)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        release_conn(conn)