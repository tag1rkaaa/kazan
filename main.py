import argparse
import sys
from pathlib import Path

from cardgen.config import ConfigError, load_settings
from cardgen.generator import generate_card
from cardgen.llm import LLMError
from cardgen.loader import InputError, load_product
from cardgen.render import to_markdown
from cardgen.validation import ensure_usable


def process(path: str, settings, out_dir: Path, quiet: bool) -> None:
    product = load_product(path)
    ensure_usable(product)
    card = generate_card(settings, product)
    markdown = to_markdown(card, product.name)

    stem = Path(path).stem
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{stem}.md").write_text(markdown, encoding="utf-8")
    (out_dir / f"{stem}.json").write_text(
        card.model_dump_json(indent=2), encoding="utf-8"
    )

    if not quiet:
        print(markdown)
    print(f"Готово: {out_dir / (stem + '.md')} и {stem}.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Генератор черновика карточки товара по JSON с данными прибора"
    )
    parser.add_argument(
        "files", nargs="+", help="один или несколько JSON-файлов с товарами"
    )
    parser.add_argument(
        "--out", default="output", help="папка для результатов (по умолчанию output)"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="не печатать результат в консоль"
    )
    args = parser.parse_args()

    try:
        settings = load_settings()
    except ConfigError as e:
        print(f"ОШИБКА НАСТРОЙКИ: {e}")
        return 1

    out_dir = Path(args.out)
    failed = 0
    for path in args.files:
        print(f"\n=== {path} ===")
        try:
            process(path, settings, out_dir, args.quiet)
        except (InputError, LLMError) as e:
            failed += 1
            print(f"ОШИБКА: {e}")
        except Exception as e:  # непредвиденное: не роняем обработку остальных файлов
            failed += 1
            print(f"Непредвиденная ошибка ({type(e).__name__}): {e}")

    if failed:
        print(f"\nНе обработано файлов: {failed} из {len(args.files)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
