"""Offline transport tests. No iPhone is connected or changed by these tests."""
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Controller, DeviceClient, Maps, Route, coordinate, distance
from app import Bridge


class FakeDevice:
    def __init__(self):
        self.info = dict(udid="selected-phone", name="Testgerät", model="iPhone16,2", ios="27.2")
        self.clears = []
        self.fail_clear = False
        self.wifi_prepared = []
        self.wifi_checked = []
        self.wifi_cleared = []
        self.mounts = []

    def inspect(self):
        return self.info.copy()

    def mount(self, udid, cancel=None):
        self.mounts.append(udid)
        if cancel and cancel.is_set():
            raise RuntimeError("Abgebrochen")

    def clear(self, udid):
        self.clears.append(udid)
        if self.fail_clear:
            raise RuntimeError("USB getrennt")

    def prepare_wifi(self, udid, cancel=None):
        self.wifi_prepared.append(udid)

    def check_wifi(self, udid):
        self.wifi_checked.append(udid)

    def clear_wifi(self, udid):
        self.wifi_cleared.append(udid)


class GeometryTests(unittest.TestCase):
    def test_invalid_coordinates(self):
        for point in ([91, 0], [0, -181], [float("nan"), 0], [0], None):
            with self.assertRaises((ValueError, TypeError)):
                coordinate(point)

    def test_distance_and_interpolation_with_duplicates(self):
        route = Route([[0, 0], [0, 0], [0, .01], [0, .01]])
        self.assertAlmostEqual(route.total, 1111.9508, places=3)
        self.assertAlmostEqual(route.at(route.total / 2)[1], .005, places=8)
        self.assertEqual(route.at(-10), [0, 0])
        self.assertEqual(route.at(route.total + 10), [0, .01])

    def test_dateline_takes_short_path(self):
        route = Route([[0, 179.99], [0, -179.99]])
        self.assertLess(route.total, 2300)
        self.assertAlmostEqual(abs(route.at(route.total / 2)[1]), 180)

    def test_stationary_route(self):
        self.assertEqual(Route([[47, 9]]).at(100), [47, 9])


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.device = FakeDevice()
        self.controller = Controller(self.temp.name, self.device)
        self.controller.connect()
        self.controller.thread.join(2)
        self.assertEqual(self.controller.snapshot()["phase"], "ready")

    def tearDown(self):
        self.temp.cleanup()

    def test_snapshot_does_not_expose_serial(self):
        self.assertNotIn("udid", self.controller.snapshot()["device"])

    def test_start_validation_and_pending_reset(self):
        for plan in ({"mode": "fly", "points": [[47, 9]]},
                     {"mode": "pin", "points": [[47, 9], [47, 10]]},
                     {"mode": "walk", "points": [[47, 9], [47, 9]]},
                     {"mode": "pin", "points": [[47, 9]], "speed": float("nan")}):
            with self.assertRaises(ValueError):
                self.controller.start(plan)
        self.controller._needs_clear = True
        with self.assertRaisesRegex(RuntimeError, "resetting"):
            self.controller.start({"mode": "pin", "points": [[47, 9]]})

    def test_pending_reset_keeps_original_phone(self):
        self.controller._needs_clear = True
        self.device.info["udid"] = "other-phone"
        self.controller.connect()
        self.controller.thread.join(2)
        self.assertEqual(self.controller.snapshot()["phase"], "error")
        self.assertEqual(self.controller._device["udid"], "selected-phone")

    def test_failed_reset_stays_pending_then_recovers(self):
        self.controller._needs_clear = True
        self.device.fail_clear = True
        self.controller.recover()
        self.controller.thread.join(2)
        self.assertTrue(self.controller.snapshot()["needs_clear"])
        self.assertEqual(self.controller.snapshot()["phase"], "error")
        self.device.fail_clear = False
        self.controller.recover()
        self.controller.thread.join(2)
        self.assertFalse(self.controller.snapshot()["needs_clear"])
        self.assertEqual(self.device.clears, ["selected-phone", "selected-phone"])

    def test_worker_fallback_clears_original_phone(self):
        async def failed_session(*args):
            self.controller._needs_clear = True
            raise RuntimeError("Verbindung unterbrochen")
        with patch.object(self.controller, "_session", failed_session):
            self.controller.start({"mode": "pin", "points": [[47, 9]]})
            self.controller.thread.join(2)
        self.assertEqual(self.device.clears, ["selected-phone"])
        self.assertFalse(self.controller.snapshot()["needs_clear"])
        self.assertEqual(self.controller.snapshot()["phase"], "error")

    def test_local_favorites_roundtrip(self):
        self.controller.favorite("Mein Punkt", [-33.8, 151.2], "Sydney")
        loaded = Controller(self.temp.name, self.device)
        self.assertEqual(loaded.favorites[0]["point"], [-33.8, 151.2])
        self.assertEqual(loaded.favorites[0]["name"], "Mein Punkt")

    def test_wifi_preparation_persists_and_connect_verifies(self):
        self.controller.prepare_wifi()
        self.controller.thread.join(2)
        state = self.controller.snapshot()
        self.assertTrue(state["wifi_prepared"])
        self.assertEqual(state["connection"], "wifi")
        self.assertEqual(state["phase"], "disconnected")
        self.assertEqual(self.device.wifi_prepared, ["selected-phone"])
        with self.assertRaisesRegex(RuntimeError, "Connect"):
            self.controller.start({"mode": "pin", "points": [[47, 9]]})
        self.controller.favorite("Test", [47, 9])
        loaded = Controller(self.temp.name, self.device)
        self.assertEqual(loaded._wifi_device["udid"], "selected-phone")
        loaded.connection("wifi")
        loaded.connect()
        loaded.thread.join(2)
        self.assertEqual(self.device.wifi_checked, ["selected-phone"])
        self.assertEqual(loaded.snapshot()["phase"], "ready")

    def test_wifi_worker_never_mounts_usb_and_fallback_uses_wifi(self):
        self.controller._wifi_device = self.device.info.copy()
        self.controller.connection("wifi")
        self.controller.connect()
        self.controller.thread.join(2)
        async def failed_session(*args):
            self.controller._needs_clear = True
            raise RuntimeError("WLAN getrennt")
        with patch.object(self.controller, "_session", failed_session):
            self.controller.start({"mode": "pin", "points": [[47, 9]]})
            self.controller.thread.join(2)
        self.assertEqual(self.device.mounts, [])
        self.assertEqual(self.device.clears, [])
        self.assertEqual(self.device.wifi_cleared, ["selected-phone"])

    def test_connection_failure_before_sending_does_not_claim_reset(self):
        async def failed_session(*args):
            raise RuntimeError("WLAN nicht gefunden")
        with patch.object(self.controller, "_session", failed_session):
            self.controller.start({"mode": "pin", "points": [[47, 9]]})
            self.controller.thread.join(2)
        self.assertIn("Connection failed", self.controller.snapshot()["message"])
        self.assertNotIn("Reset command", self.controller.snapshot()["message"])
        self.assertEqual(self.device.clears, [])

    def test_lost_wifi_can_reset_same_phone_via_usb(self):
        self.controller._connection = "wifi"
        self.controller._needs_clear = True
        self.controller.state["phase"] = "error"
        self.controller.connection("usb")
        self.controller.recover()
        self.controller.thread.join(2)
        self.assertEqual(self.device.clears, ["selected-phone"])
        self.assertFalse(self.controller.snapshot()["needs_clear"])

    def test_bridge_reports_errors(self):
        bridge = Bridge(self.controller, None)
        self.assertFalse(bridge.set_speed(999)["ok"])
        self.assertTrue(bridge.set_speed(8)["ok"])

    def test_async_tunnel_keeps_running_while_paused_and_clears(self):
        controller = self.controller
        positions, cleared, heartbeats = [], [], []
        class Context:
            def __init__(self, *args, **kwargs):
                self.udid = kwargs.get("serial", "selected-phone")
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
        class Location(Context):
            async def set(self, lat, lon):
                positions.append([lat, lon])
                if len(positions) == 1:
                    controller._paused = True
                if len(positions) == 3:
                    controller.stop_event.set()
            async def clear(self):
                cleared.append(True)
        names = {
            "pymobiledevice3.remote.userspace_tunnel": ("UserspaceRsdTunnel", Context),
            "pymobiledevice3.services.dvt.instruments.dvt_provider": ("DvtProvider", Context),
            "pymobiledevice3.services.dvt.instruments.location_simulation": ("LocationSimulation", Location),
        }
        modules = {}
        for name, (attribute, value) in names.items():
            module = types.ModuleType(name)
            setattr(module, attribute, value)
            modules[name] = module
        async def exercise():
            async def heartbeat():
                while not controller.stop_event.is_set():
                    heartbeats.append(True)
                    await asyncio.sleep(.01)
            task = asyncio.create_task(heartbeat())
            await controller._session("selected-phone", Route([[47, 9], [47.01, 9]]), "walk", False)
            await task
        @asynccontextmanager
        async def fake_tunnel(udid, connection):
            yield Context(serial=udid)
        with patch.dict(sys.modules, modules), patch("transport.open_tunnel", fake_tunnel):
            asyncio.run(exercise())
        self.assertGreater(len(heartbeats), 100)
        self.assertEqual(len(positions), 3)
        self.assertEqual(positions[1], positions[0])
        self.assertEqual(positions[2], positions[0])
        self.assertEqual(cleared, [True])
        self.assertFalse(controller.snapshot()["needs_clear"])


class DeviceAndMapTests(unittest.TestCase):
    def test_usb_uses_exact_selected_device(self):
        device = DeviceClient(".")
        with patch.object(device, "call", return_value=["other-phone"]):
            with self.assertRaisesRegex(RuntimeError, "selected"):
                device.usb("selected-phone")

    def test_route_uses_foot_or_car_and_validates(self):
        root = Path(__file__).resolve().parents[1]
        maps = Maps(root)
        urls = []
        def request(url):
            urls.append(url)
            return {"code": "Ok", "routes": [{"geometry": {"coordinates": [[9, 47], [9.001, 47.001]]}}]}
        with patch.object(maps, "request", request):
            foot = maps.route([[47, 9], [47.001, 9.001]], "run")
            maps.route([[47, 9], [47.001, 9.001]], "drive")
        self.assertIn("routed-foot", urls[0])
        self.assertIn("routed-car", urls[1])
        self.assertEqual(foot["points"][0], [47, 9])
        self.assertGreater(foot["distance"], 100)
        with self.assertRaises(ValueError):
            maps.route([[47, 9]], "walk")


if __name__ == "__main__":
    unittest.main()
