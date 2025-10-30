import os
import tempfile
import base64
import time
from gtts import gTTS
import streamlit as st

class VoiceSynth:
    def __init__(self, backend="gtts", language="fr", hf_token=None):
        self.backend = backend
        self.language = language
        self.temp_dir = "outputs/tts"
        os.makedirs(self.temp_dir, exist_ok=True)

    def speak(self, text, outfile=None, autoplay=True):
        """
        Génère un audio et, si autoplay=True, le joue directement sans afficher de lecteur visible.
        """
        if outfile is None:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir=self.temp_dir)
            outfile = tmp.name

        # Génération avec gTTS
        tts = gTTS(text=text, lang=self.language)
        tts.save(outfile)

        if autoplay:
            # Lecture auto via HTML audio tag caché
            try:
                with open(outfile, "rb") as f:
                    audio_bytes = f.read()
                b64 = base64.b64encode(audio_bytes).decode()
                audio_html = f"""
                <audio autoplay hidden>
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
                """
                st.markdown(audio_html, unsafe_allow_html=True)
            except Exception as e:
                st.warning(f"Erreur lecture auto : {e}")

        return outfile

    def cleanup(self):
        """Supprime les fichiers audio temporaires"""
        for f in os.listdir(self.temp_dir):
            if f.endswith(".mp3"):
                try:
                    os.remove(os.path.join(self.temp_dir, f))
                except Exception:
                    pass
