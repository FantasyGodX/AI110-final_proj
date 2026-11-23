"""Agentic workflow: turn a plain-language request into recommendations.

    python -m src.agent "something calm to study to late at night"

The agent runs a plan -> retrieve -> act -> check -> revise loop:

1. GUARD     reject empty, oversized or non-text input (never crash).
2. RETRIEVE  search the knowledge base; if nothing relevant is found, stop and
             ask for clarification instead of guessing.
3. PROFILE   build the taste profile *from the retrieved documents*: genre and
             mood come from their votes, numeric targets are score-weighted
             averages of their targets. Retrieval therefore decides the result.
4. ACT       score the catalog with the recommender.
5. CHECK     confidence is at least medium, the top pick has no big feature
             mismatch, and no artist repeats.
6. REVISE    if a check fails, try the next strategy (different mode, more
             diversity, dropping an over-confident genre guess). Keep the best
             attempt. Every step is logged and returned in the trace.
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.log_setup import get_logger
from src.recommender import (
    assess_confidence, coverage_notes, load_songs, max_score, mismatch_notes,
    recommend_songs,
)
from src.retriever import Retriever, load_knowledge_base

log = get_logger()

MAX_QUERY_CHARS = 300
MAX_K = 20
CONFLICT_SPREAD = 0.45    # retrieved sources whose energy targets differ by more than this disagree
CONFLICT_RELEVANCE = 0.5  # only sources at least this fraction as relevant as the best one are compared
MIN_DOC_SCORE = 0.15      # below this a retrieved document is treated as noise
TOP_DOCS = 3              # how many documents shape the profile
SCENARIO_BOOST = 1.5      # scenarios encode intent, so they count a little more
_BPM = re.compile(r"\b(\d{2,3})\s*bpm\b")

# (mode, diversity, keep the genre guess?)  Tried in order until the checks pass.
# The first attempt originally used diversity 0.05, but the artist-repeat check failed on 17 of
# 20 evaluation queries, so "revision" was only a diversity bump. 0.10 fixes the starting point.
STRATEGIES = [
    ("balanced", 0.10, True),
    ("vibe_first", 0.15, True),
    ("mood_first", 0.15, False),
]


@dataclass
class Step:
    name: str
    detail: str


@dataclass
class AgentResult:
    query: str
    status: str                       # ok | needs_review | needs_clarification | rejected
    message: str
    profile: Dict = field(default_factory=dict)
    recs: List[Tuple[Dict, float, str]] = field(default_factory=list)
    citations: List[Dict] = field(default_factory=list)
    trace: List[Step] = field(default_factory=list)
    confidence: str = "n/a"
    ratio: float = 0.0
    notes: List[str] = field(default_factory=list)
    mode: str = ""
    max_score: float = 0.0


def validate_query(query) -> Optional[str]:
    """Return a reason string if the query must be rejected, else None."""
    if not isinstance(query, str):
        return "the request must be text"
    if not query.strip():
        return "the request is empty; describe what you want to listen to"
    if len(query) > MAX_QUERY_CHARS:
        return f"the request is too long ({len(query)} characters; the limit is {MAX_QUERY_CHARS})"
    return None


def build_profile(hits: List[Tuple[Dict, float]], query: str) -> Dict:
    """Combine retrieved documents into a preference dict for the recommender."""
    weights = [(doc, score * (SCENARIO_BOOST if doc["type"] == "scenario" else 1.0))
               for doc, score in hits]
    votes = {"genre": {}, "mood": {}}
    for doc, w in weights:
        for kind, labels in (("genre", doc["genres"]), ("mood", doc["moods"])):
            n = len(labels)
            for i, label in enumerate(labels):
                # the first label a document lists counts the most
                share = (n - i) / (n * (n + 1) / 2)
                votes[kind][label] = votes[kind].get(label, 0.0) + w * share

    profile: Dict = {}
    for kind in ("genre", "mood"):
        if votes[kind]:
            profile[kind] = max(votes[kind].items(), key=lambda kv: (kv[1], kv[0]))[0]

    for key in ("energy", "valence", "danceability", "acousticness", "tempo_bpm"):
        pairs = [(doc["targets"][key], w) for doc, w in weights if key in doc["targets"]]
        if pairs:
            total = sum(w for _, w in pairs)
            value = sum(v * w for v, w in pairs) / total
            profile[key] = round(value) if key == "tempo_bpm" else round(value, 2)

    match = _BPM.search(query.lower())  # an explicit "120 bpm" overrides the retrieved tempo
    if match and 40 <= int(match.group(1)) <= 220:
        profile["tempo_bpm"] = int(match.group(1))
    return profile


def find_conflict(hits: List[Tuple[Dict, float]]) -> Optional[str]:
    """Describe a disagreement between the strongest retrieved sources, if any.

    Averaging "calm" and "workout" targets would give a middle-of-the-road profile
    that satisfies neither, so the agent detects this instead of hiding it.
    """
    if len(hits) < 2:
        return None
    top = hits[0][1]
    strong = [(d, s) for d, s in hits if s >= CONFLICT_RELEVANCE * top and "energy" in d["targets"]]
    if len(strong) < 2:
        return None
    energies = [(d["targets"]["energy"], d["title"]) for d, _ in strong]
    lo, hi = min(energies), max(energies)
    if hi[0] - lo[0] > CONFLICT_SPREAD:
        return (f"the request mixes conflicting signals: '{lo[1]}' targets energy {lo[0]:.2f} "
                f"but '{hi[1]}' targets {hi[0]:.2f}")
    return None


def _check(recs, profile, mode, k) -> Tuple[Dict[str, bool], str, float, List[str]]:
    label, ratio = assess_confidence(recs, profile, mode)
    mism = mismatch_notes(recs[0][0], profile) if recs else ["no songs returned"]
    artists = [s["artist"] for s, _, _ in recs]
    checks = {
        "confidence>=medium": label in ("high", "medium"),
        "no big mismatch": not mism,
        "no repeated artist": len(artists) == len(set(artists)),
        "returned k songs": len(recs) == k,
    }
    return checks, label, ratio, mism


def run_agent(query, songs: List[Dict], retriever: Retriever, k: int = 5,
              max_attempts: int = len(STRATEGIES)) -> AgentResult:
    """Run the full workflow. Never raises for bad user input; returns a status."""
    trace: List[Step] = []

    def note(name: str, detail: str) -> None:
        trace.append(Step(name, detail))
        log.info("%s | %s", name, detail)

    reason = validate_query(query)
    if not reason and not (isinstance(k, int) and 1 <= k <= MAX_K):
        reason = f"the number of songs must be a whole number from 1 to {MAX_K}"
    if reason:
        log.warning("rejected query: %s", reason)
        return AgentResult(str(query)[:60], "rejected", f"Request rejected: {reason}.",
                           trace=[Step("guard", f"rejected: {reason}")])
    query = " ".join(query.split())
    note("guard", f"accepted query ({len(query)} chars): {query!r}")

    hits = [(d, s) for d, s in retriever.search(query, TOP_DOCS) if s >= MIN_DOC_SCORE]
    if not hits:
        note("retrieve", "no document scored above the relevance threshold")
        log.warning("no relevant knowledge for query %r", query)
        return AgentResult(query, "needs_clarification",
                           "I could not match that to any genre, mood, or listening situation. "
                           "Try describing an activity (studying, workout, road trip), a mood "
                           "(sad, happy, calm), or a genre (jazz, lofi, k-pop).",
                           trace=trace)
    note("retrieve", "; ".join(f"{d['id']} ({s:.2f})" for d, s in hits))

    conflict = find_conflict(hits)
    if conflict:
        note("conflict", f"{conflict}; using only the best match '{hits[0][0]['title']}'")
        log.warning("conflicting retrieval for query %r: %s", query, conflict)
        profile_hits = hits[:1]
    else:
        profile_hits = hits
    base = build_profile(profile_hits, query)
    note("profile", f"built from retrieved documents: {base}")

    attempts = []
    for n, (mode, diversity, keep_genre) in enumerate(STRATEGIES[:max_attempts], 1):
        profile = dict(base)
        if not keep_genre:
            profile.pop("genre", None)
        recs = recommend_songs(profile, songs, k, mode, diversity)
        checks, label, ratio, mism = _check(recs, profile, mode, k)
        failed = [name for name, ok in checks.items() if not ok]
        note(f"attempt {n}", f"mode={mode} diversity={diversity} genre={'kept' if keep_genre else 'dropped'} "
                             f"-> confidence {label} ({ratio:.0%}); "
                             f"{'all checks passed' if not failed else 'failed: ' + ', '.join(failed)}")
        attempts.append((len(checks) - len(failed), ratio, n, mode, profile, recs, label, mism, failed))
        if not failed:
            break
        note("revise", f"trying a different strategy because: {', '.join(failed)}")

    best = max(attempts, key=lambda a: (a[0], a[1]))
    passed, ratio, n, mode, profile, recs, label, mism, failed = best
    status = "ok" if not failed and not conflict else "needs_review"
    note("final", f"chose attempt {n} ({mode}); status={status}")
    if failed:
        log.warning("best attempt still failed checks %s for query %r", failed, query)

    notes = coverage_notes(profile, songs) + [f"top pick {m}" for m in mism]
    if conflict:
        notes.insert(0, f"{conflict}; I followed '{hits[0][0]['title']}' and ignored the rest")
    return AgentResult(
        query=query, status=status,
        message=explain(query, hits, profile, recs, label, ratio, status),
        profile=profile, recs=recs,
        citations=[{"id": d["id"], "title": d["title"], "type": d["type"],
                    "score": round(s, 2), "text": d["text"]} for d, s in hits],
        trace=trace, confidence=label, ratio=ratio, notes=notes, mode=mode,
        max_score=max_score(profile, mode),
    )


def explain(query, hits, profile, recs, label, ratio, status) -> str:
    """Write the answer in plain language, citing the retrieved documents."""
    sources = ", ".join(f"'{d['title']}' ({d['type']})" for d, _ in hits)
    parts = [f"For \"{query}\" I retrieved {sources}."]
    shaped = []
    if "genre" in profile:
        shaped.append(f"genre '{profile['genre']}'")
    if "mood" in profile:
        shaped.append(f"mood '{profile['mood']}'")
    if "energy" in profile:
        shaped.append(f"energy around {profile['energy']:.2f}")
    if "tempo_bpm" in profile:
        shaped.append(f"tempo near {profile['tempo_bpm']} BPM")
    if shaped:
        parts.append("From that I aimed for " + ", ".join(shaped) + ".")
    if recs:
        parts.append(f"My top pick is '{recs[0][0]['title']}' by {recs[0][0]['artist']}.")
    parts.append(f"Confidence: {label} ({ratio:.0%}).")
    if status == "needs_review":
        parts.append("My own checks flagged this result (see the notes), so please review it before trusting it.")
    return " ".join(parts)


def supporting_docs(song: Dict, citations: List[Dict], kb_docs: List[Dict]) -> List[str]:
    """Titles of retrieved documents that mention this song's genre or mood."""
    by_id = {d["id"]: d for d in kb_docs}
    titles = []
    for c in citations:
        doc = by_id[c["id"]]
        if song["genre"] in doc["genres"] or song["mood"] in doc["moods"]:
            titles.append(doc["title"])
    return titles


def load_system(catalog: str = "data/songs.csv", kb_path: str = "data/knowledge_base.json"):
    """Load the catalog, knowledge base and retriever once."""
    songs = load_songs(catalog)
    docs = load_knowledge_base(kb_path, songs)
    return songs, docs, Retriever(docs)


def format_result(result: AgentResult, docs: List[Dict], show_trace: bool = True) -> str:
    lines = [f"Query: {result.query}", f"Status: {result.status}", result.message]
    if show_trace and result.trace:
        lines += ["", "Agent trace:"] + [f"  [{s.name}] {s.detail}" for s in result.trace]
    if result.recs:
        lines += ["", "Recommendations:"]
        for rank, (song, score, why) in enumerate(result.recs, 1):
            lines.append(f"{rank}. {song['title']} by {song['artist']}  "
                         f"[{song['genre']}/{song['mood']}]  score {score:.2f} / {result.max_score:.2f}")
            support = supporting_docs(song, result.citations, docs)
            if support:
                lines.append(f"     supported by retrieved: {', '.join(support)}")
            lines.append(f"     {why.replace('; ', ' | ')}")
    for n in result.notes:
        lines.append(f"Note: {n}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Ask VibeFinder in plain language")
    parser.add_argument("query", nargs="?", default=None, help="what you want to listen to")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--no-trace", action="store_true", help="hide the agent trace")
    args = parser.parse_args(argv)

    try:
        songs, docs, retriever = load_system()
    except (OSError, ValueError) as err:
        log.error("could not load data: %s", err)
        print(f"Could not start: {err}", file=sys.stderr)
        return 1

    query = args.query
    if query is None:
        query = input("What do you want to listen to? ")
    result = run_agent(query, songs, retriever, args.k)
    print(format_result(result, docs, show_trace=not args.no_trace))
    return 0 if result.status in ("ok", "needs_review") else 2


if __name__ == "__main__":
    sys.exit(main())
