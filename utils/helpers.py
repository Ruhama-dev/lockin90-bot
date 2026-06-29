"""
utils/helpers.py — Shared utility functions
"""

import os
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()

CHALLENGE_START = date.fromisoformat(
    os.getenv("CHALLENGE_START_DATE", "2026-06-29")
)


def get_current_day_number() -> int:
    """Returns the current challenge day (1-based). Returns 0 before start."""
    today = date.today()
    delta = (today - CHALLENGE_START).days + 1
    return max(0, min(delta, 90))


def get_today() -> date:
    return date.today()


def validate_member_id(member_id: str) -> bool:
    """Validate the LU90-XXX format."""
    parts = member_id.upper().split("-")
    if len(parts) != 2:
        return False
    if parts[0] != "LU90":
        return False
    if not parts[1].isdigit() or len(parts[1]) < 1:
        return False
    return True


def get_streak_milestone(streak: int) -> str | None:
    milestones = {
        7: "🏅 One Week Warrior! 7 days strong!",
        30: "🏆 30-Day Champion! You're unstoppable!",
        90: "👑 LEGEND! You completed the 90-day challenge!",
    }
    return milestones.get(streak)


def build_leaderboard_text(rows: list[dict], day_number: int) -> str:
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = [
        f"🏆 *LockIn 90 — Leaderboard*",
        f"📅 Day {day_number}/90\n",
    ]
    for i, row in enumerate(rows, start=1):
        medal = medals.get(i, f"{i}.")
        status = "✅" if row["logged_today"] else "💤"
        streak = row["current_streak"]
        day_word = "day" if streak == 1 else "days"
        name = row["full_name"] or row["member_id"]
        lines.append(f"{medal} {name} ({row['member_id']}) — {streak} {day_word} {status}")

    lines.append("\n✅ = logged today  💤 = not yet")
    return "\n".join(lines)


def build_log_post_text(member: dict, log: dict, day_number: int) -> str:
    name = member["full_name"] or member["member_id"]
    streak = member["current_streak"]
    text = (
        f"📋 *Daily Log — {name}*\n"
        f"🆔 {member['member_id']}  |  📅 Day {day_number}/90  |  🔥 Streak: {streak}\n\n"
        f"*📌 Plan:*\n{log['plan_text']}\n\n"
    )
    if log.get("progress_text"):
        text += f"*✅ Progress:*\n{log['progress_text']}"
    return text