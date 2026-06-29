"""
handlers/stats.py — /streak, /leaderboard, and /resettoday commands
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database.queries import (
    get_member_by_telegram_id,
    get_leaderboard_with_today_status,
    delete_log_for_today,
    update_streak,
)
from utils.helpers import get_current_day_number, get_today, build_leaderboard_text


async def streak_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    member = get_member_by_telegram_id(telegram_id)

    if not member:
        await update.message.reply_text(
            "⚠️ You're not registered yet. Send /start to get started."
        )
        return

    day = get_current_day_number()
    streak = member["current_streak"]
    longest = member["longest_streak"]
    total = member["total_days"]

    milestones = [(7, "🏅 7-Day"), (30, "🏆 30-Day"), (90, "👑 Legend")]
    next_milestone = None
    for target, label in milestones:
        if streak < target:
            next_milestone = (target, label, target - streak)
            break

    text = (
        f"📊 *Your Stats — {member['full_name']}*\n"
        f"🆔 {member['member_id']}\n\n"
        f"📅 Challenge Progress: Day *{day}/90*\n"
        f"🔥 Current Streak: *{streak} day{'s' if streak != 1 else ''}*\n"
        f"🏅 Longest Streak: *{longest} day{'s' if longest != 1 else ''}*\n"
        f"✅ Total Days Logged: *{total}*\n"
    )

    if next_milestone:
        target, label, days_left = next_milestone
        text += f"\n🎯 Next milestone: {label} — *{days_left} day{'s' if days_left != 1 else ''} to go!*"
    else:
        text += "\n👑 You've hit the ultimate milestone — LEGEND!"

    await update.message.reply_text(text, parse_mode="Markdown")


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = get_today()
    day = get_current_day_number()
    rows = get_leaderboard_with_today_status(today)

    if not rows:
        await update.message.reply_text(
            "📋 No members registered yet. Tell everyone to /start the bot!"
        )
        return

    lb_text = build_leaderboard_text(rows, day)
    await update.message.reply_text(lb_text, parse_mode="Markdown")


async def reset_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = get_member_by_telegram_id(update.effective_user.id)
    if member:
        delete_log_for_today(member["member_id"], get_today())
        update_streak(
            member["member_id"],
            0,
            member["longest_streak"],
            max(0, member["total_days"] - 1)
        )
        await update.message.reply_text("🔄 Today's log and streak reset. You can /log again!")
    else:
        await update.message.reply_text("⚠️ You're not registered yet. Send /start.")


def get_stats_handlers():
    return [
        CommandHandler("streak", streak_command),
        CommandHandler("leaderboard", leaderboard_command),
        CommandHandler("resettoday", reset_today),
    ]