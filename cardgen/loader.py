import json
from pathlib import Path

from pydantic import ValidationError

from .models import ProductInput


class InputError(Exception):
    """Входные данные нельзя использовать."""


def load_product(path: str) -> ProductInput:
    p = Path(path)
    try:
        # utf-8-sig спокойно читает файлы с BOM, которые любит Блокнот Windows
        raw = p.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise InputError(f"Файл не найден: {p}")
    except (OSError, UnicodeDecodeError) as e:
        raise InputError(f"Не удалось прочитать файл {p}: {e}")
    return parse_product(raw)


def parse_product(raw: str) -> ProductInput:
    if not raw.strip():
        raise InputError("Файл пустой: ожидался JSON с данными товара")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InputError(
            f"Некорректный JSON: {e.msg} (строка {e.lineno}, позиция {e.colno})"
        ) from e

    if not isinstance(data, dict):
        raise InputError("Ожидался JSON-объект {...} с данными одного товара")

    try:
        return ProductInput.model_validate(data)
    except ValidationError as e:
        problems = "; ".join(
            f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()
        )
        raise InputError(f"Неверная структура данных: {problems}") from e
