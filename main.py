"""
main.py — LockIn90 Telegram Bot entry point
"""

import os
import logging
from dotenv import load_dotenv

from telegram.ext import ApplicationBuilder

from database.db import init_db
from handlers.start import get_start_handler
from handlers.log import get_log_handler
from handlers.progress import get_progress_handler
from handlers.stats import get_stats_handlers
from utils.scheduler import setup_scheduler

load_dotenv()

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

import threading
from flask import Flask
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "LockIn90 Bot is running! 🔥"

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN is not set in .env!")

    # Initialize database tables
    init_db()

    # Build the application
    app = ApplicationBuilder().token(token).build()

    # Register handlers
    app.add_handler(get_start_handler())
    app.add_handler(get_log_handler())
    app.add_handler(get_progress_handler())
    for handler in get_stats_handlers():
        app.add_handler(handler)

    # Set up scheduled jobs
    scheduler = setup_scheduler(app.bot)
    scheduler.start()
    logger.info("✅ Scheduler started.")

    logger.info("🚀 LockIn90 Bot is running...")
    threading.Thread(target=run_flask, daemon=True).start()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()