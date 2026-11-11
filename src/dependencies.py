from .errors import RepositoryError


def parse_packages(text):
    fields = {}
    last_key = None
    for line in text.splitlines():
        if not line.strip():
            if fields:
                yield fields
            fields = {}
            last_key = None
        elif line.startswith((" ", "\t")):
            if last_key is None:
                raise RepositoryError("Некорректный индекс Packages: продолжение без поля")
            fields[last_key] += " " + line.strip()
        else:
            key, separator, value = line.partition(":")
            key = key.lower()
            if not separator or not key or key in fields:
                raise RepositoryError("Некорректный индекс Packages: неверное или повторное поле")
            fields[key] = value.strip()
            last_key = key
    if fields:
        yield fields


def find_package(text, package, version):
    for fields in parse_packages(text):
        if "package" not in fields or "version" not in fields:
            raise RepositoryError("Некорректный индекс Packages: отсутствует Package или Version")
        if fields["package"] == package and fields["version"] == version:
            return fields
    raise RepositoryError(f"Пакет {package} версии {version} не найден в репозитории")


def get_direct_dependencies(text, package, version):
    fields = find_package(text, package, version)
    dependencies = []
    for key in ("pre-depends", "depends"):
        dependencies.extend(item.strip() for item in fields.get(key, "").split(",") if item.strip())
    return dependencies
