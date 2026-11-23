# 🎧 Model Card: VibeFinder 2.0

## 1. Model Name

**VibeFinder 2.0**, an extension of my Module 3 Music Recommender Simulation (VibeFinder 1.0).

---

## 2. Goal / Intended Use

VibeFinder recommends songs from a 40-song catalog. A user can describe what they want in plain language ("something calm to study to late at night") or pick a genre, mood, and numeric targets. For plain-language requests the system retrieves matching knowledge, builds a taste profile from it, checks its own result, and explains every pick.

It is built for classroom exploration and as a demonstration of retrieval, a self-checking workflow, and reliability testing. It is **not** meant for real users or a real music service.

**Not intended for:** decisions about real people, replacing a streaming service, judging what music is "good", or any setting where a wrong suggestion could cause harm.

---

## 3. How the System Works

1. **Guardrails** reject empty, oversized (over 300 characters), non-text, or invalid-`k` input with a clear message.
2. **Retrieval.** A TF-IDF retriever searches 48 documents: 18 genre descriptions, 15 mood descriptions, and 15 listening scenarios. If nothing scores above a relevance threshold (0.15), the system asks the user to clarify and returns no songs.
3. **Conflict check.** If the strongest retrieved sources disagree on energy by more than 0.45 (for example "calm" and "workout"), the system follows only the best match and marks the result `needs_review`.
4. **Profile.** Genre and mood come from weighted votes of the retrieved documents. Energy, valence, danceability, acousticness, and tempo are relevance-weighted averages of the documents' targets. An explicit "120 bpm" in the request overrides the tempo.
5. **Recommend.** The catalog is scored on up to 7 features with partial credit for related genres and moods, then re-ranked for diversity.
6. **Self-check and revise.** Four checks: confidence at least medium, the top pick has no large feature mismatch, no repeated artist, and k songs returned. On failure the agent tries the next strategy (up to 3 attempts) and keeps the best.
7. **Answer.** Plain-language summary citing the retrieved documents, per-feature score reasons, confidence, notes, and the full step trace. Every step is logged to `logs/vibefinder.log`.

The "reasoning" is rule-based and fully inspectable. There is no learned model and no network call.

---

## 4. Data

- **Songs:** 40 invented songs in `data/songs.csv` (18 genres, 15 moods; energy, valence, danceability, acousticness, tempo). Version 1 had 20 songs; I wrote 20 more so every genre has at least two. Labels were assigned by hand.
- **Knowledge base:** `data/knowledge_base.json`. Genre and mood descriptions are my own wording. Their numeric targets are computed from the catalog. The 15 scenario documents (study, workout, road trip, and so on) have targets I chose by judgment.
- **Families** used for partial credit (for example country, folk, and blues are "roots") are my own groupings.
- **Missing:** lyrics, language, artist popularity, release year, and any real listener behavior.

---

## 5. Strengths

- Retrieval on clear requests is accurate: top-1 **90%**, top-3 **100%** on 20 test queries.
- Retrieval genuinely changes the output: "study" and "workout" produce different profiles and non-overlapping lists (covered by a test).
- Every decision is inspectable: retrieved documents are cited, each score has per-feature reasons, and the trace shows each attempt and why it was revised.
- Bad input is handled, not crashed on: 12 of 12 guardrail tests pass, and unusable requests (random letters, non-English text) get a clarification request rather than a guess.
- Contradictory requests are detected and flagged in 4 of 4 tests.
- Fully reproducible: no API key, no randomness, identical output on repeated runs.

---

## 6. Limitations and Bias

- **Small, invented, hand-labelled data.** 40 songs and 48 documents reflect my opinions. The scenario targets (for example "studying = energy 0.30") are judgment calls, not measurements.
- **Vocabulary-bound retrieval.** TF-IDF only matches words it has seen. "Sunshine and ocean waves" matched reggae before beach because "ocean" is not in the knowledge base. "Música para estudiar" gets a clarification request because the knowledge base is English only. People who describe music in other languages, slang, or regional terms are served worse.
- **Word collisions.** "Driving across the *country*" retrieved the country genre ahead of the road-trip scenario. "Taking the *train* to work" matched the workout document ("training") and triggered a false conflict flag.
- **Western-style genre labels.** The catalog and families assume a Western genre taxonomy. Tastes outside it must be squeezed into the nearest label.
- **Confidence is not a probability and does not discriminate.** It is the top score divided by the best possible score for the *profile the system built*. All 20 normal test queries scored "high". For a contradictory request the confidence still read "high (98%)" because the system had quietly chosen one side. The `needs_review` status carries the real warning.
- **Conflict handling is crude.** It follows the highest-scoring document. When two sources are nearly tied (0.23 vs 0.22 in one test) that choice is close to arbitrary. The user's actual intent may have been the other side.
- **Partial credit can over-reach.** In the profile-based mode, the "urban" genre family let a hip-hop song into a "Romantic Evening" list.
- **The check-and-revise loop is mostly a diversity retry on ordinary requests.** Twelve of 20 queries revised, all because of the repeated-artist check. The confidence and mismatch checks never fired on ordinary queries; they only matter for unusual ones.
- **Weights and thresholds are my choices.** Retrieval threshold 0.15, conflict spread 0.45, and the mode weights were set by judgment. I changed one default (starting diversity 0.05 to 0.10) after seeing the evaluation, which means that setting was partly tuned to my own test queries.
- **My evaluation is subjective and small.** I wrote the queries, the "correct document" labels, and the contradictory examples (after I understood how the detector works). Twenty queries cannot support strong claims.
- **No personalization or listener data.** No history, skips, or other users.

---

## 7. Evaluation

Reproduce with `python -m src.evaluate_agent` and `python -m src.evaluate`. Raw results: `assets/evaluation_results.md`, `assets/v1_vs_v2_evaluation.txt`, `assets/test_output.txt`.

### 7a. Retrieval, agent, and guardrails

| Experiment | Result |
|---|---|
| Retrieval, 20 queries | Top-1 90% (18/20), top-3 100% (20/20) |
| Paraphrase stability, 4 groups of 3 wordings | Mean top-5 overlap 0.84 (study 1.00, workout 1.00, sleep 0.78, party 0.59) |
| Repeatability | Identical output across 5 runs |
| Agent on the 20 queries | 19 ok, 1 needs_review (false alarm), 12 revised, 12 recovered |
| Contradictory requests | 4/4 flagged |
| Guardrails | 12/12 handled |
| Automated tests | 73 passed |

### 7b. Human-judgment results

These are my own judgments, recorded in a parseable form.

| Test input | Evaluation criterion | Result |
|---|---|---|
| "driving across the country with my friends" | Road-trip document ranked first | Fail (country genre ranked first, road trip third) |
| "sunshine and ocean waves" | Beach document ranked first | Fail (reggae ranked first, beach second) |
| "taking the train to work" | Handled as a normal commute request | Fail (false conflict flag; recommendations were still sensible) |
| "calm and peaceful but also super high energy workout" | Flags the contradiction | Pass |
| "asdfgh qwerty zxcv" | Asks for clarification, does not guess | Pass |
| Empty input | Handled gracefully | Pass |

### 7c. Version 1 vs 2 (profile-based)

Ten profiles with my hand-labelled "reasonable songs". Precision@5: **0.54** (v1, 20 songs), **0.70** (v1, 40 songs), **0.72** (balanced). The bigger catalog produced most of the gain; the new scoring added only 0.02, within what ten profiles can resolve. It helped most where the user supplied extra inputs ("Quiet Acoustic Study" 0.60 to 0.80). Diversity raised unique genres from 3.1 to 3.5 at a cost of 0.02 precision.

---

## 8. Misuse and Prevention

**Could it be misused?** The potential for harm is low because the system recommends songs from a toy catalog. The realistic risks are:

- **Manipulating results by editing the knowledge base or catalog.** Whoever controls the documents and weights controls what is recommended. In a real product this could be used to promote particular artists or genres without telling users. *Prevention:* the knowledge base is a plain, versioned JSON file, every recommendation cites the documents behind it, and the loader validates the file's structure so a malformed edit fails loudly. A real deployment would need review on changes and disclosure of any promoted content.
- **Over-trusting the output.** A user might read "high confidence" as "this is what you meant". *Prevention:* the `needs_review` status, source-conflict notes, and coverage notes appear next to the result, and the system declines to answer when it finds nothing relevant. Confidence alone is not enough, and I document that.
- **Abusive or oversized input.** *Prevention:* a 300-character limit, type checks, a cap on `k`, and no code execution or network calls, so text such as SQL-style strings is just treated as words (tested).
- **Privacy.** Requests are written to a local log file. *Prevention:* `logs/` is excluded from git, nothing is sent over a network, and a real deployment would need a retention and anonymization policy.
- **Unequal service.** Non-English requests and tastes outside the Western genre taxonomy get worse results, which is a fairness problem described under Limitations. It would need a multilingual knowledge base and real listener data to fix.

---

## 9. What Surprised Me While Testing Reliability

- **The "revision" loop was firing on 17 of 20 ordinary queries.** I expected it to rescue rare failures. Instead one check (repeated artist) failed almost every time at the starting diversity of 0.05, so most "revisions" were just a parameter bump. I raised the starting value to 0.10, and it still fires on 12 of 20. A check that nearly always fails is miscalibrated, not protective.
- **Confidence told me almost nothing.** All 20 normal queries scored "high", and a contradictory request still scored 98%. I had assumed a confidence ratio would separate good from bad answers. It does not, so the explicit conflict check was the more useful guardrail.
- **Contradictions were being silently averaged.** "Calm and peaceful but also super high energy workout" initially produced a middle-of-the-road profile marked `ok`. Nothing was technically broken, and the output looked fine. Only a deliberately contradictory test exposed it.
- **Two tiny tokenizer details broke real requests.** Splitting "k-pop" at the hyphen made it collide with "pop", and "asleep" did not match the sleep document at all.
- **The catalog mattered more than the algorithm.** Doubling the song count lifted precision@5 from 0.54 to 0.70, while all of the new scoring added 0.02. I expected the opposite.
- **A word-level collision ("country") beat a whole-sentence meaning.** The retriever has no notion of context.

---

## 10. Collaboration

<!-- REVIEW BEFORE SUBMITTING: this section records what happened during the project. Edit the first-person statements so they match your own decisions and what you actually reviewed. -->

I built this project with an AI coding assistant (Claude Code) working in my repository, and that is part of how the work was produced. Below is what happened with specific suggestions. The assistant wrote most of the code and drafts; the design direction, the test inputs I chose to trust, and the final decision about what to submit are mine.

**A suggestion I accepted: separate the effect of the bigger catalog from the effect of the new scoring.** The assistant proposed evaluating the original recipe on both the 20-song and 40-song catalogs, instead of only comparing version 1 to version 2. I accepted it because it could change my conclusion, and it did: most of the improvement came from the data, not the new rules. Without that comparison the README would have credited the algorithm for a gain that came from more songs.

**A suggestion I did not accept as written: a single confidence number.** The first design measured confidence as the top score divided by the best possible score, and treated "high" as safe. Testing showed that the sad, high-energy blues profile read "high (80%)" while its top pick missed the energy target by 0.52, and later that a contradictory request read "high (98%)". I did not keep it as written. I added a separate per-feature mismatch warning and a source-conflict check, and I documented that confidence is not a probability. The original idea was not wrong so much as insufficient on its own for this system.

**A suggestion I did not adopt: a hosted language model to write the answers or to retrieve with embeddings.** It would have given more natural wording and better handling of paraphrases and non-English requests. I did not use it because the project should run for anyone with no account or API key, and because a deterministic retriever and rule-based answer text let me test the system exactly and repeat every result. The cost is real and documented under Limitations: the retriever only matches words it knows.

**Also changed after testing:** the assistant's first attempt used a starting diversity of 0.05. When my evaluation showed the repeated-artist check failing on 17 of 20 queries, I raised it. I also note that this means that value was tuned to my own test set.

**What I verified myself:** I ran the full test suite and the evaluation scripts, read the sample outputs, and checked that version 1's scores are reproduced exactly by `classic` mode on the original 20 songs. I did not verify the Mermaid diagram by rendering it in this environment, only by keeping its syntax simple.

---

## 11. Future Work

- Replace TF-IDF with embeddings, or add synonym lists and a multilingual knowledge base, so "ocean waves" and non-English requests work.
- Make the conflict handler ask the user which side they meant when two sources are nearly tied, instead of choosing.
- Calibrate confidence against real listener ratings, and measure whether users agree with `needs_review` flags.
- Get other people to label the "correct document" and "reasonable songs" sets, to replace my own judgment.
- Grow the catalog to hundreds of songs and include non-Western genres.
- Learn genre and mood similarity from audio features instead of hand-made families.

---

## 12. Personal Reflection

The most useful thing I did was test the system against its own claims. A confidence score that always said "high", a revision loop that fired on most queries, and a contradictory request that was quietly averaged into a bland answer all looked fine in a demo. They only showed up when I measured. That changed what I trust: a reliable system needs checks that can fail, and I should be suspicious of any check that never does, or always does.

I also learned to be careful about credit. The biggest improvement came from more data, not from my cleverest rules. Reporting that honestly made the project weaker on paper and more trustworthy in practice.
