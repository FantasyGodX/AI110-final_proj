import json
import logging

import pytest

from src import agent as agent_module
from src.agent import (
    MAX_QUERY_CHARS, build_profile, find_conflict, format_result, load_system, run_agent,
    supporting_docs, validate_query,
)
from src.log_setup import get_logger
from src.retriever import Retriever, load_knowledge_base, stem, tokenize


@pytest.fixture(scope="module")
def system():
    return load_system()


def ids(retriever, query, k=3):
    return [d["id"] for d, _ in retriever.search(query, k)]


# ---- retriever --------------------------------------------------------------

def test_stemmer_lines_up_word_forms():
    assert stem("studying") == stem("study") == stem("studied")
    assert stem("dancing") == stem("dance")
    assert tokenize("lo-fi and k-pop")[:2] == ["lofi", "kpop"]


def test_knowledge_base_loads_all_document_types(system):
    _, docs, _ = system
    types = {d["type"] for d in docs}
    assert types == {"genre", "mood", "scenario"}
    assert len([d for d in docs if d["type"] == "genre"]) == 18


def test_genre_targets_are_computed_from_the_catalog(system):
    songs, docs, _ = system
    metal = next(d for d in docs if d["id"] == "genre:metal")
    metal_songs = [s for s in songs if s["genre"] == "metal"]
    assert metal["targets"]["energy"] == pytest.approx(
        sum(s["energy"] for s in metal_songs) / len(metal_songs), abs=0.01)


@pytest.mark.parametrize("query,expected", [
    ("music to study to", "scenario:study"),
    ("gym workout", "scenario:workout"),
    ("i love reggae", "genre:reggae"),
    ("help me fall asleep", "scenario:sleep"),
    ("i want k-pop", "genre:k-pop"),
])
def test_retriever_finds_expected_document(system, query, expected):
    assert ids(system[2], query)[0] == expected


def test_retriever_returns_nothing_for_unknown_words(system):
    assert system[2].search("asdfgh qwerty zxcv") == []


def test_retriever_scores_are_sorted_and_positive(system):
    hits = system[2].search("relaxing jazz for a rainy dinner", 5)
    scores = [s for _, s in hits]
    assert scores == sorted(scores, reverse=True) and all(s > 0 for s in scores)


def test_empty_retriever_is_rejected():
    with pytest.raises(ValueError):
        Retriever([])


def test_bad_knowledge_base_is_rejected(tmp_path, system):
    songs = system[0]
    bad = tmp_path / "kb.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_knowledge_base(str(bad), songs)
    bad.write_text(json.dumps({"genres": [], "moods": [], "scenarios": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty"):
        load_knowledge_base(str(bad), songs)


# ---- retrieval actually changes the answer ----------------------------------

def test_different_requests_produce_different_profiles(system):
    songs, _, retriever = system
    calm = run_agent("music to study to", songs, retriever)
    loud = run_agent("gym workout music", songs, retriever)
    assert calm.profile["energy"] < 0.4 < 0.8 < loud.profile["energy"]
    calm_titles = {s["title"] for s, _, _ in calm.recs}
    loud_titles = {s["title"] for s, _, _ in loud.recs}
    assert not calm_titles & loud_titles


def test_profile_comes_from_retrieved_documents(system):
    _, docs, _ = system
    study = next(d for d in docs if d["id"] == "scenario:study")
    profile = build_profile([(study, 0.5)], "study")
    assert profile["energy"] == study["targets"]["energy"]
    assert profile["genre"] == "lofi"  # first genre the document lists


def test_explicit_bpm_overrides_retrieved_tempo(system):
    _, docs, _ = system
    study = next(d for d in docs if d["id"] == "scenario:study")
    assert build_profile([(study, 0.5)], "study at 140 bpm")["tempo_bpm"] == 140
    assert build_profile([(study, 0.5)], "study at 999 bpm")["tempo_bpm"] == 75  # out of range, ignored


def test_citations_and_support_are_reported(system):
    songs, docs, retriever = system
    res = run_agent("music to study to", songs, retriever)
    assert res.citations and res.citations[0]["id"] == "scenario:study"
    top = res.recs[0][0]
    assert "Studying" in supporting_docs(top, res.citations, docs)
    assert "Studying" in res.message


# ---- guardrails ---------------------------------------------------------------

@pytest.mark.parametrize("bad", ["", "   ", None, 42, "x" * (MAX_QUERY_CHARS + 1)])
def test_bad_queries_are_rejected_without_crashing(system, bad):
    songs, _, retriever = system
    res = run_agent(bad, songs, retriever)
    assert res.status == "rejected" and res.recs == []
    assert validate_query(bad)


@pytest.mark.parametrize("k", [0, -1, 100, "5", None])
def test_invalid_k_is_rejected(system, k):
    songs, _, retriever = system
    assert run_agent("study music", songs, retriever, k=k).status == "rejected"


def test_unmatched_request_asks_for_clarification(system):
    songs, _, retriever = system
    res = run_agent("asdfgh qwerty zxcv", songs, retriever)
    assert res.status == "needs_clarification" and res.recs == []
    assert "Try describing" in res.message


def test_non_english_request_is_not_guessed(system):
    songs, _, retriever = system
    assert run_agent("música para estudiar", songs, retriever).status == "needs_clarification"


# ---- the check / revise loop ---------------------------------------------------

def test_conflicting_sources_are_detected_and_flagged(system):
    songs, _, retriever = system
    res = run_agent("calm and peaceful but also super high energy workout", songs, retriever)
    assert res.status == "needs_review"
    assert any("conflicting signals" in n for n in res.notes)
    assert any(step.name == "conflict" for step in res.trace)


def test_find_conflict_ignores_weak_sources(system):
    _, docs, _ = system
    by_id = {d["id"]: d for d in docs}
    hits = [(by_id["scenario:study"], 0.5), (by_id["scenario:workout"], 0.1)]
    assert find_conflict(hits) is None          # workout is under half as relevant
    hits[1] = (by_id["scenario:workout"], 0.45)
    assert find_conflict(hits) is not None


def test_agent_revises_when_a_check_fails(system, monkeypatch):
    songs, _, retriever = system
    calls = []
    real = agent_module._check

    def failing_first(recs, profile, mode, k):
        checks, label, ratio, mism = real(recs, profile, mode, k)
        calls.append(mode)
        if len(calls) == 1:
            checks["confidence>=medium"] = False
        return checks, label, ratio, mism

    monkeypatch.setattr(agent_module, "_check", failing_first)
    res = run_agent("music to study to", songs, retriever)
    assert len(calls) >= 2 and calls[0] != calls[1]
    assert any(step.name == "revise" for step in res.trace)


def test_agent_gives_up_gracefully_when_every_attempt_fails(system, monkeypatch):
    songs, _, retriever = system
    real = agent_module._check

    def always_fail(recs, profile, mode, k):
        checks, label, ratio, mism = real(recs, profile, mode, k)
        checks["confidence>=medium"] = False
        return checks, label, ratio, mism

    monkeypatch.setattr(agent_module, "_check", always_fail)
    res = run_agent("music to study to", songs, retriever)
    attempts = [s for s in res.trace if s.name.startswith("attempt")]
    assert len(attempts) == len(agent_module.STRATEGIES)   # bounded: no infinite loop
    assert res.status == "needs_review" and res.recs


def test_max_attempts_is_respected(system):
    songs, _, retriever = system
    res = run_agent("music to study to", songs, retriever, max_attempts=1)
    assert sum(s.name.startswith("attempt") for s in res.trace) == 1


# ---- reliability ----------------------------------------------------------------

def test_same_query_gives_identical_results(system):
    songs, _, retriever = system
    a = run_agent("a rainy day at home", songs, retriever)
    b = run_agent("a rainy day at home", songs, retriever)
    assert [s["id"] for s, _, _ in a.recs] == [s["id"] for s, _, _ in b.recs]
    assert a.profile == b.profile


def test_recommendations_are_unique_and_k_long(system):
    songs, _, retriever = system
    res = run_agent("party with friends", songs, retriever, k=7)
    ids_ = [s["id"] for s, _, _ in res.recs]
    assert len(ids_) == len(set(ids_)) == 7


def test_format_result_mentions_trace_and_status(system):
    songs, docs, retriever = system
    text = format_result(run_agent("gym workout", songs, retriever), docs)
    assert "Agent trace:" in text and "Status:" in text and "supported by retrieved" in text


# ---- logging --------------------------------------------------------------------

def test_agent_steps_are_logged(system, caplog):
    songs, _, retriever = system
    logger = get_logger()
    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="vibefinder"):
            run_agent("gym workout", songs, retriever)
            run_agent("", songs, retriever)
    finally:
        logger.propagate = False
    text = caplog.text
    assert "retrieve |" in text and "profile |" in text and "final |" in text
    assert "rejected query" in text
