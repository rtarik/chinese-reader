from fasthtml.common import *
import jieba
from dictionary import ChineseDictionary
import math
from pathlib import Path
import time
from dataclasses import dataclass
from typing import List, Optional

app,rt = fast_app()

# Initialize database for saved words
Path('data').mkdir(exist_ok=True)
db = database('data/saved_words.db')
saved_words = db.t.saved_words
review_stats = db.t.review_stats

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

text_content = ""
segmented_words = []
dictionary = ChineseDictionary()
WORDS_PER_PAGE = 200
current_page = 0

@dataclass
class ReviewSession:
    words: List[dict]
    current_index: int = 0
    total_words: int = 0
    
    @property
    def current_word(self) -> Optional[dict]:
        if self.current_index < len(self.words):
            return self.words[self.current_index]
        return None
    
    @property
    def is_complete(self) -> bool:
        return self.current_index >= len(self.words)

# Add this with other globals
current_session: Optional[ReviewSession] = None

def mk_textarea():
    return Div(
        Form(
            Textarea(
                placeholder="Paste your Chinese text here...",
                name="content",
                id="content-input",
                style="width: 100%; height: 150px; margin-bottom: 10px;"
            ),
            Button("Submit", type="submit"),
            hx_post="/",
            hx_target="#result",
            id="input-form",
            #style="display: none;"

        ),
        id="input-area",
    )

def mk_word_span(word):
    return Card(
        word,
        cls="chinese-word",
        hx_post=f"/lookup/{word}",
        hx_target="#definition",
        hx_indicator="#loading"
    )

def mk_flashcard(word: dict, answer_revealed: bool = False) -> Card:
    """Create a flashcard for reviewing a word"""
    if answer_revealed:
        return Div(
            H3(word['simplified'], style="text-align: center; margin-bottom: 10px;"),
            P(f"[{word['pinyin']}]", style="text-align: center; color: var(--muted-color); margin-bottom: 15px;"),
            P(word['traditional'], style="text-align: center; color: var(--muted-color); margin-bottom: 15px;") if word['traditional'] != word['simplified'] else None,
            Div(
                *[P(d, style="margin: 5px 0;") for d in word['definitions'].split('\n')],
                style="text-align: center; margin-bottom: 20px;"
            ),
            Div(
                Button("✅", hx_post=f"/review/answer/correct/{word['word']}", hx_target="#review-area", cls="correct-btn"),
                Button("❌", hx_post=f"/review/answer/incorrect/{word['word']}", hx_target="#review-area", cls="incorrect-btn"),
                style="display: flex; justify-content: center; gap: 10px;"
            ),
            cls="flashcard",
            style="margin: 0 auto; max-width: 500px; padding: 20px; border: 1px solid var(--card-border-color); border-radius: var(--border-radius); background: var(--card-background-color);"
        )
    else:
        return Card(
            H3(word['simplified'], style="text-align: center; margin-bottom: 20px;"),
            Button(
                "Show Answer",
                hx_post=f"/review/reveal/{word['word']}",
                hx_target="closest .flashcard",
                style="display: block; margin: 0 auto;"
            ),
            cls="flashcard",
            style="margin: 0 auto; max-width: 500px;"
        )

@rt('/')
def get():
    return Container(
        Link(href="/static/styles.css", rel="stylesheet"),
        Div(
            Form(
                Textarea(
                    placeholder="Paste your Chinese text here...",
                    name="content",
                    id="content-input",
                    style="width: 100%; height: 150px; margin-bottom: 10px;"
                ),
                Button("Submit", type="submit"),
                hx_post="/",
                hx_target="#result",
                id="input-form"
            ),
            id="input-area"
        ),
        Div(
            Div(
                P(text_content) if text_content else P("No text submitted yet."),
                id="result"
            ),
            Div(
                id="pagination-controls",
                cls="pagination-controls"
            ),
            id="result-container"
        ),
        Card(
            Div(
                Span("Looking up... ", id="loading"),
                id="definition"
            ),
            cls="definition-card"
        ),
        A("View Saved Words →", href="/saved-words", id="view-saved-words")
    )

@rt('/show-input')
def post():
    return Form(
        Textarea(
            placeholder="Paste your Chinese text here...",
            name="content",
            id="content-input",
            style="width: 100%; height: 150px; margin-bottom: 10px;"
        ),
        Button("Submit", type="submit"),
        hx_post="/",
        hx_target="#result",
        id="input-form"
    )

@rt('/page/{page}')
def get_page(page: int):
    global current_page
    current_page = page
    total_pages = math.ceil(len(segmented_words) / WORDS_PER_PAGE)
    start_idx = page * WORDS_PER_PAGE
    end_idx = start_idx + WORDS_PER_PAGE
    page_words = segmented_words[start_idx:end_idx]
    
    word_spans = [mk_word_span(word) for word in page_words]
    
    return (
        Div(
            P(*word_spans, style="line-height: 2; display: flex; flex-wrap: wrap; gap: 4px; align-items: center;"),
            id="result"
        ),
        Div(
            Button("←", disabled=page==0, hx_post=f"/page/{page-1}", hx_target="#result-container") if page > 0 else None,
            Span(f"Page {page + 1} of {total_pages}", cls="page-info"),
            Button("→", disabled=page>=total_pages-1, hx_post=f"/page/{page+1}", hx_target="#result-container") if page < total_pages-1 else None,
            id="pagination-controls",
            cls="pagination-controls"
        )
    )

@rt('/')
async def post(request):
    form = await request.form()
    global text_content, segmented_words, current_page
    text_content = form.get('content', '').strip()
    
    # Return early if no text is provided
    if not text_content:
        return Div(
            Div(
                P("Please enter some text to segment.", style="color: var(--muted-color);"),
                id="result"
            ),
            Div(id="pagination-controls", cls="pagination-controls"),
            id="result-container"
        )
    
    current_page = 0
    # Segment the Chinese text into words
    segmented_words = list(jieba.cut(text_content))
    
    total_pages = math.ceil(len(segmented_words) / WORDS_PER_PAGE)
    # Get first page of words
    page_words = segmented_words[:WORDS_PER_PAGE]
    word_spans = [mk_word_span(word) for word in page_words]
    
    # Return the segmented text with clickable words and replace textarea with button
    return (
        Div(
            Div(
                P(*word_spans, style="line-height: 2; display: flex; flex-wrap: wrap; gap: 4px; align-items: center;"),
                id="result"
            ),
            Div(
                Button("←", disabled=True),
                Span(f"Page 1 of {total_pages}", cls="page-info"),
                Button("→", disabled=total_pages<=1, hx_post="/page/1", hx_target="#result-container") if total_pages > 1 else None,
                id="pagination-controls",
                cls="pagination-controls"
            ),
            id="result-container"
        ),
        Div(
            Button(
                "Add New Text",
                id="add-text-btn",
                hx_post="/show-input",
                hx_target="#input-area",
                hx_swap="innerHTML"
            ),
            id="input-area",
            hx_swap_oob="true"
        )
    )

@rt('/lookup/{word}')
def lookup(word: str):
    result = dictionary.lookup(word)
    
    if result:
        definitions = result['definitions']
        # Remove empty definitions and any leading/trailing whitespace
        definitions = [d.strip() for d in definitions if d.strip()]
        
        # Check if word is saved
        is_saved = word in saved_words
        
        return Div(
            H4(
                Span(result['simplified'], style="margin-right: 10px;"),
                Span(f"[{result['pinyin']}]", style="color: var(--muted-color); font-weight: normal;"),
                style="margin-bottom: 10px;"
            ),
            P(
                Span(result['traditional'], style="color: var(--muted-color);"),
                style="margin-bottom: 15px; font-size: 0.9em;"
            ) if result['traditional'] != result['simplified'] else None,
            Ul(
                *[Li(d) for d in definitions],
                style="margin: 0; padding-left: 20px;"
            ),
            Button(
                "★ Saved" if is_saved else "☆ Save",
                cls=f"save-button {'saved' if is_saved else ''}",
                hx_post=f"/toggle-save/{word}",
                hx_target="#definition",
                style="margin-top: 15px;"
            )
        )
    else:
        return P(f"No definition found for: {word}", style="color: var(--muted-color);")

@rt('/toggle-save/{word}')
def post(word: str, request):
    result = dictionary.lookup(word)
    if not result:
        return P(f"Error: Word not found", style="color: var(--error-color);")
    
    # If word exists, remove it; if not, add it
    if word in saved_words:
        saved_words.delete(word)
        # Also delete review stats if they exist
        if word in review_stats:
            review_stats.delete(word)
        # Get updated word count after deletion
        word_count = len(saved_words())
        
        # Check if we're removing from the saved words list
        if request.headers.get("HX-Target", "").startswith("saved-word-"):
            # If this was the last word, return empty list with header
            if word_count == 0:
                return (
                    Div(id="saved-words-list"),
                    Div(
                        Span("0 words saved", cls="word-count"),
                        Button(
                            "Start Review",
                            hx_post="/review",
                            hx_target="#review-area",
                            cls="review-button",
                            disabled=True
                        ),
                        cls="saved-words-header",
                        id="saved-words-header",
                        hx_swap_oob="true"
                    )
                )
            
            # Update the header with new count
            return (
                "",  # Empty string to remove the card
                Div(
                    Span(f"{word_count} word{'s' if word_count != 1 else ''} saved", cls="word-count"),
                    Button(
                        "Start Review",
                        hx_post="/review",
                        hx_target="#review-area",
                        cls="review-button",
                        disabled=word_count == 0
                    ),
                    cls="saved-words-header",
                    id="saved-words-header",
                    hx_swap_oob="true"
                )
            )
    else:
        saved_words.insert({
            'word': word,
            'simplified': result['simplified'],
            'traditional': result['traditional'],
            'pinyin': result['pinyin'],
            'definitions': '\n'.join(result['definitions']),
            'timestamp': time.time()
        })
        
        # If we're in the dictionary view, return the updated lookup view
        if not request.headers.get("HX-Target", "").startswith("saved-word-"):
            return lookup(word)
        
        # Get updated word count after addition
        word_count = len(saved_words())
        
        # If we're in the saved words list, return the new card and updated header
        return (
            Card(
                Div(
                    Span(result['simplified'], cls="saved-word-text"),
                    Span(f"[{result['pinyin']}]", cls="saved-word-pinyin"),
                    Button(
                        "★",
                        cls="save-button saved compact",
                        hx_post=f"/toggle-save/{word}",
                        hx_target=f"#saved-word-{word}",
                        hx_swap="outerHTML"
                    ),
                    cls="saved-word-row"
                ),
                cls="saved-word-card",
                id=f"saved-word-{word}"
            ),
            Div(
                Span(f"{word_count} word{'s' if word_count != 1 else ''} saved", cls="word-count"),
                Button(
                    "Start Review",
                    hx_post="/review",
                    hx_target="#review-area",
                    cls="review-button",
                    disabled=word_count == 0
                ),
                cls="saved-words-header",
                id="saved-words-header",
                hx_swap_oob="true"
            )
        )
    
    # Return the updated lookup view (only for the dictionary view)
    return lookup(word)

@rt('/saved-words')
def get():
    # Get all saved words ordered by most recently saved
    words = saved_words(order_by='-timestamp')
    word_count = len(words)
    
    return Container(
        Link(href="/static/styles.css", rel="stylesheet"),
        H2("Saved Words"),
        Div(
            A("← Back to Reader", href="/", cls="back-link"),
            Div(
                Span(f"{word_count} word{'s' if word_count != 1 else ''} saved", cls="word-count"),
                Button(
                    "Start Review",
                    hx_post="/review",
                    hx_target="#review-area",
                    cls="review-button",
                    disabled=word_count == 0
                ),
                cls="saved-words-header",
                id="saved-words-header"
            ),
            style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;"
        ),
        Div(
            Div(
                *[
                    Card(
                        Div(
                            Span(word['simplified'], cls="saved-word-text"),
                            Span(f"[{word['pinyin']}]", cls="saved-word-pinyin"),
                            Button(
                                "★",
                                cls="save-button saved compact",
                                hx_post=f"/toggle-save/{word['word']}",
                                hx_target=f"#saved-word-{word['word']}",
                                hx_swap="outerHTML"
                            ),
                            cls="saved-word-row"
                        ),
                        cls="saved-word-card",
                        id=f"saved-word-{word['word']}"
                    )
                    for word in words
                ],
                id="saved-words-list"
            ),
            id="review-area"
        )
    )

def calculate_next_review(correct: bool, stats: dict) -> tuple[float, float, float]:
    """Calculate the next review time using a modified SuperMemo 2 algorithm.
    Returns (next_review_timestamp, new_interval, new_ease_factor)"""
    current_time = time.time()
    
    # Default values for new words
    ease_factor = stats.get('ease_factor', 2.5)
    interval = stats.get('interval', 1.0)
    
    if correct:
        if interval == 1.0:  # First review
            interval = 1.0
        elif interval == 1:  # Second review
            interval = 6.0
        else:
            interval *= ease_factor
        
        # Increase ease factor for correct answers (max 2.5)
        ease_factor = min(ease_factor + 0.1, 2.5)
    else:
        # Reset interval and decrease ease factor for incorrect answers (min 1.3)
        interval = 1.0
        ease_factor = max(1.3, ease_factor - 0.2)
    
    # Convert interval from days to seconds and add to current time
    next_review = current_time + (interval * 86400)  # 86400 seconds = 1 day
    
    return next_review, interval, ease_factor

def get_words_to_review(limit: int = 10) -> list:
    """Get words for review, prioritizing:
    1. Words that are overdue (next_review < current_time)
    2. New words (not in review_stats)
    3. Words with more incorrect answers
    4. Any saved words (even if not due yet)
    
    Args:
        limit: Maximum number of words to return (only applies if there are more than 10 words)
    """
    current_time = time.time()
    
    # Get all saved words
    all_saved_words = saved_words()
    if not all_saved_words:
        return []
    
    # Get words with review stats
    reviewed_words = {r['word']: r for r in review_stats()}
    
    # Separate words into categories
    new_words = []
    due_words = []
    future_words = []
    
    for word in all_saved_words:
        word_id = word['word']
        if word_id not in reviewed_words:
            new_words.append(word)
        else:
            stats = reviewed_words[word_id]
            if stats['next_review'] <= current_time:
                # Calculate priority based on how overdue and incorrect count
                overdue_days = (current_time - stats['next_review']) / 86400
                priority = overdue_days + stats['incorrect_count']
                due_words.append((priority, word))
            else:
                # For words not due yet, prioritize by incorrect count and shorter intervals
                priority = stats['incorrect_count'] - (stats['next_review'] - current_time) / 86400
                future_words.append((priority, word))
    
    # Sort due and future words by priority (highest first)
    due_words.sort(reverse=True, key=lambda x: x[0])
    future_words.sort(reverse=True, key=lambda x: x[0])
    
    # Extract just the words from the priority tuples
    due_words = [word for _, word in due_words]
    future_words = [word for _, word in future_words]
    
    # Combine all words in priority order
    review_words = new_words + due_words + future_words
    
    # If we have 10 or fewer words, return them all
    # If we have more than 10 words, limit to 10
    return review_words if len(review_words) <= 10 else review_words[:10]

@rt('/review')
def post():
    """Start a new review session"""
    global current_session
    
    # Check if there are any saved words first
    all_saved_words = saved_words()
    if not all_saved_words:
        return Div(
            Div(
                P("No words available for review.", style="text-align: center; color: var(--muted-color);"),
                id="saved-words-list"
            ),
            id="review-area"
        )
    
    # Get words to review
    words = get_words_to_review()
    if not words:
        return Div(
            Div(
                P("No words available for review.", style="text-align: center; color: var(--muted-color);"),
                id="saved-words-list"
            ),
            id="review-area"
        )
    
    # Initialize new session
    current_session = ReviewSession(words=words, total_words=len(words))
    
    # Get total count of saved words
    total_saved_words = len(all_saved_words)
    
    # Return the first flashcard, progress indicator, and update the button
    return (
        Div(
            Div(
                Div(
                    P(
                        f"Card 1 of {len(words)}", 
                        style="text-align: center; color: var(--muted-color); margin: 20px 0 5px;"
                    ),
                    mk_flashcard(words[0]),
                    style="display: flex; flex-direction: column; align-items: center;"
                ),
                id="saved-words-list",
                style="display: block; width: 100%;"
            ),
            id="review-area",
            style="max-width: 800px; margin: 20px auto 0;"
        ),
        Div(
            Span(f"{total_saved_words} word{'s' if total_saved_words != 1 else ''} saved", cls="word-count"),
            Button(
                "End Review",
                hx_post="/end-review",
                hx_target="#review-area",
                cls="review-button"
            ),
            cls="saved-words-header",
            id="saved-words-header",
            hx_swap_oob="true"
        )
    )

@rt('/review/reveal/{word}')
def post(word: str):
    """Reveal the answer for a flashcard"""
    if not current_session or not current_session.current_word:
        return "Review session expired"
    
    current_word = current_session.current_word
    if current_word['word'] != word:
        return "Word mismatch error"
    
    return mk_flashcard(current_word, answer_revealed=True)

@rt('/review/answer/{result}/{word}')
def post(result: str, word: str):
    """Handle the answer (correct/incorrect) and show the next card"""
    global current_session
    
    if not current_session or not current_session.current_word:
        return "Review session expired"
    
    current_word = current_session.current_word
    if current_word['word'] != word:
        return "Word mismatch error"
    
    # Update review stats
    is_correct = result == "correct"
    stats = review_stats[word] if word in review_stats else {}
    next_review, interval, ease_factor = calculate_next_review(is_correct, stats)
    
    # Update or insert review stats
    review_data = {
        'word': word,
        'correct_count': stats.get('correct_count', 0) + (1 if is_correct else 0),
        'incorrect_count': stats.get('incorrect_count', 0) + (0 if is_correct else 1),
        'last_reviewed': time.time(),
        'next_review': next_review,
        'ease_factor': ease_factor,
        'interval': interval
    }
    
    if word in review_stats:
        review_stats.update(review_data, word)
    else:
        review_stats.insert(review_data)
    
    # Move to next word
    current_session.current_index += 1
    
    # Check if session is complete
    if current_session.is_complete:
        # Get all saved words ordered by most recently saved
        words = saved_words(order_by='-timestamp')
        word_count = len(words)
        
        return (
            Div(
                *[
                    Card(
                        Div(
                            Span(word['simplified'], cls="saved-word-text"),
                            Span(f"[{word['pinyin']}]", cls="saved-word-pinyin"),
                            Button(
                                "★",
                                cls="save-button saved compact",
                                hx_post=f"/toggle-save/{word['word']}",
                                hx_target=f"#saved-word-{word['word']}",
                                hx_swap="outerHTML"
                            ),
                            cls="saved-word-row"
                        ),
                        cls="saved-word-card",
                        id=f"saved-word-{word['word']}"
                    )
                    for word in words
                ],
                id="saved-words-list"
            ),
            Div(
                Span(f"{word_count} word{'s' if word_count != 1 else ''} saved", cls="word-count"),
                Button(
                    "Start Review",
                    hx_post="/review",
                    hx_target="#review-area",
                    cls="review-button",
                    disabled=word_count == 0
                ),
                cls="saved-words-header",
                id="saved-words-header",
                hx_swap_oob="true"
            )
        )
    
    # Show next card
    next_word = current_session.current_word
    return Div(
        Div(
            Div(
                P(
                    f"Card {current_session.current_index + 1} of {current_session.total_words}",
                    style="text-align: center; color: var(--muted-color); margin: 20px 0 5px;"
                ),
                mk_flashcard(next_word),
                style="display: flex; flex-direction: column; align-items: center;"
            ),
            id="saved-words-list",
            style="display: block; width: 100%;"
        ),
        id="review-area",
        style="max-width: 800px; margin: 20px auto 0;"
    )

@rt('/end-review')
def post():
    """End the current review session and restore the saved words view"""
    global current_session
    current_session = None
    
    # Get all saved words ordered by most recently saved
    words = saved_words(order_by='-timestamp')
    word_count = len(words)
    
    return (
        Div(
            *[
                Card(
                    Div(
                        Span(word['simplified'], cls="saved-word-text"),
                        Span(f"[{word['pinyin']}]", cls="saved-word-pinyin"),
                        Button(
                            "★",
                            cls="save-button saved compact",
                            hx_post=f"/toggle-save/{word['word']}",
                            hx_target=f"#saved-word-{word['word']}",
                            hx_swap="outerHTML"
                        ),
                        cls="saved-word-row"
                    ),
                    cls="saved-word-card",
                    id=f"saved-word-{word['word']}"
                )
                for word in words
            ],
            id="saved-words-list"
        ),
        Div(
            Span(f"{word_count} word{'s' if word_count != 1 else ''} saved", cls="word-count"),
            Button(
                "Start Review",
                hx_post="/review",
                hx_target="#review-area",
                cls="review-button",
                disabled=word_count == 0
            ),
            cls="saved-words-header",
            id="saved-words-header",
            hx_swap_oob="true"
        )
    )

serve()