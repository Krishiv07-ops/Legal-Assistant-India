# Vidhi Sahayak (विधि सहायक) — Indian Legal Rights Assistant

A web app that takes a plain-language description of a legal situation (e.g. "the police
detained me and never told me why") and returns the relevant Indian laws — Constitution
articles, Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita (BNSS), and other
acts — along with concrete next steps.

> ⚠️ **This provides general legal information, not legal advice.** It is not a substitute for
> a licensed advocate. For real cases, contact [NALSA](https://nalsa.gov.in) for free legal aid.

## How it works

1. **Curated knowledge base** (`data/knowledge_base.json`) — hand-curated entries for 10 topics:
   arrest/illegal detention, FIR refusal, dowry harassment, general domestic violence, cheque
   dishonour, consumer complaints, cybercrime/IT Act, motor vehicle accidents, and RTI. Each
   entry has exact section citations and step-by-step guidance.
2. **Constitution layer** (`data/constitution_articles.json`) — Part III (Fundamental Rights,
   Articles 14–32), the part of the Constitution people actually invoke in real situations.
   This acts as a broader fallback search layer alongside the curated entries.
3. **Retrieval** (`retrieval.py`) — TF-IDF + keyword matching searches both layers for a
   free-text query and returns the most relevant curated topic(s) and article(s). No external
   API needed for this step.
4. **Answer generation** (`llm_layer.py`) — three modes, tried in order:
   - **Ollama (local, free)** — set `OLLAMA_MODEL` (e.g. `llama3.1`) with Ollama running
     locally; no API costs, fully offline, good fit if you already have Ollama installed.
   - **Anthropic Claude API** — set `ANTHROPIC_API_KEY` for hosted, higher-quality answers.
   - **Templated fallback** (default, no setup) — clean structured answer built directly from
     retrieved data. Free, deterministic, always works.
5. **Web app** (`app.py` + `templates/` + `static/`) — Flask backend, single-page frontend.

### Using Ollama (free, local, no API key)

```bash
# 1. Install Ollama: https://ollama.com/download
# 2. Pull a model (llama3.1 or mistral work well on an RTX 4060)
ollama pull llama3.1

# 3. Make sure the Ollama server is running (usually starts automatically)
ollama serve

# 4. Tell the app to use it
export OLLAMA_MODEL=llama3.1      # Windows: set OLLAMA_MODEL=llama3.1
python app.py
```
If Ollama isn't reachable, the app automatically falls back to the templated answer instead of crashing.

## Running it locally

```bash
git clone <your-repo-url>
cd legal-assistant-india
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
pip install -r requirements.txt

python app.py
```

Then open **http://localhost:5000**.

### Optional: enable natural-language answers via Claude

```bash
export ANTHROPIC_API_KEY=your-key-here   # Windows: set ANTHROPIC_API_KEY=your-key-here
python app.py
```

## Project structure

```
legal-assistant-india/
├── app.py                  # Flask app + /api/ask endpoint
├── retrieval.py             # TF-IDF retrieval over the knowledge base
├── llm_layer.py              # Optional Claude call + templated fallback
├── data/
│   ├── knowledge_base.json         # Curated legal entries (laws + steps)
│   └── constitution_articles.json  # Part III Fundamental Rights (Art 14-32)
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── app.js
├── requirements.txt
└── README.md
```

## Extending the knowledge base

Add a new object to `data/knowledge_base.json` following the existing shape:

```json
{
  "id": "your-topic-id",
  "topic": "Human-readable topic name",
  "keywords": ["short", "phrases", "someone", "might", "type"],
  "laws": [
    { "act": "Act name", "section": "Section X", "summary": "Plain-English summary." }
  ],
  "steps": ["Step 1...", "Step 2..."]
}
```

No code changes needed — retrieval picks up new entries automatically.

**Verify every citation against a primary source** (indiacode.nic.in, Indian Kanoon, or a
lawyer) before adding it — an incorrect section number in a legal tool is worse than none.

## Known limitations (MVP)

- **This does not cover "every law"** — 10 curated situations + Part III of the Constitution.
  Full coverage of every Act would require ingesting full statutory text for dozens of laws;
  this is a real project, not a quick data-entry task. See Roadmap below.
- Citations were written from general legal knowledge, not verified line-by-line against
  India Code (indiacode.nic.in). **Verify anything high-stakes before relying on it.**
- TF-IDF retrieval is simple; may miss oddly-phrased queries. A production version would use
  proper embeddings + a vector DB (e.g. Chroma) for better semantic matching.
- Not reviewed by a lawyer — treat all output as a starting point for research, not a final
  answer.

## Roadmap ideas

- [ ] Ingest full text of more major Acts (Labour Codes, Rent Control, Companies Act, POCSO,
      Property/Succession law) as additional fallback layers, same pattern as
      `constitution_articles.json`
- [ ] Add remaining Constitution parts (Directive Principles, Fundamental Duties, Schedules)
- [ ] Verify every citation against India Code before treating as production-ready
- [ ] Swap TF-IDF for proper embeddings + vector search for better semantic matching at scale
- [ ] Add a disclaimer/consent screen on first load
- [ ] Track which queries get no match, to prioritize new knowledge base entries
- [ ] Flutter mobile wrapper (calls the same `/api/ask` endpoint)

## Pushing to your GitHub

```bash
cd legal-assistant-india
git init
git add .
git commit -m "Initial commit: Vidhi Sahayak MVP"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

## License

MIT — do whatever you like with it, just keep the disclaimer intact.
