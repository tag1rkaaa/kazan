from .models import ProductCard

NO_DATA = "данных нет"

# Характеристики, которые контент-менеджер ожидает увидеть в карточке КИП.
# (подпись в таблице, основа слова для поиска в названиях пришедших параметров)
EXPECTED_SPECS = [
    ("Диапазон измерений", "диапазон"),
    ("Класс точности", "класс"),
    ("Питание", "питан"),
    ("Тип / диаметр корпуса", "корпус"),
    ("Интерфейсы", "интерфейс"),
]


def _cell(text: str) -> str:
    """Экранирует символы, ломающие таблицу Markdown."""
    return text.replace("|", "\\|").replace("\n", " ")


def _missing_expected(card: ProductCard) -> list[str]:
    names = [s.name.lower().replace("ё", "е") for s in card.key_specs]
    return [
        label
        for label, stem in EXPECTED_SPECS
        if not any(stem in name for name in names)
    ]


def to_markdown(card: ProductCard, product_name: str) -> str:
    lines = [
        f"# {product_name}",
        "",
        "> Черновик карточки товара. Перед публикацией проверьте текст.",
        "",
        "## SEO",
        "",
        f"**Заголовок** ({len(card.seo_title)}/70 символов):",
        "",
        card.seo_title,
        "",
        f"**Описание** ({len(card.seo_description)} символов, цель 800-1200):",
        "",
        card.seo_description,
        "",
        "## Ключевые характеристики",
        "",
        "| Параметр | Значение |",
        "|---|---|",
    ]
    lines += [f"| {_cell(s.name)} | {_cell(s.value)} |" for s in card.key_specs]
    lines += [f"| {label} | {NO_DATA} |" for label in _missing_expected(card)]
    lines.append("")

    lines += ["## Поисковые запросы", ""]
    lines += [f"- {q}" for q in card.search_queries]
    lines.append("")

    lines += ["## Для менеджера", "", card.commercial_block, ""]

    if card.missing_data or card.warnings:
        lines += ["## Требует внимания", ""]
        if card.missing_data:
            lines.append("**Не хватает данных:**")
            lines += [f"- {m}" for m in card.missing_data]
            lines.append("")
        if card.warnings:
            lines.append("**Замечания автоматической проверки:**")
            lines += [f"- {w}" for w in card.warnings]
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
