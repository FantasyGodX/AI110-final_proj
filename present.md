# Presentation Notes: VibeFinder 2.0

Everything needed to present the project in about 5 to 7 minutes: the story, the changes, their effects, a demo script, and answers to likely questions.

---

## 1. One-sentence pitch

VibeFinder 2.0 is an explainable music recommender that I extended from my earlier Music Recommender Simulation. It scores more of each song, handles "close enough" labels, varies its results, tells the user when it is unsure, and comes with an evaluation that measures whether each change actually helped.

---

## 2. Where I started (VibeFinder 1.0)

- 20-song CSV catalog, content-based filtering (no other users).
- Score = **+2.0** genre match + **+1.0** mood match + **up to +1.0** energy closeness. Max 4.0.
- Printed the top 5 with reasons ("genre match (+2.0)").
- My own model card listed its problems:
  1. Genre dominated: **Gym Hero** (an intense workout song) kept showing up for "happy pop" listeners.
  2. Most genres had one song, so users got one good result and then filler.
  3. Exact-match labels: "indie pop" got nothing for being near "pop".
  4. Tempo, valence, danceability, and acousticness were loaded but never used.
  5. A weak list looked just as confident as a strong one.

**Framing for the talk:** the final project is "I found these five problems in v1, so I fixed them, and then I tested whether the fixes worked."

---

## 3. What I added, and the effect of each change

| # | Change | Why | Effect (measured or observed) |
|---|---|---|---|
| 1 | **Score all features** (valence, danceability, acousticness, tempo) when the user supplies a target | v1 ignored them | "Quiet Acoustic Study" precision@5 went from 0.60 to 0.80. Classic could not use those inputs at all. |
| 2 | **Partial credit for related genres/moods** (families, for example pop / indie pop / k-pop) | Exact matching was too strict | Gym Hero dropped from #3 to #5 for Default Pop/Happy because Rooftop Lights and Seoul Static now earn credit. Downside below. |
| 3 | **Five scoring modes**: classic, balanced, genre_first, mood_first, vibe_first | Weights were hard-coded and the v1 experiment showed they decide the results | Lets a user (or me) change what "good" means without editing code. `classic` reproduces v1 exactly. |
| 4 | **Diversity re-ranking** (penalty for a repeated artist, half for a repeated genre) | One artist or genre could fill the top 5 | Unique genres 3.1 to 3.5 and unique artists 3.8 to 4.2, for a precision cost of 0.02. Every penalty shows up in the explanation. |
| 5 | **Confidence label, coverage notes, mismatch warnings** | v1 presented guesses as confident answers | Unknown genre ("bossa nova") now says so. The sad plus high-energy profile warns that its top pick is 0.52 away from the energy target. |
| 6 | **Catalog 20 to 40 songs** (every genre has at least 2) | Single-song genres caused filler results | The largest single improvement (see section 4). |
| 7 | **Input and catalog validation** | Bad data failed silently | Clear errors with line numbers. Out-of-range prefs are rejected. 10 test cases cover it. |
| 8 | **Evaluation script** (`src/evaluate.py`) with 10 profiles and hand-labelled relevant songs | I wanted evidence, not impressions | Produces the table in section 4. |
| 9 | **Streamlit app** (`app.py`) | Easier to demo and to explore the modes | Sliders, mode picker, diversity slider, confidence badge, and a "Why this song?" expander. |
| 10 | **36 automated tests** (6 from v1 + 30 new) | Make sure v1 behavior survives and the new features work | All pass. |

---

## 4. Results

Precision@5 means: of the 5 recommended songs, what fraction were in my hand-written list of reasonable picks for that profile (averaged across 10 profiles).

| Configuration | Precision@5 | Unique genres in top 5 | Unique artists in top 5 | Profiles flagged low confidence |
|---|---|---|---|---|
| v1 classic, 20 songs | 0.54 | 4.10 | 4.70 | 1 / 10 |
| v1 classic, 40 songs | 0.70 | 3.30 | 4.10 | 1 / 10 |
| balanced | **0.72** | 3.10 | 3.80 | 0 / 10 |
| balanced + diversity | 0.70 | 3.50 | 4.20 | 0 / 10 |
| genre_first | 0.68 | 2.70 | 3.60 | 1 / 10 |
| mood_first | 0.66 | 4.00 | 4.40 | 0 / 10 |
| vibe_first | 0.70 | 3.70 | 4.20 | 0 / 10 |

### The honest takeaway (say this out loud, it is the strongest part of the talk)

- **Going from 20 to 40 songs did most of the work (0.54 to 0.70).** The new scoring on top of that added only **0.02**, which is about two songs across ten profiles, too small to call a win.
- The new scoring mattered in **specific cases**: the Gym Hero fix, the acoustic profile, and the honest warnings.
- **No mode wins everywhere.** For example, "High-Energy Pop" does best in `mood_first` and `vibe_first` (0.60), while "Mid-everything" does best in `balanced` (0.80). That is the same lesson as my v1 weight experiment: the weights are opinions.
- The top-1 pick was correct (in my relevant set) for every configuration, so the differences are in positions 2 to 5.

---

## 5. Things that did not work (be upfront about these)

1. **Family credit over-reaches.** In "Romantic Evening," the "urban" family (hip hop and r&b) let *Concrete Crown* (hip hop, confident) into the top 5 in balanced mode, though it is not romantic.
2. **Partial credit inflates confidence.** The bossa nova profile went from "low" (classic) to "medium" (balanced) partly because related labels now earn points. That is arguably too generous.
3. **High confidence can hide a big miss.** The conflicting profile reads "high (80%)" while its top pick misses the energy target by 0.52. I added the mismatch warning because of this, and it fixes the symptom but not the underlying nature of confidence as a score ratio.
4. **Diversity costs relevance** (about 0.02 precision) in return for variety.
5. **The evaluation is subjective.** I wrote the "relevant songs" sets myself. Ten profiles is small. I set the mode weights before running the evaluation and did not tune them to it, but my choice of profiles could still favor my own design.

---

## 6. Demo script (about 2 minutes)

Run from the project folder.

1. **Show v1 vs v2 on the same profile**
   ```
   python -m src.main --mode classic
   python -m src.main
   ```
   Point at "Default Pop/Happy": Gym Hero is #3 in classic and #5 in balanced. Point at the reasons list: "similar genre 'indie pop' ~ 'pop' (+0.75)".

2. **Show the honesty features**: scroll to "Conflicting: high energy + sad" (mismatch note) and "Unknown genre (bossa nova)" (coverage note and medium confidence).

3. **Show the evidence**
   ```
   python -m src.evaluate --per-profile
   ```
   Show the table and say the "20 vs 40 songs" line first.

4. **Show the app**
   ```
   streamlit run app.py
   ```
   Pick `k-pop` and mood `happy`, move the energy slider, switch the mode from `classic` to `vibe_first`, and open "Why this song?". Then tick "Set tempo" and show the list change.

5. **Show the tests**
   ```
   pytest
   ```
   36 passed.

---

## 7. Design decisions and why

- **Kept `classic` mode** so every v2 change can be compared to v1 under the same code. I checked it reproduces the original scores exactly on the original 20 songs.
- **Only score fields the user provides.** A user who just says "pop, happy, 0.8" is scored on three fields, so the maximum score changes per profile and the output prints `score / best possible`.
- **Closeness, not "higher is better,"** for every numeric feature, so a user who wants 0.4 energy is not rewarded for a 0.95 song.
- **Tempo gap capped at 60 BPM** so one extreme value cannot dominate.
- **Partial credit is half the weight** and **similar-but-not-exact never beats exact** (tested).
- **Diversity as a greedy re-rank** with the penalty written into the explanation, so the system never changes a ranking without saying so.
- **Confidence as a ratio, plus separate warnings,** because one number cannot capture "good total, bad single feature."
- **Hand-labelled relevance** because there is no real listener data in a classroom project, and a clearly stated subjective yardstick is better than none.

---

## 8. How it maps to real recommenders

- v1 and v2 are **content-based**. Spotify and YouTube combine this with **collaborative filtering** (what similar users played, skipped, or replayed), which needs many users.
- My **diversity penalty** is a small version of what real systems do to avoid repetitive feeds.
- My **mode weights** show the central point: whoever sets the weights quietly defines "good."
- My **catalog-size result** matches what real systems face: coverage of the data matters more than clever rules, and tastes that are under-represented in the data get worse recommendations.

---

## 9. Likely questions and answers

**Why is the improvement from your algorithm so small?**
Because most of the v1 problem was data, not logic. I measured it by separating the catalog change from the scoring change. That separation is why I can say it with evidence.

**How do you know the new version is better?**
I compared configurations on 10 profiles against hand-labelled relevant sets. The gains from scoring are small and I say so. The clearest improvements are in specific cases (Gym Hero, acoustic profile) and in the honesty features.

**Isn't labelling the relevant songs yourself biased?**
Yes, and it is the biggest weakness. I wrote the labels before running the scorers and did not tune weights to them, but the next step would be having other people label the songs.

**What does "confidence" mean?**
Top score divided by the best possible score for that profile. It is not a probability. High is 75% or more, medium is 50% to 75%, low is below 50%.

**What happens with bad input?**
Out-of-range preferences (energy 1.5, tempo 500), empty profiles, and unknown modes raise a clear `ValueError`. A malformed CSV row raises an error naming the line number. In the app, the controls cannot produce invalid values.

**Why does partial credit sometimes give a bad result?**
My families are hand-made groupings. "Urban" puts hip hop and r&b together, which is reasonable for genre, but it does not know a song is not romantic. Families are blunt; learned similarity would be better.

**What would you do next?**
Get real listener ratings to replace my labels, grow the catalog beyond 40 songs with non-Western genres, replace hand-made families with similarity learned from audio features, and calibrate confidence against actual ratings.

**What did you learn?**
That separating variables matters. I expected the new rules to be the main improvement, and an honest comparison showed the catalog size was. Also that every improvement had a cost (partial credit raised confidence, diversity reduced precision).

---

## 10. File map

```
app.py                  Streamlit app
data/songs.csv          40-song catalog (20 original + 20 added)
src/recommender.py      scoring, modes, families, diversity, confidence, validation
src/main.py             CLI (--mode, --diversity, --k, --experiment)
src/profiles.py         10 test profiles + hand-labelled relevant songs
src/evaluate.py         configuration comparison and metrics
tests/test_recommender.py   6 tests from v1 (catalog assertion updated to 40)
tests/test_v2.py            30 new tests
README.md               overview, usage, results, limitations
model_card.md           intended use, data, evaluation, bias, reflection
```

### Quick numbers to remember

- 20 to 40 songs, 18 genres, 15 moods
- 5 scoring modes, 7 scorable features
- 10 evaluation profiles
- 36 tests, all passing
- Precision@5: 0.54 (v1, 20 songs) to 0.70 (v1, 40 songs) to 0.72 (balanced)
- Diversity: genres 3.1 to 3.5, artists 3.8 to 4.2, precision minus 0.02
