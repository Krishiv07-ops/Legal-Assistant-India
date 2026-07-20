"""
app.py
Flask web app for the India Legal Assistant.
Run: python app.py  (then open http://localhost:5000)
"""

from flask import Flask, render_template, request, jsonify
from retrieval import LegalRetriever
from llm_layer import generate_answer

app = Flask(__name__)
retriever = LegalRetriever()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({"error": "Please describe your situation."}), 400

    results = retriever.search_all(query, kb_top_k=2, article_top_k=2)
    kb_results = results["kb_results"]
    article_results = results["article_results"]

    answer = generate_answer(query, kb_results, article_results)

    return jsonify({
        "answer": answer,
        "matched_topics": [r["entry"]["topic"] for r in kb_results],
        "matched_articles": [r["article"]["article"] for r in article_results],
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
