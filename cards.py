# cards.py — Flashcard definitions
#
# Each card needs:
#   id    : matches the image filenames  (q_1.jpg / a_1.jpg)
#   label : short description shown in results and admin report
#   hint  : (optional) small italic text shown under the progress bar
#
# Add or remove cards freely. The bot shuffles them automatically.

FLASHCARDS = [
    {
        "id": "1",
        "label": "Card 1",
        "hint": "Study the question image carefully.",
    },
    {
        "id": "2",
        "label": "Card 2",
        "hint": "Study the question image carefully.",
    },
    {
        "id": "3",
        "label": "Card 3",
        "hint": "Study the question image carefully.",
    },
    {
        "id": "4",
        "label": "Card 4",
        "hint": "Study the question image carefully.",
    },
    {
        "id": "5",
        "label": "Card 5",
        "hint": "Study the question image carefully.",
    },
    {
        "id": "6",
        "label": "Card 6",
        "hint": "Study the question image carefully.",
    },
    {
        "id": "7",
        "label": "Card 7",
        "hint": "Study the question image carefully.",
    },
    {
        "id": "8",
        "label": "Card 8",
        "hint": "Study the question image carefully.",
    },
    {
        "id": "9",
        "label": "Card 9",
        "hint": "Study the question image carefully.",
    },
    {
        "id": "10",
        "label": "Card 10",
        "hint": "Study the question image carefully.",
    },
]

# ─── How to add more cards ────────────────────────────────────────────────────
#
# 1. Add your image files to the images/ folder:
#       images/q_11.jpg   ← question image
#       images/a_11.jpg   ← answer image
#
# 2. Add an entry here:
#    {
#        "id": "11",
#        "label": "The Lord's Prayer",          ← shown in results
#        "hint": "Identify the verse.",          ← shown during quiz
#    },
#
# Supported image formats: jpg, jpeg, png, webp
# ─────────────────────────────────────────────────────────────────────────────
