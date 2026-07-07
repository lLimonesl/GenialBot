from story_engine import extract_level_ups, extract_metadata, strip_metadata_tags, strip_prompt_leaks


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
