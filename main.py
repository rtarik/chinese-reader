from fasthtml.common import *
import jieba
from dictionary import ChineseDictionary
import math

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
        )
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
            )
        )
    else:
        return P(f"No definition found for: {word}", style="color: var(--muted-color);")

serve()