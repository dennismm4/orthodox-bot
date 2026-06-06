import logging
import os
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
ADMIN_CHAT_IDS = [
    chat_id.strip()
    for chat_id in os.environ.get("ADMIN_CHAT_IDS", ADMIN_CHAT_ID or "").split(",")
    if chat_id.strip()
]
ADMIN_GROUP_ID = os.environ.get("ADMIN_GROUP_ID")

from cards import FLASHCARDS

DAYS = {
    "1": {"label": "Day 1 Flashcards", "folder": "images"},
    "2": {"label": "Day 2 Flashcards", "folder": "images2"},
    "3": {"label": "Day 3 Flashcards", "folder": "images3"},
}

DAY_OPEN = {day: True for day in DAYS}
QUIZ_STATS = {
    day: {"started": 0, "completed": 0, "score_total": 0}
    for day in DAYS
}
KNOWN_USERS = set()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Keyboards ────────────────────────────────────────────────────────────────

def main_menu_kb():
    rows = []
    for day, day_config in DAYS.items():
        status = "" if DAY_OPEN[day] else " (Closed)"
        rows.append([
            InlineKeyboardButton(
                f"{day_config['label']}{status}",
                callback_data=f"start_day_{day}",
            )
        ])
    rows.append(
        [InlineKeyboardButton("ℹ️ About", callback_data="about")],
    )
    rows.append([InlineKeyboardButton("Exit", callback_data="exit_home")])
    return InlineKeyboardMarkup(rows)

def bootcamp_start_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Start", callback_data="bootcamp_start")],
        [InlineKeyboardButton("Exit", callback_data="exit_home")],
    ])

def bootcamp_intro_text() -> str:
    return (
        "*Orthodoxia Flashcards*\n\n"
        "These flashcards are here to help you review what you’ve learned throughout the "
        "Introduction to Orthodoxy Bootcamp. Your progress will be recorded to help us "
        "track participation and course completion."
    )

def yes_kb(day: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes", callback_data=f"confirm_day_{day}")],
        [InlineKeyboardButton("Exit", callback_data="exit_home")],
    ])

def day_ready_kb(day: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes", callback_data=f"confirm_day_{day}")],
        [InlineKeyboardButton("Go Back", callback_data="main_menu")],
        [InlineKeyboardButton("Exit", callback_data="exit_home")],
    ])

def reveal_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁 Reveal Answer", callback_data="reveal_answer")],
        [InlineKeyboardButton("Exit", callback_data="exit_home")],
    ])

def self_grade_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("I got it right!", callback_data="grade_right"),
            InlineKeyboardButton("Review again", callback_data="grade_wrong"),
        ],
        [InlineKeyboardButton("Exit", callback_data="exit_home")],
    ])

def results_kb(has_wrong: bool):
    rows = []
    if has_wrong:
        rows.append([InlineKeyboardButton("Review again", callback_data="retry_wrong")])
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    rows.append([InlineKeyboardButton("Exit", callback_data="exit_home")])
    return InlineKeyboardMarkup(rows)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def progress_bar(current: int, total: int) -> str:
    filled = int((current / total) * 10)
    return "🟦" * filled + "⬜" * (10 - filled)

def get_image_path(name: str, folder: str = "images") -> str:
    """Return the full path to an image file (jpg or png)."""
    base = os.path.join(os.path.dirname(__file__), folder)
    for ext in ("jpg", "jpeg", "png", "webp"):
        path = os.path.join(base, f"{name}.{ext}")
        if os.path.exists(path):
            return path
    return None

def build_day_deck(day: str) -> list:
    day_config = DAYS[day]
    return [
        {
            **card,
            "day": day,
            "day_label": day_config["label"],
            "image_folder": day_config["folder"],
        }
        for card in FLASHCARDS
    ]

def is_admin(user_id: int) -> bool:
    return str(user_id) in ADMIN_CHAT_IDS

def admin_menu_kb():
    rows = [
        [
            InlineKeyboardButton("Stats", callback_data="admin_stats"),
            InlineKeyboardButton("Health", callback_data="admin_health"),
        ],
        [
            InlineKeyboardButton("Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("Reset Stats", callback_data="admin_reset_stats"),
        ],
        [
            InlineKeyboardButton("Post Group Intro", callback_data="admin_post_group_intro"),
        ],
    ]
    for day, day_config in DAYS.items():
        action = "Close" if DAY_OPEN[day] else "Open"
        rows.append([
            InlineKeyboardButton(
                f"{action} {day_config['label']}",
                callback_data=f"admin_toggle_{day}",
            )
        ])
    rows.append([InlineKeyboardButton("Refresh", callback_data="admin_menu")])
    rows.append([InlineKeyboardButton("Exit", callback_data="exit_home")])
    return InlineKeyboardMarkup(rows)

def admin_status_text() -> str:
    lines = ["☦️ Admin Menu", ""]
    for day, day_config in DAYS.items():
        status = "Open" if DAY_OPEN[day] else "Closed"
        lines.append(f"{day_config['label']}: {status}")
    return "\n".join(lines)

def stats_text() -> str:
    lines = ["Stats since last Railway restart", ""]
    for day, day_config in DAYS.items():
        stats = QUIZ_STATS[day]
        completed = stats["completed"]
        average = int(stats["score_total"] / completed) if completed else 0
        lines.extend([
            day_config["label"],
            f"Started: {stats['started']}",
            f"Completed: {completed}",
            f"Average score: {average}/{len(FLASHCARDS)}",
            "",
        ])
    return "\n".join(lines).strip()

def health_text() -> str:
    lines = [
        "Bot health",
        "",
        "Status: Running",
        f"Admins configured: {len(ADMIN_CHAT_IDS)}",
        f"Admin group configured: {'Yes' if ADMIN_GROUP_ID else 'No'}",
        f"Known users this restart: {len(KNOWN_USERS)}",
        f"Cards configured per day: {len(FLASHCARDS)}",
        "",
    ]

    for day, day_config in DAYS.items():
        folder = day_config["folder"]
        base = os.path.join(os.path.dirname(__file__), folder)
        status = "Open" if DAY_OPEN[day] else "Closed"
        folder_status = "Found" if os.path.isdir(base) else "Missing"
        lines.extend([
            day_config["label"],
            f"Status: {status}",
            f"Folder: {folder} ({folder_status})",
            "",
        ])

    return "\n".join(lines).strip()

async def imagecheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Report which images are available in the deployed app."""
    sections = ["Image check"]

    for day_config in DAYS.values():
        folder = day_config["folder"]
        base = os.path.join(os.path.dirname(__file__), folder)

        if not os.path.isdir(base):
            sections.append(
                f"\n{day_config['label']}\n"
                f"Folder not found: {folder}"
            )
            continue

        files = sorted(
            name for name in os.listdir(base)
            if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        )

        missing = []
        for card in FLASHCARDS:
            card_id = card["id"]
            if not get_image_path(f"q_{card_id}", folder):
                missing.append(f"q_{card_id}")
            if not get_image_path(f"a_{card_id}", folder):
                missing.append(f"a_{card_id}")

        section = (
            f"\n{day_config['label']}\n"
            f"Folder: {folder}\n"
            f"Cards configured: {len(FLASHCARDS)}\n"
            f"Image files found: {len(files)}\n"
            f"Missing expected images: {len(missing)}"
        )

        if missing:
            section += "\nMissing: " + ", ".join(missing[:20])
            if len(missing) > 20:
                section += f"\n...and {len(missing) - 20} more"

        sections.append(section)

    text = "\n".join(sections)

    await update.message.reply_text(text)

# ─── Handlers ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    KNOWN_USERS.add(user.id)
    await update.message.reply_text(
        bootcamp_intro_text(),
        parse_mode="Markdown",
        reply_markup=bootcamp_start_kb(),
    )

async def show_bootcamp_ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.edit_message_text(
        f"Welcome, {user.first_name}\n\n"
        "Ready to review what you've learned during the Introduction to Orthodoxy Bootcamp?\n\n"
        "How it works:\n"
        "- Each flashcard will display a question\n"
        "- Think of the answer before revealing it\n"
        "- Tap “Reveal answer” to check yourself\n"
        "- Mark whether you got it right\n"
        "- If you would like to see it again later, choose “Review again.”\n\n"
        "Take your time, learn at your own pace, and don't worry about getting everything right "
        "the first time.\n\n"
        "Ready to begin?",
        reply_markup=yes_kb("1"),
    )

async def show_day_ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    day = query.data.replace("start_day_", "")

    await query.edit_message_text(
        f"Welcome back, {user.first_name}!\n\n"
        "Ready for another round?",
        reply_markup=day_ready_kb(day),
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("You are not authorized to use the admin menu.")
        return

    await update.message.reply_text(
        admin_status_text(),
        reply_markup=admin_menu_kb(),
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    KNOWN_USERS.add(query.from_user.id)
    await query.answer()
    data = query.data

    dispatch = {
        "bootcamp_start": show_bootcamp_ready,
        "start_day_1":   show_day_ready,
        "start_day_2":   show_day_ready,
        "start_day_3":   show_day_ready,
        "confirm_day_1": begin_quiz,
        "confirm_day_2": begin_quiz,
        "confirm_day_3": begin_quiz,
        "reveal_answer": reveal_answer,
        "grade_right":   grade_right,
        "grade_wrong":   grade_wrong,
        "retry_wrong":   start_retry,
        "main_menu":     go_main_menu,
        "exit_home":     exit_home,
        "about":         show_about,
        "back_to_menu":  go_main_menu,
        "admin_menu":    show_admin_menu,
        "admin_stats":   show_admin_stats,
        "admin_health":  show_admin_health,
        "admin_broadcast": start_broadcast,
        "admin_reset_stats": reset_stats,
        "admin_post_group_intro": post_group_intro,
        "admin_toggle_1": toggle_day,
        "admin_toggle_2": toggle_day,
        "admin_toggle_3": toggle_day,
    }

    if data in dispatch:
        await dispatch[data](update, context)

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.message.reply_text("You are not authorized to use the admin menu.")
        return

    await query.edit_message_text(
        admin_status_text(),
        reply_markup=admin_menu_kb(),
    )

async def exit_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.edit_message_text(
            bootcamp_intro_text(),
            parse_mode="Markdown",
            reply_markup=bootcamp_start_kb(),
        )
    except Exception:
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text(
            bootcamp_intro_text(),
            parse_mode="Markdown",
            reply_markup=bootcamp_start_kb(),
        )

async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.message.reply_text("You are not authorized to use the admin menu.")
        return

    await query.edit_message_text(
        stats_text(),
        reply_markup=admin_menu_kb(),
    )

async def show_admin_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.message.reply_text("You are not authorized to use the admin menu.")
        return

    await query.edit_message_text(
        health_text(),
        reply_markup=admin_menu_kb(),
    )

async def reset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.message.reply_text("You are not authorized to use the admin menu.")
        return

    for stats in QUIZ_STATS.values():
        stats["started"] = 0
        stats["completed"] = 0
        stats["score_total"] = 0

    await query.edit_message_text(
        "Stats have been reset.",
        reply_markup=admin_menu_kb(),
    )

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.message.reply_text("You are not authorized to use the admin menu.")
        return

    context.user_data["awaiting_broadcast"] = True
    await query.edit_message_text(
        "Send the broadcast message as your next Telegram message.\n\n"
        "Send /cancel to stop.",
        reply_markup=admin_menu_kb(),
    )

async def post_group_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.message.reply_text("You are not authorized to use the admin menu.")
        return

    if not ADMIN_GROUP_ID:
        await query.edit_message_text(
            "ADMIN_GROUP_ID is not configured on Railway.\n\n"
            "Add your Telegram group chat ID to Railway, then redeploy.",
            reply_markup=admin_menu_kb(),
        )
        return

    try:
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=bootcamp_intro_text(),
            parse_mode="Markdown",
            reply_markup=bootcamp_start_kb(),
        )
        await query.edit_message_text(
            "The intro message was posted to the group.",
            reply_markup=admin_menu_kb(),
        )
    except Exception as e:
        logger.error(f"Group intro post failed: {e}")
        await query.edit_message_text(
            "Could not post the intro message to the group.\n\n"
            "Check that ADMIN_GROUP_ID is correct and that the bot is a member of the group.",
            reply_markup=admin_menu_kb(),
        )

async def toggle_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.message.reply_text("You are not authorized to use the admin menu.")
        return

    day = query.data.replace("admin_toggle_", "")
    DAY_OPEN[day] = not DAY_OPEN[day]
    await query.edit_message_text(
        admin_status_text(),
        reply_markup=admin_menu_kb(),
    )

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:
        return

    if update.message and update.message.text == "/cancel":
        context.user_data["awaiting_broadcast"] = False
        await update.message.reply_text("Broadcast cancelled.", reply_markup=admin_menu_kb())
        return

    if not is_admin(user.id) or not context.user_data.get("awaiting_broadcast"):
        return

    context.user_data["awaiting_broadcast"] = False
    message = update.message.text
    sent = 0
    failed = 0

    recipients = set(KNOWN_USERS)
    for chat_id in recipients:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
            )
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast failed for {chat_id}: {e}")

    await update.message.reply_text(
        f"Broadcast complete.\nSent: {sent}\nFailed: {failed}",
        reply_markup=admin_menu_kb(),
    )

# ─── Quiz Flow ────────────────────────────────────────────────────────────────

async def begin_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    day = query.data.replace("confirm_day_", "")
    day_config = DAYS[day]

    if not DAY_OPEN[day]:
        await query.edit_message_text(
            f"{day_config['label']} is currently closed.",
            reply_markup=main_menu_kb(),
        )
        return

    day_deck = build_day_deck(day)
    deck = random.sample(day_deck, len(day_deck))  # shuffle all cards
    QUIZ_STATS[day]["started"] += 1
    context.user_data.update({
        "deck":          deck,
        "index":         0,
        "score":         0,
        "wrong":         [],
        "log":           [],
        "mode":          "quiz",
        "day":           day,
        "day_label":     day_config["label"],
        "total":         len(deck),
        "answer_msg_id": None,
    })
    await query.edit_message_text(
        f"Starting {day_config['label']}...",
        parse_mode="Markdown"
    )
    await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the question image for the current card."""
    query   = update.callback_query
    ud      = context.user_data
    deck    = ud["deck"]
    idx     = ud["index"]
    total   = ud["total"]
    card    = deck[idx]

    caption = (
        f"*{card.get('day_label', 'Flashcards')}*\n"
        f"*Question {idx + 1} of {total}*\n"
        f"{progress_bar(idx, total)}\n\n"
        f"_{card.get('hint', 'Study this image, then reveal the answer below.')}_"
    )

    img_path = get_image_path(f"q_{card['id']}", card.get("image_folder", "images"))

    if img_path:
        with open(img_path, "rb") as f:
            msg = await query.message.reply_photo(
                photo=f,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=reveal_kb(),
            )
    else:
        # Fallback if image file is missing
        msg = await query.message.reply_text(
            f"⚠️ _Image q\\_{card['id']} not found in {card.get('image_folder', 'images')}_\n\n{caption}",
            parse_mode="Markdown",
            reply_markup=reveal_kb(),
        )

    ud["question_msg_id"] = msg.message_id

async def reveal_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the answer image below the question."""
    query = update.callback_query
    ud    = context.user_data
    deck  = ud["deck"]
    idx   = ud["index"]
    card  = deck[idx]

    # Remove the reveal button from the question message
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    caption = "Did you get it right?"

    img_path = get_image_path(f"a_{card['id']}", card.get("image_folder", "images"))

    if img_path:
        with open(img_path, "rb") as f:
            msg = await query.message.reply_photo(
                photo=f,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=self_grade_kb(),
            )
    else:
        msg = await query.message.reply_text(
            f"⚠️ _Image a\\_{card['id']} not found in {card.get('image_folder', 'images')}_\n\n{caption}",
            parse_mode="Markdown",
            reply_markup=self_grade_kb(),
        )

    ud["answer_msg_id"] = msg.message_id

async def grade_right(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _record_grade(update, context, correct=True)

async def grade_wrong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _record_grade(update, context, correct=False)

async def _record_grade(update: Update, context: ContextTypes.DEFAULT_TYPE, correct: bool):
    query = update.callback_query
    ud    = context.user_data
    deck  = ud["deck"]
    idx   = ud["index"]
    card  = deck[idx]

    # Remove grading buttons
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    if correct:
        ud["score"] += 1
    else:
        ud["wrong"].append(card)

    ud["log"].append({
        "id":      card["id"],
        "label":   card.get("label", f"Card {card['id']}"),
        "correct": correct,
    })

    ud["index"] += 1

    if ud["index"] >= ud["total"]:
        await show_results(update, context)
    else:
        await send_question(update, context)

# ─── Results ──────────────────────────────────────────────────────────────────

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    user   = query.from_user
    ud     = context.user_data
    score  = ud["score"]
    total  = ud["total"]
    wrong  = ud["wrong"]
    pct    = int(score / total * 100) if total else 0
    day    = ud.get("day")

    if day in QUIZ_STATS:
        QUIZ_STATS[day]["completed"] += 1
        QUIZ_STATS[day]["score_total"] += score

    text = (
        f"{ud.get('day_label', 'Flashcards').replace('Flashcards', 'Review Complete')}\n\n"
        "📖 Flashcards Completed\n"
        f"👤 {user.first_name} {user.last_name or ''}\n"
        f"📊 Score: {score} / {total}\n\n"
        "Glory to God!\n\n"
        "Thank you for taking the time to review today's lesson. Keep going, and we'll see you in the "
        "next session."
    )

    if day == "3":
        text += (
            "\n\nCongratulations! Glory to God!\n\n"
            "You have completed all seven flashcard reviews for the Introduction to Orthodoxy Bootcamp.\n"
            "We hope it was helpful.\n\n"
            "The next step is the final examination.\n\n"
            "We wish you the very best on your exam. May God bless your studies."
        )

    await query.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=results_kb(bool(wrong)),
    )

    await _send_admin_report(context, user, ud)

async def _send_admin_report(context, user, ud):
    if not ADMIN_CHAT_IDS:
        return
    score = ud["score"]
    total = ud["total"]
    pct   = int(score / total * 100) if total else 0
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"📋 *New Quiz Result*",
        f"🕐 {ts}",
        f"",
        f"👤 {user.first_name} {user.last_name or ''}",
        f"🆔 @{user.username or 'N/A'}  |  ID: `{user.id}`",
        f"",
        f"📖 {ud.get('day_label', 'Flashcards')}",
        f"",
        f"📊 Score: *{score}/{total}* ({pct}%)",
        f"",
        f"━━━━━━━━━━━━━━",
        f"*Answer log:*",
    ]
    for entry in ud.get("log", []):
        icon = "✅" if entry["correct"] else "❌"
        lines.append(f"{icon} Card {entry['id']}: {entry['label']}")

    for chat_id in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="\n".join(lines),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Admin report failed for {chat_id}: {e}")

# ─── Retry ────────────────────────────────────────────────────────────────────

async def start_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ud    = context.user_data
    wrong = ud.get("wrong", [])

    if not wrong:
        await query.edit_message_text(
            "No cards to retry! 🎉",
            parse_mode="Markdown",
            reply_markup=bootcamp_start_kb(),
        )
        return

    ud.update({
        "deck":  wrong.copy(),
        "index": 0,
        "score": 0,
        "wrong": [],
        "log":   [],
        "mode":  "retry",
        "total": len(wrong),
    })

    await query.edit_message_text(
        f"🔄 *Retry Mode*\n\n"
        f"Redoing *{len(wrong)}* card(s) you marked for review.\nGood luck! ☦️",
        parse_mode="Markdown",
    )
    await send_question(update, context)

# ─── Misc ─────────────────────────────────────────────────────────────────────

async def go_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = query.from_user
    await query.edit_message_text(
        f"☦️ *Welcome back, {user.first_name}!*\n\nReady for another round?",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )

async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text(
        "☦️ *Orthodox Flashcard Quiz*\n\n"
        "An image-based flashcard bot for deepening your knowledge of:\n\n"
        "• 📖 Bible verses\n"
        "• ⛪ Orthodox theology & dogma\n"
        "• 🕯️ Saints and Church history\n"
        "• 🙏 Liturgical traditions\n\n"
        "Results are recorded and sent to the parish administrator.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")],
            [InlineKeyboardButton("Exit", callback_data="exit_home")],
        ]),
    )

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("Set BOT_TOKEN in config.py or as an environment variable.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("imagecheck", imagecheck))
    app.add_handler(MessageHandler(filters.TEXT, handle_admin_text))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("☦️ Orthodox Flashcard Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
