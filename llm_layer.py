"""
llm_layer.py
Turns retrieved knowledge-base entries + constitution articles into a natural
language answer. Three modes, tried in this order:

1. Ollama (local, free) - if OLLAMA_MODEL env var is set and a local Ollama
   server is reachable at OLLAMA_HOST (default http://localhost:11434).
2. Anthropic Claude API - if ANTHROPIC_API_KEY is set.
3. Templated fallback - built directly from retrieved data, no LLM needed.
   Always works, zero cost, zero setup.
"""

import os
import json
import urllib.request
import urllib.error

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL")  # e.g. "llama3.1" or "mistral"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

SYSTEM_PROMPT = """You are a legal information assistant for Indian law. You must answer
ONLY using the legal sections, articles, and steps provided to you in the context below.
Do not invent section numbers, article numbers, acts, or case law that isn't given to you.
If the context doesn't fully cover the situation, say so plainly rather than guessing.
Be clear and practical, structured as: (1) what likely happened / relevant laws, (2) concrete
next steps, in plain language a non-lawyer can follow. Always end by reminding the user this
is informational, not a substitute for a licensed lawyer, and to contact NALSA (nalsa.gov.in)
or a lawyer for their specific case."""


def _build_context(query: str, kb_results: list, article_results: list) -> str:
    blocks = []
    for r in kb_results:
        entry = r["entry"]
        law_lines = "\n".join(f"- {l['act']}, {l['section']}: {l['summary']}" for l in entry["laws"])
        step_lines = "\n".join(f"- {s}" for s in entry["steps"])
        blocks.append(f"Topic: {entry['topic']}\nLaws:\n{law_lines}\nSuggested steps:\n{step_lines}")

    for r in article_results:
        a = r["article"]
        blocks.append(f"Constitution {a['article']} ({a['title']}): {a['text']}")

    return "\n\n".join(blocks)


def _templated_fallback(query: str, kb_results: list, article_results: list) -> str:
    """Build a clean answer directly from retrieved data, no LLM call."""
    if not kb_results and not article_results:
        return (
            "I couldn't confidently match your situation to a topic in the current "
            "knowledge base or the Constitution's Fundamental Rights. Try rephrasing, "
            "or this topic may need to be added to the knowledge base."
        )

    lines = []
    for r in kb_results:
        entry = r["entry"]
        lines.append(f"## {entry['topic']}  (relevance: {r['score']})\n")
        lines.append("**Relevant laws:**")
        for law in entry["laws"]:
            lines.append(f"- **{law['act']}, {law['section']}** — {law['summary']}")
        lines.append("\n**Steps you can take:**")
        for i, step in enumerate(entry["steps"], 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    if article_results:
        lines.append("## Related Constitutional Provisions\n")
        for r in article_results:
            a = r["article"]
            lines.append(f"- **{a['article']} — {a['title']}**: {a['text']}")
        lines.append("")

    lines.append(
        "\n_This is general legal information, not legal advice for your specific case. "
        "For personalized help, contact NALSA (nalsa.gov.in) for free legal aid or consult a lawyer._"
    )
    return "\n".join(lines)


def _call_ollama(query: str, context: str) -> str:
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\nUser's situation: {query}\n\nRelevant legal context:\n{context}\n\nAnswer:",
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("response", "").strip()


def _call_claude(query: str, context: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"User's situation: {query}\n\nRelevant legal context:\n{context}"}
        ],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def generate_answer(query: str, kb_results: list, article_results: list) -> str:
    context = _build_context(query, kb_results, article_results)

    if OLLAMA_MODEL:
        try:
            return _call_ollama(query, context)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            return (
                _templated_fallback(query, kb_results, article_results)
                + f"\n\n_(Could not reach local Ollama server at {OLLAMA_HOST} - "
                  f"is `ollama serve` running and is the model pulled? Showing direct data instead. Error: {e})_"
            )
        except Exception as e:
            return _templated_fallback(query, kb_results, article_results) + f"\n\n_(Ollama call failed: {e})_"

    if ANTHROPIC_API_KEY:
        try:
            return _call_claude(query, context)
        except Exception as e:
            return _templated_fallback(query, kb_results, article_results) + f"\n\n_(LLM call failed, showing direct data: {e})_"

    return _templated_fallback(query, kb_results, article_results)
