import io
import os

import anthropic
import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

MAX_CHARS = 300_000  # ~100K tokens; guards against very large PDFs

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")

st.set_page_config(page_title="PDF Q&A", page_icon="📄")
st.title("📄 PDF Question & Answer")
st.markdown(
    "Upload a PDF in the sidebar, then type a question and click **Ask**. "
    "All answers are grounded in the document content."
)

# --- Provider setup ---
if LLM_PROVIDER == "claude":
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error(
            "**ANTHROPIC_API_KEY not found.** "
            "Create a `.env` file in this directory with:\n"
            "```\nANTHROPIC_API_KEY=sk-ant-...\n```"
        )
        st.stop()
    claude_client = anthropic.Anthropic(api_key=api_key)

elif LLM_PROVIDER == "local":
    from openai import OpenAI
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
    ollama_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

else:
    st.error(
        f"**Unknown LLM_PROVIDER '{LLM_PROVIDER}'.** "
        "Set LLM_PROVIDER to `claude` or `local` in your `.env` file."
    )
    st.stop()

# --- Session state ---
if "history" not in st.session_state:
    st.session_state.history = []
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = None
if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = None

# --- Sidebar: PDF upload + provider badge ---
with st.sidebar:
    st.header("Document")
    uploaded = st.file_uploader("Upload a PDF", type="pdf")

    if uploaded is not None and uploaded.name != st.session_state.pdf_name:
        try:
            reader = PdfReader(io.BytesIO(uploaded.read()))
            pages_text = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages_text).strip()

            if not text:
                st.error(
                    "No text could be extracted. The PDF may be scanned "
                    "or image-only and requires OCR."
                )
            else:
                truncated = False
                if len(text) > MAX_CHARS:
                    text = text[:MAX_CHARS]
                    truncated = True

                st.session_state.pdf_text = text
                st.session_state.pdf_name = uploaded.name
                st.session_state.history = []

                if truncated:
                    st.warning(
                        f"Document is very large — using the first "
                        f"{MAX_CHARS:,} characters to stay within limits."
                    )
                else:
                    st.success(f"Loaded ({len(text):,} characters)")

        except Exception as exc:
            st.error(f"Failed to read PDF: {exc}")

    if st.session_state.pdf_name:
        st.info(f"**Active:** {st.session_state.pdf_name}")

    if st.session_state.history:
        if st.button("Clear history"):
            st.session_state.history = []
            st.rerun()

    st.divider()
    if LLM_PROVIDER == "claude":
        st.caption("Provider: Claude (claude-sonnet-4-6)")
    else:
        st.caption(f"Provider: Ollama ({OLLAMA_MODEL})")

# --- Prompt if no PDF ---
if st.session_state.pdf_text is None:
    st.info("👈 Upload a PDF in the sidebar to get started.")
    st.stop()

# --- Q&A form ---
with st.form("qa_form", clear_on_submit=True):
    question = st.text_area(
        "Your question",
        placeholder="What is this document about?",
        height=80,
    )
    submitted = st.form_submit_button("Ask")

if submitted:
    q = question.strip()
    if not q:
        st.warning("Please enter a question before submitting.")
    else:
        with st.spinner("Thinking…"):
            system_prompt = (
                "You are a helpful assistant that answers questions about documents. "
                "Base your answers only on the provided document. "
                "If the answer is not found in the document, say so clearly."
            )
            user_content = (
                "Here is the document:\n\n"
                f"<document>\n{st.session_state.pdf_text}\n</document>\n\n"
                f"Question: {q}"
            )

            try:
                if LLM_PROVIDER == "claude":
                    response = claude_client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=1024,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_content}],
                    )
                    answer = response.content[0].text

                else:  # local / Ollama
                    response = ollama_client.chat.completions.create(
                        model=OLLAMA_MODEL,
                        max_tokens=1024,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                    )
                    answer = response.choices[0].message.content

                st.session_state.history.insert(0, {"question": q, "answer": answer})

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

# --- Q&A history ---
if st.session_state.history:
    st.divider()
    st.subheader("Q&A History")
    for i, item in enumerate(st.session_state.history):
        label = item["question"]
        if len(label) > 80:
            label = label[:80] + "…"
        with st.expander(f"Q: {label}", expanded=(i == 0)):
            st.markdown(f"**Question:** {item['question']}")
            st.markdown(f"**Answer:** {item['answer']}")
