from fasthtml.common import database
from pathlib import Path
from dataclasses import dataclass

# Ensure data directory exists
Path('data').mkdir(exist_ok=True)

# Initialize database
db = database('data/saved_words.db')
saved_words = db.t.saved_words
review_stats = db.t.review_stats

# Create tables if they don't exist
if saved_words not in db.t:
    saved_words.create(
        word=str,
        simplified=str,
        traditional=str,
        pinyin=str,
        definitions=str,
        timestamp=float,
        pk='word'
    )

if review_stats not in db.t:
    review_stats.create(
        word=str,          # The word being reviewed
        correct_count=int, # Number of times correctly guessed
        incorrect_count=int, # Number of times incorrectly guessed
        last_reviewed=float, # Timestamp of last review
        next_review=float,  # Timestamp when word should be reviewed next
        ease_factor=float,  # SRS ease factor (starts at 2.5, adjusted based on performance)
        interval=float,     # Current interval in days
        pk='word'
    )

@dataclass
class SavedWord:
    word: str
    simplified: str
    traditional: str
    pinyin: str
    definitions: str
    timestamp: float

@dataclass
class ReviewStats:
    word: str
    correct_count: int
    incorrect_count: int
    last_reviewed: float
    next_review: float
    ease_factor: float
    interval: float 