import streamlit as st
import json
import time
import os
from pathlib import Path
import tempfile
from audio_recorder_streamlit import audio_recorder

from config import (
    DEVICE, LANGUAGE, WHISPER_MODEL_SIZE,
    SIMILARITY_THRESHOLD, AI_CHARACTER_DEFAULT
)

from src.script_runner import ScriptRunner, parse_txt_script, parse_docx_script
from src.stt import SpeechRecognizer
from src.tts_synth import VoiceSynth

# ============================
# UI CONFIG
# ============================
st.set_page_config(page_title="IA partenaire théâtre", page_icon="🎭", layout="centered")
st.title("🎭 IA partenaire de répétition — V2 (mobile compatible)")

# Crée le dossier temporaire
Path("temp").mkdir(exist_ok=True)

# ============================
# UPLOAD SCRIPT
# ============================
script_file = st.file_uploader("📜 Importer votre script (.json, .txt ou .docx)", type=["json", "txt", "docx"])

if not script_file:
    st.info("Dépose un script pour commencer (format: JSON, TXT ou DOCX).")
    st.stop()

# Parse selon le type de fichier
if script_file.name.endswith(".json"):
    data = json.load(script_file)
elif script_file.name.endswith(".txt"):
    data = parse_txt_script(script_file, ai_character=AI_CHARACTER_DEFAULT)
else:
    data = parse_docx_script(script_file)

runner = ScriptRunner(data=data)

st.success(f"✅ Script chargé : **{runner.title}**")
st.caption(f"Langue : {runner.language} • Répliques : {len(runner.lines)}")

# ============================
# CHOIX DU PERSONNAGE + MODE
# ============================
speakers = sorted(list(runner.speakers))
default_idx = 0 if AI_CHARACTER_DEFAULT.upper() not in speakers else speakers.index(AI_CHARACTER_DEFAULT.upper())
your_role = st.selectbox("🎭 Quel personnage joues-tu ?", speakers, index=default_idx)
runner.set_user_character(your_role)

mode = st.radio("Mode :", ["Performance (score global à la fin)", "Répétition (feedback à chaque réplique)"], horizontal=True)

# ============================
# TTS BACKEND + PARAMS
# ============================
backend = st.selectbox("Synthèse vocale IA (TTS)", ["gtts"])  # gTTS = léger et compatible cloud
custom_voice_path = None
hf_token = st.secrets.get("HF_TOKEN", "")

# Init STT/TTS
stt = SpeechRecognizer(model_size=WHISPER_MODEL_SIZE, device=DEVICE, language=LANGUAGE)
tts = VoiceSynth(backend=backend, language="fr")

# ============================
# SESSION STATE
# ============================
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "results" not in st.session_state:
    st.session_state.results = []
if "cache_dir" not in st.session_state:
    st.session_state.cache_dir = "cache_tts"
    os.makedirs(st.session_state.cache_dir, exist_ok=True)
if "cache_tts" not in st.session_state:
    st.session_state.cache_tts = {}  # {line_index: outfile_path}

# ============================
# PRÉ-GÉNÉRATION TTS (FLUIDITÉ)
# ============================
def pregenerate_ai_audio():
    progress = st.progress(0, text="Préparation des voix IA…")
    ai_indexes = [i for i, ln in enumerate(runner.lines) if ln.speaker != runner.user_character]
    total = len(ai_indexes)
    for k, i in enumerate(ai_indexes, start=1):
        line = runner.lines[i]
        base = f"{i:04d}_{line.speaker}"
        outfile = os.path.join(st.session_state.cache_dir, base + (".mp3" if backend == "gtts" else ".wav"))
        if not os.path.exists(outfile):
            tts.speak(line.text, outfile=outfile, autoplay=False)
        st.session_state.cache_tts[i] = outfile
        progress.progress(k / total, text=f"Préparation des voix IA… ({k}/{total})")
    progress.empty()
    st.success("✅ Voix IA prégénérées. La scène sera fluide 👌")

st.button("⚡ Précharger toutes les répliques IA", on_click=pregenerate_ai_audio)

# ============================
# LECTURE AUTOMATIQUE DE LA SCÈNE
# ============================
def play_one_ai_line(i):
    """Fait parler l'IA (lecture auto + attend la fin de la réplique)"""
    line = runner.lines[i]
    outfile = st.session_state.cache_tts.get(i)
    if not outfile:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir=st.session_state.cache_dir)
        outfile = tts.speak(line.text, outfile=tmp.name, autoplay=True)
        st.session_state.cache_tts[i] = outfile
    else:
        tts.speak(line.text, outfile=outfile, autoplay=True)

    words = len(line.text.split())
    estimated_duration = max(2, words / 2.5)
    time.sleep(estimated_duration)

def run_scene_automatic():
    scores_buffer = []
    with st.spinner("🎬 La scène se joue automatiquement…"):
        i = st.session_state.idx
        while i < len(runner.lines):
            line = runner.lines[i]
            st.subheader(f"{line.speaker}")
            st.write(line.text)

            if line.speaker != runner.user_character:
                play_one_ai_line(i)
                time.sleep(0.5)

            else:   
                # 🎙️ Enregistrement via navigateur (téléphone/PC)
                st.info("🎤 À toi ! Appuie pour parler puis clique sur 'Valider'")
                audio_bytes = audio_recorder(text="Appuyer pour parler (max ~6s)")

                # On n’arrête pas tout, on attend juste que l’utilisateur enregistre quelque chose
                if audio_bytes:
                    if st.button("➡️ Valider l'enregistrement", key=f"val_{i}"):
                        wav_path = "temp/actor.wav"
                        with open(wav_path, "wb") as f:
                            f.write(audio_bytes)
                        # ... suite (transcription, score, etc.)
                        i += 1
                        st.session_state.idx = i
                        st.rerun()

                if st.button("➡️ Valider l'enregistrement", key=f"val_{i}"):
                    wav_path = "temp/actor.wav"
                    with open(wav_path, "wb") as f:
                        f.write(audio_bytes)

                    transcript = stt.transcribe(wav_path)
                    st.caption(f"Vous avez dit : {transcript}")

                    ok, score = runner.validate_actor_line(transcript, threshold=SIMILARITY_THRESHOLD)
                    if mode.startswith("Répétition"):
                        st.write(f"Similarité : {score:.1f}% (seuil {SIMILARITY_THRESHOLD})")
                        if ok:
                            st.success("✅ Réplique validée")
                        else:
                            st.error("❌ Trop différent")
                    else:
                        scores_buffer.append(score)

                    i += 1
                    st.session_state.idx = i
                    st.rerun()

            i += 1
            st.session_state.idx = i
            time.sleep(0.3)

    st.success("🏁 Fin de la scène.")
    tts.cleanup()

    if mode.startswith("Performance") and scores_buffer:
        final_score = round(sum(scores_buffer) / len(scores_buffer), 1)
        st.subheader("📊 Résultat final")
        st.write(f"Score global : **{final_score}%**")

        if final_score >= SIMILARITY_THRESHOLD:
            st.success("✅ Scène réussie !")
        else:
            st.warning("⚠️ Scène à retravailler un peu.")

    # ============================
    # 🔁 Bouton de retour au menu
    # ============================
    if "should_reset" not in st.session_state:
        st.session_state.should_reset = False

    def ask_reset():
        st.session_state.should_reset = True

    st.divider()
    st.button("↩️ Revenir au menu principal", on_click=ask_reset)

    if st.session_state.should_reset:
        for key in ["idx", "results", "cache_tts", "should_reset"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.divider()

# ============================
# OPTIONS
# ============================
direct_mode = st.checkbox("⏩ Enchaînement direct (sans délai entre les répliques)", value=False)
st.session_state.direct_mode = direct_mode

st.button("🎭 Lancer la scène (automatique)", on_click=run_scene_automatic)
