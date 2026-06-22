import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

PDF_DIR = "pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

def export_day_to_pdf(day: int, title: str, text: str) -> str:
    """
    Genera un PDF del día y devuelve la ruta del archivo.
    """
    filename = os.path.join(PDF_DIR, f"dia_{day}.pdf")

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Margenes
    x_margin = 40
    y_margin = 40
    y = height - y_margin

    # Título
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_margin, y, sanitize_pdf_text(f"Día {day}: {title}"))
    y -= 30

    # Texto
    c.setFont("Helvetica", 10)

    for raw_line in text.split("\n"):
        for line in wrap_pdf_line(sanitize_pdf_text(raw_line), 105) or [""]:
            if y < y_margin:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - y_margin

            c.drawString(x_margin, y, line)
            y -= 14

    c.save()
    return filename


def sanitize_pdf_text(text: str) -> str:
    replacements = {
        "“": '"',
        "”": '"',
        "„": '"',
        "‟": '"',
        "‘": "'",
        "’": "'",
        "‚": "'",
        "‛": "'",
        "—": "-",
        "–": "-",
        "…": "...",
        "•": "-",
        "→": "->",
        "←": "<-",
        "×": "x",
    }
    normalized = "".join(replacements.get(ch, ch) for ch in text)
    return "".join(ch if ord(ch) <= 255 else "" for ch in normalized)


def wrap_pdf_line(line: str, limit: int):
    if len(line) <= limit:
        return [line]

    lines = []
    current = ""
    for word in line.split(" "):
        if len(word) > limit:
            if current:
                lines.append(current)
                current = ""
            lines.extend(word[i:i + limit] for i in range(0, len(word), limit))
            continue

        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= limit:
            current = candidate
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)
    return lines
