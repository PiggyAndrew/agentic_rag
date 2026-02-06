import ast
import os
import unittest


def _iter_py_files(root: str):
    for base, _dirs, files in os.walk(root):
        for fn in files:
            if fn.endswith(".py"):
                yield os.path.join(base, fn)


def _imports_of(path: str):
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module


class TestArchitectureDependencies(unittest.TestCase):
    def test_application_must_not_import_infrastructure(self):
        contexts = ["kb", "providers", "agents", "docx", "config"]
        bad = []
        for ctx in contexts:
            root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "backend", "modules", ctx, "application")
            )
            if not os.path.isdir(root):
                continue
            for path in _iter_py_files(root):
                for mod in _imports_of(path):
                    if mod.startswith(f"backend.modules.{ctx}.infrastructure"):
                        bad.append((path, mod))
        self.assertEqual(bad, [])

    def test_domain_must_not_import_application_or_infrastructure(self):
        contexts = ["kb", "providers", "agents", "docx", "config"]
        bad = []
        for ctx in contexts:
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "modules", ctx, "domain"))
            if not os.path.isdir(root):
                continue
            for path in _iter_py_files(root):
                for mod in _imports_of(path):
                    if mod.startswith(f"backend.modules.{ctx}.application") or mod.startswith(f"backend.modules.{ctx}.infrastructure"):
                        bad.append((path, mod))
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
