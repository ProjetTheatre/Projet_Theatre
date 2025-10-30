import json
from dataclasses import dataclass
from typing import List, Optional
from rapidfuzz import fuzz

@dataclass
class Line:
    speaker: str
    text: str

class ScriptRunner:
    def __init__(self, script_path: str, ai_character: Optional[str] = None):
        data = json.load(open(script_path, "r", encoding="utf-8"))
        self.title = data.get("title", "Scène")
        self.language = data.get("language", "fr")
        self.ai_character = (ai_character or data.get("ai_character", "")).upper()
        self.lines: List[Line] = [Line(l["speaker"].upper(), l["text"]) for l in data["lines"]]
        self.idx = 0

    def current_line(self) -> Optional[Line]:
        return self.lines[self.idx] if self.idx < len(self.lines) else None

    def is_ai_turn(self) -> bool:
        cur = self.current_line()
        return bool(cur and cur.speaker == self.ai_character)

    def advance(self):
        self.idx += 1

    def validate_actor_line(self, actor_text: str, threshold: int = 70) -> (bool, int):
        cur = self.current_line()
        if not cur:
            return False, 0
        score = fuzz.partial_ratio(actor_text.lower(), cur.text.lower())
        return score >= threshold, score
