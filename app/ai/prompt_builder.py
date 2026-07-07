from dataclasses import dataclass


@dataclass(frozen=True)
class PromptBlock:
    title: str
    content: str


def render_prompt_blocks(blocks: list[PromptBlock]) -> str:
    sections = []
    for block in blocks:
        content = (block.content or "No registrado.").strip()
        sections.append(f"## {block.title}\n{content}")
    return "\n\n".join(sections)


def render_generation_contract(day: int) -> str:
    return f"""
## Contrato de salida
Escribe el Dia {day}.
No copies ni resumas las secciones de contexto del prompt.
La respuesta final debe contener solo la narracion del dia y, al final, metadatos con tags si aplican.
Las consecuencias son permanentes y deben respetar el canon.
""".strip()
