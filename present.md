# Presentation Notes: VibeFinder 2.0

Everything needed to present the project in 5 to 7 minutes: the story, the changes and their effects, a demo script, how it meets the rubric, and answers to likely questions.

---

## 1. One-sentence pitch

VibeFinder 2.0 turns a plain-language request ("something calm to study to") into an explained list of songs by **retrieving** matching knowledge, **building a profile from it**, **checking its own result**, and **revising** if the check fails, with every step logged and visible.

---

## 2. Where I started (VibeFinder 1.0, my Module 3 project)

- 20-song CSV, content-based filtering, no other users.
- Score = +2.0 genre match + 1.0 mood match + up to 1.0 energy closeness (max 4.0), printed with reasons.
- My own model card listed its weaknesses: genre dominated ("Gym Hero" kept showing up for happy pop fans), most genres had one song, exact-match labels ("indie pop" got nothing for "pop"), four features were loaded but never scored, and weak lists looked as confident as strong ones.

**Framing for the talk:** I found these problems in v1, fixed them, added retrieval and a self-checking workflow on top, and then measured whether it worked, including where it did not.

---

## 3. What I added, in two layers

### Layer 1: a better recommender

| Change | Effect |
|---|---|
| Scores all 7 features (valence, danceability, acousticness, tempo added) | "Quiet Acoustic Study" precision@5 0.60 to 0.80 |
| Partial credit for related genres and moods | Gym Hero fell from #3 to #5 for Default Pop/Happy |
| Five scoring modes (`classic` reproduces v1 exactly) | Weights can change without editing code |
| Diversity re-ranking | Unique genres 3.1 to 3.5, unique artists 3.8 to 4.2, cost 0.02 precision |
| Confidence, coverage notes, mismatch warnings | The system says when it is guessing |
| Catalog 20 to 40 songs, input validation | Biggest single quality gain |

### Layer 2: retrieval and an agentic workflow (the final-project feature)

| Component | What it does |
|---|---|
| **Knowledge base** (`data/knowledge_base.json`) | 48 documents: 18 genre, 15 mood, 15 listening scenarios. Genre and mood numeric targets are computed from the catalog |
| **Retriever** (`src/retriever.py`) | Pure-Python TF-IDF search. No API key, deterministic |
| **Agent** (`src/agent.py`) | Guard, retrieve, build profile from the retrieved documents, recommend, self-check, revise (max 3 attempts), explain with citations |
| **Conflict detection** | If the strongest sources disagree (calm + workout), follow the best one and flag `needs_review` |
| **Logging** (`src/log_setup.py`) | Every step goes to `logs/vibefinder.log` |
| **Evaluation** (`src/evaluate_agent.py`) | Retrieval accuracy, paraphrase stability, conflicts, guardrails |
| **Streamlit app** | "Ask in plain words" tab with the full trace |

**Key design point:** retrieval is not decoration. The profile's genre, mood, and numeric targets are computed from the retrieved documents, so different requests produce different lists (covered by a test).

---

## 4. Rubric checklist

| Requirement | Where it is met |
|---|---|
| Extends a Module 1-3 project; names it | README "Original project": Module 3 Music Recommender Simulation |
| At least one advanced feature, integrated into the logic | Retrieval (builds the profile) **and** an agentic plan/act/check/revise loop **and** a reliability system |
| Logging or guardrails | `src/log_setup.py`; guardrails for empty, oversized, wrong-type, invalid `k`, no-match, conflicting requests |
| Clear setup steps, reproducible | README "Setup instructions". No keys or accounts. `pytest` gives 73 passed |
| System diagram as Mermaid source in `diagrams/` | `diagrams/architecture.mmd` (also embedded in README) |
| README sections (original project, summary, architecture, setup, 2-3 sample interactions, design decisions, testing, reflection) | All present in `README.md` |
| Reliability and evaluation | 73 tests, retrieval accuracy, paraphrase stability, confidence scoring, structured human-judgment table |
| `model_card.md` with limitations/bias, misuse, surprises, collaboration (accepted and not-accepted suggestion) | Sections 6, 8, 9, 10 |
| Reproducible execution evidence as markdown/txt, not screenshots | `assets/sample_runs.md`, `assets/test_output.txt`, `assets/evaluation_results.md`, `assets/sample_log.txt`, `assets/v1_vs_v2_evaluation.txt` |
| Multiple meaningful commits | See `git log` |
| Public repo, pushed | **Still to do:** push, and confirm the repo is public on GitHub |
| Loom and slide deck | Not required for this submission |

---

## 5. Results (all reproducible)

| Experiment | Result |
|---|---|
| Retrieval, 20 queries | Top-1 **90%** (18/20), top-3 **100%** |
| Paraphrase stability (4 groups x 3 wordings) | Mean top-5 overlap **0.84** (study 1.00, workout 1.00, sleep 0.78, party 0.59) |
| Repeatability | Identical across repeated runs |
| Agent, 20 queries | 19 ok, 1 false alarm, 12 revised, 12 recovered |
| Contradictory requests | **4/4** flagged |
| Guardrails | **12/12** handled without crashing |
| Tests | **73** passed |
| v1 vs v2 precision@5 | 0.54 (v1, 20 songs), 0.70 (v1, 40 songs), 0.72 (balanced) |

### The honest takeaways (say these out loud, they are the strongest part of the talk)

1. **The bigger catalog did most of the work** (0.54 to 0.70). The new scoring added only 0.02.
2. **A check that nearly always fails is miscalibrated.** The repeated-artist check failed on 17 of 20 queries at diversity 0.05, so "revision" was a parameter bump. I raised the start to 0.10 and it still fires 12 of 20. I tuned that value on my own test queries, and I say so.
3. **Confidence did not discriminate.** All 20 normal queries were "high", and even a contradictory request read 98%. The conflict check and `needs_review` status were the useful guardrails.
4. **Contradictions were silently averaged** into a bland profile until I tested for it.

---

## 6. What did not work (be upfront)

- Two retrieval misses: "driving across the **country**" matched the country genre; "sunshine and ocean waves" matched reggae before beach ("ocean" is not in the knowledge base).
- One false conflict flag: "taking the **train** to work" matched the workout document ("training").
- Paraphrase stability for "party" is only 0.59.
- English only: "música para estudiar" gets a clarification request, by design.
- Conflict handling follows the best-scoring document; with a near-tie (0.23 vs 0.22) that choice is nearly arbitrary, so it hands the decision to a human.
- Family credit let a hip-hop song into a "Romantic Evening" list.
- My evaluation is subjective: I wrote the queries, labels, and contradictory examples (after knowing how the detector works), and 20 queries is small.

---

## 7. Demo script (about 2 minutes)

Run from the project folder.

1. **A normal request, with the self-check and revision visible**
   ```
   python -m src.agent "something calm to study to late at night"
   ```
   Point at: `[retrieve]` (what it looked up), `[profile]` (built from those documents), `[attempt 1] ... failed: no repeated artist`, `[revise]`, `[attempt 2] ... all checks passed`, and "supported by retrieved: Studying" under each song.

2. **Show that retrieval changes the answer**
   ```
   python -m src.agent "gym workout music" --no-trace
   ```
   Different profile (energy about 0.9), completely different songs.

3. **A contradictory request**
   ```
   python -m src.agent "calm and peaceful but also super high energy workout"
   ```
   Point at `[conflict]`, the status `needs_review`, and the note.

4. **Input it will not guess at**
   ```
   python -m src.agent "asdfgh qwerty zxcv"
   python -m src.agent ""
   ```

5. **The evidence**
   ```
   python -m src.evaluate_agent
   pytest
   ```

6. **The app**: `streamlit run app.py`, "Ask in plain words" tab, open "Agent trace".

---

## 8. Design decisions and why

- **Pure-Python TF-IDF, no hosted model.** Runs offline, no key, identical results every run, so every evaluation is reproducible. Cost: it only matches words it has seen.
- **Retrieval builds the profile**, so it genuinely changes behavior instead of being printed alongside a normal answer.
- **Bounded revision** (3 attempts, keep the best) so the agent cannot loop forever.
- **Fail safe, not smart, on conflict:** follow the best match and ask a human to review.
- **Genre and mood targets computed from the catalog**; scenario targets are my judgment and documented as such.
- **Kept `classic` mode** so v1 can be reproduced and compared. It reproduces every v1 score on the original 20 songs.
- **Showed the work:** trace, citations, per-feature reasons, and a log file.

---

## 9. Likely questions and answers

**What is the "AI" part, and why no language model?**
Retrieval plus an agent that plans, acts, checks, and revises, with a reliability evaluation. I chose a deterministic retriever so anyone can run it with no key and every result is repeatable. The trade-off is that it only matches words it knows, and I documented where that fails.

**How do you know it works?**
73 tests, plus structured experiments: 90% top-1 retrieval on 20 queries, 0.84 paraphrase stability, 4/4 contradictions flagged, 12/12 guardrails. And a list of failures: two retrieval misses and one false alarm.

**Why does the agent revise so often?**
Twelve of 20 queries revised, all for the repeated-artist check. I originally had 17 of 20 and raised the starting diversity. It is honest to say the loop is mostly a diversity retry for ordinary requests, and its other checks matter for unusual ones.

**What does confidence mean, and can I trust it?**
Top score divided by the best possible score for the profile the system built. It is not a probability, and it did not separate good from bad answers in my tests. The `needs_review` status and the notes are what to rely on.

**How does retrieval change the result?**
The retrieved documents decide the profile. "Study" gives energy about 0.30 and lofi/ambient; "workout" gives energy about 0.92 and EDM/hip hop. A test verifies the lists do not overlap.

**What happens with bad input?**
Empty, oversized, or non-text input is rejected with a message. Unmatchable text gets a clarification request. A contradictory request is flagged. Nothing crashes (12/12 tests).

**Could it be misused?**
Low risk, but whoever edits the knowledge base controls what is recommended, over-trusting "high confidence" is possible, and queries are logged locally. Prevention: cited sources, validation, visible notes, logs kept out of git. Details are in the model card.

**What was your biggest surprise?**
That the bigger catalog beat all my new rules, and that a check failing 85 percent of the time was a miscalibrated default.

**What would you do next?**
Embeddings or synonyms so "ocean waves" and other languages work, ask the user when two sources tie, calibrate confidence against real ratings, and have other people label my test sets.

**How did you work on this?**
I used an AI coding assistant for much of the implementation, and the model card (section 10) describes one suggestion I accepted, one I changed, and one I did not adopt.

---

## 10. File map and quick numbers

```
app.py                        Streamlit app (two tabs)
data/songs.csv                40 songs
data/knowledge_base.json      18 genre + 15 mood + 15 scenario documents
diagrams/architecture.mmd     Mermaid system diagram
assets/                       sample runs, test output, evaluation results, sample log
src/retriever.py              knowledge base loader + TF-IDF retriever
src/agent.py                  guardrails, profile, check/revise loop, answer
src/recommender.py            scoring, modes, diversity, confidence, validation
src/evaluate_agent.py         retrieval / paraphrase / conflict / guardrail evaluation
src/evaluate.py               v1 vs v2 comparison
src/log_setup.py              logging
tests/                        73 tests
README.md  model_card.md  present.md
```

- 40 songs, 48 knowledge-base documents, 7 scored features, 5 scoring modes
- 73 tests, all passing
- Retrieval top-1 90%, top-3 100%; paraphrase overlap 0.84
- Conflicts flagged 4/4; guardrails 12/12
- Precision@5: 0.54 to 0.70 (catalog) to 0.72 (scoring)
