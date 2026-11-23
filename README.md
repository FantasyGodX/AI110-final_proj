# 🎵 VibeFinder 2.0: Music Recommender

VibeFinder is a small, explainable, content-based music recommender. It reads a 40-song catalog, compares every song to a user's taste profile, and prints the top matches with a plain-language reason for each score.

**Version 1.0** (my earlier project) scored songs on three things: genre, mood, and energy, using exact label matching. I wrote down its weaknesses in its model card. **Version 2.0** is this final project, and it is built to fix those weaknesses and to measure whether the fixes actually helped.

---

## What's new in 2.0

| Weakness found in 1.0 | Change in 2.0 |
|---|---|
| Tempo, valence, danceability, and acousticness were loaded but never scored | All features can now be scored, whenever the user supplies a target for them |
| "indie pop" got zero credit for being close to "pop" | Related genres and moods earn partial credit (genre and mood families) |
| One fixed set of weights, edited by hand in code | Five named scoring modes: `classic`, `balanced`, `genre_first`, `mood_first`, `vibe_first` |
| One artist or genre could fill the whole top 5 | Diversity re-ranker that penalizes repeated artists and genres |
| Weak results were shown with the same confidence as strong ones | Confidence label, catalog-coverage notes, and per-feature mismatch warnings |
| Most genres had one song | Catalog grown from 20 to 40 songs (every genre now has at least 2) |
| Bad CSV rows or out-of-range inputs failed silently | Validation with clear error messages |
| No way to tell if a change helped | `evaluate.py` compares configurations using hand-labelled relevant songs |
| CLI only | Streamlit app (`app.py`) with sliders, mode picker, and a "why this song?" view |

The original recipe is still available as `classic` mode and reproduces every 1.0 score and ranking exactly (checked on the original 20 songs).

---

## How it works

### Scoring

For each song, the score is a weighted sum over the features the user supplied:

- **Genre / mood:** full weight for an exact match; for modes with `similar_credit`, half weight if the labels are in the same family (for example `pop` / `indie pop` / `k-pop`, or `happy` / `joyful` / `euphoric`).
- **Energy, valence, danceability, acousticness:** `weight * (1 - |song - target|)`. Closeness is rewarded, never "higher is better".
- **Tempo:** same idea, with the gap capped at 60 BPM.

| Mode | genre | mood | energy | valence | dance | acoustic | tempo | similar credit |
|---|---|---|---|---|---|---|---|---|
| classic (v1) | 2.0 | 1.0 | 1.0 | 0 | 0 | 0 | 0 | 0 |
| balanced | 1.5 | 1.0 | 1.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| genre_first | 3.0 | 1.0 | 1.0 | 0.25 | 0.25 | 0.25 | 0.25 | 0.5 |
| mood_first | 1.0 | 2.5 | 1.5 | 0.5 | 0.5 | 0.5 | 0.25 | 0.5 |
| vibe_first | 0.5 | 1.0 | 2.0 | 1.0 | 1.0 | 1.0 | 0.5 | 0.5 |

The maximum score depends on which fields the user filled in, so the output always shows `score / best possible`.

### Ranking and diversity

The scoring rule judges one song; the ranking rule runs it over the whole catalog and keeps the top K. With diversity above 0, songs are picked one at a time and each candidate loses `diversity × max score` for every artist already chosen and half that for every genre already chosen. Every penalty is printed in the explanation.

### Honesty features

- **Confidence:** top score divided by best possible score. High is 75% or more, medium is 50% or more, low is below that.
- **Coverage notes:** warns when the requested genre or mood is not in the catalog, or has only one song.
- **Mismatch notes:** warns when the top pick is far (more than 0.4) from a numeric target, even if its total score is high.

### Data flow

```
User prefs (genre, mood, energy, optional valence / danceability / acoustic / tempo)
        |  validate + normalize
        v
For each song in songs.csv:  score_song(mode) -> (score, reasons)
        |
        v
Rank by score  ->  optional diversity re-ranking
        |
        v
Top K + confidence + coverage + mismatch notes
```

---

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (source .venv/bin/activate on Mac/Linux)
pip install -r requirements.txt
```

| Task | Command |
|---|---|
| Run all 10 profiles (balanced + diversity) | `python -m src.main` |
| Reproduce the 1.0 behavior | `python -m src.main --mode classic` |
| Try another mode | `python -m src.main --mode vibe_first --diversity 0.1` |
| 1.0 weight-shift experiment | `python -m src.main --experiment` |
| Compare configurations | `python -m src.evaluate --per-profile` |
| Launch the web app | `streamlit run app.py` |
| Run tests (36) | `pytest` |

---

## Evaluation

I wrote down, by hand and before running the scorers, which songs would be reasonable recommendations for each of 10 profiles (`src/profiles.py`). Then I measured each configuration against those sets.

| Configuration | Precision@5 | Top-1 hit | Unique genres | Unique artists | Low-confidence profiles |
|---|---|---|---|---|---|
| v1 classic, 20 songs | 0.54 | 1.00 | 4.10 | 4.70 | 1 / 10 |
| v1 classic, 40 songs | 0.70 | 1.00 | 3.30 | 4.10 | 1 / 10 |
| balanced | **0.72** | 1.00 | 3.10 | 3.80 | 0 / 10 |
| balanced + diversity | 0.70 | 1.00 | 3.50 | 4.20 | 0 / 10 |
| genre_first | 0.68 | 1.00 | 2.70 | 3.60 | 1 / 10 |
| mood_first | 0.66 | 1.00 | 4.00 | 4.40 | 0 / 10 |
| vibe_first | 0.70 | 1.00 | 3.70 | 4.20 | 0 / 10 |

What the numbers say:

- **Most of the gain came from the catalog, not the algorithm.** Going from 20 to 40 songs moved precision from 0.54 to 0.70. The new scoring added only 0.02 on top, which is within what 10 profiles can resolve.
- **The new features helped where the user supplied them.** "Quiet Acoustic Study" rose from 0.60 to 0.80 once acousticness and tempo could be scored. Version 1 could not use those inputs at all.
- **Diversity is a trade.** It raised unique genres from 3.1 to 3.5 and unique artists from 3.8 to 4.2, and cost 0.02 precision.
- **Top-1 hit is 1.00 for every configuration**, so it cannot tell them apart. The differences are in positions 2 to 5.

Because the relevant sets are my own opinion and only 10 profiles were used, treat the small differences as suggestive, not proven.

### Sample output (balanced + diversity)

```
Profile: Conflicting: high energy + sad  {'genre': 'blues', 'mood': 'sad', 'energy': 0.9}
1. Blue Monday Groove by The Brass Notes  [blues/sad]
   Score: 3.22 / 4.00
     - genre match (+1.5)
     - mood match (+1.0)
     - energy 0.38 vs target 0.90 (+0.72)
2. Static Heart by Hollow Verse  [rock/sad]
   Score: 2.44 / 4.00
     - mood match (+1.0)
     - energy 0.86 vs target 0.90 (+1.44)
...
Confidence: high (80% of the best possible score)
Note: top pick 'Blue Monday Groove' is far from your energy target (0.38 vs 0.90)
```

```
Profile: Unknown genre (bossa nova)  {'genre': 'bossa nova', 'mood': 'relaxed', 'energy': 0.4}
1. Coffee Shop Stories by Slow Stereo  [jazz/relaxed]
...
Confidence: medium (61% of the best possible score)
Note: genre 'bossa nova' is not in the catalog, so no song can match it exactly
```

---

## Limitations and risks

- **The catalog is still small and invented.** Forty songs with hand-picked labels reflect my opinions, not real listeners.
- **Family credit can overreach.** For "Romantic Evening" (r&b), partial credit for the "urban" genre family let a hip-hop song into the top 5 even though it is not romantic.
- **Partial credit raises confidence.** The bossa nova profile moved from "low" to "medium" confidence in balanced mode partly because related labels now earn points. That is arguably generous.
- **Confidence is relative to the best possible score**, not a probability. A high confidence can still hide a big miss, which is why the mismatch warning exists.
- **Weights are my opinion.** The mode tables were set by judgment, not learned from data.
- **No listening history and no other users.** It cannot learn from skips or replays.
- **Genre popularity is not modeled**, and the catalog is not balanced across cultures or languages.

---

## Project files

```
app.py                  Streamlit app
data/songs.csv          40-song catalog
src/recommender.py      scoring, modes, diversity, confidence, validation
src/main.py             CLI runner
src/profiles.py         10 test profiles + hand-labelled relevant songs
src/evaluate.py         configuration comparison
tests/                  36 tests (v1 behavior preserved + all v2 features)
model_card.md           intended use, data, evaluation, bias, reflection
present.md              presentation notes
```

See the [Model Card](model_card.md) for the full write-up.
