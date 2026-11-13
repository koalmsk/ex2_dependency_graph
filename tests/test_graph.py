from contextlib import redirect_stderr, redirect_stdout
import configparser
from io import StringIO
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.apt_repository import apt_dependency_reader
from src.cli import main
from src.errors import ConfigError, RepositoryError
from src.graph import build_graph
from src.graph_repository import parse_test_repository, test_dependency_reader
from src.validators import validate_package


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class GraphTests(unittest.TestCase):
    def test_bfs_visits_levels_and_expands_each_node_once(self):
        repository = {
            "A": ["B", "C"], "B": ["D"], "C": ["D", "E"],
            "D": ["A"], "E": [],
        }
        visited = []

        def dependencies(package):
            visited.append(package)
            return repository[package]

        self.assertEqual(build_graph("A", dependencies), repository)
        self.assertEqual(visited, ["A", "B", "C", "D", "E"])

    def test_deduplicate_edges(self):
        repository = {"A": ["B", "B"], "B": []}
        self.assertEqual(
            build_graph("A", repository.__getitem__), {"A": ["B"], "B": []}
        )

    def test_test_repository_errors(self):
        for text in (
            'not json', '[]', '{"a": []}', '{"А": []}',
            '{"A": "B"}', '{"A": [1]}', '{"A": ["B"]}',
        ):
            with self.subTest(text=text):
                with self.assertRaises(RepositoryError):
                    parse_test_repository(text)
        with self.assertRaisesRegex(RepositoryError, "не найден"):
            test_dependency_reader('{"A": []}', "Z")

    def test_test_names(self):
        for name in ("A", "ABC"):
            validate_package(name, True)
        for name in ("a", "A1", "A-B", "А"):
            with self.subTest(name=name):
                with self.assertRaises(ConfigError):
                    validate_package(name, True)

    def test_cli_demonstrations(self):
        cases = {
            "A": "A -> B, C\nB -> D\nC -> D\nD ->\n",
            "E": "E -> F\nF -> E\n",
            "G": "G -> G\n",
            "H": "H -> I\nI -> J\nJ ->\n",
            "K": "K ->\n",
        }
        config = configparser.ConfigParser()
        config.read(FIXTURES / "config.ini")
        config["settings"]["repository"] = str(FIXTURES / "graph.json")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.ini"
            for package, expected in cases.items():
                with self.subTest(package=package):
                    config["settings"]["package"] = package
                    with path.open("w", encoding="utf-8") as target:
                        config.write(target)
                    result = subprocess.run(
                        [sys.executable, "-m", "src.main", str(path)],
                        cwd=PROJECT_ROOT, capture_output=True,
                        text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, expected)
                    self.assertEqual(result.stderr, "")

    def test_apt_transitive_dependencies_root_version_and_cycle(self):
        text = (
            "Package: app\nVersion: 1.0\nDepends: obsolete\n\n"
            "Package: app\nVersion: 2.0\n"
            "Depends: lib-a (>= 1.0), lib-b:any | lib-c\n\n"
            "Package: lib-a\nVersion: 1.0\nPre-Depends: common\n\n"
            "Package: lib-b\nVersion: 1.0\nDepends: common\n\n"
            "Package: lib-c\nVersion: 1.0\n\n"
            "Package: common\nVersion: 1.0\nDepends: app\n"
        )
        graph = build_graph("app", apt_dependency_reader(text, "app", "2.0"))
        self.assertEqual(graph, {
            "app": ["lib-a", "lib-b", "lib-c"],
            "lib-a": ["common"], "lib-b": ["common"],
            "lib-c": [], "common": ["app"],
        })
        self.assertEqual(
            list(graph), ["app", "lib-a", "lib-b", "lib-c", "common"]
        )
        with self.assertRaisesRegex(RepositoryError, "версии 9.0"):
            apt_dependency_reader(text, "app", "9.0")

    def test_virtual_package(self):
        text = (
            "Package: app\nVersion: 1.0\nDepends: virtual\n\n"
            "Package: implementation\nVersion: 1.0\nProvides: virtual (= 1.0)\n"
        )
        graph = build_graph("app", apt_dependency_reader(text, "app", "1.0"))
        self.assertEqual(graph, {
            "app": ["virtual"], "virtual": ["implementation"],
            "implementation": [],
        })

    def test_missing_transitive_package_reports_error(self):
        text = "Package: app\nVersion: 1.0\nDepends: missing\n"
        with self.assertRaisesRegex(RepositoryError, "missing отсутствует"):
            build_graph("app", apt_dependency_reader(text, "app", "1.0"))

    def test_real_repository_cli_path(self):
        text = (
            "Package: app\nVersion: 1.0\nDepends: lib-a\n\n"
            "Package: lib-a\nVersion: 1.0\n"
        )
        config = {
            "package": "app", "version": "1.0",
            "test_mode": False, "ascii_tree": False,
        }
        output = StringIO()
        with patch("sys.argv", ["main"]), patch(
            "src.cli.load_config", return_value=config
        ), patch("src.cli.load_repository", return_value=text):
            with redirect_stdout(output):
                self.assertEqual(main(), 0)
        self.assertEqual(output.getvalue(), "app -> lib-a\nlib-a ->\n")

    def test_missing_root_version_cli_error(self):
        config = {"package": "app", "version": "9.0", "test_mode": False}
        error = StringIO()
        with patch("sys.argv", ["main"]), patch(
            "src.cli.load_config", return_value=config
        ), patch(
            "src.cli.load_repository",
            return_value="Package: app\nVersion: 1.0\n",
        ):
            with redirect_stderr(error):
                self.assertEqual(main(), 1)
        self.assertIn("версии 9.0 не найден", error.getvalue())


if __name__ == "__main__":
    unittest.main()
