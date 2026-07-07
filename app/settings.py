import os

from dotenv import load_dotenv


load_dotenv()


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_int_env(name: str, fallback_name: str | None = None, default: int | None = None) -> int:
    raw_value = os.getenv(name)
    if raw_value is None and fallback_name:
        raw_value = os.getenv(fallback_name)
    if raw_value is None:
        if default is None:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return default
    return int(raw_value)


OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
OPENAI_FAST_MODEL = os.getenv("OPENAI_FAST_MODEL", OPENAI_MODEL)
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
ENABLE_LEGACY_PREFIX_COMMANDS = os.getenv("ENABLE_LEGACY_PREFIX_COMMANDS", "true").lower() in {"1", "true", "yes", "on"}
