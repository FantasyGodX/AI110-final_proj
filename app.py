"""Streamlit front end for VibeFinder 2.0.  Run with:  streamlit run app.py"""

import streamlit as st

from src.agent import MAX_QUERY_CHARS, format_result, load_system, run_agent, supporting_docs
from src.recommender import (
    MODES, assess_confidence, coverage_notes, load_songs, max_score, mismatch_notes,
    recommend_songs,
)

MODE_HELP = {
    "classic": "The original VibeFinder 1.0 recipe: genre, mood, energy, exact labels only.",
    "balanced": "All features, with partial credit for related genres and moods.",
    "genre_first": "Genre counts the most.",
    "mood_first": "Mood counts the most.",
    "vibe_first": "Sound features (energy, valence, danceability, acousticness) count the most.",
}

st.set_page_config(page_title="VibeFinder 2.0", page_icon="🎵")
st.title("🎵 VibeFinder 2.0")
st.caption("A content-based music recommender that explains every pick.")

STATUS_LABEL = {
    "ok": ("success", "All of my checks passed."),
    "needs_review": ("warning", "My own checks flagged this result. Please review it."),
    "needs_clarification": ("info", "I need a clearer request."),
    "rejected": ("error", "That request could not be used."),
}


@st.cache_resource
def get_system():
    return load_system()


tab_ask, tab_manual = st.tabs(["Ask in plain words", "Pick your taste"])

with tab_ask:
    st.write("Describe what you want to listen to. The system retrieves matching knowledge, "
             "builds a taste profile from it, checks its own result, and shows every step.")
    query = st.text_input("What do you want to listen to?", max_chars=MAX_QUERY_CHARS,
                          placeholder="something calm to study to late at night")
    n_songs = st.slider("Songs to return", 1, 10, 5, key="ask_k")
    if query:
        ask_songs, ask_docs, ask_retriever = get_system()
        result = run_agent(query, ask_songs, ask_retriever, n_songs)
        kind, text = STATUS_LABEL[result.status]
        getattr(st, kind)(text)
        st.write(result.message)
        for note in result.notes:
            st.warning(note)
        if result.citations:
            st.subheader("What I retrieved")
            for c in result.citations:
                st.markdown(f"- **{c['title']}** ({c['type']}, relevance {c['score']:.2f}): {c['text']}")
        for rank, (song, score, why) in enumerate(result.recs, 1):
            with st.container(border=True):
                st.markdown(f"**{rank}. {song['title']}** by {song['artist']}  \n"
                            f"`{song['genre']}` · `{song['mood']}`")
                st.progress(min(max(score / result.max_score, 0.0), 1.0),
                            text=f"Score {score:.2f} / {result.max_score:.2f}")
                support = supporting_docs(song, result.citations, ask_docs)
                if support:
                    st.caption("Supported by: " + ", ".join(support))
                with st.expander("Why this song?"):
                    for reason in why.split("; "):
                        st.write(f"- {reason}")
        with st.expander("Agent trace (every step it took)"):
            for step in result.trace:
                st.code(f"[{step.name}] {step.detail}", language=None)

with tab_manual:
    @st.cache_data
    def get_songs():
        return load_songs("data/songs.csv")


    songs = get_songs()
    genres = sorted({s["genre"] for s in songs})
    moods = sorted({s["mood"] for s in songs})

    with st.sidebar:
        st.header("Your taste")
        genre = st.selectbox("Favorite genre", genres, index=genres.index("pop"))
        mood = st.selectbox("Favorite mood", moods, index=moods.index("happy"))
        energy = st.slider("Target energy", 0.0, 1.0, 0.7, 0.05)
        with st.expander("Optional: fine-tune"):
            use_valence = st.checkbox("Set positivity (valence)")
            valence = st.slider("Target valence", 0.0, 1.0, 0.7, 0.05, disabled=not use_valence)
            use_dance = st.checkbox("Set danceability")
            dance = st.slider("Target danceability", 0.0, 1.0, 0.7, 0.05, disabled=not use_dance)
            use_acoustic = st.checkbox("Prefer acoustic or electronic sound")
            likes_acoustic = st.radio("Sound", ["Acoustic", "Electronic"], disabled=not use_acoustic)
            use_tempo = st.checkbox("Set tempo")
            tempo = st.slider("Target tempo (BPM)", 40, 220, 100, 5, disabled=not use_tempo)

        st.header("Settings")
        mode = st.selectbox("Scoring mode", list(MODES), index=list(MODES).index("balanced"))
        st.caption(MODE_HELP[mode])
        diversity = st.slider("Variety (penalty for repeats)", 0.0, 0.3, 0.05, 0.01)
        k = st.slider("Number of songs", 1, 10, 5)

    prefs = {"genre": genre, "mood": mood, "energy": energy}
    if use_valence:
        prefs["valence"] = valence
    if use_dance:
        prefs["danceability"] = dance
    if use_acoustic:
        prefs["likes_acoustic"] = likes_acoustic == "Acoustic"
    if use_tempo:
        prefs["tempo_bpm"] = tempo

    recs = recommend_songs(prefs, songs, k, mode, diversity)
    top = max_score({**prefs, **({"acousticness": 0.8 if prefs["likes_acoustic"] else 0.2}
                                 if "likes_acoustic" in prefs else {})}, mode)
    label, ratio = assess_confidence(recs, prefs, mode)

    badge = {"high": "🟢", "medium": "🟡", "low": "🔴"}[label]
    st.subheader(f"Top {len(recs)} for you")
    st.write(f"{badge} Confidence: **{label}** ({ratio:.0%} of the best possible score)")
    for note in coverage_notes(prefs, songs):
        st.info(note)
    if recs:
        for note in mismatch_notes(recs[0][0], prefs):
            st.warning(f"Top pick {note}")
    if label == "low":
        st.error("No strong match in the catalog. Treat these as best guesses.")

    for rank, (song, score, why) in enumerate(recs, 1):
        with st.container(border=True):
            st.markdown(f"**{rank}. {song['title']}** by {song['artist']}  \n"
                        f"`{song['genre']}` · `{song['mood']}` · energy {song['energy']:.2f} · "
                        f"{song['tempo_bpm']:.0f} BPM")
            st.progress(min(max(score / top, 0.0), 1.0) if top else 0.0,
                        text=f"Score {score:.2f} / {top:.2f}")
            with st.expander("Why this song?"):
                for reason in why.split("; "):
                    st.write(f"- {reason}")
