import tempfile
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel


class SpeechRecognizer:
    def __init__(self, model_size="small", device="cpu", language="fr"):
        compute = "int8" if device == "cpu" else "float16"
        self.model = WhisperModel(model_size, device=device, compute_type=compute)
        self.language = language
        self.samplerate = 16000  # recommandé pour Whisper

    def transcribe(self, wav_path: str) -> str:
        """Transcrit un fichier WAV en texte avec Whisper"""
        segments, _ = self.model.transcribe(wav_path, language=self.language, vad_filter=True)
        return " ".join([s.text for s in segments]).strip()

    def record_and_transcribe(self, duration=6) -> str:
        """Enregistre depuis le micro (duration en secondes) puis transcrit"""
        print(f" Enregistrement du micro pendant {duration}s...")
        audio = sd.rec(int(duration * self.samplerate), samplerate=self.samplerate, channels=1, dtype="float32")
        sd.wait()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            sf.write(tmp.name, audio, self.samplerate)
            wav_path = tmp.name

        return self.transcribe(wav_path)
