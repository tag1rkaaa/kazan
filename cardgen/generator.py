import re

from .config import Settings
from .llm import LLMError, generate_card_text
from .models import KeySpec, ProductCard, ProductInput
from .validation import check_card, find_gaps

MAX_ATTEMPTS = 3
NO_DATA = "данных нет"

# Отдельное предложение «Данных нет» в конце текста: недостающее и так показано в таблице
_TRAILING_NO_DATA = re.compile(r"(?<=[.!?])\s+данных нет\.?\s*$", re.IGNORECASE)


def _strip_no_data(text: str) -> str:
    return _TRAILING_NO_DATA.sub("", text).strip()


def _empty_card(product: ProductInput, gaps: list[str]) -> ProductCard:
    """Карточка-заглушка, когда данных нет совсем. Модель не вызывается."""
    return ProductCard(
        seo_title=product.name[:70],
        seo_description=f"{NO_DATA}: во входных данных нет ни характеристик, ни описания.",
        search_queries=[product.name],
        commercial_block=NO_DATA,
        missing_data=gaps,
        key_specs=[],
        warnings=[
            "Данных недостаточно для карточки: текст не формировался, "
            "чтобы не выдумывать характеристики. Дополните входной JSON"
        ],
    )


def generate_card(settings: Settings, product: ProductInput) -> ProductCard:
    gaps = find_gaps(product)

    if not product.specs and not product.description:
        return _empty_card(product, gaps)

    llm_card = None
    issues: list[str] = []
    notes: list[str] = []

    for _ in range(MAX_ATTEMPTS):
        try:
            new_card = generate_card_text(settings, product, issues or None)
        except LLMError:
            if llm_card is None:
                raise  # первая попытка не удалась совсем, показываем ошибку
            break  # иначе оставляем лучшее, что уже есть
        new_card.seo_description = _strip_no_data(new_card.seo_description)
        new_card.commercial_block = _strip_no_data(new_card.commercial_block)
        llm_card = new_card
        issues, notes = check_card(llm_card, product)
        if not issues:
            break

    if llm_card is None:  # сюда не попасть, но так проверка типов спокойна
        raise LLMError("Не удалось получить карточку от модели")

    # Список пробелов считает код: модель 7b добавляла в него ошибочные пункты
    data = llm_card.model_dump()
    data["missing_data"] = gaps
    data["seo_description"] = _strip_no_data(data["seo_description"])
    data["commercial_block"] = _strip_no_data(data["commercial_block"])
    key_specs = [KeySpec(name=k, value=v) for k, v in product.specs.items()]
    return ProductCard(**data, key_specs=key_specs, warnings=issues + notes)
