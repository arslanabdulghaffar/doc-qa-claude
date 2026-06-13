# PDF Q&A

Ask questions about any PDF — powered by Claude or a local open model via Ollama.

![screenshot](docs/screenshot.png)

## Features

- **PDF upload** — drag-and-drop any PDF; text is extracted client-side with pypdf
- **Document-grounded answers** — the model only uses content from the uploaded file
- **Dual provider** — switch between Claude (cloud) and a local open model via Ollama (free, private, no data leaves your machine)
- **Session history** — all Q&A pairs stay visible and collapsible for the duration of your session

## Tech stack

| Layer | Library |
|---|---|
| UI | [Streamlit](https://streamlit.io) |
| Cloud LLM | [Anthropic Claude API](https://docs.anthropic.com) (`claude-sonnet-4-6`) |
| Local LLM | [Ollama](https://ollama.com) via OpenAI-compatible endpoint |
| PDF parsing | [pypdf](https://pypdf.readthedocs.io) |
| Language | Python 3.11+ |

## Getting started

### 1. Clone and install

```bash
git clone <repo-url>
cd doc-qa-claude
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

Copy the example below into a `.env` file in the project root and fill in the values you need:

```dotenv
# Choose provider: "local" (default) or "claude"
LLM_PROVIDER=local

# Required when LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...

# Optional — override the default Ollama model
# OLLAMA_MODEL=gpt-oss:20b
```

### 3. Set up your chosen provider

**Local (Ollama) — free, runs on your machine:**

1. Install Ollama from [ollama.com](https://ollama.com)
2. Pull the model:
   ```bash
   ollama pull gpt-oss:20b
   ```
3. Ollama starts automatically; the app connects to `http://localhost:11434`.

**Claude (cloud):**

1. Get an API key from [console.anthropic.com](https://console.anthropic.com)
2. Set `LLM_PROVIDER=claude` and `ANTHROPIC_API_KEY=sk-ant-...` in `.env`

### 4. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `local` | `local` → Ollama; `claude` → Anthropic Claude API |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=claude` |
| `OLLAMA_MODEL` | `gpt-oss:20b` | Any model available in your local Ollama installation |

## License

MIT
