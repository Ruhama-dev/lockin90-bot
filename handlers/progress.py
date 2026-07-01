"""
handlers/progress.py — /progress command: submit end-of-day progress + proof
"""

import os
import re
from telegram import Update, InputMediaPhoto, InputMediaDocument
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
    submit_progress,
    update_streak,
    get_daily_log_id,
    add_proof_file,
)
from utils.helpers import (
    get_current_day_number,
    get_today,
    get_streak_milestone,
    build_log_post_text,
)

WAITING_FOR_PROGRESS = 20
WAITING_FOR_PROOF = 21

GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))
PROGRESS_TOPIC_ID = int(os.getenv("PROGRESS_TOPIC_ID", "0"))


def escape_markdown(text: str) -> str:
    """Escape Telegram legacy Markdown special characters so user input
    can never break message formatting."""
    if not text:
        return text
    special_chars = r"_*`["
    return re.sub(f"([{re.escape(special_chars)}])", r"\\\1", text)


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    member = get_member_by_telegram_id(telegram_id)

    if not member:
        await update.message.reply_text(
            "⚠️ You're not registered yet. Send /start to get started."
        )
        return ConversationHandler.END

    today = get_today()
    log = get_log_for_today(member["member_id"], today)

    if not log:
        await update.message.reply_text(
            "⚠️ You haven't submitted your plan yet today!\n"
            "Use /log first to submit your daily plan."
        )
        return ConversationHandler.END

    if log.get("progress_text"):
        safe_progress = escape_markdown(log["progress_text"])
        await update.message.reply_text(
            "✅ You've already submitted your progress for today!\n\n"
            f"*What you did:*\n{safe_progress}",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    day = get_current_day_number()
    await update.message.reply_text(
        f"💪 *Progress Report — Day {day}/90*\n\n"
        f"*Your plan was:*\n{escape_markdown(log['plan_text'])}\n\n"
        f"Now tell me what you actually accomplished today! Be honest. ✅\n\n"
        f"*Example:*\n"
        f"```\n"
        f"- Read Quran ✅\n"
        f"- Finished Python lesson on loops ✅\n"
        f"- Journaled 2 pages ✅\n"
        f"- Had dinner with family ✅\n"
        f"```",
        parse_mode="Markdown"
    )
    return WAITING_FOR_PROGRESS


async def receive_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    progress_text = update.message.text.strip()
    if len(progress_text) < 5:
        await update.message.reply_text(
            "⚠️ That's too short. Please describe what you accomplished today."
        )
        return WAITING_FOR_PROGRESS

    context.user_data["progress_text"] = progress_text
    context.user_data["proof_items"] = []

    await update.message.reply_text(
        "📸 *Now send your proof!*\n\n"
        "You can send one or more:\n"
        "• Photos (screenshot, selfie, work done)\n"
        "• Documents or files (code, notes, etc.)\n\n"
        "When you're done, type `done`.\n"
        "Or type `skip` if you don't have proof right now.\n\n"
        "_Proof helps keep everyone accountable!_ 🔥",
        parse_mode="Markdown"
    )
    return WAITING_FOR_PROOF


async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collects one or more photos/documents. The user types `done` to finish
    or `skip` to submit with no proof at all."""

    text = update.message.text.strip().lower() if update.message.text else None

    if "proof_items" not in context.user_data:
        context.user_data["proof_items"] = []

    proof_items = context.user_data["proof_items"]

    if text == "skip" and not proof_items:
        return await _finalize_progress(update, context, proof_type="skipped")

    if text == "done":
        if not proof_items:
            await update.message.reply_text(
                "⚠️ You haven't sent any proof yet. Send a photo/document, or type `skip`."
            )
            return WAITING_FOR_PROOF
        return await _finalize_progress(update, context, proof_type="multi")

    if update.message.photo:
        proof_items.append((update.message.photo[-1].file_id, "photo"))
        await update.message.reply_text(
            "✅ Photo added. Send more proof, or type `done` to finish."
        )
        return WAITING_FOR_PROOF

    if update.message.document:
        proof_items.append((update.message.document.file_id, "document"))
        await update.message.reply_text(
            "✅ Document added. Send more proof, or type `done` to finish."
        )
        return WAITING_FOR_PROOF

    if update.message.text:
        # Plain text proof note — append to progress_text instead of proof_files
        progress_text = context.user_data.get("progress_text", "")
        context.user_data["progress_text"] = (
            progress_text + f"\n\n📝 Proof note: {update.message.text.strip()}"
        )
        await update.message.reply_text(
            "✅ Note added. Send a photo/document, or type `done` to finish."
        )
        return WAITING_FOR_PROOF

    await update.message.reply_text(
        "⚠️ Please send a photo, document, type `done` to finish, or `skip`."
    )
    return WAITING_FOR_PROOF


async def _finalize_progress(update: Update, context: ContextTypes.DEFAULT_TYPE, proof_type: str):
    telegram_id = update.effective_user.id
    member = get_member_by_telegram_id(telegram_id)
    today = get_today()
    day = get_current_day_number()
    progress_text = context.user_data.get("progress_text", "")
    proof_items = context.user_data.get("proof_items", [])

    # Use the first item as the "primary" proof stored on daily_logs (backward compat)
    primary_file_id, primary_type = (proof_items[0] if proof_items else (None, proof_type))

    submit_progress(
        member_id=member["member_id"],
        log_date=today,
        progress_text=progress_text,
        proof_file_id=primary_file_id,
        proof_type=primary_type,
    )

    # Store every file (including the primary one) in proof_files
    daily_log_id = get_daily_log_id(member["member_id"], today)
    if daily_log_id:
        for file_id, file_type in proof_items:
            add_proof_file(daily_log_id, file_id, file_type)

    # Streak is updated HERE — only after both plan AND progress are complete
    new_streak = member["current_streak"] + 1
    longest = max(new_streak, member["longest_streak"])
    total = member["total_days"] + 1
    update_streak(member["member_id"], new_streak, longest, total)

    member["current_streak"] = new_streak
    member["longest_streak"] = longest
    member["total_days"] = total

    milestone = get_streak_milestone(new_streak)
    safe_progress_text = escape_markdown(progress_text)
    reply = (
        f"🎉 *Progress submitted for Day {day}/90!*\n\n"
        f"*What you did:*\n{safe_progress_text}\n\n"
        f"🔥 Streak: *{new_streak} day{'s' if new_streak != 1 else ''}*\n\n"
        f"Keep showing up! See you tomorrow. 💪"
    )
    if milestone:
        reply += f"\n\n🎉 *{milestone}*"

    try:
        await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception as e:
        print(f"⚠️ Markdown reply failed, sending plain text instead: {e}")
        plain_reply = (
            f"🎉 Progress submitted for Day {day}/90!\n\n"
            f"What you did:\n{progress_text}\n\n"
            f"Streak: {new_streak} day{'s' if new_streak != 1 else ''}\n\n"
            f"Keep showing up! See you tomorrow. 💪"
        )
        await update.message.reply_text(plain_reply)

    # Reload log for group post
    log = get_log_for_today(member["member_id"], today)
    if log:
        log["progress_text"] = progress_text

    # Post progress + proof to Progress topic
    if GROUP_CHAT_ID and PROGRESS_TOPIC_ID and log:
        safe_log = dict(log)
        safe_log["plan_text"] = escape_markdown(log.get("plan_text", ""))
        safe_log["progress_text"] = safe_progress_text
        post_text = build_log_post_text(member, safe_log, day)

        try:
            if proof_items:
                if len(proof_items) == 1:
                    first_id, first_type = proof_items[0]
                    if first_type == "photo":
                        await context.bot.send_photo(
                            chat_id=GROUP_CHAT_ID,
                            message_thread_id=PROGRESS_TOPIC_ID,
                            photo=first_id,
                            caption=post_text[:1024],
                            parse_mode="Markdown"
                        )
                    else:
                        await context.bot.send_document(
                            chat_id=GROUP_CHAT_ID,
                            message_thread_id=PROGRESS_TOPIC_ID,
                            document=first_id,
                            caption=post_text[:1024],
                            parse_mode="Markdown"
                        )
                else:
                    media = []
                    for i, (fid, ftype) in enumerate(proof_items[:10]):
                        caption = post_text[:1024] if i == 0 else None
                        parse_mode = "Markdown" if i == 0 else None
                        if ftype == "photo":
                            media.append(InputMediaPhoto(fid, caption=caption, parse_mode=parse_mode))
                        else:
                            media.append(InputMediaDocument(fid, caption=caption, parse_mode=parse_mode))
                    await context.bot.send_media_group(
                        chat_id=GROUP_CHAT_ID,
                        message_thread_id=PROGRESS_TOPIC_ID,
                        media=media,
                    )
            else:
                await context.bot.send_message(
                    chat_id=GROUP_CHAT_ID,
                    message_thread_id=PROGRESS_TOPIC_ID,
                    text=post_text,
                    parse_mode="Markdown"
                )
        except Exception as e:
            print(f"⚠️ Could not post progress to group (Markdown), retrying plain: {e}")
            try:
                plain_post = (
                    f"Daily Log — {member['full_name'] or member['member_id']}\n"
                    f"{member['member_id']}  |  Day {day}/90  |  Streak: {member['current_streak']}\n\n"
                    f"Plan:\n{log.get('plan_text', '')}\n\n"
                    f"Progress:\n{progress_text}"
                )
                if proof_items:
                    first_id, first_type = proof_items[0]
                    if first_type == "photo":
                        await context.bot.send_photo(
                            chat_id=GROUP_CHAT_ID,
                            message_thread_id=PROGRESS_TOPIC_ID,
                            photo=first_id,
                            caption=plain_post[:1024],
                        )
                    else:
                        await context.bot.send_document(
                            chat_id=GROUP_CHAT_ID,
                            message_thread_id=PROGRESS_TOPIC_ID,
                            document=first_id,
                            caption=plain_post[:1024],
                        )
                else:
                    await context.bot.send_message(
                        chat_id=GROUP_CHAT_ID,
                        message_thread_id=PROGRESS_TOPIC_ID,
                        text=plain_post,
                    )
            except Exception as e2:
                print(f"⚠️ Could not post progress to group at all: {e2}")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Progress submission cancelled. Use /progress when ready.")
    return ConversationHandler.END


def get_progress_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("progress", progress_command)],
        states={
            WAITING_FOR_PROGRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_progress)
            ],
            WAITING_FOR_PROOF: [
                MessageHandler(
                    (filters.PHOTO | filters.Document.ALL | filters.TEXT) & ~filters.COMMAND,
                    receive_proof
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_progress),
            CommandHandler("streak", cancel_progress),
            CommandHandler("leaderboard", cancel_progress),
            CommandHandler("log", cancel_progress),
        ],
        allow_reentry=True,
    )