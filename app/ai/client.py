import os
from functools import lru_cache

from openai import OpenAI

from app.settings import OPENAI_MODEL, OPENAI_FAST_MODEL


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_ai_model() -> str:
    return OPENAI_MODEL


def get_fast_ai_model() -> str:
    return OPENAI_FAST_MODEL
