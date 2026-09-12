import inspect
import json
import subprocess
import sys
import tempfile
import turtle
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_template import generate_catalog

ROOT = Path(__file__).resolve().parents[1]


class TemplateTests(unittest.TestCase):
    def test_covers_every_public_method_once(self):
        catalog = generate_catalog()
        for cls, public_names in (
            ("Turtle", turtle._tg_turtle_functions),
            ("_Screen", turtle._tg_screen_functions),
        ):
            owner = getattr(turtle, cls)
            expected = {getattr(owner, name) for name in public_names}
            actual = {getattr(owner, name) for name in catalog[cls]}
            self.assertEqual(actual, expected)
            self.assertEqual(len(catalog[cls]), len(expected))
            for name, entry in catalog[cls].items():
                self.assertEqual(
                    entry, {"string": inspect.getdoc(getattr(owner, name)) + "\n"}
                )
        self.assertIsNone(turtle.Turtle._screen)

    def test_keys_match_existing_translations(self):
        polish = json.loads(
            (ROOT / "translations/pl/docstrings.json").read_text(encoding="utf-8")
        )
        english = generate_catalog()
        for cls, entries in polish.items():
            self.assertLessEqual(set(entries), set(english[cls]))

    def test_cli_is_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "en/docstrings.json"
            command = [
                sys.executable,
                "-I",
                str(ROOT / "scripts/generate_template.py"),
                str(output),
            ]
            subprocess.run(command, cwd=directory, check=True, capture_output=True)
            first = output.read_bytes()
            subprocess.run(command, cwd=directory, check=True, capture_output=True)
            self.assertEqual(output.read_bytes(), first)
            self.assertEqual(json.loads(first), generate_catalog())

    def test_rejects_localized_docstrings(self):
        with patch.dict(turtle._CFG, language="pl"):
            with self.assertRaisesRegex(RuntimeError, "language override"):
                generate_catalog()


if __name__ == "__main__":
    unittest.main()
