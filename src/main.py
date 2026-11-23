"""Command line runner for VibeFinder 2.0.

Examples:
    python -m src.main                      # balanced mode with diversity
    python -m src.main --mode classic       # the version 1 recipe
    python -m src.main --mode vibe_first --diversity 0.1
    python -m src.main --experiment         # version 1 weight-shift experiment
"""

import argparse

from src.profiles import PROFILES
from src.recommender import (
    MODES, assess_confidence, coverage_notes, load_songs, max_score, mismatch_notes,
    recommend_songs,
)

DEFAULT_DIVERSITY = 0.05


def print_recommendations(name, prefs, songs, k=5, mode="balanced", diversity=0.0, weights=None):
    """Print a formatted top-k list for one profile."""
    recs = recommend_songs(prefs, songs, k, mode, diversity, weights)
    top = max_score(prefs, mode, weights)
    label, ratio = assess_confidence(recs, prefs, mode, weights)
    print("=" * 64)
    print(f"Profile: {name}  {prefs}")
    print("=" * 64)
    for rank, (song, score, explanation) in enumerate(recs, 1):
        print(f"{rank}. {song['title']} by {song['artist']}  [{song['genre']}/{song['mood']}]")
        print(f"   Score: {score:.2f} / {top:.2f}")
        for reason in explanation.split("; "):
            print(f"     - {reason}")
    print(f"Confidence: {label} ({ratio:.0%} of the best possible score)")
    for note in coverage_notes(prefs, songs):
        print(f"Note: {note}")
    if recs:
        for note in mismatch_notes(recs[0][0], prefs):
            print(f"Note: top pick {note}")
    if label == "low":
        print("Warning: no strong match in the catalog; treat these as best guesses.")
    print()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="VibeFinder 2.0 music recommender")
    parser.add_argument("--mode", default="balanced", choices=list(MODES),
                        help="scoring mode (default: balanced)")
    parser.add_argument("--diversity", type=float, default=None,
                        help=f"re-rank penalty for repeated artists/genres (default "
                             f"{DEFAULT_DIVERSITY}, or 0 in classic mode; 0 turns it off)")
    parser.add_argument("--k", type=int, default=5, help="number of songs to show")
    parser.add_argument("--catalog", default="data/songs.csv")
    parser.add_argument("--experiment", action="store_true",
                        help="version 1 weight shift: genre 2.0 -> 1.0, energy 1.0 -> 2.0")
    args = parser.parse_args(argv)

    mode, weights = args.mode, None
    diversity = args.diversity
    if diversity is None:
        diversity = 0.0 if mode == "classic" else DEFAULT_DIVERSITY
    if args.experiment:
        mode, diversity = "classic", 0.0
        weights = {"genre": 1.0, "energy": 2.0}
        print("EXPERIMENT: genre weight 2.0 -> 1.0, energy weight 1.0 -> 2.0 (max score 4.0)\n")

    songs = load_songs(args.catalog)
    print(f"Loaded songs: {len(songs)}  |  mode: {mode}  |  diversity: {diversity}\n")
    for name, prefs in PROFILES.items():
        print_recommendations(name, prefs, songs, args.k, mode, diversity, weights)


if __name__ == "__main__":
    main()
