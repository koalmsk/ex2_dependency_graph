import configparser
from pathlib import Path

from .errors import ConfigError
from .validators import (
    parse_boolean,
    validate_package,
    validate_repository,
    validate_version,
)

CONFIG_KEYS = ("package", "repository", "test_mode", "version", "ascii_tree")


def read_settings(path):
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with path.open(encoding="utf-8") as source:
            parser.read_file(source)
    except (OSError, UnicodeError, configparser.Error) as error:
        raise ConfigError(
            f"Не удалось прочитать INI-файл {path}: {error}"
        ) from error
    if "settings" not in parser:
        raise ConfigError("Отсутствует секция [settings]")
    return parser["settings"]


def load_config(path):
    path = Path(path)
    section = read_settings(path)
    values = {}
    for key in CONFIG_KEYS:
        if key not in section or not section[key].strip():
            raise ConfigError(f"Параметр {key}: необходимо указать значение")
        values[key] = section[key].strip()
    for key in ("test_mode", "ascii_tree"):
        values[key] = parse_boolean(section, key)
    values["load_order"] = (
        parse_boolean(section, "load_order")
        if "load_order" in section else False
    )
    validate_package(values["package"], values["test_mode"])
    validate_version(values["version"])
    validate_repository(values["repository"], values["test_mode"], path)
    return values
