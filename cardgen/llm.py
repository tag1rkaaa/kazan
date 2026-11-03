import httpx
from pydantic import ValidationError

from .config import Settings
from .models import LLMCard, ProductInput
from .prompts import SYSTEM_PROMPT, build_user_message

OUTPUT_TEMPLATE = """{
  "seo_title": "<строка, не более 70 символов>",
  "seo_description": "<строка, 800-1200 символов>",
  "search_queries": ["<запрос 1>", "<запрос 2>", "<запрос 3>"],
  "commercial_block": "<строка, 2-4 предложения>",
  "missing_data": ["<чего не хватает>"]
}"""


class LLMError(Exception):
    """Не удалось получить корректный ответ от модели."""


def _extract_json(text: str) -> str:
    """Берём всё от первой { до последней }: так отбрасываются рассуждения,
    пояснения и markdown-обёртка вокруг JSON."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return text.strip()
    return text[start : end + 1]


def generate_card_text(
    settings: Settings, product: ProductInput, feedback: list[str] | None = None
) -> LLMCard:
    user_message = (
        build_user_message(product)
        + "\n\nВерни ТОЛЬКО один JSON-объект такого вида, без пояснений и без markdown. "
        + "Вместо <...> подставь реальные значения на русском языке. "
        + "Не добавляй других полей:\n"
        + OUTPUT_TEMPLATE
    )
    if feedback:
        user_message += (
            "\n\nПредыдущий вариант отклонён автоматической проверкой. Замечания:\n- "
            + "\n- ".join(feedback)
            + "\nИсправь их. Новых фактов и чисел, которых нет во входных данных, не добавляй."
        )

    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json"}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"

    try:
        response = httpx.post(
            f"{settings.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=600,
        )
        response.raise_for_status()
    except httpx.ConnectError:
        raise LLMError(
            "Не удаётся подключиться к API. Проверьте LLM_BASE_URL и запущена ли Ollama"
        )
    except httpx.TimeoutException:
        raise LLMError("Сервис отвечает слишком долго. Попробуйте модель поменьше")
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code == 429:
            raise LLMError("Превышен лимит запросов. Повторите позже")
        if code == 404:
            raise LLMError(
                f"Модель или адрес не найдены (404). Проверьте LLM_MODEL: {settings.model}"
            )
        raise LLMError(f"Ошибка API ({code}): {e.response.text[:300]}")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise LLMError("Неожиданный формат ответа API")

    if not content:
        raise LLMError("Модель вернула пустой ответ")

    try:
        return LLMCard.model_validate_json(_extract_json(content))
    except ValidationError as e:
        raise LLMError(
            f"Модель вернула неполные или некорректные данные.\n"
            f"Ответ модели (начало): {content[:300]}\n{e}"
        ) from e
