"""Evaluation harness: compares version 1 against version 2 configurations.

Run with:  python -m src.evaluate

For every profile in src/profiles.py each configuration returns a top 5. We then
measure, against my hand-written relevant-song sets:

* precision@5  : how many of the 5 picks are in the relevant set (0 to 1)
* top-1 hit    : whether the #1 pick is in the relevant set
* genres / artists : unique genres and artists in the top 5 (5 = fully varied)
* low-conf     : how many profiles the system flagged as low confidence

The first row runs the original recipe on the original 20 songs (the first 20
rows of the catalog), so the effect of a bigger catalog and the effect of the
new scoring can be separated.
"""

import argparse

from src.profiles import PROFILES, RELEVANT
from src.recommender import assess_confidence, load_songs, recommend_songs

ORIGINAL_CATALOG_SIZE = 20

# (label, mode, diversity, use only the original 20 songs?)
CONFIGS = [
    ("v1 classic, 20 songs", "classic", 0.0, True),
    ("v1 classic, 40 songs", "classic", 0.0, False),
    ("balanced", "balanced", 0.0, False),
    ("balanced + diversity", "balanced", 0.05, False),
    ("genre_first", "genre_first", 0.0, False),
    ("mood_first", "mood_first", 0.0, False),
    ("vibe_first", "vibe_first", 0.0, False),
]


def evaluate_config(songs, mode, diversity, k=5):
    """Return a dict of averaged metrics for one configuration."""
    totals = {"p@5": 0.0, "top1": 0.0, "genres": 0.0, "artists": 0.0, "low": 0}
    per_profile = {}
    for name, prefs in PROFILES.items():
        recs = recommend_songs(prefs, songs, k, mode, diversity)
        titles = [s["title"] for s, _, _ in recs]
        relevant = RELEVANT[name]
        hits = sum(1 for t in titles if t in relevant)
        top1 = 1.0 if titles and titles[0] in relevant else 0.0
        label, _ = assess_confidence(recs, prefs, mode)
        totals["p@5"] += hits / k
        totals["top1"] += top1
        totals["genres"] += len({s["genre"] for s, _, _ in recs})
        totals["artists"] += len({s["artist"] for s, _, _ in recs})
        totals["low"] += label == "low"
        per_profile[name] = (hits / k, titles)
    n = len(PROFILES)
    return {
        "p@5": totals["p@5"] / n, "top1": totals["top1"] / n,
        "genres": totals["genres"] / n, "artists": totals["artists"] / n,
        "low": totals["low"], "per_profile": per_profile,
    }


def run(catalog="data/songs.csv", verbose=False):
    songs = load_songs(catalog)
    rows = []
    for label, mode, diversity, original_only in CONFIGS:
        subset = songs[:ORIGINAL_CATALOG_SIZE] if original_only else songs
        rows.append((label, evaluate_config(subset, mode, diversity)))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare VibeFinder configurations")
    parser.add_argument("--catalog", default="data/songs.csv")
    parser.add_argument("--per-profile", action="store_true",
                        help="also print precision@5 for every profile")
    args = parser.parse_args(argv)

    rows = run(args.catalog)
    print(f"{'Configuration':<24} {'P@5':>5} {'Top-1':>6} {'Genres':>7} {'Artists':>8} {'LowConf':>8}")
    print("-" * 62)
    for label, m in rows:
        print(f"{label:<24} {m['p@5']:>5.2f} {m['top1']:>6.2f} {m['genres']:>7.2f} "
              f"{m['artists']:>8.2f} {m['low']:>5d}/{len(PROFILES)}")
    if args.per_profile:
        print()
        header = "Profile".ljust(32) + "".join(label[:10].rjust(12) for label, _ in rows)
        print(header)
        for name in PROFILES:
            line = name.ljust(32)
            for _, m in rows:
                line += f"{m['per_profile'][name][0]:>12.2f}"
            print(line)


if __name__ == "__main__":
    main()
