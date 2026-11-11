import re

from .dependencies import find_package, parse_packages
from .errors import RepositoryError


def dependency_names(fields):
    names = []
    dependencies = ",".join(fields.get(key, "") for key in ("pre-depends", "depends"))
    for alternative in re.split(r"[,|]", dependencies):
        if not alternative.strip():
            continue
        match = re.match(r"\s*([a-z0-9][a-z0-9+.-]*)", alternative)
        if match is None:
            raise RepositoryError(f"Некорректная зависимость: {alternative}")
        names.append(match.group(1))
    return list(dict.fromkeys(names))


def index_packages(text):
    packages = {}
    providers = {}
    for fields in parse_packages(text):
        if not fields.get("package") or not fields.get("version"):
            raise RepositoryError("Некорректный индекс Packages: отсутствует Package или Version")
        name = fields["package"]
        packages.setdefault(name, fields)
        for provided in fields.get("provides", "").split(","):
            if provided.strip():
                virtual = provided.strip().split()[0]
                providers.setdefault(virtual, []).append(name)
    return packages, providers


def apt_dependency_reader(text, package, version):
    root = find_package(text, package, version)
    packages, providers = index_packages(text)
    packages[package] = root

    def get_dependencies(name):
        if name in packages:
            return dependency_names(packages[name])
        if name in providers:
            return providers[name]
        raise RepositoryError(f"Пакет зависимости {name} отсутствует в индексе репозитория")

    return get_dependencies
