import os
from typing import Optional
import requests
from dotenv import load_dotenv

# 1. .env dosyasını bul ve yükle
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)


def _fallback_text(rec: dict) -> str:
    rules = rec.get("rules_fired") or []
    signals = rec.get("signals_used") or {}
    congestion = signals.get("congestion_level", "uncertain")
    mempool = signals.get("mempool_tx_count", "unknown")
    
    # Translation: TR -> EN
    return (
        f"Recommendation produced by deterministic rules. Rules: {', '.join(rules) if rules else 'none'}. "
        f"Mempool tx count: {mempool}, congestion: {congestion}. "
        "Explanation generated locally because Gemini is disabled or unavailable."
    )


def generate_llm_explanation(recommendation: dict) -> Optional[str]:
    """Generate English explanation via Gemini; fallback to local summary when unavailable."""
    if not GEMINI_API_KEY:
        # API anahtarı yoksa hiç LLM metni dönmeyerek UI'yı sade tut.
        return None

    bullets = recommendation.get("explanation") or []
    rules = ", ".join(recommendation.get("rules_fired") or [])
    signals = recommendation.get("signals_used") or {}
    
    # Prompt Translation: TR -> EN (Gemini'ye İngilizce konuşmasını söylüyoruz)
    prompt = (
        "Generate an English explanation. 1 paragraph + 3 bullet points + 1 risk note. "
        "Summarize the rules and signals used. "
        "Keep bullet points short.\n"
        f"Rules: {rules}\n"
        f"Signals: {signals}\n"
        "Explanation points from logic:\n"
        + "\n".join(f"- {b}" for b in bullets)
    )
    
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                ]
            }
        ]
    }

    try:
        resp = requests.post(
            GEMINI_ENDPOINT, params={"key": GEMINI_API_KEY}, json=body, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return _fallback_text(recommendation)
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [p.get("text", "") for p in parts if p.get("text")]
        combined = " ".join(texts).strip()
        return combined or _fallback_text(recommendation)
    except Exception as e:
        # Hatayı terminale kırmızı renkli ve detaylı yazdırıyoruz
        print(f"\n❌ LLM ERROR DETAYI: {e}\n")
        return _fallback_text(recommendation)