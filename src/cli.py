import argparse
import sys

from .config import load_config
from .errors import ConfigError


def parse_arguments():
    parser = argparse.ArgumentParser(description="Прототип визуализатора зависимостей: проверка конфигурации")
    parser.add_argument("config", nargs="?", default="config.ini", help="путь к INI-файлу (по умолчанию config.ini)")
    return parser.parse_args()


def print_config(values):
    for key, value in values.items():
        if isinstance(value, bool):
            value = str(value).lower()
        print(f"{key}={value}")


def main():
    args = parse_arguments()
    try:
        values = load_config(args.config)
    except ConfigError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    print_config(values)
    return 0
