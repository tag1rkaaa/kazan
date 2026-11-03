import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(Exception):
    """Ошибка настройки."""


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str


def load_settings() -> Settings:
    load_dotenv()  # подтягивает переменные из .env, если файл есть

    base_url = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "").strip()  # для Ollama может быть пустым
    model = os.getenv("LLM_MODEL", "").strip()

    if not base_url:
        raise ConfigError(
            "Не задан LLM_BASE_URL. Заполните .env по образцу .env.example"
        )
    if not api_key:
        raise ConfigError("Не задан LLM_API_KEY. Впишите ключ OpenRouter в .env")
    if not model:
        raise ConfigError("Не задан LLM_MODEL. Заполните .env по образцу .env.example")

    return Settings(base_url=base_url, api_key=api_key, model=model)
