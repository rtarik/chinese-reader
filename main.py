from fasthtml.common import *
import jieba
from dictionary import ChineseDictionary
import math
from pathlib import Path
import time
from dataclasses import dataclass
from typing import List, Optional
import saved_words
from db import is_word_saved

app,rt = fast_app()

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
                id="content-input"
            ),
            Button("Submit", type="submit"),
            hx_post="/",
            hx_target="#result",
            id="input-form",
        ),
        id="input-area",
    )

def mk_word_span(word):
    return Card(
        word,
        cls="chinese-word",
        hx_post=f"/lookup/{word}",
        hx_target="#definition-card",
        hx_swap="outerHTML",
        hx_indicator="#loading"
    )

@rt('/')
def get():
    # Only reset state if there's no existing text content
    # This preserves the state when navigating back
    global text_content, segmented_words, current_page
    if not text_content:
        segmented_words = []
        current_page = 0
    
    # Calculate pagination info if we have content
    total_pages = math.ceil(len(segmented_words) / WORDS_PER_PAGE) if segmented_words else 0
    start_idx = current_page * WORDS_PER_PAGE
    end_idx = start_idx + WORDS_PER_PAGE
    page_words = segmented_words[start_idx:end_idx] if segmented_words else []
    
    return Title("Chinese Reader"), Container(
        Link(href="/static/styles.css", rel="stylesheet"),
        Div(
            Form(
                Textarea(
                    placeholder="Paste your Chinese text here...",
                    name="content",
                    id="content-input"
                ),
                Button("Submit", type="submit"),
                hx_post="/",
                hx_target="#result",
                id="input-form"
            ) if not text_content else Button(
                "Add New Text",
                id="add-text-btn",
                hx_post="/show-input",
                hx_target="#input-area",
                hx_swap="innerHTML"
            ),
            id="input-area"
        ),
        Div(
            Div(
                # Show segmented text if available, otherwise show message
                P(
                    *[mk_word_span(word) for word in page_words],
                    style="line-height: 2; display: flex; flex-wrap: wrap; gap: 4px; align-items: center;"
                ) if text_content and segmented_words else P("No text submitted yet."),
                id="result"
            ),
            Div(
                # Show pagination if we have segmented text with multiple pages
                Button("←", disabled=current_page==0, hx_post=f"/page/{current_page-1}", hx_target="#result-container") if current_page > 0 else Button("←", disabled=True),
                Span(f"Page {current_page + 1} of {total_pages}", cls="page-info"),
                Button("→", disabled=current_page>=total_pages-1, hx_post=f"/page/{current_page+1}", hx_target="#result-container") if current_page < total_pages-1 else Button("→", disabled=True),
                id="pagination-controls",
                cls="pagination-controls"
            ) if segmented_words else Div(id="pagination-controls", cls="pagination-controls"),
            id="result-container"
        ),
        Card(
            Div(id="definition"),
            id="definition-card",
            style="display: none;"
        ),
        A("View Saved Words →", href="/saved-words", id="view-saved-words")
    )

@rt('/show-input')
def post():
    return Form(
        Textarea(
            placeholder="Paste your Chinese text here...",
            name="content",
            id="content-input"
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
    
    return Div(
        Div(
            P(*word_spans, style="line-height: 2; display: flex; flex-wrap: wrap; gap: 4px; align-items: center;"),
            id="result"
        ),
        Div(
            Button("←", disabled=page==0, hx_post=f"/page/{page-1}", hx_target="#result-container") if page > 0 else None,
            Span(f"Page {page + 1} of {math.ceil(len(segmented_words) / WORDS_PER_PAGE)}", cls="page-info"),
            Button("→", disabled=page>=math.ceil(len(segmented_words) / WORDS_PER_PAGE)-1, hx_post=f"/page/{page+1}", hx_target="#result-container") if page < math.ceil(len(segmented_words) / WORDS_PER_PAGE)-1 else None,
            id="pagination-controls",
            cls="pagination-controls"
        ),
        id="result-container"
    )

@rt('/')
async def post(request):
    form = await request.form()
    global text_content, segmented_words, current_page
    text_content = form.get('content', '').strip()
    
    # Return early if no text is provided
    if not text_content:
        return (
            Div(
                P("Please enter some text to segment.", style="color: var(--pico-muted-color);"),
                id="result",
                hx_swap_oob="true"
            ),
            Div(
                id="pagination-controls",
                cls="pagination-controls",
                hx_swap_oob="true"
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
            P(*word_spans, style="line-height: 2; display: flex; flex-wrap: wrap; gap: 4px; align-items: center;"),
            id="result",
            hx_swap_oob="true"
        ),
        Div(
            Button("←", disabled=True),
            Span(f"Page 1 of {total_pages}", cls="page-info"),
            Button("→", disabled=total_pages<=1, hx_post="/page/1", hx_target="#result-container") if total_pages > 1 else None,
            id="pagination-controls",
            cls="pagination-controls",
            hx_swap_oob="true"
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
def post(word: str):
    return lookup(word)

def lookup(word: str):
    result = dictionary.lookup(word)
    
    if result:
        definitions = result['definitions']
        # Remove empty definitions and any leading/trailing whitespace
        definitions = [d.strip() for d in definitions if d.strip()]
        
        # Check if word is saved
        is_saved = is_word_saved(word)
        
        return Card(
            Div(
            H4(
                Span(result['simplified'], style="margin-right: 10px;"),
                Span(f"[{result['pinyin']}]", style="color: var(--pico-muted-color); font-weight: normal;"),
                style="margin-bottom: 10px;"
            ),
            P(
                Span(result['traditional'], style="color: var(--pico-muted-color);"),
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
            ),
            id="definition"
            ),
            id="definition-card"
        )
    else:
        return Card(P(f"No definition found for: {word}", style="color: var(--pico-muted-color);"), id="definition-card")

# Set up saved words routes
saved_words.setup_routes(app, lookup)

serve()