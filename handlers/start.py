"""
handlers/start.py — /start command and member ID registration flow
"""

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from database.queries import get_member_by_telegram_id, register_member, get_member_by_member_id
from utils.helpers import validate_member_id, get_current_day_number

WAITING_FOR_MEMBER_ID = 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    member = get_member_by_telegram_id(telegram_id)

    if member:
        day = get_current_day_number()
        await update.message.reply_text(
            f"👋 Welcome back, *{member['full_name']}*!\n\n"
            f"🆔 Your ID: `{member['member_id']}`\n"
            f"📅 We're on Day *{day}/90*\n"
            f"🔥 Current streak: *{member['current_streak']} days*\n\n"
            f"Use /log to submit today's plan or /streak to check your stats.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🌟 *Welcome to Summer LockIn 90!*\n\n"
        "This bot will help you log your daily progress and stay accountable "
        "throughout the 90-day challenge.\n\n"
        "To get started, please enter your *Member ID* (given to you by the admin).\n"
        "It looks like this: `LU90-001`",
        parse_mode="Markdown"
    )
    return WAITING_FOR_MEMBER_ID


async def receive_member_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    user = update.effective_user

    if not validate_member_id(raw):
        await update.message.reply_text(
            "❌ That doesn't look like a valid Member ID.\n"
            "It should be in the format `LU90-001`.\n"
            "Please try again or contact the admin.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_MEMBER_ID

    member_id = raw.upper()

    # Check if this member_id is already taken by someone else
    existing = get_member_by_member_id(member_id)
    if existing and existing["telegram_id"] != user.id:
        await update.message.reply_text(
            "❌ That Member ID is already registered by someone else.\n"
            "Please contact the admin if you think this is a mistake."
        )
        return WAITING_FOR_MEMBER_ID

    full_name = user.full_name or user.username or "Member"
    registered = register_member(member_id, user.id, user.username, full_name)

    if registered:
        day = get_current_day_number()
        await update.message.reply_text(
            f"✅ *You're registered!*\n\n"
            f"🆔 Member ID: `{member_id}`\n"
            f"👤 Name: {full_name}\n"
            f"📅 Challenge Day: *{day}/90*\n\n"
            f"*Your daily commitment:*\n"
            f"1️⃣ Use /log to share your plan for the day\n"
            f"2️⃣ Use /progress to submit what you accomplished + proof\n"
            f"3️⃣ Use /streak to track your streak\n\n"
            f"The challenge starts now. Show up every day! 🔥",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"✅ You're already registered as `{member_id}`!\n"
            f"Use /log to submit today's plan.",
            parse_mode="Markdown"
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Registration cancelled. Send /start to try again.")
    return ConversationHandler.END


def get_start_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_MEMBER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_member_id)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )