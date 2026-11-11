from .errors import RepositoryError


def visit_level(frontier, get_dependencies, graph, discovered):
    if not frontier:
        return
    next_frontier = []
    for package in frontier:
        dependencies = list(dict.fromkeys(get_dependencies(package)))
        graph[package] = dependencies
        for dependency in dependencies:
            if dependency not in discovered:
                discovered.add(dependency)
                next_frontier.append(dependency)
    visit_level(next_frontier, get_dependencies, graph, discovered)


def build_graph(package, get_dependencies):
    graph = {}
    try:
        visit_level([package], get_dependencies, graph, {package})
    except RecursionError as error:
        raise RepositoryError("Граф слишком глубокий для рекурсивного BFS") from error
    return graph
