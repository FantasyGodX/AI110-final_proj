# VibeFinder 2.0: Presentation Script

**Total time: about 6 minutes.** Read the **SAY** lines out loud. Do the **SHOW** lines on screen. Open a terminal in the project folder before you start.

| Part | Time |
|---|---|
| 1. The starting point | 0:45 |
| 2. What I built | 1:15 |
| 3. Live demo | 2:00 |
| 4. Results | 1:00 |
| 5. What went wrong, and what I learned | 1:00 |

---

## 1. The starting point (0:45)

**SAY:**

- "This is an extension of my Module 3 project, the Music Recommender Simulation."
- "Version 1 had 20 songs. It scored each song on three things: genre, mood, and energy."
- "My own model card listed its weaknesses:"
  - Genre counted too much, so a workout song kept showing up for happy-pop fans.
  - Most genres had only one song.
  - 'Indie pop' got no credit for being close to 'pop'.
  - Four song features were loaded but never used.
  - A weak list looked just as confident as a strong one.
- "For the final project I fixed those, then added retrieval and a system that checks its own work."

---

## 2. What I built (1:15)

**SAY:**

- "Now you can type a sentence, like 'something calm to study to late at night.'"
- "The system works in five steps:"
  1. **Guard.** It rejects empty, huge, or invalid input.
  2. **Retrieve.** It searches a knowledge base of 48 documents about genres, moods, and listening situations.
  3. **Build a profile.** The retrieved documents decide the target genre, mood, energy, and tempo. This is the key point: retrieval changes the answer, it isn't just decoration.
  4. **Check its own result.** Is confidence okay? Does the top song miss a target badly? Does an artist repeat?
  5. **Revise.** If a check fails, it tries a different strategy, up to 3 times.
- "If it finds nothing relevant, it asks you to clarify instead of guessing."
- "If your request contradicts itself, like 'calm' and 'workout,' it flags the result for review."
- "Everything is logged, and it needs no API key, so anyone can run it."

**SHOW:** the diagram in the README (`diagrams/architecture.mmd`). Point to: Guardrails, Retriever, Profile, Recommender, Self-check, and the human review box.

**Also built (mention in one sentence):** all 7 song features are now scored, related genres get partial credit, results are re-ranked for variety, and the catalog doubled to 40 songs.

---

## 3. Live demo (2:00)

### Demo 1: a normal request (about 45 sec)

**SHOW:**
```
python -m src.agent "something calm to study to late at night"
```
**SAY:** "Watch the trace."
- Point to `[retrieve]`: "It looked up the Studying document."
- Point to `[profile]`: "It built the target from that: low energy, acoustic, slow tempo."
- Point to `[attempt 1] ... failed: no repeated artist`: "Its own check caught a repeated artist."
- Point to `[revise]` then `[attempt 2] ... all checks passed`: "So it changed strategy and passed."
- Point to a song: "Each song says which retrieved document supports it."

### Demo 2: retrieval changes the answer (about 20 sec)

**SHOW:**
```
python -m src.agent "gym workout music" --no-trace
```
**SAY:** "Different request, different profile, completely different songs."

### Demo 3: a contradictory request (about 30 sec)

**SHOW:**
```
python -m src.agent "calm and peaceful but also super high energy workout"
```
**SAY:** "It noticed the two ideas disagree. It followed the stronger match and marked the result `needs_review` instead of quietly averaging them."

### Demo 4: input it won't guess at (about 20 sec)

**SHOW:**
```
python -m src.agent "asdfgh qwerty zxcv"
```
**SAY:** "It asks me to clarify instead of making something up."

### Optional if you have time: the web app

**SHOW:** `streamlit run app.py`, then the "Ask in plain words" tab and the "Agent trace" section.

---

## 4. Results (1:00)

**SAY:**

- "I tested it with 73 automated tests, and they all pass."
- "I also ran structured experiments:"
  - Retrieval finds the right document first **90% of the time** (18 of 20 test requests), and within the top 3 **100%** of the time.
  - Different wordings of the same request give **similar songs** (84% overlap on average).
  - **4 out of 4** contradictory requests were flagged.
  - **12 out of 12** bad inputs were handled without crashing.
- "Comparing version 1 to version 2: the quality score went from **0.54 to 0.70 just by doubling the catalog**, and the new scoring added only **0.02 more** (to 0.72)."

**SHOW (optional):** `python -m src.evaluate_agent`, or open `assets/evaluation_results.md`.

---

## 5. What went wrong, and what I learned (1:00)

**SAY, the three failures:**

- "Two retrieval mistakes. 'Driving across the *country*' matched the country genre. 'Ocean waves' missed the beach document."
- "One false alarm: 'taking the *train* to work' matched the workout document because of the word 'training.'"
- "It only understands English, and only words it knows."

**SAY, what testing taught me:**

1. "**The bigger catalog mattered more than my clever rules.** I expected the opposite."
2. "**A check that fails almost every time is broken, not protective.** My repeated-artist check failed on 17 of 20 requests, so I raised the starting variety setting. It still fires on 12 of 20, so most 'revisions' are really a variety retry. I tuned that setting on my own test requests, and I'm telling you so."
3. "**The confidence number did not tell good answers from bad ones.** Every normal request scored 'high,' and even a contradictory one scored 98%. The real warning is the `needs_review` flag."
4. "**A contradiction was being quietly averaged away** until I tested for it on purpose."

**SAY, closing line:**
"The hard part of a reliable system isn't getting an answer. It's knowing when not to trust it."

---

## If someone asks (short answers)

**Why no language model?**
"I wanted it to run for anyone with no key, and give the same result every time so I could test it exactly. The cost is that it only matches words it knows, and I documented where that breaks."

**How do you know it works?**
"73 tests plus the experiments: 90% retrieval accuracy, 4 out of 4 contradictions caught, 12 out of 12 bad inputs handled. And I listed where it fails."

**What does confidence mean?**
"The top score divided by the best possible score for the profile it built. It isn't a probability, and it didn't separate good from bad in my tests. Rely on the `needs_review` flag and the notes."

**Is your evaluation fair?**
"Not fully. I wrote the test requests and the correct answers myself, and 20 requests is small. The next step would be having other people label them."

**Could it be misused?**
"The risk is low. Whoever edits the knowledge base controls what gets recommended, people could over-trust 'high confidence,' and requests are logged locally. I handle that with cited sources, visible warnings, and keeping logs out of git."

**What would you do next?**
"Better word matching so 'ocean waves' and other languages work, ask the user which side they meant when a request is split, and check confidence against real listener ratings."

**Did you use AI tools?**
"Yes, an AI coding assistant wrote most of the code and drafts. I set the scope and made the final decisions. The model card, section 10, describes one suggestion I accepted, one I changed, and one I didn't adopt."

---

## Cheat sheet: numbers to remember

- **40** songs, **48** knowledge documents, **7** scored song features
- **73** tests, all passing
- Retrieval: **90%** first-try, **100%** within top 3
- Wording stability: **0.84**
- Contradictions flagged: **4 of 4**. Bad inputs handled: **12 of 12**
- Quality score: **0.54, then 0.70** (bigger catalog), **then 0.72** (new scoring)
- Revisions on ordinary requests: **12 of 20** (down from 17 of 20)

## Where things are

- `README.md`: overview, setup, sample outputs
- `model_card.md`: limitations, misuse, reflection, collaboration
- `diagrams/architecture.mmd`: the system diagram
- `assets/`: saved outputs from the demo, tests, and evaluations
- `src/agent.py`, `src/retriever.py`: the main code
