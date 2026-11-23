"""Test profiles shared by the CLI, the evaluation script, and the tests.

RELEVANT holds, for each profile, the titles I judged to be reasonable
recommendations by listening to the descriptions in the catalog. I wrote these
labels by hand before running the scorers, so they are my opinion of a "good
list", not the output of any model. They are the yardstick used in evaluate.py.
"""

PROFILES = {
    "Default Pop/Happy": {"genre": "pop", "mood": "happy", "energy": 0.8},
    "High-Energy Pop": {"genre": "pop", "mood": "intense", "energy": 0.9},
    "Chill Lofi": {"genre": "lofi", "mood": "chill", "energy": 0.35},
    "Deep Intense Rock": {"genre": "rock", "mood": "intense", "energy": 0.92},
    # Profiles that use the extra features only version 2 can score
    "Quiet Acoustic Study": {"genre": "ambient", "mood": "focused", "energy": 0.3,
                             "likes_acoustic": True, "tempo_bpm": 70},
    "Workout EDM": {"genre": "edm", "mood": "euphoric", "energy": 0.95,
                    "danceability": 0.9, "tempo_bpm": 130},
    "Romantic Evening": {"genre": "r&b", "mood": "romantic", "energy": 0.5, "valence": 0.7},
    # Adversarial / edge-case profiles
    "Conflicting: high energy + sad": {"genre": "blues", "mood": "sad", "energy": 0.9},
    "Unknown genre (bossa nova)": {"genre": "bossa nova", "mood": "relaxed", "energy": 0.4},
    "Mid-everything": {"genre": "folk", "mood": "relaxed", "energy": 0.5},
}

RELEVANT = {
    "Default Pop/Happy": {"Sunrise City", "Rooftop Lights", "Seoul Static",
                          "Pop Confetti", "Salt & Sunday"},
    "High-Energy Pop": {"Gym Hero", "Idol Hours", "Neon Pulse", "Rave Cathedral", "Storm Runner"},
    "Chill Lofi": {"Library Rain", "Midnight Coding", "Focus Flow",
                   "Rainy Window Beats", "Spacewalk Thoughts"},
    "Deep Intense Rock": {"Storm Runner", "Burn the Map", "Hollow Anthem",
                          "Wildfire Riff", "Gym Hero"},
    "Quiet Acoustic Study": {"Spacewalk Thoughts", "Cathedral Strings", "Library Rain",
                             "Daybreak Choir", "Quiet Fields", "Focus Flow"},
    "Workout EDM": {"Neon Pulse", "Idol Hours", "Rave Cathedral", "Chrome Horizon", "Gym Hero"},
    "Romantic Evening": {"Velvet Hours", "Afterglow Avenue", "Sol y Sombra",
                         "Smoke & Satin", "Coffee Shop Stories"},
    "Conflicting: high energy + sad": {"Static Heart", "Blue Monday Groove",
                                       "Hollow Anthem", "Burn the Map"},
    "Unknown genre (bossa nova)": {"Coffee Shop Stories", "Lantern Walk", "Rainy Window Beats",
                                   "Tidewater", "Island Drift"},
    "Mid-everything": {"Lantern Walk", "Porch Light Folk", "Coffee Shop Stories",
                       "Island Drift", "Dust Road Home"},
}
