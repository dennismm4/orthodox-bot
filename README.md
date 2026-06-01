# ✝️ Orthodox Flashcard Bot (Image Edition)

A Telegram bot that presents image-based flashcards for Orthodox Christianity study.

---

## How it works

1. User taps **Start Quiz**
2. A **question image** (`q_1.jpg`) is shown with a "Reveal Answer" button
3. User taps to reveal the **answer image** (`a_1.jpg`)
4. User self-grades: ✅ Got it right / 🔄 Review later
5. Missed cards are collected and offered as a **retry round** at the end
6. Admin receives a full **results report** after every completed quiz

---

## File structure

```
orthodox_bot/
├── bot.py            ← Main bot logic
├── cards.py          ← Card definitions (id + label)
├── config.py         ← Token & admin chat ID
├── requirements.txt  ← Dependencies
├── Procfile          ← Railway deployment
└── images/           ← Your image files go here
    ├── q_1.jpg       ← Question image for card 1
    ├── a_1.jpg       ← Answer image for card 1
    ├── q_2.jpg
    ├── a_2.jpg
    └── ...
```

---

## Adding your flashcard images

1. Create an `images/` folder next to `bot.py`
2. Name files as `q_<id>` and `a_<id>` — for example:
   - `q_1.jpg` and `a_1.jpg` for card 1
   - `q_2.png` and `a_2.png` for card 2
3. Supported formats: `.jpg`, `.jpeg`, `.png`, `.webp`
4. Update `cards.py` if you add new card IDs

---

## Setup

### 1. Get your bot token
Message **@BotFather** on Telegram → `/newbot` → copy the token.

### 2. Get your admin chat ID
Message **@userinfobot** on Telegram → copy the `Id` number.

### 3. Edit config.py
```python
BOT_TOKEN    = "123456789:ABCDEfgh..."
ADMIN_CHAT_ID = "123456789"
```

### 4. Install & run locally
```bash
pip install -r requirements.txt
python bot.py
```

---

## Deploy to Railway (free, 24/7)

1. Push all files **except `config.py`** to a private GitHub repo
   - Include the `images/` folder with all your card images
2. Sign up at **railway.app** → Login with GitHub
3. New Project → Deploy from GitHub repo → select your repo
4. Go to **Variables** tab and add:
   - `BOT_TOKEN` = your token
   - `ADMIN_CHAT_ID` = your chat ID
5. Redeploy — done!

---

*Glory to God for all things! ✝️*
