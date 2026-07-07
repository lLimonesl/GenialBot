from story_engine import (
    build_character_rotation_context,
    extract_level_ups,
    extract_metadata,
    format_prompt_value,
    strip_metadata_tags,
    strip_prompt_leaks,
)


def test_extract_level_ups_accepts_expected_format():
    assert extract_level_ups("[LEVEL_UP] Javiche +2 niveles") == [("Javiche", 2)]


def test_extract_metadata_reads_quotes_and_weather():
    metadata = extract_metadata('[WEATHER] Lluvia fina\n[QUOTE] Red: "La noche recuerda."')

    assert metadata["weather"] == "Lluvia fina"
    assert metadata["quotes"] == [("Red", "La noche recuerda.")]


def test_strip_metadata_tags_keeps_story_text():
    text = "La batalla termino.\n[WEATHER] Niebla"


    assert strip_metadata_tags(text) == "La batalla termino."


def test_strip_prompt_leaks_removes_context_sections():
    leaked = "Intro\nPERSONAJES VIVOS:\n- secreto\nNarracion final"

    assert strip_prompt_leaks(leaked) == "Intro"


def test_format_prompt_value_translates_ability_keys():
    text = format_prompt_value({
        "name": "Duplicar",
        "description": "Crea copias temporales.",
        "limits": "Maximo 5 copias.",
        "cost": "Gasta mana.",
        "cooldown": "1 dia.",
    })

    assert "Limites" in text
    assert "Coste" in text
    assert "Enfriamiento" in text
    assert "limits:" not in text.lower()
    assert "cost:" not in text.lower()


def test_format_prompt_value_handles_pet_gender_without_sex_name():
    text = format_prompt_value({"name": "Lobo gigante", "sex": "Macho"})

    assert "Mascota/companero: Lobo gigante" in text
    assert "Genero: Macho" in text
    assert "Sex" not in text


def test_build_character_rotation_context_blocks_two_consecutive_days():
    recent_days = [
        {"day": 5, "title": "Dia 5", "summary": "Javiche combate.", "full_text": "Javiche gana."},
        {"day": 4, "title": "Dia 4", "summary": "Javiche viaja.", "full_text": "Javiche decide."},
        {"day": 3, "title": "Dia 3", "summary": "Red observa.", "full_text": "Red espera."},
    ]
    characters = [{"name": "Javiche"}, {"name": "Red"}, {"name": "Winters"}]

    context = build_character_rotation_context(recent_days, characters)

    assert "Javiche" in context
    assert "Personajes bloqueados" in context
    assert "Winters" in context
