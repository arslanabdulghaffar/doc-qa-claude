import io
import os

import anthropic
import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

MAX_CHARS = 300_000

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="PDF Q&A", page_icon="📄", layout="centered")

# ── Session state ─────────────────────────────────────────────────────────────
_defaults = {
    "messages": [],
    "pdf_text": None,
    "pdf_name": None,
    "pdf_pages": 0,
    "provider": os.getenv("LLM_PROVIDER", "local"),
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📄 PDF Q&A")

    # PDF uploader
    uploaded = st.file_uploader("Document", type="pdf")

    if uploaded is not None and uploaded.name != st.session_state.pdf_name:
        with st.spinner("Reading PDF…"):
            try:
                reader = PdfReader(io.BytesIO(uploaded.read()))
                pages_text = [p.extract_text() or "" for p in reader.pages]
                text = "\n\n".join(pages_text).strip()
                if not text:
                    st.error(
                        "No extractable text found. "
                        "The PDF may be scanned or image-only."
                    )
                else:
                    truncated = len(text) > MAX_CHARS
                    st.session_state.pdf_text = text[:MAX_CHARS]
                    st.session_state.pdf_name = uploaded.name
                    st.session_state.pdf_pages = len(reader.pages)
                    st.session_state.messages = []
                    if truncated:
                        st.warning(
                            "Very large document — truncated to the first "
                            f"{MAX_CHARS:,} characters."
                        )
            except Exception as exc:
                st.error(f"Failed to read PDF: {exc}")

    if st.session_state.pdf_name:
        n = st.session_state.pdf_pages
        st.success(
            f"**{st.session_state.pdf_name}**  \n"
            f"{n} page{'s' if n != 1 else ''}"
        )

    st.divider()

    # Provider selector
    st.session_state.provider = st.radio(
        "Provider",
        ["local", "claude"],
        format_func=lambda x: "🖥  Local (Ollama)" if x == "local" else "☁  Claude",
        index=["local", "claude"].index(st.session_state.provider),
    )

    if st.session_state.messages:
        st.divider()
        if st.button("🗑  Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

provider = st.session_state.provider

# ── Client init ───────────────────────────────────────────────────────────────
if provider == "claude":
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error(
            "**ANTHROPIC_API_KEY not found.** Add it to `.env`:\n"
            "```\nANTHROPIC_API_KEY=sk-ant-...\n```"
        )
        st.stop()
    llm = anthropic.Anthropic(api_key=api_key)
else:
    from openai import OpenAI as _OpenAI
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
    llm = _OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("PDF Q&A")
st.caption("Ask questions about any document. Answers are grounded in the uploaded file.")

# ── Empty state ───────────────────────────────────────────────────────────────
if st.session_state.pdf_text is None:
    st.info(
        "**Get started**\n\n"
        "1. Upload a PDF using the sidebar panel\n"
        "2. Choose a provider — Local (Ollama) runs entirely on your machine; "
        "Claude uses the Anthropic cloud API\n"
        "3. Type your first question below"
    )

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat input ────────────────────────────────────────────────────────────────
prompt = st.chat_input(
    "Ask about the document…",
    disabled=st.session_state.pdf_text is None,
)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    SYSTEM = (
        "You are a helpful assistant that answers questions strictly based on the "
        "provided document. If the answer is not in the document, say so clearly.\n\n"
        f"<document>\n{st.session_state.pdf_text}\n</document>"
    )
    # Full conversation including the current user turn
    api_msgs = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]

    def _stream_claude():
        with llm.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM,
            messages=api_msgs,
        ) as s:
            yield from s.text_stream

    def _stream_ollama():
        resp = llm.chat.completions.create(
            model=OLLAMA_MODEL,
            max_tokens=1024,
            stream=True,
            messages=[{"role": "system", "content": SYSTEM}, *api_msgs],
        )
        for chunk in resp:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    with st.chat_message("assistant"):
        try:
            streamer = _stream_claude if provider == "claude" else _stream_ollama
            answer = st.write_stream(streamer())
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except anthropic.AuthenticationError:
            st.error("Invalid API key — check ANTHROPIC_API_KEY in your `.env` file.")
        except anthropic.RateLimitError:
            st.error("Rate limit reached. Please wait a moment and try again.")
        except anthropic.BadRequestError as exc:
            st.error(f"Bad request: {exc.message}")
        except anthropic.APIStatusError as exc:
            st.error(f"API error {exc.status_code}: {exc.message}")
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
