import json
import re

from .errors import RepositoryError


def parse_test_repository(text):
    try:
        graph = json.loads(text)
    except ValueError as error:
        raise RepositoryError(
            f"Некорректный JSON тестового репозитория: {error}"
        ) from error
    if not isinstance(graph, dict):
        raise RepositoryError("Тестовый репозиторий должен быть объектом JSON")
    for package, dependencies in graph.items():
        if not re.fullmatch(r"[A-Z]+", package):
            raise RepositoryError(
                "Имена тестовых пакетов должны состоять "
                "из больших латинских букв"
            )
        if not isinstance(dependencies, list):
            raise RepositoryError(f"Зависимости {package} должны быть списком")
        for dependency in dependencies:
            if not isinstance(dependency, str) or dependency not in graph:
                raise RepositoryError(
                    f"Неизвестная зависимость пакета {package}: "
                    f"{dependency}"
                )
    return graph


def test_dependency_reader(text, package):
    graph = parse_test_repository(text)
    if package not in graph:
        raise RepositoryError(
            f"Пакет {package} не найден в тестовом репозитории"
        )
    return graph.__getitem__
