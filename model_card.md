# 🎧 Model Card: VibeFinder 2.0

## 1. Model Name

**VibeFinder 2.0** (extends VibeFinder 1.0)

---

## 2. Goal / Intended Use

VibeFinder suggests the top songs from a small catalog that best match a user's favorite genre, favorite mood, target energy, and optionally valence, danceability, acoustic preference, and tempo. It explains each pick in plain words and warns when its own answer is weak.

It assumes the user can describe their taste with a few labels and numbers. It is built for classroom exploration and as a demonstration of how scoring rules shape recommendations. It is **not** meant for real users or a real music app.

**Not intended for:** making decisions about real people, replacing a streaming service, judging what music is "good", or any use where a wrong suggestion could cause harm.

---

## 3. How the Model Works

Every song earns points; the songs with the most points win.

- **Genre and mood:** full weight for an exact match. In every mode except `classic`, a related label in the same family (for example `pop` and `k-pop`, or `sad` and `melancholy`) earns half the weight.
- **Energy, valence, danceability, acousticness:** the closer the song is to the target, the more points. Higher is never automatically better.
- **Tempo:** same idea, with the gap capped at 60 BPM.
- **Only fields the user supplies are scored**, so a profile with just genre, mood, and energy is scored on three things.

Five modes set the weights: `classic` (the 1.0 recipe), `balanced` (default), `genre_first`, `mood_first`, and `vibe_first`.

After scoring, an optional diversity step picks songs one at a time and subtracts points for an artist or genre that has already been chosen.

Finally, the system reports a **confidence** level (top score divided by the best possible score), **coverage notes** (the genre or mood is missing from the catalog), and **mismatch notes** (the top pick is far from a numeric target).

### What changed from 1.0

1. Scores all numeric features instead of only energy.
2. Adds partial credit for related genres and moods.
3. Adds modes, diversity re-ranking, confidence, coverage, and mismatch notes.
4. Adds input validation for the catalog and for user preferences.
5. Doubles the catalog and adds an evaluation script.

---

## 4. Data

- **40 songs** in `data/songs.csv`. Version 1 had 20; I added 20 more, so every genre now has at least two songs.
- **Genres (18):** pop, indie pop, k-pop, lofi, rock, ambient, jazz, synthwave, r&b, country, hip hop, edm, classical, metal, latin, folk, blues, reggae.
- **Moods (15):** happy, chill, intense, relaxed, moody, focused, romantic, nostalgic, confident, euphoric, serene, angry, joyful, melancholy, sad.
- **Numbers per song:** energy, valence, danceability, acousticness (0 to 1) and tempo in BPM.
- **Families:** the genre and mood families used for partial credit are my own groupings (for example, `country`, `folk`, and `blues` are "roots"). They are a judgment call, not a standard taxonomy.
- **Missing:** lyrics, language, artist popularity, release year, and anything about real listener behavior. All songs and artists are invented, and the labels were assigned by hand.

---

## 5. Strengths

- It works well when the user's taste is well covered by the catalog. "Chill Lofi" reaches precision@5 of 1.00 in the balanced mode.
- Supplying extra features actually changes results. "Quiet Acoustic Study" improved from 0.60 to 0.80 precision@5 when acousticness and tempo were scored.
- The Gym Hero problem from 1.0 is reduced. For "Default Pop/Happy", Gym Hero (an intense workout song) moved from #3 to #5 because related happy songs (Rooftop Lights, Seoul Static) now earn partial genre credit.
- The "conflicting" profile (sad, high energy, blues) now surfaces `Static Heart`, a sad rock song at 0.86 energy, as its #2 pick instead of a second quiet blues song.
- Every score comes with its reasons, so any result can be checked by hand.
- It tells the user when it is guessing (unknown genre) or when the top pick misses a target by a lot.

---

## 6. Limitations and Bias

- **Catalog size beat algorithm design.** In my evaluation, doubling the catalog improved precision@5 from 0.54 to 0.70, but all the new scoring added only 0.02. The most important fix for 1.0 was more data, not smarter rules.
- **Family credit over-reaches.** In "Romantic Evening," the "urban" genre family let `Concrete Crown` (hip hop, confident) reach the top 5 in balanced mode, though it is not a romantic song. Families are blunt tools.
- **Partial credit can inflate confidence.** The bossa nova profile went from "low" confidence in classic mode to "medium" in balanced mode partly because related labels now earn points.
- **Confidence is not a probability.** It is a ratio against the best possible score. The conflicting profile reads "high (80%)" even though the top pick's energy is 0.52 away from the target. The separate mismatch warning exists for this reason.
- **Diversity costs relevance.** It improved variety (unique genres 3.1 to 3.5) but lowered precision@5 by 0.02, and it can push a relevant song out for a less relevant one from a new artist.
- **The weights are my opinion.** Whoever chooses the weights decides what a "good" recommendation is. `genre_first` produced the least varied lists (2.7 unique genres) and `mood_first` the most (4.0).
- **Under-represented tastes get worse results.** The catalog is built around Western-style genre labels and English-language titles. Someone who likes music outside those labels has to pick the nearest one.
- **No personalization over time.** No listening history, skips, or other users.

---

## 7. Evaluation

**Method.** Ten profiles (src/profiles.py): four standard (pop/happy, high-energy pop, chill lofi, intense rock), three that use the extra features (acoustic study, workout EDM, romantic evening), and three edge cases (sad plus high energy, a genre not in the catalog, and a profile with mixed targets). For each profile I wrote a set of songs I would consider reasonable picks *before* running the scorers. Each configuration returns a top 5, and I measured precision@5, whether the #1 pick is in the set, the number of unique genres and artists in the list, and how many profiles were flagged low confidence.

| Configuration | P@5 | Top-1 | Genres | Artists | Low-conf |
|---|---|---|---|---|---|
| v1 classic, 20 songs | 0.54 | 1.00 | 4.10 | 4.70 | 1 / 10 |
| v1 classic, 40 songs | 0.70 | 1.00 | 3.30 | 4.10 | 1 / 10 |
| balanced | 0.72 | 1.00 | 3.10 | 3.80 | 0 / 10 |
| balanced + diversity | 0.70 | 1.00 | 3.50 | 4.20 | 0 / 10 |
| genre_first | 0.68 | 1.00 | 2.70 | 3.60 | 1 / 10 |
| mood_first | 0.66 | 1.00 | 4.00 | 4.40 | 0 / 10 |
| vibe_first | 0.70 | 1.00 | 3.70 | 4.20 | 0 / 10 |

**Reading the table**

- The 20-to-40-song jump is the biggest effect. The gap between `balanced` and `v1 classic, 40 songs` is 0.02, which is two songs across ten profiles, too small to call a real win.
- Top-1 hit is 1.00 for all rows, so the first pick was never the problem. Improvements show up in positions 2 to 5.
- No mode wins everywhere. "High-Energy Pop" scored 0.40 in balanced and 0.60 in `mood_first` and `vibe_first`, while "Mid-everything" scored 0.80 in balanced and 0.60 in the other two.
- The "Conflicting" profile scored 0.40 in most modes and 0.20 in `genre_first`. No song is both sad and very loud and also blues, so the profile is partly unanswerable by design.

**Limits of this evaluation.** The relevant sets are my own opinion, ten profiles is small, and I chose the profiles and the labels myself. The mode weights were set before I ran the evaluation and not tuned to its results, but I cannot rule out that my choice of profiles favors my own design.

**Example before and after (Default Pop/Happy)**

- classic: Sunrise City, Pop Confetti, **Gym Hero**, Rooftop Lights, Seoul Static
- balanced: Sunrise City, Pop Confetti, Rooftop Lights, Seoul Static, **Gym Hero**

**Verification.** `pytest` runs 36 tests. They cover version 1 compatibility (classic mode reproduces the 1.0 scores), each scoring component, input and catalog validation, diversity behavior, confidence, and the evaluation script. I also confirmed by hand that `classic` mode on the original 20 songs produces the same rankings and scores that were in the 1.0 model card.

---

## 8. Future Work

- Grow the catalog to hundreds of songs and add non-English and non-Western genres.
- Replace hand-made families with similarity learned from audio features, so "close genre" is measured and not asserted.
- Calibrate confidence against real user ratings instead of a score ratio.
- Collect real listener feedback (likes and skips) to tune the weights and to test whether the hand-labelled relevant sets agree with other people.
- Let a user pick several genres or moods, and add an "I've already heard this" memory.
- Test the diversity penalty at other strengths and look for a better trade-off than a flat penalty.

---

## 9. Personal Reflection

The biggest lesson came from the evaluation, not from the code. I expected the new scoring rules to be the main improvement. When I separated the effects, most of the improvement came from simply having 40 songs instead of 20. The rules mattered mainly in specific cases: the Gym Hero fix, the acoustic profile that finally used its extra inputs, and the honest warnings. That made me more careful about claiming credit for a design change without a controlled comparison.

I also learned that every "improvement" had a cost. Partial credit fixed Gym Hero, but it let a hip-hop song into a romantic list and made the system more confident than it arguably should be. Diversity gave more varied lists but lowered precision. A recommender is a set of trade-offs, and the person who picks the weights decides which ones to accept.

The honesty features changed how I think about the output. Version 1 presented a weak list in the same format as a strong one. Adding a confidence label and the "top pick is far from your energy target" warning showed me that a high score can hide a large miss, and that a system should say when it is guessing.

If I continued, I would get real listener judgments to replace my own labels, since my relevant sets are the weakest part of the evaluation.
