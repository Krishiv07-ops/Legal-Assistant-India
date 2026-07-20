"""
retrieval.py
Pure-Python retrieval engine (no numpy/scipy/scikit-learn) over two layers:
1. Curated knowledge base (situations -> laws + action steps) - primary source.
2. Constitution Part III articles (Fundamental Rights) - broader fallback text layer.

Uses simple TF-IDF-style word overlap scoring implemented in plain Python,
so it has zero compiled/native dependencies - this matters specifically for
serverless platforms like Vercel, where scikit-learn/numpy/scipy can fail to
import due to bundle size and native-extension constraints. For local/Render
use this works identically, just without the numpy speed boost (irrelevant
at this data size - under 30 entries).
"""

import json
import os
import re
import math
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
KB_PATH = os.path.join(DATA_DIR, "knowledge_base.json")
CONSTITUTION_PATH = os.path.join(DATA_DIR, "constitution_articles.json")

TOKEN_RE = re.compile(r"[a-z0-9]+")

# Minimal English stopword list - without this, common words (the, and, of, my...)
# dominate scores and cause false matches, since scikit-learn's stop_words="english"
# was doing this for us before.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "he", "her", "his", "i", "in", "is", "it", "its", "me", "my", "of", "on", "or",
    "she", "that", "the", "their", "them", "they", "this", "to", "was", "we", "were",
    "will", "with", "you", "your", "not", "no", "do", "does", "did", "can", "could",
    "should", "would", "about", "if", "so", "than", "any", "all", "been", "being",
}


def tokenize(text: str):
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


class _MiniTfidfIndex:
    """A minimal TF-IDF + cosine-similarity index in pure Python."""

    def __init__(self, documents: list):
        self.doc_tokens = [tokenize(doc) for doc in documents]
        self.doc_count = len(documents)

        df = Counter()
        for tokens in self.doc_tokens:
            for term in set(tokens):
                df[term] += 1
        self.idf = {
            term: math.log((1 + self.doc_count) / (1 + freq)) + 1
            for term, freq in df.items()
        }

        self.doc_vectors = [self._vectorize(tokens) for tokens in self.doc_tokens]

    def _vectorize(self, tokens):
        tf = Counter(tokens)
        vec = {term: count * self.idf.get(term, 0.0) for term, count in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {term: v / norm for term, v in vec.items()}

    def query(self, text: str):
        tokens = tokenize(text)
        tf = Counter(tokens)
        # Use idf from the fitted corpus; unseen terms contribute 0.
        vec = {term: count * self.idf.get(term, 0.0) for term, count in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        qvec = {term: v / norm for term, v in vec.items()}

        scores = []
        for doc_vec in self.doc_vectors:
            score = sum(qvec.get(term, 0.0) * w for term, w in doc_vec.items())
            scores.append(score)
        return scores


class LegalRetriever:
    def __init__(self, kb_path: str = KB_PATH, constitution_path: str = CONSTITUTION_PATH):
        with open(kb_path, "r", encoding="utf-8") as f:
            self.entries = json.load(f)

        with open(constitution_path, "r", encoding="utf-8") as f:
            self.articles = json.load(f)

        # --- Curated knowledge base corpus ---
        self.corpus = []
        for entry in self.entries:
            law_text = " ".join(
                f"{law['act']} {law['section']} {law['summary']}"
                for law in entry["laws"]
            )
            blob = f"{entry['topic']} {' '.join(entry['keywords'])} {law_text}"
            self.corpus.append(blob)
        self.kb_index = _MiniTfidfIndex(self.corpus)

        # --- Constitution articles corpus ---
        self.article_corpus = [f"{a['title']} {a['text']}" for a in self.articles]
        self.article_index = _MiniTfidfIndex(self.article_corpus)

    def search(self, query: str, top_k: int = 2, min_score: float = 0.1):
        """Search curated knowledge base entries. Returns up to top_k matches."""
        scores = self.kb_index.query(query)

        query_lower = query.lower()
        for i, entry in enumerate(self.entries):
            for kw in entry["keywords"]:
                if kw in query_lower:
                    scores[i] += 0.3
                    break

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in ranked[:top_k]:
            if score >= min_score:
                results.append({"entry": self.entries[idx], "score": round(float(score), 3)})
        return results

    def search_constitution(self, query: str, top_k: int = 2, min_score: float = 0.08):
        """Search Constitution (Part III) articles. Returns up to top_k matches."""
        scores = self.article_index.query(query)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in ranked[:top_k]:
            if score >= min_score:
                results.append({"article": self.articles[idx], "score": round(float(score), 3)})
        return results

    def search_all(self, query: str, kb_top_k: int = 2, article_top_k: int = 2):
        """Combined search: curated entries + constitution articles, curated ranked first."""
        return {
            "kb_results": self.search(query, top_k=kb_top_k),
            "article_results": self.search_constitution(query, top_k=article_top_k),
        }


if __name__ == "__main__":
    retriever = LegalRetriever()
    for q in ["police detained me and didn't tell me why", "freedom to practice my religion at work",
              "my UPI got hacked and money was stolen", "random question about the solar system"]:
        print(f"\nQuery: {q}")
        res = retriever.search_all(q)
        for r in res["kb_results"]:
            print("  KB:", r["entry"]["topic"], r["score"])
        for r in res["article_results"]:
            print("  Article:", r["article"]["article"], r["article"]["title"], r["score"])
