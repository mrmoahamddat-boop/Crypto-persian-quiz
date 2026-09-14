import os
import sqlite3
import logging
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))

DB_PATH = os.environ.get("DB_PATH", "quiz_results.db")

QUESTIONS = [
    {
        "q": "در تحلیل تکنیکال، برای مشخص‌کردن جهت اصلی حرکت بازار، طبق چارچوب کتاب بهتر است ابتدا کدام مورد بررسی شود؟",
        "options": ["فقط حجم معاملات", "روند اصلی در تایم‌فریم بزرگ‌تر", "فقط کندل آخر", "فقط تایم‌فریم یک‌دقیقه‌ای"],
        "answer": 1,
    },
    {
        "q": "طبق توضیح کتاب، ۱۶ کندل ماهانه معادل کدام بازه زمانی است؟",
        "options": ["۲ سال", "۸ ماه", "۱ سال و ۳ ماه", "۱ سال و ۶ ماه"],
        "answer": 2,
    },
    {
        "q": "برای رسم یک ترندلاین معتبر در چارچوب کتاب، باید از چه چیزی استفاده کرد؟",
        "options": ["سه کندل تصادفی", "فقط قیمت بسته‌شدن", "دو پیوت ماژور", "یک پیوت مینور"],
        "answer": 2,
    },
    {
        "q": "کدام وضعیت در کتاب به‌عنوان شکست معتبر ترندلاین توصیف شده است؟",
        "options": [
            "صرفاً نزدیک‌شدن قیمت به خط",
            "عبور قیمت و برگشت فوری به همان سمت بدون تشکیل کندل بعدی",
            "هر سایه‌ای که خط را لمس کند",
            "یک کندل قوی خط را بشکند و کندل بعدی بدون لمس خط شکسته‌شده تشکیل شود",
        ],
        "answer": 3,
    },
    {
        "q": "در چارچوب کتاب، «پولبک» پس از شکست ترندلاین به چه معناست؟",
        "options": [
            "حرکت بدون اصلاح قیمت",
            "بازگشت قیمت به خط شکسته‌شده و سپس ادامه حرکت",
            "افزایش حجم بدون تغییر قیمت",
            "تغییر قطعی روند در همان لحظه شکست",
        ],
        "answer": 1,
    },
    {
        "q": "کدام گزینه تفاوت SNR استاتیک و داینامیک را درست بیان می‌کند؟",
        "options": [
            "هر دو فقط افقی هستند",
            "استاتیک مورب است و داینامیک افقی است",
            "استاتیک افقی است و داینامیک مورب است",
            "هر دو فقط با کندل ماهانه رسم می‌شوند",
        ],
        "answer": 2,
    },
    {
        "q": "طبق معیار مطرح‌شده در کتاب، یک پیوت ماژور باید تقریباً چه مقدار اصلاح داشته باشد؟",
        "options": ["دقیقاً ۱۰٪", "حداقل ۵۰٪", "حداقل حدود ۱٫۷۹٪", "حداقل ۰٫۱٪"],
        "answer": 2,
    },
    {
        "q": "در معاملات Futures، پوزیشن LONG زمانی از حرکت قیمت سود می‌گیرد که:",
        "options": ["قیمت کاهش پیدا کند", "فقط حجم کاهش یابد", "قیمت افزایش پیدا کند", "قیمت حتماً ثابت بماند"],
        "answer": 2,
    },
    {
        "q": "مزیت اصلی استفاده از حالت Log در تحلیل نمودار، طبق توضیح کتاب، چیست؟",
        "options": [
            "حذف نیاز به ترندلاین",
            "توجه به تغییرات درصدی قیمت",
            "ثابت‌کردن قیمت در همه تایم‌فریم‌ها",
            "حذف کامل نوسانات بازار",
        ],
        "answer": 1,
    },
    {
        "q": "کدام ویژگی برای کندل Marubozu در کتاب مطرح شده است؟",
        "options": [
            "فقط سایه بالایی بسیار بلند",
            "بدنه بزرگ با سایه بسیار کم یا بدون سایه",
            "بدنه بسیار کوچک با دو سایه بلند",
            "قیمت باز و بسته‌شدن کاملاً متفاوت نیستند و بدنه ندارد",
        ],
        "answer": 1,
    },
]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            username TEXT,
            full_name TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            answers TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def save_attempt(user, full_name, answers):
    score = sum(
        1 for i, selected in enumerate(answers)
        if selected == QUESTIONS[i]["answer"]
    )
    now = datetime.now(timezone.utc).isoformat()
    conn = db()
    conn.execute(
        """INSERT INTO attempts
        (telegram_user_id, username, full_name, started_at, finished_at, score, total, answers)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user.id,
            user.username or "",
            full_name,
            now,
            now,
            score,
            len(QUESTIONS),
            ",".join(map(str, answers)),
        ),
    )
    conn.commit()
    conn.close()
    return score


def user_state(context):
    return context.user_data.setdefault(
        "exam",
        {"full_name": None, "index": 0, "answers": []}
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("exam", None)
    await update.message.reply_text(
        "🎓 آزمون امپراتوری سایه‌ها\n\n"
        "برای شروع، لطفاً نام و نام خانوادگی خود را به‌صورت کامل تایپ کنید.\n\n"
        "مثال: علی رضایی"
    )
    context.user_data["waiting_name"] = True


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_name"):
        return

    full_name = update.message.text.strip()
    if len(full_name) < 3:
        await update.message.reply_text("لطفاً نام و نام خانوادگی را کامل وارد کنید.")
        return

    context.user_data["waiting_name"] = False
    context.user_data["exam"] = {
        "full_name": full_name,
        "index": 0,
        "answers": [],
    }
    await update.message.reply_text(
        f"سلام {full_name} 🌹\n\nآزمون شامل {len(QUESTIONS)} سؤال چهارگزینه‌ای است.\n"
        "پس از انتخاب پاسخ، به سؤال بعدی می‌روید.\n\nموفق باشید."
    )
    await send_question(update.effective_chat.id, context)


async def send_question(chat_id, context):
    exam = user_state(context)
    i = exam["index"]
    item = QUESTIONS[i]

    keyboard = [
        [InlineKeyboardButton(f"{chr(65+j)}) {option}", callback_data=f"ans:{j}")]
        for j, option in enumerate(item["options"])
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"❓ سؤال {i+1} از {len(QUESTIONS)}\n\n{item['q']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    exam = user_state(context)
    if exam["index"] >= len(QUESTIONS):
        await query.edit_message_reply_markup(reply_markup=None)
        return

    try:
        selected = int(query.data.split(":")[1])
    except (ValueError, IndexError):
        return

    i = exam["index"]
    correct = QUESTIONS[i]["answer"]

    exam["answers"].append(selected)
    exam["index"] += 1

    # Lock the answered question by removing its buttons.
    await query.edit_message_reply_markup(reply_markup=None)

    if exam["index"] < len(QUESTIONS):
        await send_question(query.message.chat_id, context)
        return

    score = save_attempt(
        update.effective_user,
        exam["full_name"],
        exam["answers"],
    )
    total = len(QUESTIONS)
    percent = round(score * 100 / total)

    if score >= 9:
        msg = "🏆 عالی! تسلط بسیار خوبی دارید."
    elif score >= 7:
        msg = "👏 خوب بود! با کمی مرور بهتر هم می‌شوید."
    elif score >= 5:
        msg = "📚 قابل قبول است؛ مرور مطالب کتاب پیشنهاد می‌شود."
    else:
        msg = "🔄 پیشنهاد می‌کنم مطالب کتاب را دوباره مرور کنید و آزمون را تکرار کنید."

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            "✅ آزمون به پایان رسید.\n\n"
            f"👤 نام: {exam['full_name']}\n"
            f"✅ صحیح: {score}\n"
            f"❌ غلط: {total - score}\n"
            f"📊 نمره: {score}/{total}\n"
            f"📈 درصد: {percent}%\n\n"
            f"{msg}\n\n"
            "برای شرکت دوباره، /start را بزنید."
        ),
    )
    context.user_data.pop("exam", None)


def admin_only(update: Update):
    return ADMIN_USER_ID != 0 and update.effective_user.id == ADMIN_USER_ID


async def results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update):
        await update.message.reply_text("⛔ این دستور فقط برای مدیر آزمون فعال است.")
        return

    conn = db()
    rows = conn.execute(
        """SELECT full_name, username, finished_at, score, total
           FROM attempts ORDER BY id DESC LIMIT 50"""
    ).fetchall()
    count = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
    avg = conn.execute("SELECT AVG(score) FROM attempts").fetchone()[0] or 0
    conn.close()

    if not rows:
        await update.message.reply_text("هنوز هیچ آزمونی ثبت نشده است.")
        return

    lines = [
        "📊 نتایج آزمون",
        "",
        f"تعداد کل شرکت‌ها: {count}",
        f"میانگین نمره: {avg:.2f}/{len(QUESTIONS)}",
        "",
    ]

    for n, row in enumerate(rows, 1):
        name, username, finished_at, score, total = row
        try:
            dt = datetime.fromisoformat(finished_at).astimezone()
            when = dt.strftime("%Y/%m/%d %H:%M")
        except Exception:
            when = finished_at
        percent = round(score * 100 / total)
        lines.append(f"{n}. {name} — {score}/{total} ({percent}%) — {when}")

    text = "\n".join(lines)
    # Telegram messages have a size limit; split if necessary.
    for start in range(0, len(text), 3800):
        await update.message.reply_text(text[start:start+3800])


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update):
        await update.message.reply_text("⛔ این دستور فقط برای مدیر آزمون فعال است.")
        return

    conn = db()
    count, avg, best, worst = conn.execute(
        "SELECT COUNT(*), AVG(score), MAX(score), MIN(score) FROM attempts"
    ).fetchone()
    conn.close()

    if not count:
        await update.message.reply_text("هنوز آماری ثبت نشده است.")
        return

    await update.message.reply_text(
        "📈 آمار کلی\n\n"
        f"تعداد آزمون‌ها: {count}\n"
        f"میانگین: {avg:.2f}/{len(QUESTIONS)}\n"
        f"بالاترین نمره: {best}/{len(QUESTIONS)}\n"
        f"پایین‌ترین نمره: {worst}/{len(QUESTIONS)}"
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"شناسه عددی تلگرام شما:\n{update.effective_user.id}\n\n"
        "این عدد را برای ADMIN_USER_ID استفاده کنید؛ توکن بات را هرگز ارسال نکنید."
    )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")

    db()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("results", results))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CallbackQueryHandler(answer, pattern=r"^ans:\d+$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot is running on Render webhook...")
    port = int(os.environ.get("PORT", "10000"))
    external_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")

    if external_url:
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="telegram-webhook",
            webhook_url=f"{external_url}/telegram-webhook",
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
    else:
        # Local fallback: polling mode.
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
