from collections import deque

from .errors import RepositoryError


def get_load_order(graph):
    remaining = {
        name: len(dependencies) for name, dependencies in graph.items()
    }
    dependents = {name: [] for name in graph}
    for name, dependencies in graph.items():
        for dependency in dependencies:
            dependents[dependency].append(name)
    ready = deque(name for name in graph if not remaining[name])
    order = []
    while ready:
        name = ready.popleft()
        order.append(name)
        for dependent in dependents[name]:
            remaining[dependent] -= 1
            if not remaining[dependent]:
                ready.append(dependent)
    if len(order) != len(graph):
        raise RepositoryError(
            "Граф содержит цикл: порядок загрузки "
            "с зависимостями перед пакетами невозможен"
        )
    return order
