# src/stt.py
from faster_whisper import WhisperModel

class SpeechRecognizer:
    def __init__(self, model_size="base", device="cpu", language="fr"):
        # int8 = léger en CPU; passe en "float32" si souci de qualité
        compute = "int8" if device == "cpu" else "float16"
        self.model = WhisperModel(model_size, device=device, compute_type=compute)
        self.language = language

    def transcribe(self, audio_path: str) -> str:
        """
        Transcrit un fichier audio (wav/mp3) via faster-whisper.
        """
        segments, _ = self.model.transcribe(
            audio_path,
            language=self.language,
            vad_filter=True,
            beam_size=5,
        )
        return " ".join(seg.text for seg in segments).strip()
