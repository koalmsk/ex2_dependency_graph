import configparser
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.config import load_config
from src.errors import ConfigError

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "config.ini"
        self.values = {
            "package": "demo",
            "repository": "https://archive.ubuntu.com/ubuntu/dists/noble/main/binary-amd64/Packages.gz",
            "test_mode": "false",
            "version": "2:1.2.3-1ubuntu2~24.04.1",
            "ascii_tree": "true",
        }

    def write_config(self):
        parser = configparser.ConfigParser()
        parser["settings"] = self.values
        with self.path.open("w", encoding="utf-8") as target:
            parser.write(target)

    def run_cli(self, package):
        self.values.update(
            package=package, repository=str(PROJECT_ROOT / "tests/fixtures/graph.json"), test_mode="true",
        )
        self.write_config()
        return subprocess.run(
            [sys.executable, "-m", "src.main", str(self.path)],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )

    def test_valid_config_and_cli_output(self):
        result = self.run_cli("A")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "A -> B, C\nB -> D\nC -> D\nD ->\n")
        self.assertEqual(result.stderr, "")

    def test_cli_package_without_dependencies(self):
        result = self.run_cli("K")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "K ->\n")

    def test_cli_missing_test_package(self):
        result = self.run_cli("Z")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Пакет Z не найден", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_values_for_every_parameter(self):
        invalid = {
            "package": "bad package!",
            "repository": "not-a-url",
            "test_mode": "maybe",
            "version": "latest",
            "ascii_tree": "maybe",
        }
        for key, value in invalid.items():
            with self.subTest(parameter=key):
                original = self.values[key]
                self.values[key] = value
                self.write_config()
                with self.assertRaisesRegex(ConfigError, key):
                    load_config(self.path)
                self.values[key] = original

    def test_missing_and_empty_parameters(self):
        for key in list(self.values):
            original = self.values.pop(key)
            for empty in (False, True):
                with self.subTest(parameter=key, empty=empty):
                    if empty:
                        self.values[key] = " "
                    self.write_config()
                    with self.assertRaisesRegex(ConfigError, key):
                        load_config(self.path)
            self.values[key] = original

    def test_local_repository_relative_to_config(self):
        (self.path.parent / "Packages").write_text("Package: demo\nVersion: 1.0\n", encoding="utf-8")
        self.values.update(package="A", repository="Packages", test_mode="true")
        self.write_config()
        self.assertTrue(load_config(self.path)["test_mode"])

    def test_missing_repository_file_and_directory(self):
        for repository in ("missing.json", "."):
            with self.subTest(repository=repository):
                self.values.update(package="A", repository=repository, test_mode="true")
                self.write_config()
                with self.assertRaisesRegex(ConfigError, "repository"):
                    load_config(self.path)

    def test_invalid_urls(self):
        for url in ("ftp://example.com", "https://", "https://example.com:wrong", "https://example.com:0", "https://[", "https://bad host"):
            with self.subTest(url=url):
                self.values["repository"] = url
                self.write_config()
                with self.assertRaisesRegex(ConfigError, "repository"):
                    load_config(self.path)

    def test_file_errors(self):
        with self.assertRaises(ConfigError):
            load_config(self.path)
        for content in (b"not an ini", b"[other]\nvalue=1", b"[settings]\npackage=a\npackage=b", b"\xff"):
            with self.subTest(content=content):
                self.path.write_bytes(content)
                with self.assertRaises(ConfigError):
                    load_config(self.path)

    def test_cli_error(self):
        self.values["ascii_tree"] = "maybe"
        result = self.run_cli("A")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("ascii_tree", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
