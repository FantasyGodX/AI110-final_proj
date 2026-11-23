# Sample runs

Real output captured by running each command below. Re-run them to reproduce.

## `python -m src.agent "something calm to study to late at night"`

```text
Query: something calm to study to late at night
Status: ok
For "something calm to study to late at night" I retrieved 'Studying' (scenario), 'Relaxed' (mood), 'Meditation and yoga' (scenario). From that I aimed for genre 'ambient', mood 'focused', energy around 0.30, tempo near 74 BPM. My top pick is 'Focus Flow' by LoRoom. Confidence: high (92%).

Agent trace:
  [guard] accepted query (40 chars): 'something calm to study to late at night'
  [retrieve] scenario:study (0.42); mood:relaxed (0.24); scenario:meditation (0.15)
  [profile] built from retrieved documents: {'genre': 'ambient', 'mood': 'focused', 'energy': 0.3, 'valence': 0.57, 'danceability': 0.6, 'acousticness': 0.79, 'tempo_bpm': 74}
  [attempt 1] mode=balanced diversity=0.1 genre=kept -> confidence high (86%); failed: no repeated artist
  [revise] trying a different strategy because: no repeated artist
  [attempt 2] mode=vibe_first diversity=0.15 genre=kept -> confidence high (92%); all checks passed
  [final] chose attempt 2 (vibe_first); status=ok

Recommendations:
1. Focus Flow by LoRoom  [lofi/focused]  score 6.47 / 7.00
     supported by retrieved: Studying
     similar genre 'lofi' ~ 'ambient' (+0.25) | mood match (+1.0) | energy 0.40 vs target 0.30 (+1.80) | valence 0.59 vs target 0.57 (+0.98) | danceability 0.60 vs target 0.60 (+1.00) | acousticness 0.78 vs target 0.79 (+0.99) | tempo 80 vs target 74 BPM (+0.45)
2. Spacewalk Thoughts by Orbit Bloom  [ambient/chill]  score 5.94 / 7.00
     supported by retrieved: Studying, Meditation and yoga
     genre match (+0.5) | similar mood 'chill' ~ 'focused' (+0.50) | energy 0.28 vs target 0.30 (+1.96) | valence 0.65 vs target 0.57 (+0.92) | danceability 0.41 vs target 0.60 (+0.81) | acousticness 0.92 vs target 0.79 (+0.87) | tempo 60 vs target 74 BPM (+0.38)
3. Lantern Walk by Willow Creek  [folk/relaxed]  score 5.60 / 7.00
     supported by retrieved: Relaxed
     similar mood 'relaxed' ~ 'focused' (+0.50) | energy 0.35 vs target 0.30 (+1.90) | valence 0.60 vs target 0.57 (+0.97) | danceability 0.50 vs target 0.60 (+0.90) | acousticness 0.91 vs target 0.79 (+0.88) | tempo 80 vs target 74 BPM (+0.45)
4. Rainy Window Beats by Paper Lanterns  [lofi/relaxed]  score 5.56 / 7.00
     supported by retrieved: Studying, Relaxed
     similar genre 'lofi' ~ 'ambient' (+0.25) | similar mood 'relaxed' ~ 'focused' (+0.50) | energy 0.33 vs target 0.30 (+1.94) | valence 0.55 vs target 0.57 (+0.98) | danceability 0.60 vs target 0.60 (+1.00) | acousticness 0.84 vs target 0.79 (+0.95) | tempo 70 vs target 74 BPM (+0.47) | genre already picked (-0.53)
5. Coffee Shop Stories by Slow Stereo  [jazz/relaxed]  score 5.43 / 7.00
     supported by retrieved: Relaxed
     similar mood 'relaxed' ~ 'focused' (+0.50) | energy 0.37 vs target 0.30 (+1.86) | valence 0.71 vs target 0.57 (+0.86) | danceability 0.54 vs target 0.60 (+0.94) | acousticness 0.89 vs target 0.79 (+0.90) | tempo 90 vs target 74 BPM (+0.37)
```

## `python -m src.agent "calm and peaceful but also super high energy workout"`

```text
WARNING: conflicting retrieval for query 'calm and peaceful but also super high energy workout': the request mixes conflicting signals: 'Serene' targets energy 0.21 but 'Workout' targets 0.92
Query: calm and peaceful but also super high energy workout
Status: needs_review
For "calm and peaceful but also super high energy workout" I retrieved 'Serene' (mood), 'Workout' (scenario), 'Relaxed' (mood). From that I aimed for mood 'serene', energy around 0.21, tempo near 64 BPM. My top pick is 'Daybreak Choir' by Orbit Bloom. Confidence: high (98%). My own checks flagged this result (see the notes), so please review it before trusting it.

Agent trace:
  [guard] accepted query (52 chars): 'calm and peaceful but also super high energy workout'
  [retrieve] mood:serene (0.23); scenario:workout (0.22); mood:relaxed (0.20)
  [conflict] the request mixes conflicting signals: 'Serene' targets energy 0.21 but 'Workout' targets 0.92; using only the best match 'Serene'
  [profile] built from retrieved documents: {'mood': 'serene', 'energy': 0.21, 'valence': 0.53, 'danceability': 0.28, 'acousticness': 0.95, 'tempo_bpm': 64}
  [attempt 1] mode=balanced diversity=0.1 genre=kept -> confidence high (98%); all checks passed
  [final] chose attempt 1 (balanced); status=needs_review

Recommendations:
1. Daybreak Choir by Orbit Bloom  [ambient/serene]  score 4.41 / 4.50
     supported by retrieved: Serene
     mood match (+1.0) | energy 0.22 vs target 0.21 (+1.48) | valence 0.55 vs target 0.53 (+0.49) | danceability 0.30 vs target 0.28 (+0.49) | acousticness 0.94 vs target 0.95 (+0.49) | tempo 58 vs target 64 BPM (+0.45)
2. Cathedral Strings by Anya Lenz  [classical/serene]  score 4.39 / 4.50
     supported by retrieved: Serene
     mood match (+1.0) | energy 0.20 vs target 0.21 (+1.48) | valence 0.50 vs target 0.53 (+0.48) | danceability 0.25 vs target 0.28 (+0.48) | acousticness 0.97 vs target 0.95 (+0.49) | tempo 70 vs target 64 BPM (+0.45)
3. Rainy Window Beats by Paper Lanterns  [lofi/relaxed]  score 3.54 / 4.50
     supported by retrieved: Relaxed
     similar mood 'relaxed' ~ 'serene' (+0.50) | energy 0.33 vs target 0.21 (+1.32) | valence 0.55 vs target 0.53 (+0.49) | danceability 0.60 vs target 0.28 (+0.34) | acousticness 0.84 vs target 0.95 (+0.45) | tempo 70 vs target 64 BPM (+0.45)
4. Lantern Walk by Willow Creek  [folk/relaxed]  score 3.49 / 4.50
     supported by retrieved: Relaxed
     similar mood 'relaxed' ~ 'serene' (+0.50) | energy 0.35 vs target 0.21 (+1.29) | valence 0.60 vs target 0.53 (+0.47) | danceability 0.50 vs target 0.28 (+0.39) | acousticness 0.91 vs target 0.95 (+0.48) | tempo 80 vs target 64 BPM (+0.37)
5. Coffee Shop Stories by Slow Stereo  [jazz/relaxed]  score 3.29 / 4.50
     supported by retrieved: Relaxed
     similar mood 'relaxed' ~ 'serene' (+0.50) | energy 0.37 vs target 0.21 (+1.26) | valence 0.71 vs target 0.53 (+0.41) | danceability 0.54 vs target 0.28 (+0.37) | acousticness 0.89 vs target 0.95 (+0.47) | tempo 90 vs target 64 BPM (+0.28)
Note: the request mixes conflicting signals: 'Serene' targets energy 0.21 but 'Workout' targets 0.92; I followed 'Serene' and ignored the rest
```

## `python -m src.agent "asdfgh qwerty zxcv"`

```text
WARNING: no relevant knowledge for query 'asdfgh qwerty zxcv'
Query: asdfgh qwerty zxcv
Status: needs_clarification
I could not match that to any genre, mood, or listening situation. Try describing an activity (studying, workout, road trip), a mood (sad, happy, calm), or a genre (jazz, lofi, k-pop).

Agent trace:
  [guard] accepted query (18 chars): 'asdfgh qwerty zxcv'
  [retrieve] no document scored above the relevance threshold
```

## `python -m src.agent ""`

```text
WARNING: rejected query: the request is empty; describe what you want to listen to
Query: 
Status: rejected
Request rejected: the request is empty; describe what you want to listen to.

Agent trace:
  [guard] rejected: the request is empty; describe what you want to listen to
```
