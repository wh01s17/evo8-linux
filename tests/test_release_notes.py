import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("release_notes", ROOT / "tools" / "release_notes.py")
release_notes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_notes)

SAMPLE = """# Cambios

## [Sin publicar]

## [0.2.0] - 2027-01-10

### Añadido

- Algo nuevo.

## [0.1.0] - 2026-11-21

- Primera.

[Sin publicar]: https://example.com/compare/v0.2.0...HEAD
[0.2.0]: https://example.com/releases/tag/v0.2.0
"""


class ReleaseNotes(unittest.TestCase):
    def test_middle_and_last_sections(self):
        self.assertEqual(release_notes.section(SAMPLE, "0.2.0"), "### Añadido\n\n- Algo nuevo.")
        self.assertEqual(release_notes.section(SAMPLE, "0.1.0"), "- Primera.")

    def test_missing_or_empty(self):
        self.assertEqual(release_notes.section(SAMPLE, "9.9.9"), "")
        self.assertEqual(release_notes.section(SAMPLE, "Sin publicar"), "")
        self.assertEqual(release_notes.main(["9.9.9", str(ROOT / "CHANGELOG.md")]), 1)

    def test_the_real_changelog_has_the_current_version(self):
        import evo8
        notes = release_notes.section((ROOT / "CHANGELOG.md").read_text(), evo8.__version__)
        self.assertTrue(notes, f"CHANGELOG.md no tiene la sección de {evo8.__version__}")


if __name__ == "__main__":
    unittest.main()
