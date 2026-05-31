"""
pedagogy_service.py — Generación de planes pedagógicos.
Usa la lógica pedagógica basada en reglas de ocr_service para generar el plan.
El directorio pedagogy_model/ (modelo T5 local) está excluido de git por .gitignore.
"""

from typing import List, Dict, Any


def generate_plan_with_model(problems: List[Dict[str, Any]]) -> str:
    from .ocr_service import generate_teaching_plan
    return generate_teaching_plan(problems)
