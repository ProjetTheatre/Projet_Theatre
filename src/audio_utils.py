import sounddevice as sd
import soundfile as sf
from pathlib import Path
import numpy as np

def record_to_wav(outfile: str, seconds: float = 6.0, samplerate: int = 16000):
    Path(outfile).parent.mkdir(parents=True, exist_ok=True)
    print(f"🎙️ Enregistrement {seconds:.1f}s...")
    audio = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1, dtype='float32')
    sd.wait()
    sf.write(outfile, audio, samplerate)
    print(" Enregistrement terminé.")
    return outfile

def beep():
    fs = 44100
    t = 0.15
    f = 880
    samples = (np.sin(2*np.pi*np.arange(fs*t)*f/fs)).astype('float32')
    sd.play(samples, fs)
    sd.wait()
