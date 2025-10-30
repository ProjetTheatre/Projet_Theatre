import json
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from rapidfuzz import fuzz

# ============================
# Modèle de ligne
# ============================

@dataclass
class Line:
    speaker: str
    text: str

# ============================
# Normalisation & Score
# ============================

def normalize_text(txt: str) -> str:
    """Nettoie le texte pour comparaison tolérante."""
    txt = txt.lower()
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    txt = re.sub(r"[^a-z0-9\s]", " ", txt)
    return " ".join(txt.split())

def fuzzy_score(ref: str, hyp: str) -> int:
    ref_n = normalize_text(ref)
    hyp_n = normalize_text(hyp)
    return fuzz.ratio(ref_n, hyp_n)

# ============================
# Parseurs (txt, docx)
# ============================

def parse_txt_script(txt_file, ai_character="IA") -> Dict[str, Any]:
    """
    Parse un .txt en script JSON-like.
    Format attendu : une ligne = "PERSONNAGE: texte"
    """
    content = txt_file.read().decode("utf-8", errors="ignore")
    lines = []
    for raw in content.splitlines():
        if ":" in raw:
            speaker, text = raw.split(":", 1)
            lines.append({"speaker": speaker.strip().upper(), "text": text.strip()})
    return {
        "title": "Script importé (.txt)",
        "language": "fr",
        "ai_character": ai_character,
        "lines": lines
    }

def parse_docx_script(docx_file) -> Dict[str, Any]:
    """
    Parse un .docx (Word) en script JSON-like.
    Format recommandé : une ligne = "PERSONNAGE: texte"
    """
    from docx import Document
    doc = Document(docx_file)
    lines = []
    for para in doc.paragraphs:
        raw = para.text.strip()
        if ":" in raw:
            speaker, text = raw.split(":", 1)
            lines.append({"speaker": speaker.strip().upper(), "text": text.strip()})
    return {
        "title": "Script importé (.docx)",
        "language": "fr",
        "lines": lines
    }

# ============================
# ScriptRunner
# ============================

class ScriptRunner:
    def __init__(self, script_path: Optional[str] = None, ai_character: Optional[str] = None, data: Optional[dict] = None):
        """
        Initialise à partir d'un fichier JSON (script_path) ou d'un dict (data).
        Détecte automatiquement tous les personnages.
        """
        if data is None and script_path:
            with open(script_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        if data is None:
            raise ValueError("❌ ScriptRunner: il faut fournir soit script_path, soit data")

        self.title = data.get("title", "Scène")
        self.language = data.get("language", "fr")
        self.lines: List[Line] = [Line(l["speaker"].upper(), l["text"]) for l in data.get("lines", [])]

        # Détection des personnages
        self.speakers = {ln.speaker for ln in self.lines}
        # Personnage joué par l'utilisateur (à définir via set_user_character)
        self.user_character: Optional[str] = None

        self.idx = 0

    def set_user_character(self, name: str):
        self.user_character = (name or "").upper()

    def current_line(self) -> Optional[Line]:
        return self.lines[self.idx] if self.idx < len(self.lines) else None

    def is_ai_turn(self) -> bool:
        cur = self.current_line()
        if not cur:
            return False
        if not self.user_character:
            return True  # si user non défini, tout est IA
        return cur.speaker != self.user_character

    def advance(self):
        self.idx += 1

    def validate_actor_line(self, actor_text: str, threshold: int = 70, debug: bool = False) -> (bool, int):
        """
        Compare la réplique attendue (ligne courante) avec ce que dit le comédien :
        - Normalisation tolérante
        - Similarité fuzzy globale (fuzz.ratio)
        """
        cur = self.current_line()
        if not cur:
            return False, 0

        score = fuzzy_score(cur.text, actor_text)

        if debug:
            print("[DEBUG] REF:", normalize_text(cur.text))
            print("[DEBUG] HYP:", normalize_text(actor_text))
            print("[DEBUG] SCORE:", score)

        return score >= threshold, score
