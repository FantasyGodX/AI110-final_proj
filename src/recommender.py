"""VibeFinder 2.0: a content-based music recommender.

Version 1 scored songs on three things (genre, mood, energy) with exact label
matching. Version 2 keeps that recipe available as the "classic" mode and adds:

* scoring on every numeric feature (valence, danceability, acousticness, tempo)
* partial credit for related genres and moods ("indie pop" is close to "pop")
* named scoring modes so the weights can be swapped without editing code
* a diversity re-ranker that stops one artist or genre from filling the list
* confidence and catalog-coverage notes so weak results are not shown as strong
* input validation for both the catalog and the user's preferences
"""

import csv
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

# The original "Algorithm Recipe" from version 1. Max score is 4.0.
WEIGHTS = {"genre": 2.0, "mood": 1.0, "energy": 1.0}

_FEATURES = ("genre", "mood", "energy", "valence", "danceability", "acousticness", "tempo")

# similar_credit is the fraction of a label's weight a *related* (not identical)
# genre or mood earns. 0 means exact matching only, like version 1.
MODES: Dict[str, Dict[str, float]] = {
    "classic": {**WEIGHTS, "similar_credit": 0.0},
    "balanced": {
        "genre": 1.5, "mood": 1.0, "energy": 1.5,
        "valence": 0.5, "danceability": 0.5, "acousticness": 0.5, "tempo": 0.5,
        "similar_credit": 0.5,
    },
    "genre_first": {
        "genre": 3.0, "mood": 1.0, "energy": 1.0,
        "valence": 0.25, "danceability": 0.25, "acousticness": 0.25, "tempo": 0.25,
        "similar_credit": 0.5,
    },
    "mood_first": {
        "genre": 1.0, "mood": 2.5, "energy": 1.5,
        "valence": 0.5, "danceability": 0.5, "acousticness": 0.5, "tempo": 0.25,
        "similar_credit": 0.5,
    },
    "vibe_first": {
        "genre": 0.5, "mood": 1.0, "energy": 2.0,
        "valence": 1.0, "danceability": 1.0, "acousticness": 1.0, "tempo": 0.5,
        "similar_credit": 0.5,
    },
}

# Related labels. Same family = partial credit when similar_credit > 0.
GENRE_FAMILIES = {
    "pop": "pop", "indie pop": "pop", "k-pop": "pop",
    "edm": "electronic", "synthwave": "electronic",
    "lofi": "downtempo", "ambient": "downtempo",
    "jazz": "refined", "classical": "refined",
    "rock": "heavy", "metal": "heavy",
    "hip hop": "urban", "r&b": "urban",
    "country": "roots", "folk": "roots", "blues": "roots",
    "latin": "island", "reggae": "island",
}
MOOD_FAMILIES = {
    "happy": "upbeat", "joyful": "upbeat", "euphoric": "upbeat", "confident": "upbeat",
    "chill": "calm", "relaxed": "calm", "serene": "calm", "focused": "calm",
    "intense": "dark", "angry": "dark", "moody": "dark",
    "sad": "wistful", "melancholy": "wistful", "nostalgic": "wistful", "romantic": "wistful",
}

TEMPO_RANGE = 60.0  # a 60 BPM gap (or more) earns zero tempo points

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Song:
    """A song and its attributes."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """A user's taste preferences. The last four fields are optional."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    target_valence: Optional[float] = None
    target_danceability: Optional[float] = None
    target_tempo_bpm: Optional[float] = None


# ---------------------------------------------------------------------------
# Loading and validation
# ---------------------------------------------------------------------------

_REQUIRED_COLUMNS = (
    "id", "title", "artist", "genre", "mood",
    "energy", "tempo_bpm", "valence", "danceability", "acousticness",
)


def load_songs(csv_path: str) -> List[Dict]:
    """Read songs.csv into a list of dicts with numeric fields converted.

    Raises ValueError with the row number if a row is malformed, so a bad
    catalog fails loudly instead of silently producing wrong scores.
    """
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in _REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {', '.join(missing)}")
        for line_no, row in enumerate(reader, start=2):
            try:
                row["id"] = int(row["id"])
                row["tempo_bpm"] = float(row["tempo_bpm"])
                for key in ("energy", "valence", "danceability", "acousticness"):
                    row[key] = float(row[key])
                    if not 0.0 <= row[key] <= 1.0:
                        raise ValueError(f"{key} must be between 0 and 1")
            except (TypeError, ValueError) as err:
                raise ValueError(f"{csv_path} line {line_no}: {err}") from err
            row["genre"] = row["genre"].strip().lower()
            row["mood"] = row["mood"].strip().lower()
            songs.append(row)
    return songs


def normalize_prefs(user_prefs: Dict) -> Dict:
    """Validate a preference dict and return a cleaned copy.

    Accepted keys: genre, mood, energy, valence, danceability, acousticness
    (all 0-1), tempo_bpm (40-220) and likes_acoustic (bool). A boolean
    likes_acoustic becomes an acousticness target unless one is given.
    Raises ValueError for anything out of range or an empty profile.
    """
    if not isinstance(user_prefs, dict):
        raise ValueError("preferences must be a dict")
    prefs = dict(user_prefs)
    for key in ("genre", "mood"):
        if prefs.get(key) is not None:
            if not isinstance(prefs[key], str) or not prefs[key].strip():
                raise ValueError(f"{key} must be a non-empty string")
            prefs[key] = prefs[key].strip().lower()
        else:
            prefs.pop(key, None)
    for key in ("energy", "valence", "danceability", "acousticness"):
        if prefs.get(key) is not None:
            if not isinstance(prefs[key], (int, float)) or not 0.0 <= prefs[key] <= 1.0:
                raise ValueError(f"{key} must be a number between 0 and 1")
        else:
            prefs.pop(key, None)
    if prefs.get("tempo_bpm") is not None:
        if not isinstance(prefs["tempo_bpm"], (int, float)) or not 40 <= prefs["tempo_bpm"] <= 220:
            raise ValueError("tempo_bpm must be a number between 40 and 220")
    else:
        prefs.pop("tempo_bpm", None)
    if "likes_acoustic" in prefs and "acousticness" not in prefs:
        prefs["acousticness"] = 0.8 if prefs["likes_acoustic"] else 0.2
    if not any(k in prefs for k in ("genre", "mood", "energy", "valence",
                                    "danceability", "acousticness", "tempo_bpm")):
        raise ValueError("preferences must include at least one taste field")
    return prefs


def resolve_weights(mode="classic", weights: Optional[Dict] = None) -> Dict[str, float]:
    """Return a full weight dict from a mode name and optional overrides."""
    if mode not in MODES:
        raise ValueError(f"unknown mode '{mode}'. Choose from: {', '.join(MODES)}")
    resolved = {name: 0.0 for name in _FEATURES}
    resolved["similar_credit"] = 0.0
    resolved.update(MODES[mode])
    if weights:
        resolved.update(weights)
    return resolved


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

_NUMERIC = (("energy", "energy"), ("valence", "valence"),
            ("danceability", "danceability"), ("acousticness", "acousticness"))


def _label_points(kind: str, families: Dict[str, str], user_val: str, song_val: str,
                  w: Dict[str, float]) -> Tuple[float, Optional[str]]:
    weight = w[kind]
    if weight <= 0:
        return 0.0, None
    if song_val == user_val:
        return weight, f"{kind} match (+{weight:.1f})"
    credit = w["similar_credit"]
    fam = families.get(user_val)
    if credit > 0 and fam is not None and families.get(song_val) == fam:
        pts = weight * credit
        return pts, f"similar {kind} '{song_val}' ~ '{user_val}' (+{pts:.2f})"
    return 0.0, None


def max_score(user_prefs: Dict, mode="classic", weights: Optional[Dict] = None) -> float:
    """Highest score a song could earn for these prefs (only counts scored fields)."""
    w = resolve_weights(mode, weights)
    prefs = user_prefs
    total = 0.0
    for kind in ("genre", "mood"):
        if kind in prefs:
            total += w[kind]
    for pref_key, _ in _NUMERIC:
        if pref_key in prefs:
            total += w[pref_key]
    if "tempo_bpm" in prefs:
        total += w["tempo"]
    return total


def score_song(user_prefs: Dict, song: Dict, mode="classic",
               weights: Optional[Dict] = None) -> Tuple[float, List[str]]:
    """Score one song against user prefs; return (score, list of reasons).

    Only the fields the user supplied are scored. Numeric fields reward
    closeness (1 - gap), never "higher is better".
    """
    w = resolve_weights(mode, weights)
    score = 0.0
    reasons: List[str] = []

    if "genre" in user_prefs:
        pts, why = _label_points("genre", GENRE_FAMILIES, user_prefs["genre"], song["genre"], w)
        score += pts
        if why:
            reasons.append(why)
    if "mood" in user_prefs:
        pts, why = _label_points("mood", MOOD_FAMILIES, user_prefs["mood"], song["mood"], w)
        score += pts
        if why:
            reasons.append(why)

    for pref_key, song_key in _NUMERIC:
        weight = w[pref_key]
        if weight > 0 and pref_key in user_prefs:
            gap = abs(song[song_key] - user_prefs[pref_key])
            pts = weight * (1.0 - gap)
            score += pts
            reasons.append(
                f"{pref_key} {song[song_key]:.2f} vs target {user_prefs[pref_key]:.2f} (+{pts:.2f})")

    if w["tempo"] > 0 and "tempo_bpm" in user_prefs and "tempo_bpm" in song:
        gap = min(abs(song["tempo_bpm"] - user_prefs["tempo_bpm"]), TEMPO_RANGE)
        pts = w["tempo"] * (1.0 - gap / TEMPO_RANGE)
        score += pts
        reasons.append(
            f"tempo {song['tempo_bpm']:.0f} vs target {user_prefs['tempo_bpm']:.0f} BPM (+{pts:.2f})")

    return score, reasons


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5, mode="classic",
                    diversity: float = 0.0, weights: Optional[Dict] = None,
                    ) -> List[Tuple[Dict, float, str]]:
    """Score every song and return the top k as (song, score, explanation).

    diversity is 0 for a plain top-k (version 1 behavior). Above 0, picks are
    made one at a time and each candidate loses points for an artist already
    chosen (diversity * max score) and for a genre already chosen (half that).
    """
    prefs = normalize_prefs(user_prefs)
    scored = []
    for song in songs:
        score, reasons = score_song(prefs, song, mode, weights)
        scored.append((song, score, reasons))

    if diversity <= 0:
        # sorted() is stable and returns a new list, so ties keep catalog order
        ranked = sorted(scored, key=lambda item: item[1], reverse=True)[:k]
        return [(s, sc, "; ".join(r)) for s, sc, r in ranked]

    unit = diversity * max(max_score(prefs, mode, weights), 1e-9)
    pool = list(scored)
    chosen: List[Tuple[Dict, float, str]] = []
    artists: Dict[str, int] = {}
    genres: Dict[str, int] = {}
    while pool and len(chosen) < k:
        best_i, best_adj, best_notes = 0, None, []
        for i, (song, score, _) in enumerate(pool):
            a_n, g_n = artists.get(song["artist"], 0), genres.get(song["genre"], 0)
            penalty = unit * a_n + 0.5 * unit * g_n
            notes = []
            if a_n:
                notes.append(f"artist already picked (-{unit * a_n:.2f})")
            if g_n:
                notes.append(f"genre already picked (-{0.5 * unit * g_n:.2f})")
            adj = score - penalty
            if best_adj is None or adj > best_adj:
                best_i, best_adj, best_notes = i, adj, notes
        song, _, reasons = pool.pop(best_i)
        artists[song["artist"]] = artists.get(song["artist"], 0) + 1
        genres[song["genre"]] = genres.get(song["genre"], 0) + 1
        chosen.append((song, best_adj, "; ".join(reasons + best_notes)))
    return chosen


# ---------------------------------------------------------------------------
# Honesty helpers: confidence and catalog coverage
# ---------------------------------------------------------------------------


def assess_confidence(recs: List[Tuple[Dict, float, str]], user_prefs: Dict,
                      mode="classic", weights: Optional[Dict] = None) -> Tuple[str, float]:
    """Return (label, ratio) where ratio is top score / best possible score.

    high >= 0.75, medium >= 0.50, otherwise low.
    """
    if not recs:
        return "low", 0.0
    prefs = normalize_prefs(user_prefs)
    top = max_score(prefs, mode, weights)
    ratio = recs[0][1] / top if top > 0 else 0.0
    label = "high" if ratio >= 0.75 else "medium" if ratio >= 0.5 else "low"
    return label, ratio


def coverage_notes(user_prefs: Dict, songs: List[Dict]) -> List[str]:
    """Plain-language warnings about labels the catalog cannot satisfy."""
    prefs = normalize_prefs(user_prefs)
    notes = []
    genres = {s["genre"] for s in songs}
    moods = {s["mood"] for s in songs}
    if "genre" in prefs and prefs["genre"] not in genres:
        notes.append(f"genre '{prefs['genre']}' is not in the catalog, so no song can match it exactly")
    if "mood" in prefs and prefs["mood"] not in moods:
        notes.append(f"mood '{prefs['mood']}' is not in the catalog, so no song can match it exactly")
    if "genre" in prefs and prefs["genre"] in genres:
        n = sum(1 for s in songs if s["genre"] == prefs["genre"])
        if n == 1:
            notes.append(f"only 1 '{prefs['genre']}' song exists, so later picks come from other genres")
    return notes


def mismatch_notes(song: Dict, user_prefs: Dict, threshold: float = 0.4) -> List[str]:
    """Warn when a song is far from the user's target on a numeric feature.

    A high overall score can hide one big miss (for example a sad blues song
    that earns genre and mood points but sits 0.5 below the energy target).
    """
    prefs = normalize_prefs(user_prefs)
    notes = []
    for key in ("energy", "valence", "danceability", "acousticness"):
        if key in prefs and abs(song[key] - prefs[key]) > threshold:
            notes.append(f"'{song['title']}' is far from your {key} target "
                         f"({song[key]:.2f} vs {prefs[key]:.2f})")
    return notes


# ---------------------------------------------------------------------------
# Object-oriented wrapper
# ---------------------------------------------------------------------------


class Recommender:
    """Object-oriented wrapper around the scoring logic."""

    def __init__(self, songs: List[Song], mode: str = "classic", diversity: float = 0.0):
        self.songs = songs
        self.mode = mode
        self.diversity = diversity

    @staticmethod
    def _prefs(user: UserProfile) -> Dict:
        """Convert a UserProfile into the dict format score_song expects."""
        prefs = {"genre": user.favorite_genre, "mood": user.favorite_mood,
                 "energy": user.target_energy}
        if user.target_valence is not None:
            prefs["valence"] = user.target_valence
        if user.target_danceability is not None:
            prefs["danceability"] = user.target_danceability
        if user.target_tempo_bpm is not None:
            prefs["tempo_bpm"] = user.target_tempo_bpm
        # Only score acousticness in modes that use it; classic ignores it anyway.
        prefs["likes_acoustic"] = user.likes_acoustic
        return prefs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k Song objects for this user."""
        by_id = {s.id: s for s in self.songs}
        dicts = [s.__dict__ for s in self.songs]
        ranked = recommend_songs(self._prefs(user), dicts, k, self.mode, self.diversity)
        return [by_id[song["id"]] for song, _, _ in ranked]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Explain in plain text why a song scored the way it did."""
        prefs = normalize_prefs(self._prefs(user))
        score, reasons = score_song(prefs, song.__dict__, self.mode)
        return f"Score {score:.2f}: " + "; ".join(reasons)
