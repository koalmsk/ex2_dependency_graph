import argparse
import sys

from .config import load_config
from .dependencies import get_direct_dependencies
from .errors import ConfigError, RepositoryError
from .repository import load_repository


def parse_arguments():
    parser = argparse.ArgumentParser(description="Прямые зависимости пакета Ubuntu APT")
    parser.add_argument("config", nargs="?", default="config.ini", help="путь к INI-файлу (по умолчанию config.ini)")
    return parser.parse_args()


def print_dependencies(dependencies):
    if not dependencies:
        print("Прямых зависимостей нет.")
    for dependency in dependencies:
        print(dependency)


def main():
    args = parse_arguments()
    try:
        values = load_config(args.config)
        repository = load_repository(values, args.config)
        dependencies = get_direct_dependencies(repository, values["package"], values["version"])
    except (ConfigError, RepositoryError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    print_dependencies(dependencies)
    return 0
