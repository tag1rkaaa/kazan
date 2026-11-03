from cardgen.config import ConfigError, load_settings

try:
    s = load_settings()
    print(f"OK. Адрес: {s.base_url}, модель: {s.model}, ключ: задан")
except ConfigError as e:
    print(f"Ошибка: {e}")
