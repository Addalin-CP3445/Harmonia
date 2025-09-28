# app.py
import os
import streamlit as st
from dotenv import load_dotenv
from llm import guess_preset, generate_quote
from music_tools import recommend_tracks


load_dotenv()


st.set_page_config(page_title="MoodMate", page_icon="🎧", layout="centered")

st.title("🎧 MoodMate — Music & Quotes")
st.caption("Local LLM via Ollama + Spotify recs")

with st.sidebar:
    st.header("Settings")
    model = st.text_input("Ollama model", os.getenv("OLLAMA_MODEL", "llama3:8b"))
    limit = st.slider("# of tracks", 5, 20, 10)
    st.markdown("---")
    ok_sp = bool(os.getenv("SPOTIFY_CLIENT_ID") and os.getenv("SPOTIFY_CLIENT_SECRET"))
    st.write("Spotify keys:", "✅" if ok_sp else "❌")
    if not ok_sp:
        st.info("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env")

user_text = st.text_input("How do you feel?", placeholder="e.g., Sleepy but need to focus for an exam…")

colA, colB = st.columns(2)
with colA:
    do_music = st.button("Recommend Music 🎵", use_container_width=True)
with colB:
    do_quote = st.button("Give me a Quote ✨", use_container_width=True)

if (do_music or do_quote) and not user_text.strip():
    st.warning("Please describe your mood first.")

if user_text and (do_music or do_quote):
    with st.spinner("Thinking…"):
        preset = guess_preset(user_text, model_name=model)
        st.subheader("Preset")
        st.write({
        "bucket": preset.bucket,
        "energy": round(preset.energy, 2),
        "valence": round(preset.valence, 2),
        "seed_genres": preset.seed_genres,
        })

        if do_music:
            tracks = recommend_tracks(
            bucket=preset.bucket,
            energy=preset.energy,
            valence=preset.valence,
            limit=limit,
            )
            st.subheader("Suggestions")
            for t in tracks:
                with st.container(border=True):
                    c1, c2 = st.columns([1,3])
                    with c1:
                        if t.get("album_image"):
                            st.image(t["album_image"], use_container_width=True)
                        with c2:
                            st.markdown(f"**{t['title']}** — {t['artists']}")
                            st.caption(t["album"])
                            link = t.get("spotify_url")
                            prev = t.get("preview_url")
                            if link:
                                st.markdown(f"[Open in Spotify]({link})")
                            if prev:
                                st.audio(prev)

        if do_quote:
            st.subheader("Quote")
            q = generate_quote(preset.bucket, context=user_text, model_name=model)
            st.markdown(f"> {q}")

st.markdown("---")
st.caption("Tip: Change the Ollama model in the sidebar (e.g., mistral:7b, llama3:instruct). Ensure it's pulled via `ollama pull`. ")