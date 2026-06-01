import logging
import os
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN, ADMIN_CHAT_ID
from cards import FLASHCARDS

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Keyboards ────────────────────────────────────────────────────────────────

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Start Quiz", callback_data="start_quiz")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about")],
    ])

def reveal_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁 Reveal Answer", callback_data="reveal_answer")]
    ])

def self_grade_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Got it right!", callback_data="grade_right"),
            InlineKeyboardButton("🔄 Review later", callback_data="grade_wrong"),
        ]
    ])

def results_kb(has_wrong: bool):
    rows = []
    if has_wrong:
        rows.append([InlineKeyboardButton("🔄 Retry wrong answers", callback_data="retry_wrong")])
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def progress_bar(current: int, total: int) -> str:
    filled = int((current / total) * 10)
    return "🟦" * filled + "⬜" * (10 - filled)

def get_image_path(name: str) -> str:
    """Return the full path to an image file (jpg or png)."""
    base = os.path.join(os.path.dirname(__file__), "images")
    for ext in ("jpg", "jpeg", "png", "webp"):
        path = os.path.join(base, f"{name}.{ext}")
        if os.path.exists(path):
            return path
    return None

# ─── Handlers ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"✝️ *Welcome, {user.first_name}!*\n\n"
        "This quiz tests your knowledge of *Orthodox Christianity* through image flashcards.\n\n"
        "• 📸 Each card shows a question image\n"
        "• 👁 Tap to reveal the answer\n"
        "• ✅ Mark whether you got it right\n"
        "• 🔄 Missed cards come back at the end\n\n"
        "Ready to begin?",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    dispatch = {
        "start_quiz":    begin_quiz,
        "reveal_answer": reveal_answer,
        "grade_right":   grade_right,
        "grade_wrong":   grade_wrong,
        "retry_wrong":   start_retry,
        "main_menu":     go_main_menu,
        "about":         show_about,
        "back_to_menu":  go_main_menu,
    }

    if data in dispatch:
        await dispatch[data](update, context)

# ─── Quiz Flow ────────────────────────────────────────────────────────────────

async def begin_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    deck = random.sample(FLASHCARDS, len(FLASHCARDS))  # shuffle all cards
    context.user_data.update({
        "deck":          deck,
        "index":         0,
        "score":         0,
        "wrong":         [],
        "log":           [],
        "mode":          "quiz",
        "total":         len(deck),
        "answer_msg_id": None,
    })
    await query.edit_message_text("✝️ Starting quiz…", parse_mode="Markdown")
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
        f"*Question {idx + 1} of {total}*\n"
        f"{progress_bar(idx, total)}\n\n"
        f"_{card.get('hint', 'Study this image, then reveal the answer below.')}_"
    )

    img_path = get_image_path(f"q_{card['id']}")

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
            f"⚠️ _Image q\\_{card['id']} not found_\n\n{caption}",
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

    caption = (
        f"✝️ *Answer for card {idx + 1}*\n\n"
        "Did you get it right?"
    )

    img_path = get_image_path(f"a_{card['id']}")

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
            f"⚠️ _Image a\\_{card['id']} not found_\n\n{caption}",
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

    if pct >= 90:
        grade = "🏆 Excellent! Glory to God!"
    elif pct >= 70:
        grade = "👏 Well done! Keep studying!"
    elif pct >= 50:
        grade = "📚 Good effort! Review and try again."
    else:
        grade = "🙏 Keep praying and studying!"

    text = (
        f"✝️ *Quiz Complete!*\n\n"
        f"👤 *{user.first_name} {user.last_name or ''}*\n"
        f"📊 Score: *{score} / {total}* ({pct}%)\n\n"
        f"{grade}"
    )

    if wrong:
        text += f"\n\n❌ *Cards to review: {len(wrong)}*\n"
        for w in wrong:
            text += f"\n• {w.get('label', 'Card ' + str(w['id']))}"

    await query.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=results_kb(bool(wrong)),
    )

    await _send_admin_report(context, user, ud)

async def _send_admin_report(context, user, ud):
    if not ADMIN_CHAT_ID:
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
        f"📊 Score: *{score}/{total}* ({pct}%)",
        f"",
        f"━━━━━━━━━━━━━━",
        f"*Answer log:*",
    ]
    for entry in ud.get("log", []):
        icon = "✅" if entry["correct"] else "❌"
        lines.append(f"{icon} Card {entry['id']}: {entry['label']}")

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text="\n".join(lines),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Admin report failed: {e}")

# ─── Retry ────────────────────────────────────────────────────────────────────

async def start_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ud    = context.user_data
    wrong = ud.get("wrong", [])

    if not wrong:
        await query.edit_message_text("No cards to retry! 🎉", parse_mode="Markdown")
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
        f"Redoing *{len(wrong)}* card(s) you marked for review.\nGood luck! ✝️",
        parse_mode="Markdown",
    )
    await send_question(update, context)

# ─── Misc ─────────────────────────────────────────────────────────────────────

async def go_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = query.from_user
    await query.edit_message_text(
        f"✝️ *Welcome back, {user.first_name}!*\n\nReady for another round?",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )

async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text(
        "✝️ *Orthodox Flashcard Quiz*\n\n"
        "An image-based flashcard bot for deepening your knowledge of:\n\n"
        "• 📖 Bible verses\n"
        "• ⛪ Orthodox theology & dogma\n"
        "• 🕯️ Saints and Church history\n"
        "• 🙏 Liturgical traditions\n\n"
        "Results are recorded and sent to the parish administrator.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
        ]),
    )

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("Set BOT_TOKEN in config.py or as an environment variable.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("✝️ Orthodox Flashcard Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
