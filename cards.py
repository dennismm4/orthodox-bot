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
        "id": str(card_id),
        "label": f"Card {card_id}",
        "hint": "Study the question image carefully.",
    }
    for card_id in range(1, 30)
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
