# llm.py
from typing import Literal, TypedDict
from pydantic import BaseModel, Field
import json
import os

from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate


DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")

class PresetOut(BaseModel):
    bucket: Literal["focus", "energize", "calm"] = Field(..., description="One of focus/energize/calm")
    energy: float = Field(..., ge=0.0, le=1.0)
    valence: float = Field(..., ge=0.0, le=1.0)
    seed_genres: list[str] = Field(default_factory=list, min_items=1, max_items=5)

# Guard-rail: if LLM fails, fall back to heuristic
_DEF_PRESETS = {
"focus": {"energy": 0.35, "valence": 0.4, "seed_genres": ["focus", "lofi", "classical"]},
"energize": {"energy": 0.8, "valence": 0.7, "seed_genres": ["electronic", "pop", "dance"]},
"calm": {"energy": 0.2, "valence": 0.5, "seed_genres": ["ambient", "acoustic", "chill"]},
}

_preset_prompt = ChatPromptTemplate.from_messages([
    ("system", (
    "You classify a user's short mood text into a music preset and return STRICT JSON.\n"
    "Buckets: focus | energize | calm.\n"
    "Choose seed_genres (1-5) valid for Spotify like focus, lofi, classical, electronic, pop, dance, ambient, acoustic, chill.\n"
    "Pick target_energy (0-1) and target_valence (0-1) consistent with the bucket.\n"
    "OUTPUT JSON ONLY with keys: bucket, energy, valence, seed_genres. No prose."
    )),
    ("human", "User mood/context: {text}\nReturn JSON now.")
])

_quote_prompt = ChatPromptTemplate.from_messages([
    ("system", (
    "You write a SHORT, original quote (<= 18 words), no author attribution, for the given mood bucket.\n"
    "Tone: supportive and crisp. Output ONLY the quote text, nothing else."
    )),
    ("human", "Bucket: {bucket}. Context: {context}")
])

def _chat(model_name: str | None = None) -> ChatOllama:
    return ChatOllama(model=model_name or DEFAULT_MODEL, temperature=0.3)

def guess_preset(user_text: str, model_name: str | None = None) -> PresetOut:
    """Ask Ollama to produce a preset; fall back safely if parsing fails."""
    llm = _chat(model_name)
    msg = _preset_prompt.format_messages(text=user_text)
    out = llm.invoke(msg).content
    try:
        data = json.loads(out)
        return PresetOut(**data)
    except Exception:
    # Heuristic fallback
        t = user_text.lower()
        if any(k in t for k in ["sleepy", "tired", "focus", "study", "concentrat"]):
            b = "focus"
        elif any(k in t for k in ["gym", "motivat", "energy", "pump", "workout"]):
            b = "energize"
        elif any(k in t for k in ["anxious", "stress", "calm", "relax", "overwhelm"]):
            b = "calm"
        else:
            b = "focus"
        d = _DEF_PRESETS[b]
        return PresetOut(bucket=b, energy=d["energy"], valence=d["valence"], seed_genres=d["seed_genres"])
    
def generate_quote(bucket: Literal["focus", "energize", "calm"], context: str = "", model_name: str | None = None) -> str:
    llm = _chat(model_name)
    msg = _quote_prompt.format_messages(bucket=bucket, context=context)
    quote = llm.invoke(msg).content.strip().strip('"')
    # Ensure it's single-line and short
    return " ".join(quote.split())[:180]