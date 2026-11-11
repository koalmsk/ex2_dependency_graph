import gzip
from http.client import HTTPException
import lzma
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
import zlib

from .errors import RepositoryError


def read_repository(repository, test_mode, config_path):
    try:
        if test_mode:
            path = Path(repository)
            if not path.is_absolute():
                path = Path(config_path).parent / path
            return path.read_bytes()
        with urlopen(repository, timeout=30) as response:
            return response.read()
    except (OSError, ValueError, URLError, HTTPException) as error:
        raise RepositoryError(f"Не удалось прочитать репозиторий: {error}") from error


def decode_repository(data):
    try:
        if data.startswith(b"\x1f\x8b"):
            data = gzip.decompress(data)
        elif data.startswith(b"\xfd7zXZ\x00"):
            data = lzma.decompress(data)
        return data.decode("utf-8")
    except (OSError, EOFError, lzma.LZMAError, zlib.error, UnicodeError) as error:
        raise RepositoryError(f"Не удалось распаковать или декодировать индекс Packages: {error}") from error


def load_repository(config, config_path):
    data = read_repository(config["repository"], config["test_mode"], config_path)
    return decode_repository(data)
