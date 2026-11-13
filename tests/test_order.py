import configparser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.errors import RepositoryError
from src.graph import build_graph
from src.order import get_load_order


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class OrderTests(unittest.TestCase):
    def run_cli(self, package, mode="true"):
        config = configparser.ConfigParser()
        config.read(FIXTURES / "config.ini")
        config["settings"].update(
            package=package,
            repository=str(FIXTURES / "graph.json"),
            load_order=mode,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.ini"
            with path.open("w", encoding="utf-8") as target:
                config.write(target)
            return subprocess.run(
                [sys.executable, "-m", "src.main", str(path)],
                cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=10,
            )

    def test_dependency_order(self):
        repository = json.loads((FIXTURES / "graph.json").read_text())
        cases = {"A": ["D", "B", "C", "A"], "H": ["J", "I", "H"], "K": ["K"]}
        for package, expected in cases.items():
            with self.subTest(package=package):
                graph = build_graph(package, repository.__getitem__)
                order = get_load_order(graph)
                self.assertEqual(order, expected)
                for name, dependencies in graph.items():
                    for dependency in dependencies:
                        self.assertLess(
                            order.index(dependency), order.index(name)
                        )
        for package in ("E", "G"):
            with self.subTest(package=package):
                with self.assertRaisesRegex(RepositoryError, "цикл"):
                    get_load_order(build_graph(package, repository.__getitem__))

    def test_load_order_cli(self):
        cases = {
            "A": "D -> B -> C -> A\n", "H": "J -> I -> H\n", "K": "K\n",
            "E": None, "G": None,
        }
        for package, expected in cases.items():
            with self.subTest(package=package):
                result = self.run_cli(package)
                if expected is None:
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("цикл", result.stderr)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, expected)
                    self.assertEqual(result.stderr, "")
        result = self.run_cli("A", "false")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "A -> B, C\nB -> D\nC -> D\nD ->\n")

    def test_invalid_load_order(self):
        for mode in ("maybe", ""):
            with self.subTest(mode=mode):
                result = self.run_cli("A", mode)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn("load_order", result.stderr)


if __name__ == "__main__":
    unittest.main()
