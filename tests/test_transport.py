"""Pinned-library adapter contract tests without network or Apple hardware."""
import asyncio
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from transport import open_tunnel


class WifiTransportTests(unittest.TestCase):
    def exercise(self, services=True, wrong_device=False):
        calls = []
        userspace = types.ModuleType("pymobiledevice3.remote.userspace_tunnel")
        tunnel_service = types.ModuleType("pymobiledevice3.remote.tunnel_service")
        package = types.ModuleType("pymobiledevice3")
        package.__path__ = []
        remote = types.ModuleType("pymobiledevice3.remote")
        remote.__path__ = []
        package.remote = remote
        remote.userspace_tunnel = userspace
        async def original(*args):
            calls.append("USB")
            raise AssertionError("Wi-Fi must not open USB")
        userspace._create_no_root_tunnel_provider = original
        class Provider:
            async def close(self):
                calls.append("extra-closed")
        async def discover(**kwargs):
            calls.append(kwargs)
            return [Provider(), Provider()] if services else []
        tunnel_service.get_remote_pairing_tunnel_services = discover
        class Handle:
            def __init__(self, serial, autopair, remotepairing_fallback):
                self.serial = serial
            async def aopen(self):
                await userspace._create_no_root_tunnel_provider(self.serial, False, False)
                return types.SimpleNamespace(udid="other-phone" if wrong_device else "selected-phone")
            async def aclose(self):
                calls.append("closed")
        userspace.UserspaceRsdTunnel = Handle
        modules = {"pymobiledevice3": package, "pymobiledevice3.remote": remote,
                   userspace.__name__: userspace, tunnel_service.__name__: tunnel_service}
        async def run():
            async with open_tunnel("selected-phone", "wifi") as rsd:
                self.assertEqual(rsd.udid, "selected-phone")
                self.assertIs(userspace._create_no_root_tunnel_provider, original)
        with patch.dict(sys.modules, modules):
            try:
                asyncio.run(run())
            finally:
                self.assertIs(userspace._create_no_root_tunnel_provider, original)
                self.assertIn("closed", calls)
                self.assertNotIn("USB", calls)
        return calls

    def test_explicit_wifi_discovers_only_selected_phone_and_closes_extras(self):
        calls = self.exercise()
        self.assertEqual(calls[0], {"udid": "selected-phone", "bonjour_timeout": 5})
        self.assertIn("extra-closed", calls)

    def test_missing_wifi_never_falls_back_to_usb(self):
        with self.assertRaisesRegex(RuntimeError, "WLAN nicht gefunden"):
            self.exercise(services=False)

    def test_wrong_rsd_identifier_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Gerätekennung"):
            self.exercise(wrong_device=True)


if __name__ == "__main__":
    unittest.main()
