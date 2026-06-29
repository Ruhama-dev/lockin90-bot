"""
handlers/log.py — /log command: submit daily plan
"""

import os
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from database.queries import (
    get_member_by_telegram_id,
    get_log_for_today,
    submit_plan,
    update_streak,
    get_leaderboard_with_today_status,
)
from utils.helpers import (
    get_current_day_number,
    get_today,
    get_streak_milestone,
    build_leaderboard_text,
    build_log_post_text,
)

WAITING_FOR_PLAN = 10

GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))
DAILY_LOGS_TOPIC_ID = int(os.getenv("DAILY_LOGS_TOPIC_ID", "0"))
GENERAL_TOPIC_ID = int(os.getenv("GENERAL_TOPIC_ID", "0"))


async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    member = get_member_by_telegram_id(telegram_id)

    if not member:
        await update.message.reply_text(
            "⚠️ You're not registered yet. Send /start to get started."
        )
        return ConversationHandler.END

    today = get_today()
    existing = get_log_for_today(member["member_id"], today)

    if existing:
        await update.message.reply_text(
            f"✅ You've already submitted your plan for today (Day {get_current_day_number()}/90)!\n\n"
            f"If you haven't submitted your progress yet, use /progress to do so."
        )
        return ConversationHandler.END

    day = get_current_day_number()
    await update.message.reply_text(
        f"📋 *Daily Log — Day {day}/90*\n\n"
        f"Share your plan for today! List the tasks you're committing to.\n\n"
        f"*Format your message like this:*\n"
        f"```\n"
        f"- Read Quran after Fajr\n"
        f"- Study Python for 2 hours\n"
        f"- Journal before bed\n"
        f"- 30 min walk with family\n"
        f"```\n\n"
        f"Just send your tasks and I'll handle the rest. 💪",
        parse_mode="Markdown"
    )
    return WAITING_FOR_PLAN


async def receive_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    member = get_member_by_telegram_id(telegram_id)
    today = get_today()
    day = get_current_day_number()

    plan_text = update.message.text.strip()
    if len(plan_text) < 10:
        await update.message.reply_text(
            "⚠️ Your plan seems too short. Please add at least a few tasks and try again."
        )
        return WAITING_FOR_PLAN

    success = submit_plan(
        member_id=member["member_id"],
        telegram_id=telegram_id,
        day_number=day,
        log_date=today,
        plan_text=plan_text,
    )

    if not success:
        await update.message.reply_text(
            "⚠️ You've already logged today. Use /progress to submit your progress!"
        )
        return ConversationHandler.END

    # Update streak
    new_streak = member["current_streak"] + 1
    longest = max(new_streak, member["longest_streak"])
    total = member["total_days"] + 1
    update_streak(member["member_id"], new_streak, longest, total)

    # Refresh member data
    member["current_streak"] = new_streak
    member["longest_streak"] = longest
    member["total_days"] = total

    # Build fake log dict for display
    log_dict = {"plan_text": plan_text, "progress_text": None}

    # Confirm to user
    milestone = get_streak_milestone(new_streak)
    reply = (
        f"✅ *Plan logged for Day {day}/90!*\n\n"
        f"🔥 Streak: *{new_streak} day{'s' if new_streak != 1 else ''}*\n\n"
        f"*Your plan:*\n{plan_text}\n\n"
        f"When you're done, use /progress to submit your results + proof!"
    )
    if milestone:
        reply += f"\n\n🎉 *{milestone}*"

    await update.message.reply_text(reply, parse_mode="Markdown")

    # Post to group Daily Logs topic
    if GROUP_CHAT_ID and DAILY_LOGS_TOPIC_ID:
        post_text = build_log_post_text(member, log_dict, day)
        try:
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=DAILY_LOGS_TOPIC_ID,
                text=post_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"⚠️ Could not post to group logs topic: {e}")

    # Post updated leaderboard to General topic
    if GROUP_CHAT_ID and GENERAL_TOPIC_ID:
        rows = get_leaderboard_with_today_status(today)
        lb_text = build_leaderboard_text(rows, day)
        try:
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=GENERAL_TOPIC_ID,
                text=lb_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"⚠️ Could not post leaderboard: {e}")

    return ConversationHandler.END


async def cancel_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Log cancelled. Send /log when you're ready.")
    return ConversationHandler.END


def get_log_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("log", log_command)],
        states={
            WAITING_FOR_PLAN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_plan)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_log),
            CommandHandler("streak", cancel_log),
            CommandHandler("leaderboard", cancel_log),
            CommandHandler("progress", cancel_log),
        ],
        allow_reentry=True,
    )