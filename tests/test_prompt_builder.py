from app.ai.prompt_builder import PromptBlock, render_generation_contract, render_prompt_blocks


def test_render_prompt_blocks_uses_clear_sections():
    prompt = render_prompt_blocks([
        PromptBlock("Canon", "Regla permanente"),
        PromptBlock("Personajes", "Javiche"),
    ])

    assert "## Canon" in prompt
    assert "Regla permanente" in prompt
    assert "## Personajes" in prompt
    assert "Javiche" in prompt


def test_render_generation_contract_names_day():
    contract = render_generation_contract(12)

    assert "Dia 12" in contract
    assert "metadatos" in contract
