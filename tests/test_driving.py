"""Road-speed, timing and lifecycle tests with synthetic roads, no device."""
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
from driving import ACCELERATION, BRAKING, DrivingProfile, build_driving_profile
from engine import Controller, Maps, Route


def road_data(route, speeds):
    lengths = [b - a for a, b in zip(route.lengths, route.lengths[1:])]
    return [{"annotation": {"distance": lengths, "duration": [d / (v / 3.6) if d else 0 for d, v in zip(lengths, speeds)],
                            "speed": [v / 3.6 for v in speeds]}}]


class DrivingTests(unittest.TestCase):
    def setUp(self):
        self.route = Route([[0, 0], [0, .02], [0, .2], [0, .22]])
        self.profile = build_driving_profile(self.route, road_data(self.route, [30, 120, 50]))

    def test_city_then_motorway_then_city_respects_each_road_speed(self):
        for d, v in zip(self.profile.distances, self.profile.speeds):
            cap = 30 if d <= self.route.lengths[1] else 120 if d < self.route.lengths[2] else 50
            self.assertLessEqual(v * 3.6, cap + 1e-6)
        self.assertGreater(max(v * 3.6 for d, v in zip(self.profile.distances, self.profile.speeds)
                               if 6000 < d < 15000), 110)
        self.assertLess(self.profile.duration, self.route.total / (40 / 3.6))

    def test_brakes_before_lower_limit_and_accelerates_after_higher_limit(self):
        for i in range(1, len(self.profile.distances)):
            d = self.profile.distances[i] - self.profile.distances[i - 1]
            acceleration = (self.profile.speeds[i] ** 2 - self.profile.speeds[i - 1] ** 2) / (2 * d)
            self.assertLessEqual(acceleration, ACCELERATION + 1e-7)
            self.assertGreaterEqual(acceleration, -BRAKING - 1e-7)
        boundary = self.route.lengths[2]
        approaching = [(d, v * 3.6) for d, v in zip(self.profile.distances, self.profile.speeds) if boundary - 80 < d < boundary]
        self.assertLess(approaching[-1][1], 60)

    def test_tight_corner_slows_down_but_straights_remain_fast(self):
        route = Route([[0, 0], [0, .02], [.02, .02]])
        p = build_driving_profile(route, road_data(route, [100, 100]))
        corner = p.distances.index(route.lengths[1])
        self.assertLess(p.speeds[corner] * 3.6, 20)
        self.assertGreater(max(p.speeds) * 3.6, 90)

    def test_arrival_time_matches_positions_and_stops_at_end(self):
        self.assertEqual(self.profile.at(0), (0, 0))
        self.assertEqual(self.profile.at(self.profile.duration), (self.route.total, 0))
        last = -1
        for i in range(1001):
            d, v = self.profile.at(self.profile.duration * i / 1000)
            self.assertGreaterEqual(d, last)
            self.assertGreaterEqual(v, 0)
            last = d
        self.assertEqual(self.profile.travel(self.profile.duration + 100), (self.route.total, self.route.total, 0, 0))
        d, v = self.profile.at(.5)
        self.assertAlmostEqual(d, .5 * ACCELERATION * .5 ** 2, places=6)
        self.assertAlmostEqual(v, ACCELERATION * .5, places=6)

    def test_repeat_turns_at_endpoint_without_teleporting(self):
        t = self.profile.duration
        before = self.profile.travel(t - .01, True)
        end = self.profile.travel(t, True)
        after = self.profile.travel(t + .01, True)
        self.assertEqual(end[:3], (self.route.total, self.route.total, 0))
        self.assertAlmostEqual(before[0], after[0], places=3)
        self.assertGreater(after[1], end[1])
        self.assertEqual(self.profile.travel(2 * t, True)[:3], (0, 2 * self.route.total, 0))

    def test_missing_or_misaligned_data_does_not_invent_speeds(self):
        for legs in ([], [{}], road_data(self.route, [30])):
            with self.assertRaises(ValueError):
                build_driving_profile(self.route, legs)

    def test_duplicate_points_and_short_routes_are_valid(self):
        for route in (Route([[0, 0], [0, 0], [0, .01]]), Route([[0, 0], [0, .00002]])):
            p = build_driving_profile(route, road_data(route, [30] * (len(route.points) - 1)))
            self.assertGreater(p.duration, 0)
            self.assertEqual(p.at(p.duration), (route.total, 0))

    def test_corrupt_profile_and_wrong_route_are_rejected(self):
        samples = self.profile.export()
        for bad in (None, [[0, 0], [100, 1]], [[0, 0], [10, float('nan')], [self.route.total, 0]],
                    [[0, 0], [1, 36], [self.route.total, 0]], samples[:-1]):
            with self.assertRaises(ValueError):
                DrivingProfile(self.route, bad)
        with self.assertRaises(ValueError):
            DrivingProfile(Route([[0, 0], [0, 1]]), samples)

    def test_maps_requests_road_annotations_and_returns_matching_time(self):
        maps = Maps(Path(__file__).resolve().parents[1])
        data = {"code": "Ok", "routes": [{"geometry": {"coordinates": [[lon, lat] for lat, lon in self.route.points]},
                                            "legs": road_data(self.route, [30, 120, 50])}]}
        with patch.object(maps, "request", return_value=data) as request:
            result = maps.route([self.route.points[0], self.route.points[-1]], "drive")
        self.assertIn('annotations=duration,distance,speed', request.call_args.args[0])
        self.assertAlmostEqual(result['duration'], self.profile.duration)
        self.assertEqual(result['driving_profile'], self.profile.export())
        data['routes'][0].pop('legs')
        with patch.object(maps, 'request', return_value=data):
            result = maps.route([self.route.points[0], self.route.points[-1]], 'drive')
        self.assertIsNone(result['driving_profile'])
        self.assertIsNone(result['duration'])

    def test_auto_requires_profile_and_rejects_manual_changes_during_trip(self):
        with tempfile.TemporaryDirectory() as root:
            c = Controller(root)
            c._device = {'udid': 'test'}
            c._connected = True
            with self.assertRaises(ValueError):
                c.start({'mode': 'drive', 'points': self.route.points, 'speed_mode': 'auto'})
            with patch.object(c, '_worker'):
                c.start({'mode': 'drive', 'points': self.route.points, 'speed_mode': 'auto', 'driving_profile': self.profile.export()})
                c.thread.join(1)
            self.assertEqual(c.snapshot()['speed_mode'], 'auto')
            self.assertAlmostEqual(c.snapshot()['duration'], self.profile.duration)
            with self.assertRaises(RuntimeError):
                c.speed(160)

    def test_session_uses_profile_and_pause_freezes_its_clock(self):
        with tempfile.TemporaryDirectory() as root:
            c = Controller(root)
            route = self.route
            route.driving_profile = self.profile
            c._speed = 160  # A stale manual setting must not drive the automatic route.
            positions, clears = [], []
            class Context:
                udid = 'test'
                def __init__(self, *args): pass
                async def __aenter__(self): return self
                async def __aexit__(self, *args): pass
            class Location(Context):
                async def set(self, lat, lon):
                    positions.append([lat, lon])
                    if len(positions) == 2: c._paused = True
                    if len(positions) == 3: c._paused = False
                    if len(positions) == 4: c.stop_event.set()
                async def clear(self): clears.append(True)
            @asynccontextmanager
            async def tunnel(*args): yield Context()
            modules = {}
            for name, attribute, value in (
                ('pymobiledevice3.services.dvt.instruments.dvt_provider', 'DvtProvider', Context),
                ('pymobiledevice3.services.dvt.instruments.location_simulation', 'LocationSimulation', Location)):
                module = types.ModuleType(name);setattr(module, attribute, value);modules[name] = module
            ticks = iter([100, 100, 101, 102, 103])
            fake_time = types.SimpleNamespace(monotonic=lambda:next(ticks), time=lambda:1000)
            with patch.dict(sys.modules, modules), patch('transport.open_tunnel', tunnel), patch('engine.time', fake_time):
                asyncio.run(c._session('test', route, 'drive', False))
            self.assertEqual(positions[0], route.points[0])
            self.assertEqual(positions[1], positions[2])
            self.assertAlmostEqual(c.snapshot()['traveled'], self.profile.at(2)[0], places=5)
            self.assertAlmostEqual(c.snapshot()['current_speed'], self.profile.at(2)[1] * 3.6, places=5)
            self.assertEqual(clears, [True])


if __name__ == '__main__':
    unittest.main()
