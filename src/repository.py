import gzip
import lzma
import zlib
from http.client import HTTPException
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from .errors import RepositoryError


def load_repository(config, config_path):
    repository = config["repository"]
    try:
        if config["test_mode"]:
            path = Path(repository)
            if not path.is_absolute():
                path = Path(config_path).parent / path
            data = path.read_bytes()
        else:
            with urlopen(repository, timeout=30) as response:
                data = response.read()
    except (OSError, ValueError, URLError, HTTPException) as error:
        raise RepositoryError(f"Не удалось прочитать репозиторий: {error}") from error
    return decode_repository(data)


def decode_repository(data):
    try:
        if data.startswith(b"\x1f\x8b"):
            data = gzip.decompress(data)
        elif data.startswith(b"\xfd7zXZ\x00"):
            data = lzma.decompress(data)
        return data.decode("utf-8")
    except (OSError, EOFError, lzma.LZMAError, zlib.error, UnicodeError) as error:
        raise RepositoryError(f"Не удалось распаковать или декодировать индекс Packages: {error}") from error

