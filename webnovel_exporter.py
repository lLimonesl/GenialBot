import html
import os

from database import get_all_days, get_quotes_for_day, get_all_battles


OUTPUT_DIR = "novel"


async def export_web_novel():
    days = await get_all_days()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "index.html")

    chapters = []
    toc = []
    battles = await get_all_battles()
    for day in days:
        day_number = day["day"]
        title = day["title"] or f"Día {day_number}"
        weather = day["weather"] or "No registrado"
        text = day["full_text"] or day["summary"] or ""
        quotes = await get_quotes_for_day(day_number)
        day_battles = [b for b in battles if b["day"] == day_number]

        toc.append(f'<li><a href="#day-{day_number}">{html.escape(title)}</a></li>')
        quote_html = "".join(
            f'<li>"{html.escape(q["quote"])}" — {html.escape(q["character_name"] or "Desconocido")}</li>'
            for q in quotes
        )
        battle_html = "".join(
            f'<li><strong>{html.escape(b["outcome"] or "Resultado")}</strong>: {html.escape(b["summary"] or "")}</li>'
            for b in day_battles
        )

        sections = [
            f'<article id="day-{day_number}" class="chapter">',
            f'<h2>{html.escape(title)}</h2>',
            f'<p class="weather">Clima: {html.escape(weather)}</p>',
            f'<div class="story">{format_story_html(text)}</div>'
        ]
        if quote_html:
            sections.append(f'<h3>Citas</h3><ul>{quote_html}</ul>')
        if battle_html:
            sections.append(f'<h3>Combates</h3><ul>{battle_html}</ul>')
        sections.append('</article>')
        chapters.append("\n".join(sections))

    page = build_page("\n".join(toc), "\n".join(chapters))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)

    return output_path


def format_story_html(text):
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    return "\n".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)


def build_page(toc, chapters):
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GenialBot - Web Novel</title>
  <style>
    body {{ margin: 0; font-family: Georgia, serif; background: #f6efe3; color: #24160e; }}
    header {{ padding: 48px 24px; text-align: center; background: #24160e; color: #f6efe3; }}
    main {{ max-width: 900px; margin: 0 auto; padding: 32px 20px; }}
    nav, .chapter {{ background: #fffaf0; padding: 24px; margin-bottom: 28px; border: 1px solid #dac7a5; }}
    a {{ color: #7a3415; }}
    h1, h2, h3 {{ font-family: Georgia, serif; }}
    .weather {{ color: #6c5b46; font-style: italic; }}
    .story p {{ line-height: 1.75; font-size: 1.08rem; }}
  </style>
</head>
<body>
  <header>
    <h1>GenialBot</h1>
    <p>Archivo web novel de la historia</p>
  </header>
  <main>
    <nav>
      <h2>Índice</h2>
      <ol>{toc}</ol>
    </nav>
    {chapters}
  </main>
</body>
</html>"""
