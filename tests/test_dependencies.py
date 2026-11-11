import gzip
from io import BytesIO
import lzma
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from src.dependencies import get_direct_dependencies
from src.errors import RepositoryError
from src.repository import decode_repository, load_repository
from src.validators import validate_package, validate_version


FIXTURES = Path(__file__).resolve().parent / "fixtures"
VERSION = "2:1.2.3-1ubuntu2~24.04.1"
EXPECTED = ["init-helper (>= 1.0)", "library-a (>= 2.0)", "library-b:any | library-c", "library-d"]


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.text = (FIXTURES / "Packages").read_text(encoding="utf-8")

    def test_direct_dependencies_of_exact_version(self):
        self.assertEqual(get_direct_dependencies(self.text, "demo", VERSION), EXPECTED)
        self.assertEqual(get_direct_dependencies(self.text, "demo", "1.0-1ubuntu1"), ["old-library"])

    def test_no_dependencies(self):
        self.assertEqual(get_direct_dependencies(self.text, "empty", "1.0"), [])

    def test_missing_package_or_version(self):
        for package, version in (("missing", "1.0"), ("demo", "9.0")):
            with self.subTest(package=package, version=version):
                with self.assertRaisesRegex(RepositoryError, "не найден"):
                    get_direct_dependencies(self.text, package, version)

    def test_final_stanza_and_case_insensitive_fields(self):
        text = "package: demo\nversion: 1.0\ndepends: library-a"
        self.assertEqual(get_direct_dependencies(text, "demo", "1.0"), ["library-a"])

    def test_malformed_index(self):
        for text in ("<html>not an index</html>", " continuation", "Package: demo\nPackage: other", "Package: demo"):
            with self.subTest(text=text):
                with self.assertRaisesRegex(RepositoryError, "Некорректный индекс"):
                    get_direct_dependencies(text, "demo", "1.0")

    def test_plain_gzip_and_xz(self):
        data = self.text.encode("utf-8")
        for content in (data, gzip.compress(data), lzma.compress(data)):
            with self.subTest(magic=content[:6]):
                self.assertEqual(decode_repository(content), self.text)

    def test_damaged_repository(self):
        for content in (b"\xff", b"\x1f\x8bwrong", b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03\x07", b"\xfd7zXZ\x00wrong"):
            with self.subTest(content=content):
                with self.assertRaises(RepositoryError):
                    decode_repository(content)

    def test_download_index(self):
        url = "https://example.org/ubuntu/dists/noble/main/binary-amd64/Packages.gz"
        config = {"repository": url, "test_mode": False}
        with patch("src.repository.urlopen", return_value=BytesIO(gzip.compress(self.text.encode()))) as request:
            text = load_repository(config, "config.ini")
        request.assert_called_once_with(url, timeout=30)
        self.assertEqual(get_direct_dependencies(text, "demo", VERSION), EXPECTED)

    def test_network_errors(self):
        config = {"repository": "https://example.org/Packages", "test_mode": False}
        errors = (
            URLError("unavailable"),
            HTTPError(config["repository"], 404, "Not Found", {}, None),
            TimeoutError("timeout"),
        )
        for error in errors:
            with self.subTest(error=error):
                with patch("src.repository.urlopen", side_effect=error):
                    with self.assertRaisesRegex(RepositoryError, "репозиторий"):
                        load_repository(config, "config.ini")

    def test_local_repository(self):
        config = {"repository": "Packages", "test_mode": True}
        with patch("src.repository.urlopen") as request:
            self.assertEqual(load_repository(config, FIXTURES / "config.ini"), self.text)
        request.assert_not_called()

    def test_apt_names_and_versions(self):
        for package in ("bash", "libstdc++6", "g++", "python3.12"):
            with self.subTest(package=package):
                validate_package(package)
        for version in ("5.2.21-2ubuntu4", VERSION, "1.0+git20240101-0ubuntu1", "1.0~rc1", "1.0-beta-1"):
            with self.subTest(version=version):
                validate_version(version)

if __name__ == "__main__":
    unittest.main()
