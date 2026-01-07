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
    c.drawString(x_margin, y, f"Día {day}: {title}")
    y -= 30

    # Texto
    c.setFont("Helvetica", 10)

    for line in text.split("\n"):
        if y < y_margin:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - y_margin

        # Evitar líneas demasiado largas
        while len(line) > 110:
            c.drawString(x_margin, y, line[:110])
            line = line[110:]
            y -= 14
            if y < y_margin:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - y_margin

        c.drawString(x_margin, y, line)
        y -= 14

    c.save()
    return filename
