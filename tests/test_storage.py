"""A standalone update preserves user data without filling the EXE folder."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import data_directory


class StorageTests(unittest.TestCase):
    def test_source_installation_keeps_its_existing_directory(self):
        with tempfile.TemporaryDirectory() as scratch, patch.object(sys, "frozen", False, create=True):
            root = Path(scratch) / "source"
            self.assertEqual(data_directory(root), root)
            self.assertFalse(root.exists())

    def test_exe_settings_survive_moving_the_program(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            with patch.object(sys, "frozen", True, create=True), patch.dict("os.environ", {"LOCALAPPDATA": str(root / "profile")}):
                with patch.object(sys, "executable", str(root / "downloads" / "Larp Studio.exe")):
                    first = data_directory(root / "unpacked-assets")
                    (first / ".atlas-data.json").write_text('{"favorites":[]}')
                with patch.object(sys, "executable", str(root / "desktop" / "Larp Studio.exe")):
                    second = data_directory(root / "different-assets")
                self.assertEqual(first, second)
                self.assertEqual(json.loads((second / ".atlas-data.json").read_text()), {"favorites": []})
                self.assertFalse((root / "downloads").exists())

    def test_old_settings_migrate_once_without_overwriting_current_data(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            previous = root / "old-app"
            previous.mkdir()
            favorites = {"favorites": [{"name": "My place", "point": [52, 13]}]}
            routes = [{"name": "My route", "mode": "walk", "points": [
                {"title": "Start", "point": [52, 13]}, {"title": "End", "point": [52.01, 13.01]}]}]
            (previous / ".atlas-data.json").write_text(json.dumps(favorites))
            (previous / ".larp-routes.json").write_text(json.dumps(routes))
            (previous / "notes.txt").write_text("Unrelated file")
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(previous / "Larp Studio.exe")), patch.dict("os.environ", {"LOCALAPPDATA": str(root / "profile")}):
                target = data_directory(root / "assets")
                self.assertEqual(json.loads((target / ".atlas-data.json").read_text()), favorites)
                self.assertEqual(json.loads((target / ".larp-routes.json").read_text()), routes)
                self.assertFalse((target / "notes.txt").exists())
                (target / ".atlas-data.json").write_text('{"favorites":[]}')
                data_directory(root / "assets")
                self.assertEqual(json.loads((target / ".atlas-data.json").read_text()), {"favorites": []})
            self.assertEqual(json.loads((previous / ".atlas-data.json").read_text()), favorites)

    def test_invalid_old_files_are_not_imported(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            previous = root / "old-app"
            previous.mkdir()
            (previous / ".atlas-data.json").write_text("not JSON")
            (previous / ".larp-routes.json").write_text('[{"mode":"fly"}]')
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(previous / "Larp Studio.exe")), patch.dict("os.environ", {"LOCALAPPDATA": str(root / "profile")}):
                target = data_directory(root / "assets")
                self.assertEqual(list(target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
