from fasthtml.common import *
import jieba

app,rt = fast_app()

text_content = ""
segmented_words = []

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
        hx_target="#definition"
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
            #result {
                margin-top: 20px;
                line-height: 1.4;
                display: flex;
                flex-wrap: wrap;
                gap: 4px;
                align-items: center;
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
        Div(id="definition", style="margin-top: 20px; padding: 10px; border-top: 1px solid var(--muted-border-color);")
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
    # Placeholder for dictionary lookup - we'll implement this next
    return P(f"Looking up: {word}")

serve()