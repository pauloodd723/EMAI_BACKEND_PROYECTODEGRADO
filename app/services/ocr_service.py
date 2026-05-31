"""
ocr_service.py — EMAI-APP v7
- Solo EasyOCR (elimina dependencia de Tesseract)
- Flash: umbral 160, doble dilatación para + y -
- Sin flash: CLAHE para sombras
- Parser basado en '=' como ancla
"""

import base64

import io
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from PIL import Image, ImageEnhance, ImageOps, ImageFilter

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

_easyocr_reader = None
def _get_easyocr():
    global _easyocr_reader
    if _easyocr_reader is None and EASYOCR_AVAILABLE:
        _easyocr_reader = easyocr.Reader(['es', 'en'], gpu=False, verbose=False)
    return _easyocr_reader


def _tesseract_to_text(img: "Image.Image") -> str:
    if not TESSERACT_AVAILABLE:
        return ""
    try:
        config = "--oem 3 --psm 6 -l spa+eng"
        return pytesseract.image_to_string(img, config=config)
    except Exception:
        return ""

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


def decode_base64_image(b64: str) -> Image.Image:
    if "," in b64:
        b64 = b64.split(",")[1]
    b64 += "=" * (4 - len(b64) % 4)
    return Image.open(io.BytesIO(base64.b64decode(b64)))


def _normalize_vf(text: str) -> str:
    """
    Normaliza líneas de V/F:
    - '?' → '>' cuando está entre números (OCR confunde > con ?)
    - Líneas que terminan en '=' sin respuesta → marcar como incompletas
    - Normaliza variantes de V y F
    """
    def _fix_token(tok: str) -> str:
        tok = tok.strip()
        if tok in ("v", "u", "U", "\\/", "VV", "W", "w", "V"):
            return "V"
        if tok in ("f", "E", "P", "T", "F"):
            return "F"
        if re.match(r"^[VvuUwW]+[.,]?$", tok):
            return "V"
        if re.match(r"^[FfEPT]+[.,]?$", tok):
            return "F"
        if tok.lower() == "verdadero":
            return "V"
        if tok.lower() == "falso":
            return "F"
        return tok

    fixed_lines = []
    for line in text.split("\n"):
        # ? entre números → > (OCR confunde el signo mayor que)
        line = re.sub(r"(\d)\s*\?\s*(\d)", r"\1 > \2", line)

        # Activar normalización si hay patrón de desigualdad
        if re.search(r"[><]\s*\d|[><].*=|\d\s*=\s*\d.*=", line):
            # Normalizar V/F al final
            line = re.sub(
                r"([=:\-]\s*)([A-Za-z\\/]{1,9})\s*$",
                lambda m: m.group(1) + _fix_token(m.group(2)),
                line
            )
            # Línea que termina en "= " sin respuesta (V desapareció por flash)
            # Dejarla sin ? para que INEQ_NO_ANS_RE la capture limpiamente
            if re.search(r"[><=]\s*\d+\s*=\s*$", line):
                line = line.rstrip().rstrip("=").rstrip()

        fixed_lines.append(line)
    return "\n".join(fixed_lines)


def _score_text(text: str) -> int:
    score = 0
    for line in text.split("\n"):
        l = line.strip()
        if "=" in l and re.search(r"\d", l):
            score += 4
        elif re.search(r"\d", l) and re.search(r"[+\-*/><]", l):
            score += 2
        elif re.search(r"[a-zA-ZáéíóúÁÉÍÓÚ]{3,}", l):
            score += 1
        if re.search(r"[><]\s*\d.*[=:]\s*[VFvf]", l):
            score += 3
    return score


def _clean_text(text: str) -> str:
    lines, result, prev_empty = text.split("\n"), [], False
    for line in lines:
        s = line.strip()
        if not s:
            if not prev_empty:
                result.append("")
            prev_empty = True
            continue
        alnum = sum(1 for c in s if c.isalnum())
        if len(s) > 5 and alnum < len(s) * 0.20:
            continue
        s = (s.replace("—", "-").replace("–", "-")
              .replace("×", "*").replace("÷", "/")
              .replace("\u00d7", "*").replace("\u00f7", "/"))
        s = re.sub(r"(\d),(\d)", r"\1.\2", s)
        s = re.sub(r" {2,}", " ", s)
        result.append(s)
        prev_empty = False
    return "\n".join(result)


def _easyocr_to_text(results: list) -> str:
    if not results:
        return ""
    results = [(bbox, text.strip(), conf) for bbox, text, conf in results
               if text.strip() and conf > 0.10]
    if not results:
        return ""

    def center_y(r): return (r[0][0][1] + r[0][2][1]) / 2
    def center_x(r): return (r[0][0][0] + r[0][2][0]) / 2
    def height(r):   return abs(r[0][2][1] - r[0][0][1])

def _easyocr_to_text(results: list) -> str:
    if not results:
        return ""
    results = [(bbox, text.strip(), conf) for bbox, text, conf in results
               if text.strip() and conf > 0.10]
    if not results:
        return ""

    def center_y(r): return (r[0][0][1] + r[0][2][1]) / 2
    def center_x(r): return (r[0][0][0] + r[0][2][0]) / 2
    def height(r):   return abs(r[0][2][1] - r[0][0][1])

    sorted_r = sorted(results, key=center_y)
    lines_groups, current_group = [], [sorted_r[0]]

    for item in sorted_r[1:]:
        # Comparar con el último elemento del grupo (ventana deslizante)
        # pero usar la altura del item más grande para el umbral
        prev = current_group[-1]
        max_h = max(height(prev), height(item))
        # Umbral conservador: 0.8x altura — solo agrupa si están muy cerca en Y
        # Esto evita que líneas de diferentes filas se mezclen
        if abs(center_y(item) - center_y(prev)) < max_h * 0.8:
            current_group.append(item)
        else:
            lines_groups.append(current_group)
            current_group = [item]
    lines_groups.append(current_group)

    final_lines = []
    for group in lines_groups:
        group_sorted = sorted(group, key=center_x)
        line_text = " ".join(text for _, text, _ in group_sorted).strip()
        line_text = re.sub(r"^(\d{1,2})\.\s+(\d)", r"\1. \2", line_text)
        line_text = re.sub(r"\s*[×xX]\s*", " x ", line_text)
        line_text = re.sub(r"\s*÷\s*", " / ", line_text)
        line_text = re.sub(r"\s*=\s*", " = ", line_text)
        line_text = re.sub(r"\s*\+\s*", " + ", line_text)
        line_text = re.sub(r"[—–]", "-", line_text)
        line_text = re.sub(r"(\d)\s*-\s*(\d)", r"\1 - \2", line_text)
        line_text = re.sub(r"\s+-\s+", " - ", line_text)
        line_text = re.sub(r"(\d)\s{2,}/\s{2,}(\d)", r"\1/\2", line_text)
        # Unir dígitos separados por espacio simple: "8 3" → "83", "4 1" → "41"
        # Solo cuando son dígitos solos sin operador alrededor
        line_text = re.sub(r"(?<![+\-*/=<>])\b(\d)\s(\d)\b(?![+\-*/=<>])", r"\1\2", line_text)
        # Si hay operación sin = seguida de número: "5/6 - 1/3 1/2" → "5/6 - 1/3 = 1/2"
        line_text = re.sub(
            r"([\d/]+\s*[-+*/]\s*[\d/]+)\s+([\d/]+)\s*$",
            r"\1 = \2",
            line_text
        )
        # Normalizar V/F al final
        line_text = re.sub(r"=\s*([vVfF])\s*$", lambda m: "= " + m.group(1).upper(), line_text)
        line_text = re.sub(r"\s{2,}", " ", line_text).strip()
        if line_text:
            final_lines.append(line_text)
    return "\n".join(final_lines)


def _process_single_image(b64: str, index: int) -> str:
    try:
        img = decode_base64_image(b64)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        reader = _get_easyocr()
        if reader is None and not TESSERACT_AVAILABLE:
            return f"=== PÁGINA {index+1} ===\n{_demo_text()}"

        # Escalar a máx 1200px para no agotar RAM
        w, h = img.size
        if w > 1200:
            img = img.resize((1200, int(h * 1200 / w)), Image.LANCZOS)

        # Preprocesamiento MÍNIMO — EasyOCR maneja mejor la imagen original
        # Solo un leve sharpen para definir bordes sin destruir trazos finos
        gray = img.convert("L")
        gray = ImageEnhance.Sharpness(gray).enhance(2.0)

        if reader is not None:
            buf = io.BytesIO()
            gray.save(buf, format="JPEG", quality=95)
            results = reader.readtext(buf.getvalue())
            text = _easyocr_to_text(results)
        else:
            text = _tesseract_to_text(gray)

        text = _normalize_vf(text)
        return f"=== PÁGINA {index+1} ===\n{_clean_text(text)}"
    except Exception as e:
        return f"=== PÁGINA {index+1} (error: {e}) ==="


def extract_text_from_images(b64_images: List[str]) -> str:
    if not b64_images:
        return ""
    _get_easyocr()
    results_map: Dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=min(len(b64_images), 3)) as executor:
        futures = {
            executor.submit(_process_single_image, b64, i): i
            for i, b64 in enumerate(b64_images)
        }
        for future in as_completed(futures):
            i = futures[future]
            try:
                results_map[i] = future.result()
            except Exception as e:
                results_map[i] = f"=== PÁGINA {i+1} (error: {e}) ==="
    return "\n\n".join(results_map[i] for i in sorted(results_map))


def _demo_text() -> str:
    return """=== PÁGINA 1 ===
Operaciones básicas (A)
1. 45 + 38 = 83
2. 92 - 47 = 41
3. 7 x 8 = 56
4. 56 / 7 = 8
"""


def _safe_eval(expr: str) -> Optional[float]:
    try:
        c = (expr.strip()
             .replace(",", ".")
             .replace("÷", "/").replace("×", "*")
             .replace("²", "**2").replace("³", "**3"))
        c = re.sub(r"(?<=\d)\s*[xX]\s*(?=\d)", "*", c)
        c = c.replace(" ", "")
        c = re.sub(r"(\d)\(", r"\1*(", c)
        c = re.sub(r"\)(\d)", r")*\1", c)
        if re.search(r"[a-wyzA-WYZ_]", c):
            return None
        return float(eval(c, {"__builtins__": {}}, {}))
    except Exception:
        return None


def _cn(s: str) -> str:
    return s.replace(",", ".").replace(" ", "").strip() if s else ""


def _frac_str(val: float) -> str:
    if val == int(val):
        return str(int(val))
    SIMPLE = {0.5: "1/2", 0.333: "1/3", 0.667: "2/3", 0.25: "1/4", 0.75: "3/4"}
    for ref, fstr in SIMPLE.items():
        if abs(val - ref) < 0.005:
            return fstr
    return f"{val:.2f}".rstrip("0").rstrip(".")


def detect_math_problems(ocr_text: str) -> List[Dict[str, Any]]:
    lines = ocr_text.split("\n")
    results: List[Dict[str, Any]] = []
    seen: set = set()
    current_section = "General"
    text_buffer = ""
    current_point = ""

    SECTION_RE = re.compile(
        r"^(.*?)\(([A-Z])\)\s*$|^\(([A-Z])\)$|^(A\.|B\.|C\.|D\.|E\.|F\.|G\.)\s", re.I
    )
    INEQ_VF_RE = re.compile(
        # Acepta también ? como respuesta (cuando V desapareció por flash)
        r"(\d+\.?\d*)\s*([><=≥≤?]={0,1})\s*(\d+\.?\d*)\s*[=:\-]\s*"
        r"(V|F|v|f|u|U|w|W|E|P|T|\?|Verdadero|Falso|verdadero|falso)\b",
        re.I
    )
    # Detectar línea de comparación sin respuesta: "5 > 3" o "5 > 3 =" (V desapareció)
    INEQ_NO_ANS_RE = re.compile(
        r"^(\d+\.?\d*)\s*([><=]={0,1})\s*(\d+\.?\d*)\s*$"
    )
    VF_NORM = {
        "v": "V", "u": "V", "U": "V", "w": "V", "W": "V",
        "f": "F", "E": "F", "P": "F", "T": "F",
        "verdadero": "V", "Verdadero": "V", "VERDADERO": "V",
        "falso": "F", "Falso": "F", "FALSO": "F",
        "?": "?",
    }
    UNIT_RE = re.compile(
        r"([\d.,]+)\s*[xX×*/÷]\s*([\d.,]+)\s*=\s*([\d.,]+)\s*"
        r"(km|hm|dam|dm|cm|mm|m\b|kg|g|mg|ml|litros?|l\b)", re.I
    )
    FRAC_RE  = re.compile(r"\d+/\d+")
    POWER_RE = re.compile(r"(\d+)\s*([²³\^])\s*(\d*)\s*=\s*([\d.,]+)?")
    SQRT_RE  = re.compile(r"√\s*(\d+)\s*=\s*([\d.,]+)?")

    def _strip_enum(s: str) -> str:
        m = re.match(r"^(\d{1,2})\.\s+(.+)$", s)
        if m:
            return m.group(2).strip()
        m = re.match(r"^(\d{1,2})\)\s+(.+)$", s)
        if m:
            return m.group(2).strip()
        return s

    def add(data: Dict) -> None:
        op = (data.get("operation") or "").strip()
        op = _strip_enum(op)
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

    def _normalize_line(line: str) -> str:
        line = _strip_enum(line)
        line = line.replace("—", " - ").replace("–", " - ").replace("‐", " - ")
        line = re.sub(r"(\d)\s*-\s*(\d)", r"\1 - \2", line)
        line = re.sub(r"\s*[×÷]\s*", lambda m: " * " if "×" in m.group() else " / ", line)
        # Dos fracciones juntas sin operador entre ellas: "5/6 1/3" 
        # EasyOCR a veces no detecta el - entre fracciones.
        # No podemos inferir el operador, así que dejamos pasar al core
        # que probará ambas interpretaciones.
        line = re.sub(r"\s{2,}", " ", line).strip()
        return line

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("==="):
            if not line:
                text_buffer = ""
                current_point = ""
            continue

        line_clean = _strip_enum(line)
        sec_m = SECTION_RE.match(line_clean)
        if sec_m and "=" not in line_clean and len(line_clean) < 100:
            if not re.search(r"\d\s*[+\-*/]\s*\d", line_clean):
                current_section = line_clean.rstrip(":").strip()
                text_buffer = ""
                current_point = ""
                continue

        line = _normalize_line(line)
        original_line = line

        if "=" not in line:
            # Excepción: comparaciones puras "5 > 3" o "4 < 2" (sin respuesta)
            m = INEQ_NO_ANS_RE.match(line.strip())
            if m:
                left, op_sign, right = m.group(1), m.group(2), m.group(3)
                try:
                    v1, v2 = float(left), float(right)
                    if op_sign == ">":    truth = v1 > v2
                    elif op_sign == ">=": truth = v1 >= v2
                    elif op_sign == "<":  truth = v1 < v2
                    elif op_sign == "<=": truth = v1 <= v2
                    else:                 truth = abs(v1 - v2) < 0.01
                    expected = "V" if truth else "F"
                    add({"originalText": original_line, "operation": f"{left} {op_sign} {right}",
                         "studentAnswer": "-", "correctAnswer": expected,
                         "isCorrect": None, "type": "inequality", "subType": "VF"})
                except Exception: pass
                text_buffer = ""; continue
            if len(line) > 4 and re.search(r"[a-zA-ZáéíóúÁÉÍÓÚ]", line):
                text_buffer += line + " "
            continue

        m = SQRT_RE.search(line)
        if m:
            radicand = float(m.group(1)); student = m.group(2)
            correct = radicand ** 0.5; cs = _frac_str(correct)
            ok = False
            if student:
                try: ok = abs(float(_cn(student)) - correct) < 0.05
                except Exception: pass
            add({"originalText": original_line, "operation": f"√{int(radicand)}",
                 "studentAnswer": student or "-", "correctAnswer": cs,
                 "isCorrect": ok, "type": "sqrt", "subType": "RAIZ"})
            text_buffer = ""; continue

        m = POWER_RE.search(line)
        if m and re.search(r"[²³\^]", line):
            base = float(m.group(1)); sym = m.group(2)
            exp = 2 if sym == "²" else 3 if sym == "³" else float(m.group(3) or 2)
            correct = base ** exp; cs = _frac_str(correct)
            student = m.group(4) or line.split("=")[-1].strip()
            ok = False
            try: ok = abs(float(_cn(student)) - correct) < 0.05
            except Exception: pass
            add({"originalText": original_line, "operation": f"{int(base)}{sym}",
                 "studentAnswer": student or "-", "correctAnswer": cs,
                 "isCorrect": ok, "type": "power", "subType": "POTENCIA"})
            text_buffer = ""; continue

        m = INEQ_VF_RE.search(line)
        if m:
            left = m.group(1); op_sign = m.group(2)
            right = m.group(3); raw_ans = m.group(4).strip()
            # Limpiar op_sign: ? → > (OCR confunde > con ?)
            op_sign = op_sign.replace("?", ">")
            student = VF_NORM.get(raw_ans, VF_NORM.get(raw_ans.lower(), "?"))
            try:
                v1, v2 = float(left), float(right)
                op_norm = op_sign.replace("≥", ">=").replace("≤", "<=")
                if op_norm == ">":    truth = v1 > v2
                elif op_norm == ">=": truth = v1 >= v2
                elif op_norm == "<":  truth = v1 < v2
                elif op_norm == "<=": truth = v1 <= v2
                else:                 truth = abs(v1 - v2) < 0.01
                expected = "V" if truth else "F"
                # Si respuesta es ? (V desapareció por flash), marcar como sin respuesta
                is_correct = None if student == "?" else student == expected
                add({"originalText": original_line, "operation": f"{left} {op_sign} {right}",
                     "studentAnswer": student if student != "?" else "-",
                     "correctAnswer": expected,
                     "isCorrect": is_correct,
                     "type": "inequality", "subType": "VF"})
            except Exception: pass
            text_buffer = ""; continue

        # Línea de comparación sin respuesta: "5 > 3 =" (V desapareció por flash)
        m = INEQ_NO_ANS_RE.match(line.strip())
        if m:
            left, op_sign, right = m.group(1), m.group(2), m.group(3)
            try:
                v1, v2 = float(left), float(right)
                if op_sign == ">":    truth = v1 > v2
                elif op_sign == ">=": truth = v1 >= v2
                elif op_sign == "<":  truth = v1 < v2
                elif op_sign == "<=": truth = v1 <= v2
                else:                 truth = abs(v1 - v2) < 0.01
                expected = "V" if truth else "F"
                add({"originalText": original_line, "operation": f"{left} {op_sign} {right}",
                     "studentAnswer": "-", "correctAnswer": expected,
                     "isCorrect": None,
                     "type": "inequality", "subType": "VF"})
            except Exception: pass
            text_buffer = ""; continue

        m = UNIT_RE.search(line)
        if m:
            v1 = float(_cn(m.group(1))); v2 = float(_cn(m.group(2)))
            student = _cn(m.group(3)); unit = m.group(4)
            correct = v1 * v2; cs = _frac_str(correct)
            ok = False
            try: ok = abs(float(student) - correct) < 0.1
            except Exception: pass
            add({"originalText": original_line, "operation": f"{m.group(1)} × {m.group(2)}",
                 "studentAnswer": f"{student} {unit}", "correctAnswer": f"{cs} {unit}",
                 "isCorrect": ok, "type": "units", "subType": "UNIDADES"})
            text_buffer = ""; continue

        parts_eq = line.split("=")
        if len(parts_eq) < 2:
            continue

        parsed = False
        for split_idx in range(1, len(parts_eq)):
            left_str  = "=".join(parts_eq[:split_idx]).strip()
            right_str = parts_eq[split_idx].strip()
            if len(left_str) > 60:
                continue
            right_num_m = re.match(r"^([\d.,/]+)", right_str.replace(" ", ""))
            if not right_num_m:
                right_num_m = re.search(r"([\d]+\.?[\d]*)", right_str)
                if not right_num_m:
                    continue
            student_str = right_num_m.group(1).strip().rstrip(",")
            student_val = _safe_eval(_cn(student_str).replace(":", "/").rstrip(","))

            # Generar variantes: caso normal + fracciones sin operador
            left_variants = [left_str]
            if re.search(r"\d/\d+\s+\d+/\d", left_str) and not re.search(r"[+\-]", left_str):
                left_variants.append(re.sub(r"(\d/\d+)\s+(\d+/\d)", r"\1 - \2", left_str))
                left_variants.append(re.sub(r"(\d/\d+)\s+(\d+/\d)", r"\1 + \2", left_str))

            # Evaluar todas las variantes, quedarse con la que coincide con el estudiante
            # Si ninguna coincide, usar la primera que evalúe correctamente
            best_lv = None
            best_val = None
            for lv in left_variants:
                ec = (lv.replace("÷","/").replace("×","*").replace("x","*").replace("X","*")
                      .replace("~","-").replace("—","-").replace("²","**2").replace("³","**3")
                      .replace(" ",""))
                ec = re.sub(r"[a-zA-Z]", "", ec)
                ec = re.sub(r"(\d)\(", r"\1*(", ec)
                ec = re.sub(r"\)(\d)", r")*\1", ec)
                ec = re.sub(r"([+\-*/])\1+", r"\1", ec)
                val = _safe_eval(ec)
                if val is None or abs(val) > 1_000_000:
                    continue
                if best_val is None:
                    best_lv, best_val = lv, val
                # Preferir variante que coincide con respuesta del estudiante
                if student_val is not None and abs(student_val - val) < 0.05:
                    best_lv, best_val = lv, val
                    break

            if best_val is None:
                continue

            left_str = best_lv
            correct_val = best_val
            cs = _frac_str(correct_val)
            is_correct = student_val is not None and abs(student_val - correct_val) < 0.05


            has_frac  = bool(FRAC_RE.search(left_str))
            has_paren = "(" in left_str
            has_dot   = "." in left_str and not has_frac
            left_clean = left_str.replace(" ", "")
            if has_paren:                                    sub = "HIERARCHY"
            elif has_frac:                                   sub = "FRACTION"
            elif has_dot:                                    sub = "DECIMAL"
            elif re.search(r"[*×xX]", left_str):            sub = "*"
            elif re.search(r"[/÷]", left_str) and not re.search(r"-", left_clean): sub = "/"
            elif re.search(r"-", left_clean.lstrip("-")):    sub = "-"
            else:                                            sub = "+"
            add({"originalText": original_line, "operation": left_str,
                 "studentAnswer": student_str or "-", "correctAnswer": cs,
                 "isCorrect": is_correct, "type": "arithmetic", "subType": sub})
            text_buffer = ""; parsed = True; break

        if not parsed and len(line) > 4 and re.search(r"[a-zA-ZáéíóúÁÉÍÓÚ]", line):
            text_buffer += line + " "

    return results[:100]


def calculate_final_score(problems: List[Dict]) -> float:
    definitive = [p for p in problems if p.get("isCorrect") is not None]
    if not definitive:
        return 1.0
    correct = sum(1 for p in definitive if p["isCorrect"] is True)
    return round(min(5.0, max(1.0, 1.0 + (correct / len(definitive)) * 4.0)), 1)


def generate_teaching_plan(problems: List[Dict]) -> str:
    errors = [p for p in problems if p.get("isCorrect") is False]
    if not errors:
        return ("🌟 ¡Excelente trabajo! El estudiante domina todos los temas.\n"
                "✅ Sugerencia: ejercicios de ampliación y retos adicionales.")
    seen: set = set(); parts: List[str] = []
    names = {
        "+": "Suma", "-": "Resta", "*": "Multiplicación", "/": "División",
        "FRACTION": "Fracciones", "HIERARCHY": "Jerarquía de Operaciones",
        ">": "Mayor que", "<": "Menor que", "=": "Igualdad", "VF": "Verdadero/Falso",
        "POTENCIA": "Potencias", "RAIZ": "Raíces Cuadradas", "FACTOR": "Factorización",
        "UNIDADES": "Unidades de Medida", "TEXTO": "Problemas de Texto", "DECIMAL": "Decimales",
    }
    pfx = {
        "FRACTION": "🧱", "HIERARCHY": "🧱", "POTENCIA": "⚡", "RAIZ": "⚡",
        "FACTOR": "⚡", "UNIDADES": "📏", "TEXTO": "📖",
        ">": "🐊", "<": "🐊", "=": "🐊", "VF": "🐊", "DECIMAL": "🔢",
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
        parts.append(
            f"{pfx.get(sub, '🔢')} **{names.get(sub, sub)}** "
            f"(ej: {(err.get('operation') or '')[:40]}):\n"
            + "\n".join(tips[:3])
        )
    return "\n\n".join(parts)