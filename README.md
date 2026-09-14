# Crypto Persian Quiz Bot

Telegram exam bot for the Persian crypto technical-analysis course.

## Environment variables

- `BOT_TOKEN` = Telegram bot token (keep secret)
- `ADMIN_USER_ID` = numeric Telegram user ID of the teacher/admin
- `DB_PATH` = optional SQLite path; default: `quiz_results.db`

## Commands

- `/start` — start a new attempt
- `/myid` — show your numeric Telegram ID
- `/results` — admin-only list of recent results
- `/stats` — admin-only aggregate statistics

Students can take the exam multiple times. Every attempt is stored as a separate record.

## Run locally

```bash
pip install -r requirements.txt
export BOT_TOKEN="YOUR_NEW_TOKEN"
export ADMIN_USER_ID="YOUR_TELEGRAM_ID"
python bot.py
```

Do not commit the Telegram token to GitHub.
