# 🌟 LockIn90 Telegram Bot

A Telegram accountability bot for the **Summer LockIn 90** community — 90 days of spiritual growth, consistent habits, new skills, and family time.

---

## 📁 Project Structure

```
lockin90_bot/
├── main.py                  # Entry point
├── requirements.txt
├── render.yaml              # Render deployment config
├── .env                     # Local secrets (never commit!)
├── .gitignore
│
├── database/
│   ├── __init__.py
│   ├── db.py                # Connection pool + schema init
│   └── queries.py           # All SQL query functions
│
├── handlers/
│   ├── __init__.py
│   ├── start.py             # /start + member registration
│   ├── log.py               # /log — daily plan submission
│   ├── progress.py          # /progress — EOD progress + proof
│   └── stats.py             # /streak + /leaderboard
│
└── utils/
    ├── __init__.py
    ├── helpers.py           # Day calc, formatting, milestones
    └── scheduler.py         # APScheduler jobs (reminders, leaderboard)
```

---

## 🚀 Local Setup

### 1. Clone and install dependencies
```bash
git clone <your-repo-url>
cd lockin90_bot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your `.env` file
```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql://user:password@host:5432/lockin90
GROUP_CHAT_ID=-1001234567890
DAILY_LOGS_TOPIC_ID=123
GENERAL_TOPIC_ID=456
CHALLENGE_START_DATE=2026-06-29
ADMIN_TELEGRAM_ID=your_telegram_id
```

### 3. Set up a local PostgreSQL database
```bash
createdb lockin90
```
The bot will create all tables automatically on first run.

### 4. Run the bot
```bash
python main.py
```

---

## 🔧 How to Get Group & Topic IDs

### Get your Group Chat ID:
1. Add `@userinfobot` to your group
2. It will reply with the group's chat ID (negative number like `-1001234567890`)

### Get Topic IDs (for forum groups):
1. Enable Topics in your group: Group Settings → Topics
2. Create topics: `📋 Daily Logs` and `General`
3. Send a message in each topic
4. Forward that message to `@userinfobot` — it shows the `message_thread_id`

---

## ☁️ Deploy to Render

### Option A — Using `render.yaml` (recommended)
1. Push your code to GitHub (make sure `.env` is in `.gitignore`)
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your GitHub repo — Render auto-detects `render.yaml`
4. Set environment variables in the Render dashboard:
   - `BOT_TOKEN`
   - `GROUP_CHAT_ID`
   - `DAILY_LOGS_TOPIC_ID`
   - `GENERAL_TOPIC_ID`
   - `ADMIN_TELEGRAM_ID`
5. `DATABASE_URL` is automatically injected from the Render PostgreSQL database

### Option B — Manual setup
1. Create a **PostgreSQL** database on Render (free tier works)
2. Create a **Background Worker** service (not Web Service)
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python main.py`
5. Add all environment variables from your `.env`

> ⚠️ Use **Background Worker**, not Web Service — this bot uses polling, not webhooks.

---

## 📋 Bot Commands

| Command | Description |
|---|---|
| `/start` | Register with your Member ID |
| `/log` | Submit your daily plan |
| `/progress` | Submit end-of-day progress + proof |
| `/streak` | View your personal stats and streak |
| `/leaderboard` | See all members ranked by streak |
| `/cancel` | Cancel any active conversation |

---

## ⏰ Scheduled Jobs

| Time (EAT UTC+3) | Action |
|---|---|
| 6:00 AM | Post morning leaderboard to group + reset missed streaks |
| 8:00 PM | DM reminder to members who haven't logged their plan |
| 10:00 PM | DM reminder to members who haven't submitted progress |

> To change the timezone, edit `TIMEZONE` in `utils/scheduler.py`.

---

## 🔐 Admin Notes

- Member IDs must be assigned manually (e.g., `LU90-001`, `LU90-002`)
- Share the bot link and their Member ID with each member
- Only one log per day is accepted per member
- Logs are accepted from 6:00 AM to 5:59 AM the next day

---

## 💙 Community Pillars

1. 🙏 Spiritual Growth
2. 📚 Consistent Habits
3. 💡 Learning New Skills
4. 👨‍👩‍👧 Family Time

*Show up every day. Small steps compound. 90 days from now, you'll be glad you started.* 🔥