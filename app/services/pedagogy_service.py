"""
pedagogy_service.py — Generación de planes pedagógicos con el modelo T5 local.
El modelo se carga una sola vez (lazy) para no ralentizar el arranque del servidor.
"""

import os
from typing import List, Dict, Any

_model = None
_tokenizer = None

# pedagogy_model/ está en la raíz del proyecto (dos niveles arriba de app/services/)
_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "pedagogy_model")
)


def _load_model():
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer
    try:
        from transformers import T5ForConditionalGeneration, T5Tokenizer
        _tokenizer = T5Tokenizer.from_pretrained(_MODEL_PATH, local_files_only=True)
        _model = T5ForConditionalGeneration.from_pretrained(_MODEL_PATH, local_files_only=True)
        _model.eval()
    except Exception as e:
        print(f"⚠ pedagogy_model no disponible: {e}")
        _model = None
        _tokenizer = None
    return _model, _tokenizer


def generate_plan_with_model(problems: List[Dict[str, Any]]) -> str:
    errors = [p for p in problems if p.get("isCorrect") is False]
    if not errors:
        return (
            "🌟 ¡Excelente trabajo! El estudiante domina todos los temas evaluados.\n"
            "✅ Sugerencia: ejercicios de ampliación y retos adicionales."
        )

    # Construir prompt para el modelo con los errores únicos por subTipo
    seen: set = set()
    error_parts: List[str] = []
    for p in errors:
        sub = p.get("subType", "+")
        op = (p.get("operation") or "")[:40]
        if sub not in seen:
            seen.add(sub)
            error_parts.append(f"{sub}: {op}" if op else sub)

    prompt = "genera plan pedagogico: " + "; ".join(error_parts)

    try:
        model, tokenizer = _load_model()
        if model is None or tokenizer is None:
            return _fallback_plan(problems)

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            max_length=512,
            truncation=True,
        )
        outputs = model.generate(
            **inputs,
            max_new_tokens=200,
            num_beams=4,
            early_stopping=True,
            no_repeat_ngram_size=3,
        )
        plan = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        return plan if plan else _fallback_plan(problems)

    except Exception:
        return _fallback_plan(problems)


def _fallback_plan(problems: List[Dict[str, Any]]) -> str:
    from .ocr_service import generate_teaching_plan
    return generate_teaching_plan(problems)
