"""Knowledge base loading and TF-IDF retrieval (pure Python, no API key needed).

The knowledge base holds three kinds of documents: genre descriptions, mood
descriptions, and listening scenarios ("studying", "workout", ...). Genre and
mood documents get numeric targets computed from the song catalog, so the
numbers come from the data. Scenario targets are hand-written judgments.
"""

import json
import math
import re
from typing import Dict, List, Tuple

STOPWORDS = frozenset(
    "a an and are as at be but by for from has have i in is it its me my of on or "
    "so some something that the their then there these this to up want was with you your "
    "like music songs song play give need please help make".split()
)
_TOKEN = re.compile(r"[a-z0-9&']+")
_NUMERIC_KEYS = ("energy", "valence", "danceability", "acousticness")


def stem(word: str) -> str:
    """A tiny suffix stripper so 'studying', 'studied' and 'study' line up."""
    if len(word) <= 3:
        return word
    for suffix in ("ing", "ied", "ies", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)] + ("y" if suffix in ("ied", "ies") else "")
            break
    if word.endswith("e") and len(word) > 3:
        word = word[:-1]
    if len(word) > 3 and word[-1] == word[-2] and word[-1] not in "lsz":
        word = word[:-1]
    return word


_HYPHEN = re.compile(r"(?<=[a-z0-9])-(?=[a-z0-9])")


def tokenize(text: str) -> List[str]:
    # Join hyphenated words first so "k-pop" and "lo-fi" stay one token ("kpop", "lofi")
    text = _HYPHEN.sub("", text.lower())
    return [stem(t) for t in _TOKEN.findall(text) if t not in STOPWORDS and len(t) > 1]


def load_knowledge_base(path: str, songs: List[Dict]) -> List[Dict]:
    """Load the JSON knowledge base into a flat list of document dicts.

    Each document has: id, type, title, text, keywords, genres, moods, targets.
    Raises ValueError if the file is malformed.
    """
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as err:
        raise ValueError(f"{path} is not valid JSON: {err}") from err
    for key in ("genres", "moods", "scenarios"):
        if not isinstance(raw.get(key), list) or not raw[key]:
            raise ValueError(f"{path} must contain a non-empty '{key}' list")

    docs: List[Dict] = []
    for kind, field in (("genre", "genres"), ("mood", "moods")):
        for item in raw[field]:
            label = item["label"]
            matching = [s for s in songs if s[kind] == label]
            targets = {k: round(sum(s[k] for s in matching) / len(matching), 2)
                       for k in _NUMERIC_KEYS} if matching else {}
            if matching:
                targets["tempo_bpm"] = round(sum(s["tempo_bpm"] for s in matching) / len(matching))
            docs.append({
                "id": f"{kind}:{label}", "type": kind, "title": label.title(),
                "text": item["text"], "keywords": item.get("keywords", ""),
                "genres": [label] if kind == "genre" else [],
                "moods": [label] if kind == "mood" else [],
                "targets": targets,
            })
    for item in raw["scenarios"]:
        for required in ("id", "title", "text", "genres", "moods", "targets"):
            if required not in item:
                raise ValueError(f"scenario {item.get('id', '?')} is missing '{required}'")
        docs.append({
            "id": f"scenario:{item['id']}", "type": "scenario", "title": item["title"],
            "text": item["text"], "keywords": item.get("keywords", ""),
            "genres": item["genres"], "moods": item["moods"], "targets": item["targets"],
        })
    return docs


class Retriever:
    """TF-IDF cosine retriever over the knowledge base documents."""

    def __init__(self, docs: List[Dict]):
        if not docs:
            raise ValueError("retriever needs at least one document")
        self.docs = docs
        tokenized = [tokenize(f"{d['title']} {d['title']} {d['text']} {d['keywords']}") for d in docs]
        df: Dict[str, int] = {}
        for toks in tokenized:
            for t in set(toks):
                df[t] = df.get(t, 0) + 1
        n = len(docs)
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
        self.vectors = [self._vector(toks) for toks in tokenized]

    def _vector(self, tokens: List[str]) -> Dict[str, float]:
        counts: Dict[str, int] = {}
        for t in tokens:
            if t in self.idf:  # words the knowledge base has never seen carry no signal
                counts[t] = counts.get(t, 0) + 1
        vec = {t: (1 + math.log(c)) * self.idf[t] for t, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values()))
        return {t: v / norm for t, v in vec.items()} if norm else {}

    def search(self, query: str, top_k: int = 3) -> List[Tuple[Dict, float]]:
        """Return up to top_k (document, cosine score) pairs, best first, score > 0 only."""
        qvec = self._vector(tokenize(query))
        scored = []
        for doc, dvec in zip(self.docs, self.vectors):
            score = sum(w * dvec.get(t, 0.0) for t, w in qvec.items())
            if score > 0:
                scored.append((doc, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]
