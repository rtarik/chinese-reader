from fasthtml.common import *
import jieba
from dictionary import ChineseDictionary
import math
from pathlib import Path
import time

app,rt = fast_app()

# Initialize database for saved words
db = database('data/saved_words.db')
saved_words = db.t.saved_words
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

text_content = ""
segmented_words = []
dictionary = ChineseDictionary()
WORDS_PER_PAGE = 200
current_page = 0

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
        # Check if we're removing from the saved words list
        if request.headers.get("HX-Target", "").startswith("saved-word-"):
            # Get updated count
            word_count = len(saved_words())
            # Return both the empty string for the card and the updated header
            return (
                "",  # Empty string to remove the card
                Div(
                    Span(f"{word_count} word{'s' if word_count != 1 else ''} saved", cls="word-count"),
                    Button(
                        "Start Review →",
                        hx_post="/review",
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
                    "Start Review →",
                    hx_post="/review",
                    cls="review-button",
                    disabled=word_count == 0
                ),
                cls="saved-words-header",
                id="saved-words-header"
            ),
            style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;"
        ),
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
        )
    )

serve()