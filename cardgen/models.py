from pydantic import BaseModel, Field, field_validator


class ProductInput(BaseModel):
    name: str = ""
    manufacturer: str = ""
    specs: dict[str, str] = {}
    description: str = ""

    @field_validator("name", "manufacturer", "description", mode="before")
    @classmethod
    def _clean_text(cls, v):
        if v is None:
            return ""
        if not isinstance(v, str):
            raise ValueError("должно быть строкой")
        return v.strip()

    @field_validator("specs", mode="before")
    @classmethod
    def _clean_specs(cls, v):
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError('должно быть объектом вида {"параметр": "значение"}')
        cleaned = {}
        for key, value in v.items():
            text = "" if value is None else str(value).strip()
            if text:  # пустые значения отбрасываем
                cleaned[str(key).strip()] = text
        return cleaned


class LLMCard(BaseModel):
    """То, что пишет модель. Эта схема уходит в API как схема инструмента."""

    seo_title: str = Field(description="SEO-заголовок, не более 70 символов")
    seo_description: str = Field(
        description="SEO-описание 800-1200 символов, только факты из входных данных"
    )
    search_queries: list[str] = Field(
        description="3-5 поисковых запросов для оптимизации страницы"
    )
    commercial_block: str = Field(
        description="Кому подходит прибор и какие задачи решает, 2-4 предложения"
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Чего не хватает во входных данных для полноценной карточки",
    )


class KeySpec(BaseModel):
    name: str
    value: str


class ProductCard(LLMCard):
    """Итоговая карточка: тексты модели + характеристики, собранные кодом."""

    key_specs: list[KeySpec]
    warnings: list[str] = []  # замечания автоматической проверки
