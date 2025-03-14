from fasthtml.common import *
import jieba
from dictionary import ChineseDictionary

app,rt = fast_app()

text_content = ""
segmented_words = []
dictionary = ChineseDictionary()

def mk_textarea():
    return Textarea(
        placeholder="Paste your Chinese text here...",
        name="content",
        id="content-input",
        style="width: 100%; height: 150px; margin-bottom: 10px;"
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
        Style("""
            .chinese-word {
                display: inline-block;
                padding: 0 !important;
                margin: 0 !important;
                font-size: 1.4rem;
                cursor: pointer;
                transition: all 0.2s ease;
                min-width: auto !important;
            }
            .chinese-word > :first-child {
                margin: 3px 8px !important;
            }
            .chinese-word:hover {
                transform: translateY(-1px);
                box-shadow: var(--card-box-shadow);
            }
            .chinese-word.active {
                background: var(--primary);
                color: var(--primary-inverse);
            }
            #result {
                margin-top: 20px;
                line-height: 1.4;
                display: flex;
                flex-wrap: wrap;
                gap: 4px;
                align-items: center;
            }
            #loading {
                display: none;
            }
            #loading.htmx-request {
                display: inline;
            }
            .definition-card {
                margin-top: 20px;
                padding: 20px;
                border-radius: var(--border-radius);
                background: var(--card-background-color);
                border: 1px solid var(--card-border-color);
            }
        """),
        Form(
            mk_textarea(),
            Button("Submit", type="submit"),
            hx_post="/",
            hx_target="#result"
        ),
        Div(
            P(text_content) if text_content else P("No text submitted yet."),
            id="result"
        ),
        Card(
            Div(
                Span("Looking up... ", id="loading"),
                P("Click a word above to see its definition", cls="definition-text"),
                id="definition"
            ),
            cls="definition-card"
        )
    )

@rt('/')
async def post(request):
    form = await request.form()
    global text_content, segmented_words
    text_content = form.get('content', '')
    # Segment the Chinese text into words
    segmented_words = list(jieba.cut(text_content))
    
    # Create clickable spans for each word
    word_spans = [mk_word_span(word) for word in segmented_words]
    
    # Return both the textarea reset and the segmented text with clickable words
    return (
        P(*word_spans, id="result", style="line-height: 2;"),
        Textarea(
            placeholder="Paste your Chinese text here...",
            name="content",
            id="content-input",
            style="width: 100%; height: 150px; margin-bottom: 10px;",
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