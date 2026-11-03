import re

from .loader import InputError
from .models import LLMCard, ProductInput

NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
WORD_RE = re.compile(r"[а-яa-z0-9]+")

# Основы слов, которые модель любит добавлять "для красоты" (без ё)
UNSUPPORTED_STEMS = [
    "надежн",
    "идеальн",
    "защит",
    "высок",
    "качеств",
    "эксперт",
    "профессионал",
    "долговеч",
    "безопасн",
    "лучш",
    "быстр",
    "стабильн",
    "универсальн",
    "современн",
    "оптимальн",
    "удобств",
    "комфортн",
    "эффективн",
]

# Если во входных данных меньше символов, 800 символов без выдумок не набрать
THIN_SOURCE_CHARS = 1000


def find_gaps(product: ProductInput) -> list[str]:
    """Возвращает список пробелов в данных (предупреждения)."""
    gaps = []
    if not product.manufacturer:
        gaps.append("не указан производитель")
    if not product.specs:
        gaps.append("нет характеристик (specs)")
    if not product.description:
        gaps.append("нет описания или фрагмента техпаспорта")
    return gaps


def ensure_usable(product: ProductInput) -> None:
    """Без названия карточку делать бессмысленно."""
    if not product.name:
        raise InputError("Не указано название товара (поле name)")


def _norm(text: str) -> str:
    return text.lower().replace("ё", "е")


def _numbers(text: str) -> set[str]:
    return {n.replace(",", ".") for n in NUM_RE.findall(text)}


def _source_text(product: ProductInput) -> str:
    parts = [product.name, product.manufacturer, product.description]
    for key, value in product.specs.items():
        parts += [key, value]
    return " ".join(parts)


def _unknown_query_words(query: str, source_n: str) -> list[str]:
    """Слова запроса (5+ букв), основы которых не встречаются во входных данных."""
    unknown = []
    for word in WORD_RE.findall(_norm(query)):
        if len(word) >= 5 and word[:5] not in source_n:
            unknown.append(word)
    return unknown


def check_card(card: LLMCard, product: ProductInput) -> tuple[list[str], list[str]]:
    """Возвращает (issues, notes).
    issues: замечания, из-за которых стоит переделать текст;
    notes: пометки для менеджера, переделкой не лечатся."""
    issues: list[str] = []
    notes: list[str] = []
    source = _source_text(product)
    source_n = _norm(source)

    title_len = len(card.seo_title.strip())
    if title_len == 0:
        issues.append("SEO-заголовок пустой")
    elif title_len > 70:
        issues.append(
            f"SEO-заголовок слишком длинный: {title_len} символов, нужно не более 70"
        )

    desc_len = len(card.seo_description.strip())
    if desc_len > 1200:
        issues.append(
            f"SEO-описание слишком длинное: {desc_len} символов, нужно 800-1200"
        )
    elif desc_len < 800:
        if len(source) < THIN_SOURCE_CHARS:
            notes.append(
                f"Во входных данных мало информации: SEO-описание получилось {desc_len} "
                "символов вместо 800-1200. Текст намеренно не растягивался, чтобы не "
                "выдумывать факты. Дополните данные или доработайте текст вручную"
            )
        else:
            issues.append(
                f"SEO-описание слишком короткое: {desc_len} символов, нужно 800-1200"
            )

    if not 3 <= len(card.search_queries) <= 5:
        issues.append(f"Поисковых запросов {len(card.search_queries)}, нужно от 3 до 5")

    for query in card.search_queries:
        bad = _unknown_query_words(query, source_n)
        if bad:
            issues.append(
                f"в поисковом запросе «{query}» есть слова, которых нет во входных данных: "
                + ", ".join(bad)
                + ". Запросы должны строиться только из названия, типа прибора, "
                "производителя и характеристик"
            )

    if not card.commercial_block.strip():
        issues.append("commercial-блок пустой")

    text = " ".join(
        [
            card.seo_title,
            card.seo_description,
            card.commercial_block,
            *card.search_queries,
        ]
    )

    extra_numbers = sorted(_numbers(text) - _numbers(source))
    if extra_numbers:
        issues.append(
            "в тексте есть числа, которых нет во входных данных: "
            + ", ".join(extra_numbers)
        )

    text_n = _norm(text)
    unsupported = [s for s in UNSUPPORTED_STEMS if s in text_n and s not in source_n]
    if unsupported:
        issues.append(
            "в тексте есть утверждения без опоры на входные данные (слова с основами: "
            + ", ".join(unsupported)
            + "). Уберите их: опирайтесь только на входные данные"
        )

    return issues, notes
