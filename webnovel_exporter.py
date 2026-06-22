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
    body {{ margin: 0; font-family: Georgia, serif; background: radial-gradient(circle at top left, #26324f, transparent 32rem), #080b13; color: #f8fafc; }}
    header {{ padding: 56px 24px; text-align: center; border-bottom: 1px solid rgba(148,163,184,.22); background: rgba(8,11,19,.72); }}
    main {{ max-width: 920px; margin: 0 auto; padding: 34px 20px 60px; }}
    nav, .chapter {{ background: rgba(18,24,39,.86); padding: 26px; margin-bottom: 28px; border: 1px solid rgba(148,163,184,.18); border-radius: 22px; box-shadow: 0 24px 70px rgba(0,0,0,.28); }}
    a {{ color: #7dd3fc; text-decoration: none; }}
    a:hover {{ color: #bae6fd; }}
    h1, h2, h3 {{ margin-top: 0; letter-spacing: -.02em; }}
    li {{ margin: 8px 0; }}
    .weather {{ color: #a8b3c7; font-style: italic; }}
    .story p {{ line-height: 1.82; font-size: 1.08rem; color: #e5edf8; }}
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
