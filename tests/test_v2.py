import pytest

from src.evaluate import evaluate_config, run
from src.profiles import PROFILES, RELEVANT
from src.recommender import (
    MODES, Recommender, Song, UserProfile, assess_confidence, coverage_notes,
    load_songs, max_score, mismatch_notes, normalize_prefs, recommend_songs, score_song,
)


@pytest.fixture(scope="module")
def songs():
    return load_songs("data/songs.csv")


def song(**kw):
    base = {"id": 1, "title": "T", "artist": "A", "genre": "pop", "mood": "happy",
            "energy": 0.8, "tempo_bpm": 120.0, "valence": 0.8, "danceability": 0.8,
            "acousticness": 0.2}
    base.update(kw)
    return base


# ---- catalog and validation -------------------------------------------------

def test_catalog_has_unique_ids_and_all_profiles_have_labels(songs):
    assert len({s["id"] for s in songs}) == len(songs) == 40
    assert set(PROFILES) == set(RELEVANT)
    titles = {s["title"] for s in songs}
    for name, rel in RELEVANT.items():
        assert rel <= titles, f"{name} lists a title that is not in the catalog"


def test_load_songs_rejects_bad_rows(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n"
                   "1,A,B,pop,happy,1.7,100,0.5,0.5,0.5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_songs(str(bad))


def test_load_songs_rejects_missing_columns(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("id,title\n1,A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        load_songs(str(bad))


@pytest.mark.parametrize("prefs", [
    {}, {"energy": 1.5}, {"energy": -0.1}, {"genre": ""}, {"tempo_bpm": 500}, {"valence": "high"},
])
def test_normalize_prefs_rejects_bad_input(prefs):
    with pytest.raises(ValueError):
        normalize_prefs(prefs)


def test_normalize_prefs_cleans_labels_and_maps_acoustic():
    p = normalize_prefs({"genre": "  Pop ", "mood": "HAPPY", "likes_acoustic": True})
    assert p["genre"] == "pop" and p["mood"] == "happy" and p["acousticness"] == 0.8


def test_unknown_mode_raises():
    with pytest.raises(ValueError, match="unknown mode"):
        score_song({"genre": "pop"}, song(), mode="nope")


# ---- scoring ----------------------------------------------------------------

def test_classic_mode_matches_version_1_scores(songs):
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}
    recs = recommend_songs(prefs, songs, k=1)
    assert recs[0][0]["title"] == "Sunrise City"
    assert recs[0][1] == pytest.approx(2.0 + 1.0 + (1 - 0.02))


def test_classic_ignores_extra_features():
    a, _ = score_song({"genre": "pop", "energy": 0.8}, song())
    b, _ = score_song({"genre": "pop", "energy": 0.8, "valence": 0.0}, song())
    assert a == b


def test_similar_genre_earns_partial_credit_only_in_v2_modes():
    prefs = {"genre": "pop"}
    s = song(genre="indie pop")
    assert score_song(prefs, s, "classic")[0] == 0.0
    pts, reasons = score_song(prefs, s, "balanced")
    assert pts == pytest.approx(MODES["balanced"]["genre"] * MODES["balanced"]["similar_credit"])
    assert "similar genre" in reasons[0]


def test_exact_match_beats_similar_match():
    prefs = {"genre": "pop", "mood": "happy"}
    exact, _ = score_song(prefs, song(), "balanced")
    similar, _ = score_song(prefs, song(genre="indie pop", mood="joyful"), "balanced")
    assert exact > similar > 0


def test_numeric_features_reward_closeness():
    prefs = {"valence": 0.2}
    low, _ = score_song(prefs, song(valence=0.25), "vibe_first")
    high, _ = score_song(prefs, song(valence=0.95), "vibe_first")
    assert low > high


def test_tempo_gap_is_capped():
    prefs = {"tempo_bpm": 60}
    far, _ = score_song(prefs, song(tempo_bpm=200.0), "balanced")
    farther, _ = score_song(prefs, song(tempo_bpm=215.0), "balanced")
    assert far == farther == 0.0


def test_max_score_counts_only_supplied_fields():
    assert max_score({"genre": "pop", "mood": "happy", "energy": 0.5}) == 4.0
    assert max_score({"genre": "pop"}, "balanced") == MODES["balanced"]["genre"]


def test_weight_override_changes_ranking(songs):
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}
    base = [s["title"] for s, _, _ in recommend_songs(prefs, songs, 3)]
    shifted = [s["title"] for s, _, _ in
               recommend_songs(prefs, songs, 3, weights={"genre": 1.0, "energy": 2.0})]
    assert base != shifted


# ---- diversity --------------------------------------------------------------

def test_diversity_zero_equals_plain_sort(songs):
    prefs = PROFILES["Default Pop/Happy"]
    plain = recommend_songs(prefs, songs, 5, "balanced", 0.0)
    scores = [r[1] for r in plain]
    assert scores == sorted(scores, reverse=True)


def test_diversity_reduces_repeated_artists():
    catalog = [song(id=i, title=f"T{i}", artist="Same", energy=0.8) for i in range(3)]
    catalog.append(song(id=9, title="Other", artist="Different", energy=0.7))
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}
    plain = [s["artist"] for s, _, _ in recommend_songs(prefs, catalog, 2, "balanced", 0.0)]
    varied = [s["artist"] for s, _, _ in recommend_songs(prefs, catalog, 2, "balanced", 0.3)]
    assert plain == ["Same", "Same"]
    assert set(varied) == {"Same", "Different"}


def test_diversity_never_returns_duplicates_or_more_than_k(songs):
    recs = recommend_songs(PROFILES["Chill Lofi"], songs, 5, "balanced", 0.2)
    ids = [s["id"] for s, _, _ in recs]
    assert len(ids) == len(set(ids)) == 5


def test_k_larger_than_catalog_is_safe(songs):
    assert len(recommend_songs(PROFILES["Chill Lofi"], songs[:3], 10, "balanced", 0.1)) == 3


# ---- honesty helpers --------------------------------------------------------

def test_confidence_is_low_when_nothing_matches():
    catalog = [song(genre="metal", mood="angry", energy=0.1)]
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.95}
    recs = recommend_songs(prefs, catalog, 1, "balanced")
    label, ratio = assess_confidence(recs, prefs, "balanced")
    assert label == "low" and ratio < 0.5


def test_confidence_high_for_perfect_match(songs):
    prefs = PROFILES["Chill Lofi"]
    recs = recommend_songs(prefs, songs, 5, "balanced")
    assert assess_confidence(recs, prefs, "balanced")[0] == "high"


def test_coverage_notes_flag_unknown_and_single_song_genres(songs):
    assert any("not in the catalog" in n for n in coverage_notes({"genre": "bossa nova"}, songs))
    assert not coverage_notes({"genre": "folk", "mood": "relaxed"}, songs)
    tiny = [song(genre="polka")]
    assert any("only 1" in n for n in coverage_notes({"genre": "polka"}, tiny))


def test_mismatch_notes_flags_big_energy_gap(songs):
    blues = next(s for s in songs if s["title"] == "Blue Monday Groove")
    assert mismatch_notes(blues, {"energy": 0.9})
    assert not mismatch_notes(blues, {"energy": 0.4})


# ---- OO wrapper and evaluation ---------------------------------------------

def test_recommender_wrapper_uses_mode_and_extras():
    songs_ = [
        Song(1, "Calm", "A", "ambient", "focused", 0.3, 70, 0.5, 0.3, 0.95),
        Song(2, "Loud", "B", "ambient", "focused", 0.3, 170, 0.5, 0.3, 0.05),
    ]
    user = UserProfile("ambient", "focused", 0.3, likes_acoustic=True, target_tempo_bpm=70)
    rec = Recommender(songs_, mode="balanced")
    assert rec.recommend(user, k=1)[0].title == "Calm"
    assert rec.explain_recommendation(user, songs_[0]).startswith("Score ")


def test_evaluate_returns_metrics_in_range(songs):
    m = evaluate_config(songs, "balanced", 0.05)
    assert 0 <= m["p@5"] <= 1 and 0 <= m["top1"] <= 1
    assert 1 <= m["genres"] <= 5 and 1 <= m["artists"] <= 5


def test_full_evaluation_runs():
    rows = run()
    assert rows[0][0].startswith("v1 classic")
