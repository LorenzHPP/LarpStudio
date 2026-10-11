import base64
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Bridge
from artwork import decode_artwork
from route_library import RouteLibrary, validate_routes


def png_data(width=1536, height=969):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress((b'\0' + b'\0' * width * 3) * height)) + chunk(b'IEND', b'')
    return png, 'data:image/png;base64,' + base64.b64encode(png).decode()


class StudioTests(unittest.TestCase):
    def test_png_export_matches_original_bytes(self):
        raw, url = png_data()
        self.assertEqual(decode_artwork(url), raw)

    def test_wrong_format_size_and_corrupt_base64_are_rejected(self):
        for url in ['data:image/jpeg;base64,AAAA', 'data:image/png;base64,@@@', png_data(100, 100)[1]]:
            with self.assertRaises(ValueError):
                decode_artwork(url)

    def test_native_export_cancel_does_not_write_and_save_is_exact(self):
        from types import SimpleNamespace
        bridge = Bridge(None, None)
        raw, url = png_data()
        dialogs = []
        def dialog(*args, **kwargs):
            dialogs.append(kwargs)
            return None
        bridge._window = SimpleNamespace(create_file_dialog=dialog)
        with patch.dict(sys.modules, {'webview': SimpleNamespace(FileDialog=SimpleNamespace(SAVE=30))}):
            self.assertEqual(bridge.save_artwork(url), {'ok': True, 'data': {'saved': False}})
            with tempfile.TemporaryDirectory() as root:
                path = Path(root) / 'Kartenbild.png'
                bridge._window.create_file_dialog = lambda *a, **k: [str(path)]
                self.assertEqual(bridge.save_artwork(url), {'ok': True, 'data': {'saved': True}})
                self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(dialogs[0]['save_filename'], 'Larp-Studio-Kartenbild.png')

    def test_invalid_export_does_not_open_dialog(self):
        from types import SimpleNamespace
        bridge = Bridge(None, None)
        bridge._window = SimpleNamespace(create_file_dialog=lambda *a, **k: self.fail('Must not open dialog'))
        self.assertFalse(bridge.save_artwork('bad')['ok'])

    def test_routes_survive_restart_and_delete_without_touching_device_data(self):
        routes = [{'name': 'Runde', 'mode': 'drive', 'points': [
            {'title': 'Start', 'point': [47.62, 9.90]}, {'title': 'Ziel', 'point': [47.63, 9.91]}]}]
        with tempfile.TemporaryDirectory() as root:
            device = Path(root) / '.atlas-data.json'; device.write_text('{"favorites":[]}')
            library = RouteLibrary(root)
            self.assertEqual(library.load(), [])
            library.save(routes)
            self.assertEqual(RouteLibrary(root).load(), routes)
            library.save([])
            self.assertEqual(RouteLibrary(root).load(), [])
            self.assertEqual(device.read_text(), '{"favorites":[]}')

    def test_invalid_route_cannot_overwrite_saved_routes(self):
        with tempfile.TemporaryDirectory() as root:
            library = RouteLibrary(root); library.save([])
            for points in [[], [{'title': 'Bad', 'point': [float('nan'), 9]}] * 2,
                           [{'title': 'Bad', 'point': [91, 9]}] * 2,
                           [{'title': 'Bad', 'point': [True, 9]}] * 2]:
                with self.assertRaises(ValueError):
                    library.save([{'name': 'Test', 'mode': 'drive', 'points': points}])
                self.assertEqual(library.load(), [])


if __name__ == '__main__':
    unittest.main()
