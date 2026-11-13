import argparse
import sys

from .config import load_config
from .apt_repository import apt_dependency_reader
from .graph import build_graph
from .graph_repository import test_dependency_reader
from .errors import ConfigError, RepositoryError
from .repository import load_repository


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Граф зависимостей пакета Ubuntu APT"
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config.ini",
        help="путь к INI-файлу (по умолчанию config.ini)",
    )
    return parser.parse_args()


def print_graph(graph):
    for package, dependencies in graph.items():
        print(f"{package} -> {', '.join(dependencies)}".rstrip())


def main():
    args = parse_arguments()
    try:
        values = load_config(args.config)
        repository = load_repository(values, args.config)
        if values["test_mode"]:
            get_dependencies = test_dependency_reader(
                repository, values["package"]
            )
        else:
            get_dependencies = apt_dependency_reader(
                repository, values["package"], values["version"]
            )
        graph = build_graph(values["package"], get_dependencies)
    except (ConfigError, RepositoryError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    print_graph(graph)
    return 0
