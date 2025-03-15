from fasthtml.common import *
from dictionary import ChineseDictionary
from db import (
    SavedWord,
    save_word,
    delete_word,
    get_all_saved_words,
    is_word_saved,
    update_review_stats,
    get_review_stats
)
from services.review import (
    start_review_session,
    end_review_session,
    get_current_session,
    advance_session,
    calculate_next_review
)

dictionary = ChineseDictionary()

def mk_flashcard(word: SavedWord, answer_revealed: bool = False) -> Card:
    """Create a flashcard for reviewing a word"""
    if answer_revealed:
        return Div(
            H3(word.simplified, style="text-align: center; margin-bottom: 10px;"),
            P(f"[{word.pinyin}]", style="text-align: center; color: var(--pico-muted-color); margin-bottom: 15px;"),
            P(word.traditional, style="text-align: center; color: var(--pico-muted-color); margin-bottom: 15px;") if word.traditional != word.simplified else None,
            Div(
                *[P(d, style="margin: 5px 0;") for d in word.definitions.split('\n')],
                style="text-align: center; margin-bottom: 20px;"
            ),
            Div(
                Button("✓", hx_post=f"/review/answer/correct/{word.word}", hx_target="#review-area", cls="correct-btn"),
                Button("✕", hx_post=f"/review/answer/incorrect/{word.word}", hx_target="#review-area", cls="incorrect-btn"),
                style="display: flex; justify-content: center; gap: 10px;"
            ),
            cls="flashcard",
            style="margin: 0 auto; max-width: 500px; padding: 20px; border: 1px solid var(--pico-card-border-color); border-radius: var(--pico-border-radius); background: var(--pico-card-background-color);"
        )
    else:
        return Card(
            H3(word.simplified, style="text-align: center; margin-bottom: 20px;"),
            Button(
                "Show Answer",
                hx_post=f"/review/reveal/{word.word}",
                hx_target="closest .flashcard",
                style="display: block; margin: 0 auto;"
            ),
            cls="flashcard",
            style="margin: 0 auto; max-width: 500px;"
        )

def setup_routes(app, lookup_func):
    rt = app.route
    
    @rt('/saved-words')
    def get():
        # Get all saved words ordered by most recently saved
        words = get_all_saved_words(order_by='-timestamp')
        word_count = len(words)
        
        return Title("Chinese Reader"), Container(
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
                                Span(word.simplified, cls="saved-word-text"),
                                Span(f"[{word.pinyin}]", cls="saved-word-pinyin"),
                                Button(
                                    "★",
                                    cls="save-button saved compact",
                                    hx_post=f"/toggle-save/{word.word}",
                                    hx_target=f"#saved-word-{word.word}",
                                    hx_swap="outerHTML"
                                ),
                                cls="saved-word-row"
                            ),
                            cls="saved-word-card",
                            id=f"saved-word-{word.word}"
                        )
                        for word in words
                    ],
                    id="saved-words-list"
                ),
                id="review-area"
            )
        )

    @rt('/toggle-save/{word}')
    def post(word: str, request):
        result = dictionary.lookup(word)
        if not result:
            return P(f"Error: Word not found", style="color: var(--pico-error-color);")
        
        # If word exists, remove it; if not, add it
        if is_word_saved(word):
            delete_word(word)
            # Get updated word count after deletion
            word_count = len(get_all_saved_words())
            
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
            word_data = {
                'word': word,
                'simplified': result['simplified'],
                'traditional': result['traditional'],
                'pinyin': result['pinyin'],
                'definitions': '\n'.join(result['definitions'])
            }
            saved_word = save_word(word_data)
            
            # If we're in the dictionary view, return the updated lookup view
            if not request.headers.get("HX-Target", "").startswith("saved-word-"):
                return lookup_func(word)
            
            # Get updated word count after addition
            word_count = len(get_all_saved_words())
            
            # If we're in the saved words list, return the new card and updated header
            return (
                Card(
                    Div(
                        Span(saved_word.simplified, cls="saved-word-text"),
                        Span(f"[{saved_word.pinyin}]", cls="saved-word-pinyin"),
                        Button(
                            "★",
                            cls="save-button saved compact",
                            hx_post=f"/toggle-save/{word}",
                            hx_target=f"#saved-word-{saved_word.word}",
                            hx_swap="outerHTML"
                        ),
                        cls="saved-word-row"
                    ),
                    cls="saved-word-card",
                    id=f"saved-word-{saved_word.word}"
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
        return lookup_func(word)

    @rt('/review')
    def post():
        """Start a new review session"""
        # Get all saved words first to check if any exist
        all_saved_words = get_all_saved_words()
        if not all_saved_words:
            return Div(
                Div(
                    P("No words available for review.", style="text-align: center; color: var(--pico-muted-color);"),
                    id="saved-words-list"
                ),
                id="review-area"
            )
        
        # Start new session
        session = start_review_session()
        if not session or not session.current_word:
            return Div(
                Div(
                    P("No words available for review.", style="text-align: center; color: var(--pico-muted-color);"),
                    id="saved-words-list"
                ),
                id="review-area"
            )
        
        # Return the first flashcard, progress indicator, and update the button
        return (
            Div(
                Div(
                    Div(
                        P(
                            f"Card 1 of {session.total_words}", 
                            style="text-align: center; color: var(--pico-muted-color); margin: 20px 0 5px;"
                        ),
                        mk_flashcard(session.current_word),
                        style="display: flex; flex-direction: column; align-items: center;"
                    ),
                    id="saved-words-list",
                    style="display: block; width: 100%;"
                ),
                id="review-area",
                style="max-width: 800px; margin: 20px auto 0;"
            ),
            Div(
                Span(f"{len(all_saved_words)} word{'s' if len(all_saved_words) != 1 else ''} saved", cls="word-count"),
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
        session = get_current_session()
        if not session or not session.current_word:
            return "Review session expired"
        
        current_word = session.current_word
        if current_word.word != word:
            return "Word mismatch error"
        
        return mk_flashcard(current_word, answer_revealed=True)

    @rt('/review/answer/{result}/{word}')
    def post(result: str, word: str):
        """Handle the answer (correct/incorrect) and show the next card"""
        session = get_current_session()
        if not session or not session.current_word:
            return "Review session expired"
        
        current_word = session.current_word
        if current_word.word != word:
            return "Word mismatch error"
        
        # Update review stats
        is_correct = result == "correct"
        stats = get_review_stats(word)
        next_review, interval, ease_factor = calculate_next_review(is_correct, stats)
        update_review_stats(word, is_correct, next_review, interval, ease_factor)
        
        # Move to next word
        has_more = advance_session()
        
        # Check if session is complete
        if not has_more:
            # Get all saved words ordered by most recently saved
            words = get_all_saved_words(order_by='-timestamp')
            word_count = len(words)
            
            return (
                Div(
                    *[
                        Card(
                            Div(
                                Span(word.simplified, cls="saved-word-text"),
                                Span(f"[{word.pinyin}]", cls="saved-word-pinyin"),
                                Button(
                                    "★",
                                    cls="save-button saved compact",
                                    hx_post=f"/toggle-save/{word.word}",
                                    hx_target=f"#saved-word-{word.word}",
                                    hx_swap="outerHTML"
                                ),
                                cls="saved-word-row"
                            ),
                            cls="saved-word-card",
                            id=f"saved-word-{word.word}"
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
        session = get_current_session()
        next_word = session.current_word
        return Div(
            Div(
                Div(
                    P(
                        f"Card {session.current_index + 1} of {session.total_words}",
                        style="text-align: center; color: var(--pico-muted-color); margin: 20px 0 5px;"
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
        end_review_session()
        
        # Get all saved words ordered by most recently saved
        words = get_all_saved_words(order_by='-timestamp')
        word_count = len(words)
        
        return (
            Div(
                *[
                    Card(
                        Div(
                            Span(word.simplified, cls="saved-word-text"),
                            Span(f"[{word.pinyin}]", cls="saved-word-pinyin"),
                            Button(
                                "★",
                                cls="save-button saved compact",
                                hx_post=f"/toggle-save/{word.word}",
                                hx_target=f"#saved-word-{word.word}",
                                hx_swap="outerHTML"
                            ),
                            cls="saved-word-row"
                        ),
                        cls="saved-word-card",
                        id=f"saved-word-{word.word}"
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