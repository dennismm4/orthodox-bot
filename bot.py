import logging
import os
import random
from datetime import datetime
from telegram import (
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
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

DAY_QUIZ_STATS = {
    "1": {"started": 0, "completed": 0, "score_total": 0}
}

DAY1_QUIZ = [
    {
        "question": "Which term describes a form of theism where a person worships one supreme deity while simultaneously acknowledging or allowing the existence of other minor gods?",
        "options": {
            "A": "Monotheism",
            "B": "Polytheism",
            "C": "Henotheism",
            "D": "Ditheism",
        },
        "answer": "C",
        "explanation": "Henotheism: one main god with many minor gods - Slide 6",
    },
    {
        "question": "If an individual believes that a supreme being created the entire universe but completely abstains from interacting with or intervening in human events, what worldview are they holding?",
        "options": {
            "A": "Pantheism",
            "B": "Deism",
            "C": "Autotheism",
            "D": "Eutheism",
        },
        "answer": "B",
        "explanation": "Deism: God created the universe but does not interfere - Slide 7",
    },
    {
        "question": "How does the course text define \"Doctrine\" (Haimanot) in contrast to the personal, inward act of faith (Emnet)?",
        "options": {
            "A": "It is the subjective feeling of spiritual conviction felt without text.",
            "B": "It is the objective content of faith, comprising the set of teachings held and taught by a religious entity.",
            "C": "It is the adaptive collection of administrative rules that govern church assets.",
            "D": "It is a blended system of dynamic rituals borrowed from local secular cultures.",
        },
        "answer": "B",
        "explanation": "Doctrine: a set of teachings held/taught by a religious entity; content of faith - Slide 4 & 18",
    },
    {
        "question": "What is the primary operational distinction between Dogma and Canon within Orthodox ecclesiology?",
        "options": {
            "A": "Dogma refers to unchangeable, divinely revealed truths of the faith, while Canon encompasses rules or laws that can adapt over time.",
            "B": "Dogma changes dynamically with cultural trends, while Canon remains completely frozen and immutable.",
            "C": "Dogma applies strictly to the actions of the laity, while Canon only governs the activities of the ordained clergy.",
            "D": "Dogma is determined by secular governments, while Canon is decided by individual private interpretation.",
        },
        "answer": "A",
        "explanation": "Dogma: unchangeable core beliefs; Canon: rules/laws that can adapt - Slide 22",
    },
    {
        "question": "What is the historical meaning of the word \"Orthodox\", derived from its original Greek linguistic roots?",
        "options": {
            "A": "Ancient Tradition or Cultural Antiquity",
            "B": "Eastern Geography or Regional Consensus",
            "C": "United Body or Unified Natures",
            "D": "True Faith or Correct Path",
        },
        "answer": "D",
        "explanation": "Orthos: Correct/True/Direct; Doxa: Notion/Belief/Path - Slide 23",
    },
    {
        "question": "Based on the Cosmological Argument, why must the primary cause of the universe be understood specifically as a \"Personal\" reality?",
        "options": {
            "A": "Because human beings can only build an emotional relationship with an entity that has human-like features.",
            "B": "Because it had to make a conscious choice to create, and impersonal mechanical forces do not possess the capacity to choose.",
            "C": "Because the universe's physics are mathematically tuned for organic survival.",
            "D": "Because moral laws require an active personal entity to enforce them through rewards.",
        },
        "answer": "B",
        "explanation": "An act of creation out of nothing requires volition and a conscious choice to initiate change, which blind mechanical or impersonal forces lack - Slide 9",
    },
    {
        "question": "Which classical argument for the existence of God relies on the fact that if the strength of gravity or other physical constants were different by a fraction as small as one part in 10^60, life and galaxies could never have formed?",
        "options": {
            "A": "Cosmological Argument",
            "B": "Fine Tuning Argument",
            "C": "Moral Argument",
            "D": "Argument from Desire",
        },
        "answer": "B",
        "explanation": "Fine Tuning Argument / Teleological fact: the universe is highly calibrated and structurally planned for organic life - Slide 10-11",
    },
    {
        "question": "What is the logical starting premise of the classic Moral Argument presented in the bootcamp session?",
        "options": {
            "A": "If God does not exist, objective moral values and duties do not exist.",
            "B": "All human cultures eventually agree on the same ethical choices over time.",
            "C": "Objective moral principles are physical realities that can be measured scientifically.",
            "D": "Human society is the ultimate anchor and shifting source of absolute, unchangeable truth.",
        },
        "answer": "A",
        "explanation": "Premise 1: Without a transcendent standard to ground them, absolute, binding moral obligations do not exist - Slide 12",
    },
    {
        "question": "According to C.S. Lewis in Mere Christianity, if a person discovers an internal longing that no earthly experience can satisfy, what is the most logical conclusion?",
        "options": {
            "A": "The individual's desires are psychologically abnormal and require secular correction.",
            "B": "The material universe contains a hidden physical object that can eventually satisfy them.",
            "C": "The individual was fundamentally created for a different world beyond this natural one.",
            "D": "The individual has simply failed to master proper administrative self-discipline.",
        },
        "answer": "C",
        "explanation": "Argument from Desire: Universal human longings for ultimate satisfaction point to an eternal reality beyond the physical world - Slide 15",
    },
    {
        "question": "The presentation outlines four critical elements involved in why human beings worship God. What are they?",
        "options": {
            "A": "Humility, Fasting, Prayer, and Kindness",
            "B": "Value, Relationship, Gratitude, and Discipline",
            "C": "Dogma, Canon, Tradition, and Doctrine",
            "D": "Pluralism, Inclusivism, Exclusivism, and Nihilism",
        },
        "answer": "B",
        "explanation": "Worship components: Recognizing God's worth, engaging in deep relationship, showing thankfulness, and maintaining spiritual structure - Slide 17",
    },
    {
        "question": "The Ge'ez term \"Tewahedo\" signifies unity or oneness. What does this theological term assert regarding the nature of Jesus Christ?",
        "options": {
            "A": "The divine and human natures of Christ are united in one nature and one person without separation, confusion, alteration, or mixing.",
            "B": "Christ exists permanently in two separate, distinct, and unintegrated natures after their union.",
            "C": "The divine nature of Christ completely absorbed, dissolved, and erased His human nature.",
            "D": "Jesus was a regular human prophet who was adopted into divine status later in life.",
        },
        "answer": "A",
        "explanation": "Tewahedo/Miaphysitism definition: complete unity of person and nature where both humanity and divinity remain fully real and uncompromised - Slide 24",
    },
    {
        "question": "Which specific family of sister churches shares this identical Miaphysite Christological position alongside the Ethiopian Orthodox Tewahedo Church?",
        "options": {
            "A": "The Eastern Orthodox Churches, such as the Greek and Russian Orthodox churches.",
            "B": "The Roman Catholic and Byzantine Rite communions.",
            "C": "The Oriental Orthodox Churches, including the Coptic, Syriac, Armenian, Indian, and Eritrean churches.",
            "D": "Global Protestant and Evangelical denominations arising from the European Reformation.",
        },
        "answer": "C",
        "explanation": "The Oriental Orthodox communion family shares full dogmatic unity regarding Christ's unified nature - Slide 25 & 47",
    },
    {
        "question": "Which Apostle is historically recognized as the founder who brought Christianity to Egypt and established the Coptic Orthodox Church?",
        "options": {
            "A": "St. Thomas",
            "B": "St. Mark",
            "C": "St. Thaddeus",
            "D": "St. Philip",
        },
        "answer": "B",
        "explanation": "Coptic Church: Founded by St. Mark the Evangelist - Slide 47",
    },
    {
        "question": "According to the historical background given, who ordained Frumentius (Abba Selama), thereby cementing the formal hierarchical link for the Ethiopian Church?",
        "options": {
            "A": "St. Peter in Antioch",
            "B": "St. Athanasius in Alexandria",
            "C": "St. Mark the Evangelist",
            "D": "St. Thaddeus in Armenia",
        },
        "answer": "B",
        "explanation": "EOTC: St. Frumentius traveled to Alexandria and was consecrated as the first bishop of Ethiopia by St. Athanasius - Slide 47",
    },
    {
        "question": "Which ancient church in the Oriental Orthodox family traces its baseline apostolic roots back to the missionary journeys of St. Thomas the Apostle in Kerala?",
        "options": {
            "A": "Syriac Orthodox Church",
            "B": "Armenian Apostolic Church",
            "C": "Indian Orthodox Church",
            "D": "Coptic Orthodox Church",
        },
        "answer": "C",
        "explanation": "Indian Orthodox Church: Traces its apostolic heritage directly back to St. Thomas - Slide 47",
    },
    {
        "question": "According to the presentation, what are the four traditional marks that identify the true Church in the Creed?",
        "options": {
            "A": "Traditional, Local, Monastic, and Canonical",
            "B": "One, Holy, Catholic, and Apostolic",
            "C": "Theistic, Dogmatic, Scriptural, and Liturgical",
            "D": "Exclusivist, Inclusivist, Syncretic, and Monotheistic",
        },
        "answer": "B",
        "explanation": "Marks of the Church: Affirming the absolute unity, spiritual sanctity, universal fullness, and historic continuity of the body - Slide 26",
    },
    {
        "question": "If someone asserts that \"one's own religion is the true path, but other religions contain elements of truth and can act as vehicles for divine grace,\" what ideological pathway are they describing?",
        "options": {
            "A": "Pluralism",
            "B": "Exclusivism",
            "C": "Syncretism",
            "D": "Inclusivism",
        },
        "answer": "D",
        "explanation": "Inclusivism leaves a doorway open for partial elements of grace outside the unique path - Slide 31",
    },
    {
        "question": "Based on the text's scriptural logic, why can two directly contradictory religious propositions (such as \"God is a Trinity\" and \"God is not a Trinity\") not both express ultimate reality?",
        "options": {
            "A": "Because modern culture requires absolute conformity in all global public institutions.",
            "B": "Because truth by its very nature excludes error; two contradictory propositions cannot both be true simultaneously.",
            "C": "Because religious descriptions must shift dynamically to keep pace with scientific advancements.",
            "D": "Because subjective individual feelings are more reliable than external objective realities.",
        },
        "answer": "B",
        "explanation": "Truth by its nature excludes error; if two propositions clash directly, the law of non-contradiction dictates at least one must be false - Slide 33",
    },
    {
        "question": "How does the bootcamp text define the mark of the Church being \"Holy\" within a changing world?",
        "options": {
            "A": "The Church is strictly separated from falsehood, worldliness, and error; embracing heresy causes a church to cease to be holy.",
            "B": "The Church modifies its moral teachings over time to keep up with contemporary social values.",
            "C": "The Church relies on secular states to enforce spiritual discipline among its congregations.",
            "D": "The Church's structural holiness is completely undone the moment a single member falls into sin.",
        },
        "answer": "A",
        "explanation": "Holiness requires total consecration and absolute separation from heresy, corruption, and worldliness - Slide 36",
    },
    {
        "question": "According to the New Testament model detailed in Acts 6, what primary duty were the first Deacons (Diakonos) appointed to handle?",
        "options": {
            "A": "To independently formulate new dogmatic statements for universal church councils.",
            "B": "To govern whole regional dioceses with ultimate judicial authority over local priests.",
            "C": "To serve, manage daily distributions, and assist with physical/charitable needs so the Apostles could focus on prayer and preaching.",
            "D": "To replace the sacramental Old Covenant rituals with completely secular philosophical lectures.",
        },
        "answer": "C",
        "explanation": "Acts 6 model: Deacons were ordained as ministers of service to manage physical administration and care for the vulnerable - Slide 46",
    },
]

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
    day1_status = "" if DAY_OPEN["1"] else " (Closed)"
    rows.append([
        InlineKeyboardButton(
            f"Day 1 Quiz{day1_status}",
            callback_data="start_day_1_quiz",
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

def quiz_options_kb(options: dict):
    rows = [
        [InlineKeyboardButton(f"{letter}) {text}", callback_data=f"quiz_answer_{letter}")]
        for letter, text in options.items()
    ]
    rows.append([InlineKeyboardButton("Exit", callback_data="exit_home")])
    return InlineKeyboardMarkup(rows)

def quiz_next_kb(is_last: bool):
    label = "Show Results" if is_last else "Next Question"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="quiz_next")],
        [InlineKeyboardButton("Exit", callback_data="exit_home")],
    ])

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
    lines = ["Admin Menu", ""]
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

    lines.append("Quizzes")
    day1_quiz_stats = DAY_QUIZ_STATS["1"]
    completed = day1_quiz_stats["completed"]
    average = int(day1_quiz_stats["score_total"] / completed) if completed else 0
    lines.extend([
        "Day 1 Quiz",
        f"Started: {day1_quiz_stats['started']}",
        f"Completed: {completed}",
        f"Average score: {average}/{len(DAY1_QUIZ)}",
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
        f"Day 1 quiz questions: {len(DAY1_QUIZ)}",
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

async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
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

    if data.startswith("quiz_answer_"):
        await answer_day1_quiz(update, context)
        return

    dispatch = {
        "bootcamp_start": show_bootcamp_ready,
        "start_day_1":   show_day_ready,
        "start_day_2":   show_day_ready,
        "start_day_3":   show_day_ready,
        "start_day_1_quiz": begin_day1_quiz,
        "confirm_day_1": begin_quiz,
        "confirm_day_2": begin_quiz,
        "confirm_day_3": begin_quiz,
        "quiz_next":     next_day1_quiz_question,
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
    for stats in DAY_QUIZ_STATS.values():
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

# ─── Day 1 Quiz Flow ──────────────────────────────────────────────────────────

async def begin_day1_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not DAY_OPEN["1"]:
        await query.edit_message_text(
            "Day 1 Quiz is currently closed.",
            reply_markup=main_menu_kb(),
        )
        return

    questions = random.sample(DAY1_QUIZ, len(DAY1_QUIZ))
    DAY_QUIZ_STATS["1"]["started"] += 1
    context.user_data.update({
        "active_flow": "day1_quiz",
        "quiz_questions": questions,
        "quiz_index": 0,
        "quiz_score": 0,
        "quiz_log": [],
        "quiz_answered": False,
    })

    await query.edit_message_text("Starting Day 1 Quiz...")
    await send_day1_quiz_question(update, context)

async def send_day1_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ud = context.user_data
    questions = ud["quiz_questions"]
    idx = ud["quiz_index"]
    question = questions[idx]

    text = (
        f"Day 1 Quiz\n"
        f"Question {idx + 1} of {len(questions)}\n\n"
        f"{question['question']}"
    )

    await query.message.reply_text(
        text,
        reply_markup=quiz_options_kb(question["options"]),
    )

async def answer_day1_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ud = context.user_data

    if ud.get("active_flow") != "day1_quiz" or ud.get("quiz_answered"):
        return

    selected = query.data.replace("quiz_answer_", "")
    questions = ud["quiz_questions"]
    idx = ud["quiz_index"]
    question = questions[idx]
    correct = selected == question["answer"]
    correct_text = question["options"][question["answer"]]

    ud["quiz_answered"] = True
    if correct:
        ud["quiz_score"] += 1

    ud["quiz_log"].append({
        "number": idx + 1,
        "question": question["question"],
        "selected": selected,
        "selected_text": question["options"].get(selected, ""),
        "answer": question["answer"],
        "answer_text": correct_text,
        "correct": correct,
    })

    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    result = "Correct!" if correct else "Not quite."
    text = (
        f"{result}\n\n"
        f"Correct answer: {question['answer']}) {correct_text}\n\n"
        f"{question['explanation']}"
    )

    await query.message.reply_text(
        text,
        reply_markup=quiz_next_kb(idx >= len(questions) - 1),
    )

async def next_day1_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ud = context.user_data

    if ud.get("active_flow") != "day1_quiz":
        return

    if not ud.get("quiz_answered"):
        await query.message.reply_text("Please choose an answer before continuing.")
        return

    ud["quiz_index"] += 1
    ud["quiz_answered"] = False

    if ud["quiz_index"] >= len(ud["quiz_questions"]):
        await show_day1_quiz_results(update, context)
    else:
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await send_day1_quiz_question(update, context)

async def show_day1_quiz_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    ud = context.user_data
    score = ud["quiz_score"]
    total = len(ud["quiz_questions"])

    DAY_QUIZ_STATS["1"]["completed"] += 1
    DAY_QUIZ_STATS["1"]["score_total"] += score

    text = (
        "Day 1 Quiz Complete\n\n"
        "📖 Quiz Completed\n"
        f"👤 {user.first_name} {user.last_name or ''}\n"
        f"📊 Score: {score} / {total}\n\n"
        "Glory to God!\n\n"
        "Thank you for taking the time to review today's lesson."
    )

    await query.message.reply_text(
        text,
        reply_markup=results_kb(False),
    )

    await _send_admin_quiz_report(context, user, ud)

async def _send_admin_quiz_report(context, user, ud):
    if not ADMIN_CHAT_IDS:
        return

    score = ud["quiz_score"]
    total = len(ud["quiz_questions"])
    pct = int(score / total * 100) if total else 0
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "📋 *New Day 1 Quiz Result*",
        f"🕐 {ts}",
        "",
        f"👤 {user.first_name} {user.last_name or ''}",
        f"🆔 @{user.username or 'N/A'}  |  ID: `{user.id}`",
        "",
        f"📊 Score: *{score}/{total}* ({pct}%)",
        "",
        "*Answer log:*",
    ]

    for entry in ud.get("quiz_log", []):
        icon = "✅" if entry["correct"] else "❌"
        lines.append(
            f"{icon} Q{entry['number']}: selected {entry['selected']}, correct {entry['answer']}"
        )

    for chat_id in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="\n".join(lines),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Admin quiz report failed for {chat_id}: {e}")

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
        f"Redoing *{len(wrong)}* card(s) you marked for review.\nGood luck!",
        parse_mode="Markdown",
    )
    await send_question(update, context)

# ─── Misc ─────────────────────────────────────────────────────────────────────

async def go_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = query.from_user
    await query.edit_message_text(
        f"*Welcome back, {user.first_name}!*\n\nReady for another round?",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )

async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text(
        "*Orthodox Flashcard Quiz*\n\n"
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

async def setup_bot_commands(app: Application):
    user_commands = [
        BotCommand("start", "Open Orthodoxia Flashcards"),
        BotCommand("exit", "Return to the home page"),
    ]
    admin_commands = [
        BotCommand("start", "Open Orthodoxia Flashcards"),
        BotCommand("exit", "Return to the home page"),
        BotCommand("admin", "Open the admin menu"),
        BotCommand("imagecheck", "Check deployed flashcard images"),
    ]

    await app.bot.set_my_commands(
        user_commands,
        scope=BotCommandScopeDefault(),
    )

    for chat_id in ADMIN_CHAT_IDS:
        try:
            await app.bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=chat_id),
            )
        except Exception as e:
            logger.error(f"Could not set admin commands for {chat_id}: {e}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("Set BOT_TOKEN in config.py or as an environment variable.")

    app = Application.builder().token(BOT_TOKEN).post_init(setup_bot_commands).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("exit", exit_command))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("imagecheck", imagecheck))
    app.add_handler(MessageHandler(filters.TEXT, handle_admin_text))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Orthodox Flashcard Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
