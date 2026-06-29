"""
utils/scheduler.py — APScheduler jobs for reminders, leaderboard, and streak reset
"""

import os
import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from database.queries import (
    get_members_without_log_today,
    get_members_without_progress_today,
    get_leaderboard_with_today_status,
    reset_streaks_for_missed,
)
from utils.helpers import get_current_day_number, get_today, build_leaderboard_text

logger = logging.getLogger(__name__)

TIMEZONE = pytz.timezone("Africa/Addis_Ababa")  # UTC+3, adjust if needed
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))
GENERAL_TOPIC_ID = int(os.getenv("GENERAL_TOPIC_ID", "0"))


async def send_plan_reminder(bot):
    """8:00 PM — DM members who haven't logged their plan yet."""
    today = get_today()
    members = get_members_without_log_today(today)
    day = get_current_day_number()

    for member in members:
        try:
            await bot.send_message(
                chat_id=member["telegram_id"],
                text=(
                    f"⏰ *Hey {member['full_name'].split()[0]}!*\n\n"
                    f"Day *{day}/90* is still waiting for your log! 📋\n\n"
                    f"You haven't submitted your plan yet today.\n"
                    f"Don't break your streak — use /log now! 🔥"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not DM {member['member_id']}: {e}")


async def send_progress_reminder(bot):
    """10:00 PM — DM members who have a plan but no progress yet."""
    today = get_today()
    members = get_members_without_progress_today(today)
    day = get_current_day_number()

    for member in members:
        try:
            await bot.send_message(
                chat_id=member["telegram_id"],
                text=(
                    f"📸 *Almost midnight, {member['full_name'].split()[0]}!*\n\n"
                    f"You submitted your plan for Day *{day}/90* but haven't sent "
                    f"your progress report yet.\n\n"
                    f"Use /progress before the day ends! 💪"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not DM {member['member_id']}: {e}")


async def post_morning_leaderboard(bot):
    """6:00 AM — Post leaderboard to group and reset missed streaks."""
    today = get_today()
    yesterday = today - timedelta(days=1)
    day = get_current_day_number()

    # Reset streaks for those who missed yesterday
    reset_streaks_for_missed(yesterday)

    if not GROUP_CHAT_ID or not GENERAL_TOPIC_ID:
        logger.warning("GROUP_CHAT_ID or GENERAL_TOPIC_ID not set — skipping leaderboard post.")
        return

    rows = get_leaderboard_with_today_status(today)
    lb_text = build_leaderboard_text(rows, day)

    try:
        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=GENERAL_TOPIC_ID,
            text=f"🌅 *Good morning, LockIn 90!*\n\nDay *{day}/90* begins now. Let's go!\n\n" + lb_text,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Could not post morning leaderboard: {e}")


def setup_scheduler(bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    # 6:00 AM — Morning leaderboard + streak reset
    scheduler.add_job(
        post_morning_leaderboard,
        CronTrigger(hour=6, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="morning_leaderboard",
        replace_existing=True,
    )

    # 8:00 PM — Plan reminder
    scheduler.add_job(
        send_plan_reminder,
        CronTrigger(hour=20, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="plan_reminder",
        replace_existing=True,
    )

    # 10:00 PM — Progress reminder
    scheduler.add_job(
        send_progress_reminder,
        CronTrigger(hour=22, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="progress_reminder",
        replace_existing=True,
    )

    return scheduler