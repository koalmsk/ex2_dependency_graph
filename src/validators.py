import re
from pathlib import Path
from urllib.parse import urlsplit

from .errors import ConfigError

PACKAGE_PATTERN = r"[a-z0-9][a-z0-9+.-]+"
VERSION_PATTERN = r"(?:[0-9]+:)?[0-9][A-Za-z0-9.+~]*(?:[A-Za-z0-9.+~-]*-[A-Za-z0-9.+~]+)?"


def validate_package(package, test_mode=False):
    pattern = r"[A-Z]+" if test_mode else PACKAGE_PATTERN
    if not re.fullmatch(pattern, package):
        raise ConfigError("Параметр package: недопустимое имя пакета")


def parse_boolean(section, key):
    try:
        return section.getboolean(key)
    except ValueError as error:
        raise ConfigError(f"Параметр {key}: ожидается true/false, yes/no, on/off или 1/0") from error


def validate_version(version):
    if not re.fullmatch(VERSION_PATTERN, version):
        raise ConfigError("Параметр version: недопустимая версия APT, пример: 5.2.21-2ubuntu4")


def validate_repository(repository, test_mode, config_path):
    if not test_mode:
        validate_repository_url(repository)
        return
    repository_path = Path(repository)
    if not repository_path.is_absolute():
        repository_path = config_path.parent / repository_path
    try:
        with repository_path.open("rb") as source:
            source.read(1)
    except (OSError, ValueError) as error:
        raise ConfigError(f"Параметр repository: не удалось открыть файл {repository_path}: {error}") from error


def validate_repository_url(repository):
    try:
        url = urlsplit(repository)
        valid = url.scheme in ("http", "https") and bool(url.hostname)
        valid = valid and not any(character.isspace() for character in repository)
        if url.port is not None:
            valid = valid and 1 <= url.port <= 65535
    except ValueError:
        valid = False
    if not valid:
        raise ConfigError("Параметр repository: ожидается URL с протоколом http или https")

