"""
ocr_service.py — EMAI-APP v5

Estrategia principal:
- Preprocesamiento: aumentar brillo/contraste para resaltar tinta negra
- Parser basado en '=' como ancla de problemas matemáticos
- Detecta secciones (A)(B)(C) y puntos 1. 2. 3.
- Evalúa la expresión izquierda del = y compara con la respuesta derecha
"""

import base64
import io
import re
import uuid
from fractions import Fraction
from typing import List, Dict, Any, Optional

from PIL import Image, ImageEnhance, ImageOps, ImageFilter

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

import os
_TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if OCR_AVAILABLE and os.path.exists(_TESS):
    pytesseract.pytesseract.tesseract_cmd = _TESS

# ─── PEDAGOGÍA ────────────────────────────────────────────────────────────────
PEDAGOGIA: Dict[str, List[str]] = {
    "+":         ["🔢 Usa la recta numérica para visualizar la suma.", "🧮 Practica agrupando objetos concretos.", "🎯 Completa: 3+__=7."],
    "-":         ["🔢 Tacha lo que se quita para visualizar la resta.", "🧮 Usa la recta numérica hacia la izquierda.", "🎯 ¿Cuánto falta para llegar a 10?"],
    "*":         ["🔢 Multiplicar = sumar varias veces: 3×4 = 4+4+4.", "🧮 Dibuja arreglos de puntos en filas.", "🎯 Aprende las tablas con canciones."],
    "/":         ["🔢 Dividir = repartir en grupos iguales.", "🧮 Usa fichas y repártelas en grupos.", "🎯 ¿Cuántas veces cabe 3 en 12?"],
    "FRACTION":  ["🔢 Dibuja el entero dividido en partes iguales.", "🧮 Dobla papel para ver mitades y cuartos.", "🎯 ½ + ¼ = ¾. Dibuja dos círculos partidos."],
    "HIERARCHY": ["🔢 PEMDAS: Paréntesis primero, luego × ÷, luego + −.", "🧮 Encierra en un cuadro lo que va primero.", "🎯 (2+3)×4 = 5×4 = 20. Siempre el paréntesis."],
    ">":         ["🐊 El cocodrilo come al número más grande.", "🧮 Dibuja ambos grupos y compara cuál es mayor.", "🎯 5 > 3 porque 5 está a la derecha en la recta."],
    "<":         ["🐊 El pico apunta al número más pequeño.", "🧮 Ordena en la recta numérica.", "🎯 Ejercicio: completa 4 __ 9 con > o <."],
    "=":         ["🔢 Igualdad: ambos lados tienen el mismo valor.", "🧮 Usa una balanza: pesa lo mismo a cada lado.", "🎯 ¿3+4 = 8−1? Verifica los dos lados."],
    "POTENCIA":  ["🔢 2³ = 2×2×2 (no es 2×3).", "🧮 Escribe: base × base × base...", "🎯 2¹=2, 2²=4, 2³=8. Observa el patrón."],
    "RAIZ":      ["🔢 √9=3 porque 3×3=9.", "🧮 Pregúntate: ¿qué número × él mismo da esto?", "🎯 Memoriza: √1=1, √4=2, √9=3, √16=4, √25=5."],
    "FACTOR":    ["🔢 Factorizar = encontrar los ingredientes del número.", "🧮 Divide entre 2, 3, 5, 7...", "🎯 12 = 2×2×3. Dibuja el árbol."],
    "UNIDADES":  ["📏 Escalera: km→hm→dam→m→dm→cm→mm (×10 cada escalón).", "🧮 Bajar = ×10. Subir = ÷10.", "🎯 3 km = 3×1000 = 3000 m."],
    "TEXTO":     ["📖 Lee el problema dos veces antes de resolver.", "🧮 Subraya los datos y la pregunta.", "🎯 Dibuja la situación antes de operar."],
    "DECIMAL":   ["🔢 El punto separa enteros de décimas.", "🧮 0.5 = media unidad. Visualiza en una regla.", "🎯 Suma por partes: 1.5+2.3 → enteros 1+2=3, décimas 5+3=8 → 3.8."],
    "VF":        ["🐊 Verdadero o Falso: evalúa ambos lados del signo.", "🧮 Reemplaza por números y verifica.", "🎯 5>3 es V porque 5 está más a la derecha."],
}


# ─── PREPROCESAMIENTO ────────────────────────────────────────────────────────
def _preprocess(img: Image.Image) -> Image.Image:
    """
    Preprocesamiento optimizado para exámenes de papel con fondo gris.
    Estrategia ganadora: brightness 1.5 + threshold fijo 150.
    Probada contra imagen real del examen — score máximo.
    """
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # Escalar a 2400px de ancho
    w, h = img.size
    if w < 2400:
        img = img.resize((2400, int(h * 2400 / w)), Image.LANCZOS)

    # Convertir a escala de grises
    gray = img.convert("L")

    # 1. Subir brillo para aclarar el fondo gris del papel
    gray = ImageEnhance.Brightness(gray).enhance(1.5)

    # 2. Threshold fijo 150: separa tinta negra (< 150) del fondo (>= 150)
    gray = gray.point(lambda x: 0 if x < 150 else 255)

    return gray


def decode_base64_image(b64: str) -> Image.Image:
    if "," in b64:
        b64 = b64.split(",")[1]
    b64 += "=" * (4 - len(b64) % 4)
    return Image.open(io.BytesIO(base64.b64decode(b64)))


def extract_text_from_images(b64_images: List[str]) -> str:
    if not b64_images:
        return ""
    if not OCR_AVAILABLE:
        return _demo_text()

    parts = []
    for i, b64 in enumerate(b64_images):
        try:
            img = decode_base64_image(b64)
            processed = _preprocess(img)

            best, best_score = "", -1
            # PSM 6 = bloque uniforme (mejor para exámenes)
            # PSM 4 = columna variable
            for psm in [6, 4]:
                try:
                    t = pytesseract.image_to_string(
                        processed, lang="spa+eng",
                        config=f"--oem 3 --psm {psm}"
                    )
                    s = _score_text(t)
                    if s > best_score:
                        best_score, best = s, t
                except Exception:
                    pass

            parts.append(f"=== PÁGINA {i+1} ===\n{_clean_text(best)}")
        except Exception as e:
            parts.append(f"=== PÁGINA {i+1} (error: {e}) ===")

    return "\n\n".join(parts)


def _score_text(text: str) -> int:
    """Más líneas con = y números = mejor OCR."""
    score = 0
    for line in text.split("\n"):
        l = line.strip()
        if "=" in l and re.search(r"\d", l):
            score += 4
        elif re.search(r"\d", l) and re.search(r"[+\-*/><]", l):
            score += 2
        elif re.search(r"[a-zA-ZáéíóúÁÉÍÓÚ]{3,}", l):
            score += 1
    return score


def _clean_text(text: str) -> str:
    """Limpieza mínima: solo quitar basura obvia, preservar todo lo matemático."""
    lines, result, prev_empty = text.split("\n"), [], False
    for line in lines:
        s = line.strip()
        if not s:
            if not prev_empty:
                result.append("")
            prev_empty = True
            continue
        # Quitar líneas que son casi puro ruido (< 20% alfanumérico)
        alnum = sum(1 for c in s if c.isalnum())
        if len(s) > 5 and alnum < len(s) * 0.20:
            continue
        # Normalizar símbolos
        s = (s.replace("—", "-").replace("–", "-")
              .replace("×", "*").replace("÷", "/")
              .replace("\u00d7", "*").replace("\u00f7", "/"))
        s = re.sub(r" {2,}", " ", s)
        result.append(s)
        prev_empty = False
    return "\n".join(result)


def _demo_text() -> str:
    return """=== PÁGINA 1 ===
Operaciones básicas (A)
1. 45 + 38 = 83
2. 92 - 47 = 41
3. 7 x 8 = 56
4. 56 / 7 = 8
Menor, Igual o Mayor que (D)
5 > 3 = V
4 < 2 = F
Jerarquía (E)
(2 + 3) x 4 = 20
10 - (2 + 3) = 5
Fracciones (F)
1/2 + 1/4 = 3/4
Decimales
0.5 + 0.25 = 0.75
"""


# ─── EVALUADOR MATEMÁTICO ─────────────────────────────────────────────────────
def _safe_eval(expr: str) -> Optional[float]:
    """Evalúa expresión matemática de forma segura."""
    try:
        c = (expr.strip()
             .replace(",", ".").replace("÷", "/").replace("×", "*")
             .replace("x", "*").replace("X", "*")
             .replace("²", "**2").replace("³", "**3").replace(" ", ""))
        c = re.sub(r"(\d)\(", r"\1*(", c)
        c = re.sub(r"\)(\d)", r")*\1", c)
        # Solo permitir caracteres matemáticos
        if re.search(r"[a-wyzA-WYZ_]", c):
            return None
        return float(eval(c, {"__builtins__": {}}, {}))  # noqa: S307
    except Exception:
        return None


def _cn(s: str) -> str:
    return s.replace(",", ".").replace(" ", "").strip() if s else ""


def _factors(n: int) -> List[int]:
    f, d = [], 2
    while d * d <= n:
        while n % d == 0:
            f.append(d); n //= d
        d += 1
    if n > 1:
        f.append(n)
    return f


def _frac_str(val: float) -> str:
    """Convierte float a string legible: entero si es entero, decimal si no."""
    if val == int(val):
        return str(int(val))
    # Para decimales simples mostrar decimal, no fracción
    decimal_str = f"{val:.4f}".rstrip("0").rstrip(".")
    # Solo mostrar fracción si es muy simple (denominador ≤ 10)
    try:
        fr = Fraction(val).limit_denominator(10)
        if abs(float(fr) - val) < 0.001 and fr.denominator <= 10:
            return f"{fr.numerator}/{fr.denominator}"
    except Exception:
        pass
    return decimal_str


# ─── PARSER PRINCIPAL ─────────────────────────────────────────────────────────
def detect_math_problems(ocr_text: str) -> List[Dict[str, Any]]:
    """
    Estrategia basada en '=' como ancla.
    
    Para cada línea que contiene '=':
    1. Separar en LADO_IZQUIERDO = LADO_DERECHO
    2. Intentar evaluar el lado izquierdo matemáticamente
    3. Comparar el resultado con lo que escribió el estudiante (lado derecho)
    4. Casos especiales: desigualdades V/F, medidas con unidades
    
    Para secciones: detectar (A), (B), (C)... al inicio de línea.
    Para puntos: detectar "1.", "2.", etc. al inicio de línea.
    """
    lines = ocr_text.split("\n")
    results: List[Dict[str, Any]] = []
    seen: set = set()

    current_section = "General"
    text_buffer = ""    # Acumula texto del problema antes del =
    current_point = ""  # "Punto 1", "Punto 2", etc.

    # ── Patrones ──────────────────────────────────────────────────────────────
    # Sección: "Operaciones básicas (A)" o línea que termina en (A)-(Z)
    SECTION_RE = re.compile(
        r"^(.*?)\(([A-Z])\)\s*$|"          # "Texto (A)"
        r"^\(([A-Z])\)$|"                   # solo "(A)"
        r"^(A\.|B\.|C\.|D\.|E\.|F\.|G\.)\s",  # "A. Texto"
        re.I
    )

    # Punto numerado al inicio: "1." o "1)"
    POINT_RE = re.compile(r"^\s*(\d{1,2})[.)]\s+(.*)$")

    # Línea con = (ancla principal)
    HAS_EQ = re.compile(r"=")

    # Desigualdad V/F: "5 > 3 = V" o "4 < 2 = F"
    INEQ_VF_RE = re.compile(
        r"(\d+\.?\d*)\s*([><=])\s*(\d+\.?\d*)\s*[=:]\s*([VFvf])\b", re.I
    )

    # Medida con unidad: "1.2 x 100 = 120 cm" o "350 / 100 = 3.5 m"
    UNIT_RE = re.compile(
        r"([\d.,]+)\s*[xX×*/÷]\s*([\d.,]+)\s*=\s*([\d.,]+)\s*"
        r"(km|hm|dam|dm|cm|mm|m\b|kg|g|mg|ml|litros?|l\b)",
        re.I
    )

    # Fracción en expresión: "1/2 + 3/4 = ..."
    FRAC_EXPR_RE = re.compile(r"\d+/\d+")

    # Potencia: "2² = 4" o "3^2 = 9"
    POWER_RE = re.compile(r"(\d+)\s*([²³\^])\s*(\d*)\s*=\s*([\d.,]+)?")

    # Raíz: "√25 = 5"
    SQRT_RE = re.compile(r"√\s*(\d+)\s*=\s*([\d.,]+)?")

    def add(data: Dict) -> None:
        op = (data.get("operation") or "").strip()
        key = re.sub(r"\s+", "", op)[:50]
        if key and key not in seen and len(op) >= 2:
            seen.add(key)
            results.append({
                "id": str(uuid.uuid4()),
                "section": current_section,
                "problemText": text_buffer.strip() or current_point or current_section,
                "originalText": data.get("originalText", op),
                **{k: v for k, v in data.items() if k != "originalText"},
            })

    for raw in lines:
        line = raw.strip()

        # Saltar separadores de página
        if not line or line.startswith("==="):
            if not line:
                text_buffer = ""
                current_point = ""
            continue

        # ── 1. DETECTAR SECCIÓN ───────────────────────────────────────────────
        sec_m = SECTION_RE.match(line)
        if sec_m and "=" not in line and len(line) < 100:
            # Verificar que no sea una operación matemática disfrazada
            if not re.search(r"\d\s*[+\-*/]\s*\d", line):
                current_section = line.rstrip(":").strip()
                text_buffer = ""
                current_point = ""
                continue

        # ── 2. DETECTAR PUNTO NUMERADO ────────────────────────────────────────
        pt_m = POINT_RE.match(line)
        if pt_m:
            current_point = f"Punto {pt_m.group(1)}"
            rest = pt_m.group(2).strip()
            if "=" in rest and re.search(r"\d", rest):
                line = rest  # Procesar el resto como operación
            else:
                text_buffer = rest  # Es texto del enunciado
                continue

        # ── SOLO PROCESAR LÍNEAS QUE TIENEN = ────────────────────────────────
        if "=" not in line:
            # Acumular como contexto textual
            if len(line) > 4 and re.search(r"[a-zA-ZáéíóúÁÉÍÓÚ]", line):
                text_buffer += line + " "
            continue

        original_line = line

        # ── 3. RAÍCES: √25 = 5 ───────────────────────────────────────────────
        m = SQRT_RE.search(line)
        if m:
            radicand = float(m.group(1))
            student = m.group(2)
            correct = radicand ** 0.5
            cs = _frac_str(correct)
            ok = False
            if student:
                try: ok = abs(float(_cn(student)) - correct) < 0.05
                except Exception: pass
            add({"originalText": original_line,
                 "operation": f"√{int(radicand)}",
                 "studentAnswer": student or "-", "correctAnswer": cs,
                 "isCorrect": ok, "type": "sqrt", "subType": "RAIZ"})
            text_buffer = ""; continue

        # ── 4. POTENCIAS: 2² = 4 ─────────────────────────────────────────────
        m = POWER_RE.search(line)
        if m and re.search(r"[²³\^]", line):
            base = float(m.group(1))
            sym = m.group(2)
            exp = 2 if sym == "²" else 3 if sym == "³" else float(m.group(3) or 2)
            correct = base ** exp
            cs = _frac_str(correct)
            student = m.group(4) or line.split("=")[-1].strip()
            ok = False
            try: ok = abs(float(_cn(student)) - correct) < 0.05
            except Exception: pass
            add({"originalText": original_line,
                 "operation": f"{int(base)}{sym}{m.group(3) or ''}",
                 "studentAnswer": student or "-", "correctAnswer": cs,
                 "isCorrect": ok, "type": "power", "subType": "POTENCIA"})
            text_buffer = ""; continue

        # ── 5. DESIGUALDAD V/F: 5 > 3 = V ────────────────────────────────────
        m = INEQ_VF_RE.search(line)
        if m:
            left, op, right, student = m.group(1), m.group(2), m.group(3), m.group(4)
            try:
                v1, v2 = float(left), float(right)
                truth = (v1 > v2 if op == ">" else v1 < v2 if op == "<" else abs(v1-v2) < 0.01)
                expected = "V" if truth else "F"
                add({"originalText": original_line,
                     "operation": f"{left} {op} {right}",
                     "studentAnswer": student.upper(), "correctAnswer": expected,
                     "isCorrect": student.upper() == expected,
                     "type": "inequality", "subType": op})
            except Exception: pass
            text_buffer = ""; continue

        # ── 6. MEDIDAS CON UNIDAD: 1.2 x 100 = 120 cm ───────────────────────
        m = UNIT_RE.search(line)
        if m:
            v1, v2 = float(_cn(m.group(1))), float(_cn(m.group(2)))
            student, unit = _cn(m.group(3)), m.group(4)
            correct = v1 * v2
            cs = _frac_str(correct)
            ok = False
            try: ok = abs(float(student) - correct) < 0.1
            except Exception: pass
            add({"originalText": original_line,
                 "operation": f"{m.group(1)} × {m.group(2)}",
                 "studentAnswer": f"{student} {unit}",
                 "correctAnswer": f"{cs} {unit}",
                 "isCorrect": ok, "type": "units", "subType": "UNIDADES"})
            text_buffer = ""; continue

        # ── 7. CORE: EXPRESIÓN MATEMÁTICA con = ──────────────────────────────
        # Cuando hay múltiples = (ej: "12.5+3.75= 12.5+3.75=17:17")
        # buscar el par más simple: expresión corta = número limpio
        
        parts_eq = line.split("=")
        if len(parts_eq) < 2:
            continue

        parsed = False

        # Intentar TODOS los splits posibles, preferir el que tenga:
        # 1. Lado izquierdo evaluable
        # 2. Lado derecho que sea un número limpio
        # Probamos de izquierda a derecha (primer = ganador)
        for split_idx in range(1, len(parts_eq)):
            left_str = "=".join(parts_eq[:split_idx]).strip()
            right_str = parts_eq[split_idx].strip()

            # Ignorar lados izquierdos muy largos o con mucho texto
            if len(left_str) > 60:
                continue

            # Limpiar el lado derecho: tomar solo el primer número/fracción
            # Acepta: "83", "42 : 42 manzanas" → 42, "17:17" → 17, "84, luego..." → 84
            right_num_m = re.match(r"^([\d.,/]+)", right_str.replace(" ", ""))
            if not right_num_m:
                # Intento alternativo: primer número en el lado derecho
                right_num_m = re.search(r"([\d]+\.?[\d]*)", right_str)
                if not right_num_m:
                    continue
            student_str = right_num_m.group(1).strip().rstrip(",")

            # Preparar expresión para evaluar — limpiar ruido OCR
            expr_clean = (
                left_str
                .replace("÷", "/").replace("×", "*")
                .replace("x", "*").replace("X", "*")
                .replace("~", "-").replace("—", "-")  # OCR confunde ~ con -
                .replace("²", "**2").replace("³", "**3")
                .replace(" ", "")
            )
            # Limpiar letras sueltas que el OCR agrega (ej: "454+3g" → intentar limpiar)
            expr_clean = re.sub(r"[a-zA-Z]", "", expr_clean)
            expr_clean = re.sub(r"(\d)\(", r"\1*(", expr_clean)
            expr_clean = re.sub(r"\)(\d)", r")*\1", expr_clean)
            # Limpiar operadores dobles
            expr_clean = re.sub(r"[+\-*/]{2,}", lambda m: m.group()[0], expr_clean)

            correct_val = _safe_eval(expr_clean)
            if correct_val is None:
                continue

            # Rechazar si el resultado correcto es absurdo (muy grande o negativo raro)
            if abs(correct_val) > 1_000_000:
                continue

            cs = _frac_str(correct_val)

            # Evaluar respuesta del estudiante
            student_clean = _cn(student_str).replace(":", "/").rstrip(",")
            student_val = _safe_eval(student_clean)
            is_correct = (
                student_val is not None and abs(student_val - correct_val) < 0.05
            )

            # Determinar subtipo
            has_frac = bool(FRAC_EXPR_RE.search(left_str))
            has_paren = "(" in left_str
            has_dot = "." in left_str and not has_frac

            if has_paren:
                sub = "HIERARCHY"
            elif has_frac:
                sub = "FRACTION"
            elif has_dot:
                sub = "DECIMAL"
            elif re.search(r"[*×xX]", left_str):
                sub = "*"
            elif re.search(r"[/÷]", left_str):
                sub = "/"
            elif re.search(r"-", expr_clean.lstrip("-")):
                sub = "-"
            else:
                sub = "+"

            add({"originalText": original_line,
                 "operation": left_str,
                 "studentAnswer": student_str or "-",
                 "correctAnswer": cs,
                 "isCorrect": is_correct,
                 "type": "arithmetic", "subType": sub})
            text_buffer = ""
            parsed = True
            break

        if not parsed and len(line) > 4 and re.search(r"[a-zA-ZáéíóúÁÉÍÓÚ]", line):
            text_buffer += line + " "

    return results[:100]


# ─── CALIFICACIÓN ─────────────────────────────────────────────────────────────
def calculate_final_score(problems: List[Dict]) -> float:
    """Escala colombiana 1.0 – 5.0."""
    definitive = [p for p in problems if p.get("isCorrect") is not None]
    if not definitive:
        return 1.0
    correct = sum(1 for p in definitive if p["isCorrect"] is True)
    return round(min(5.0, max(1.0, 1.0 + (correct / len(definitive)) * 4.0)), 1)


# ─── PLAN PEDAGÓGICO ──────────────────────────────────────────────────────────
def generate_teaching_plan(problems: List[Dict]) -> str:
    errors = [p for p in problems if p.get("isCorrect") is False]
    if not errors:
        return (
            "🌟 ¡Excelente trabajo! El estudiante domina todos los temas.\n"
            "✅ Sugerencia: ejercicios de ampliación y retos adicionales."
        )

    seen: set = set()
    parts: List[str] = []
    names = {
        "+": "Suma", "-": "Resta", "*": "Multiplicación", "/": "División",
        "FRACTION": "Fracciones", "HIERARCHY": "Jerarquía de Operaciones",
        ">": "Mayor que", "<": "Menor que", "=": "Igualdad", "VF": "Verdadero/Falso",
        "POTENCIA": "Potencias", "RAIZ": "Raíces Cuadradas",
        "FACTOR": "Factorización", "UNIDADES": "Unidades de Medida",
        "TEXTO": "Problemas de Texto", "DECIMAL": "Decimales",
    }
    pfx = {
        "FRACTION": "🧱", "HIERARCHY": "🧱",
        "POTENCIA": "⚡", "RAIZ": "⚡", "FACTOR": "⚡",
        "UNIDADES": "📏", "TEXTO": "📖",
        ">": "🐊", "<": "🐊", "=": "🐊", "VF": "🐊",
        "DECIMAL": "🔢",
    }

    for err in errors:
        sub = err.get("subType", "+")
        if re.search(r"\b(km|cm|metros|litros|kg|g)\b",
                     (err.get("problemText") or "").lower()):
            sub = "UNIDADES"
        if sub in seen:
            continue
        seen.add(sub)
        tips = PEDAGOGIA.get(sub) or PEDAGOGIA["+"]
        name = names.get(sub, sub)
        op = (err.get("operation") or "")[:40]
        parts.append(
            f"{pfx.get(sub, '🔢')} **{name}** (ej: {op}):\n"
            + "\n".join(tips[:3])
        )

    return "\n\n".join(parts)
