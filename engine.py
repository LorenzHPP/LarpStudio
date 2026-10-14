"""Device transport, geographic paths and the thread-safe desktop controller."""
import asyncio
import bisect
from collections import deque
from datetime import datetime
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request

from driving import DrivingProfile, build_driving_profile

DEFAULT_POINT = [52.516275, 13.377704]
MODES = {"pin", "walk", "run", "drive"}
ACTIVE = {"preparing", "running", "paused", "holding", "stopping"}


def coordinate(point):
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise ValueError("A point needs a latitude and longitude.")
    lat, lon = (float(n) for n in point)
    if not math.isfinite(lat) or not -90 <= lat <= 90 or not math.isfinite(lon) or not -180 <= lon <= 180:
        raise ValueError("The coordinates are invalid.")
    return [lat, lon]


def distance(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlat = lat2 - lat1
    dlon = math.radians((b[1] - a[1] + 180) % 360 - 180)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371008.8 * 2 * math.atan2(math.sqrt(max(0, h)), math.sqrt(max(0, 1 - h)))


class Route:
    def __init__(self, points):
        if not isinstance(points, list) or not 1 <= len(points) <= 50000:
            raise ValueError("Use between 1 and 50,000 route points.")
        self.points = [coordinate(p) for p in points]
        self.lengths = [0.0]
        for a, b in zip(self.points, self.points[1:]):
            self.lengths.append(self.lengths[-1] + distance(a, b))
        self.total = self.lengths[-1]

    def at(self, meters):
        if self.total <= 0 or meters <= 0:
            return self.points[0][:]
        if meters >= self.total:
            return self.points[-1][:]
        i = bisect.bisect_right(self.lengths, meters) - 1
        a, b = self.points[i], self.points[i + 1]
        f = (meters - self.lengths[i]) / (self.lengths[i + 1] - self.lengths[i])
        lon = (a[1] + ((b[1] - a[1] + 180) % 360 - 180) * f + 180) % 360 - 180
        return [a[0] + (b[0] - a[0]) * f, lon]


def clean_environment():
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYMOBILEDEVICE3_") and k != "USBMUXD_SOCKET_ADDRESS"}
    env.update(NO_COLOR="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return env


class DeviceClient:
    def __init__(self, root):
        self.root = Path(root)

    def call(self, args, capture=False, timeout=90, cancel=None):
        # File IPC also works with a frozen, windowed Windows executable.
        with tempfile.TemporaryDirectory(prefix="atlas-device-") as directory:
            output = Path(directory) / "response.json"
            prefix = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, str(self.root / "app.py")]
            process = subprocess.Popen(
                [*prefix, "--device-cli", str(output), *args], env=clean_environment(),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            began = time.monotonic()
            try:
                while True:
                    if cancel is not None and cancel.is_set():
                        raise RuntimeError("Preparation cancelled.")
                    if timeout is not None and time.monotonic() - began > timeout:
                        raise RuntimeError("The device connection timed out.")
                    try:
                        stdout, stderr = process.communicate(timeout=.25)
                        break
                    except subprocess.TimeoutExpired:
                        pass
            except BaseException:
                process.terminate()
                try:
                    process.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                raise
            if not output.is_file():
                raise RuntimeError("The device connection failed. " + stderr[-1000:])
            reply = json.loads(output.read_text(encoding="utf-8"))
        if reply["code"]:
            detail = (reply["stderr"] or reply["stdout"]).strip()
            if "usbmuxd socket" in detail:
                raise RuntimeError("Apple connection service unavailable. Check iTunes/Apple Devices and the Apple Mobile Device Service.")
            raise RuntimeError(detail[-1400:] or "The device command failed.")
        if capture:
            try:
                return json.loads(reply["stdout"])
            except json.JSONDecodeError as exc:
                raise RuntimeError("The iPhone returned an unexpected response.") from exc

    def usb(self, udid=None):
        ids = self.call(["usbmux", "list", "--usb", "--simple"], capture=True)
        if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
            raise RuntimeError("Invalid USB device list.")
        if udid is not None and udid not in ids:
            raise RuntimeError("Your selected iPhone is not connected by USB.")
        return ids

    def inspect(self):
        ids = self.usb()
        if len(ids) != 1:
            raise RuntimeError("Connect exactly one iPhone by USB, unlock it and trust this PC.")
        udid = ids[0]
        info = self.call(["lockdown", "info", "--udid", udid], capture=True)
        if not isinstance(info, dict) or info.get("DeviceClass") != "iPhone" or info.get("UniqueDeviceID") != udid:
            raise RuntimeError("The device identifier does not match the connected iPhone.")
        version = str(info.get("ProductVersion", ""))
        parts = tuple(int(p) for p in version.split(".")[:2])
        if parts < (17, 4):
            raise RuntimeError("This app uses the USB developer interface for iOS 17.4 or later.")
        self.usb(udid)
        if self.call(["mounter", "query-developer-mode-status", "--udid", udid], capture=True) is not True:
            try:
                self.call(["amfi", "reveal-developer-mode", "--udid", udid])
            except RuntimeError:
                pass
            raise RuntimeError("On your iPhone: Settings → Privacy & Security → enable Developer Mode. Confirm the restart, then connect again.")
        return {"udid": udid, "name": info.get("DeviceName") or "Mein iPhone", "model": info.get("ProductType"), "ios": version}

    def mount(self, udid, cancel=None):
        self.usb(udid)
        self.call(["mounter", "auto-mount", "--udid", udid, "--userspace"], timeout=None, cancel=cancel)
        self.usb(udid)

    def clear(self, udid):
        self.usb(udid)
        self.call(["developer", "dvt", "simulate-location", "clear", "--udid", udid, "--userspace"], timeout=45)

    def prepare_wifi(self, udid, cancel=None):
        self.mount(udid, cancel=cancel)
        self.usb(udid)
        self.call(["lockdown", "wifi-connections", "on", "--udid", udid], cancel=cancel)
        self.call(["lockdown", "remotepairing", "--pair", "--udid", udid], cancel=cancel)
        self.usb(udid)

    def check_wifi(self, udid):
        from transport import probe_wifi
        asyncio.run(probe_wifi(udid))

    def clear_wifi(self, udid):
        from transport import clear_wifi
        asyncio.run(clear_wifi(udid))


class Maps:
    def __init__(self, root):
        self.settings = json.loads((Path(root) / "services.json").read_text(encoding="utf-8"))
        self._lock = threading.Lock()
        self._last_request = 0.0
        self._cache = {}

    def request(self, url):
        with self._lock:
            if url in self._cache:
                return self._cache[url]
            time.sleep(max(0, 1.05 - (time.monotonic() - self._last_request)))
            self._last_request = time.monotonic()
            request = urllib.request.Request(url, headers={"User-Agent": "LarpStudio/1.3 (personal desktop map)", "Accept": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=25) as response:
                    data = response.read(8 * 1024 * 1024 + 1)
                if len(data) > 8 * 1024 * 1024:
                    raise ValueError("This route is too large. Choose a shorter route.")
                reply = json.loads(data)
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError("Map service unavailable. Check your internet connection or try again later.") from exc
            if len(self._cache) >= 50:
                self._cache.pop(next(iter(self._cache)))
            self._cache[url] = reply
            return reply

    def search(self, query):
        query = str(query).strip()
        if not 3 <= len(query) <= 160:
            raise ValueError("Enter a place name with at least three characters.")
        # Manual searches only: no search-as-you-type, polling or bulk queries.
        data = self.request(self.settings["geocoder"] + "?" + urllib.parse.urlencode({"q": query, "limit": 6, "lang": "en"}))
        results = []
        for item in data.get("features", [])[:6]:
            lon, lat = item["geometry"]["coordinates"]
            props = item["properties"]
            title = props.get("name") or props.get("street") or query
            detail = ", ".join(str(props[k]) for k in ("housenumber", "postcode", "city", "country") if props.get(k))
            results.append({"point": coordinate([lat, lon]), "title": title, "detail": detail})
        return results

    def route(self, points, mode):
        if mode not in ("walk", "run", "drive"):
            raise ValueError("Choose walking, running or driving.")
        if not isinstance(points, list) or not 2 <= len(points) <= 12:
            raise ValueError("Choose between two and twelve route points.")
        points = [coordinate(p) for p in points]
        path = ";".join(f"{lon:.7f},{lat:.7f}" for lat, lon in points)
        options = "?overview=full&geometries=geojson&steps=false"
        if mode == "drive":
            options += "&annotations=duration,distance,speed"
        url = self.settings["driving" if mode == "drive" else "walking"] + path + options
        reply = self.request(url)
        if reply.get("code") != "Ok" or not reply.get("routes"):
            raise RuntimeError("No suitable route was found. Move your points closer to paths or roads.")
        result = reply["routes"][0]
        points = [[lat, lon] for lon, lat in result["geometry"]["coordinates"]]
        route = Route(points)
        data = {"points": route.points, "distance": route.total, "source": "FOSSGIS / OpenStreetMap"}
        if mode == "drive":
            try:
                profile = build_driving_profile(route, result.get("legs", []))
                data.update(driving_profile=profile.export(), duration=profile.duration,
                            driving_note="Road-aware speed · includes corners, acceleration and braking.")
            except (ValueError, TypeError, KeyError, OverflowError) as exc:
                data.update(driving_profile=None, duration=None,
                            driving_note=str(exc) + " Plan the route again or choose fixed speed.")
        return data


class Controller:
    def __init__(self, root, device_client=None):
        self.root = Path(root)
        self.device = device_client or DeviceClient(root)
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = None
        self._device = None
        self._wifi_device = None
        self._connected = False
        self._connection = "usb"
        self._needs_clear = False
        self._sent_attempted = False
        self._busy = False
        self._paused = False
        self._speed = 4.8
        self._logs = deque(maxlen=50)
        self.state = {"phase": "disconnected", "message": "Connect your iPhone by USB.", "device": None,
                      "position": None, "progress": 0, "distance": 0, "traveled": 0,
                      "elapsed": 0, "last_sent": None, "sent_count": 0, "mode": "pin", "speed": 4.8,
                      "connection": "usb", "wifi_prepared": False,
                      "speed_mode": "fixed", "current_speed": 0, "duration": 0, "remaining": 0}
        self.data_file = self.root / ".atlas-data.json"
        self.favorites = [{"name": "Brandenburg Gate", "detail": "Pariser Platz · Berlin", "point": DEFAULT_POINT}]
        if self.data_file.is_file():
            try:
                data = json.loads(self.data_file.read_text(encoding="utf-8"))
                self.favorites = [{"name": str(x["name"])[:60], "detail": str(x.get("detail", ""))[:100], "point": coordinate(x["point"])} for x in data["favorites"][:20]]
                wifi = data.get("wifi_device")
                if isinstance(wifi, dict) and all(isinstance(wifi.get(k), str) and wifi[k] for k in ("udid", "name", "model", "ios")):
                    self._wifi_device = {k: wifi[k] for k in ("udid", "name", "model", "ios")}
                    self.state["wifi_prepared"] = True
            except (OSError, ValueError, KeyError, TypeError):
                pass

    def log(self, message, kind="info"):
        with self.lock:
            self._logs.append({"time": datetime.now().strftime("%H:%M:%S"), "message": str(message), "kind": kind})

    def snapshot(self):
        with self.lock:
            return {**json.loads(json.dumps(self.state)), "logs": list(self._logs),
                    "favorites": self.favorites[:], "needs_clear": self._needs_clear,
                    "busy": self._busy, "speed": self._speed}

    def _begin_job(self, phase, message, target):
        with self.lock:
            if self._busy or self.state["phase"] in ACTIVE:
                raise RuntimeError("Stop your current session first.")
            self._busy = True
            self.state.update(phase=phase, message=message)
        def run():
            try:
                target()
            except Exception as exc:
                with self.lock:
                    self._connected = False
                    self.state.update(phase="error", message=str(exc))
                self.log(str(exc), "error")
            finally:
                with self.lock:
                    self._busy = False
        self.thread = threading.Thread(target=run, name="atlas-device-job", daemon=True)
        self.thread.start()

    def connect(self):
        def inspect():
            if self._connection == "wifi":
                with self.lock:
                    info = (self._device if self._needs_clear else self._wifi_device)
                    info = info.copy() if info else None
                if not info:
                    raise RuntimeError("Prepare Wi-Fi with the USB cable connected first.")
                self.device.check_wifi(info["udid"])
            else:
                info = self.device.inspect()
            with self.lock:
                if self._needs_clear and self._device and info["udid"] != self._device["udid"]:
                    raise RuntimeError("Connect the previously used iPhone to reset its location.")
                self._device = info
                self._connected = True
                visible = {k: v for k, v in info.items() if k != "udid"}
                message = "Wi-Fi connection verified. You can unplug USB; keep the PC and iPhone on the same network." if self._connection == "wifi" else "iPhone ready. Choose a point or a route."
                self.state.update(device=visible, phase="ready", message=message)
            self.log(f"{info['name']} via {'Wi-Fi' if self._connection == 'wifi' else 'USB'} connected · iOS {info['ios']}")
        self._begin_job("connecting", "Checking the iPhone connection. Please unlock it.", inspect)

    def connection(self, value):
        if value not in {"usb", "wifi"}:
            raise ValueError("Choose USB or Wi-Fi.")
        with self.lock:
            if self._busy or self.state["phase"] in ACTIVE:
                raise RuntimeError("Stop the session first.")
            self._connection = value
            self._connected = False
            self.state.update(connection=value, phase="disconnected", message="Select Wi-Fi, then choose Connect to check it." if value == "wifi" else "Connect your iPhone by USB and choose Connect.")

    def prepare_wifi(self):
        with self.lock:
            if self._needs_clear:
                raise RuntimeError("Finish resetting the location first.")
        def prepare():
            self.stop_event.clear()
            info = self.device.inspect()
            self.device.prepare_wifi(info["udid"], cancel=self.stop_event)
            with self.lock:
                self._wifi_device = info
                self._device = info
                self._connected = False
                self._connection = "wifi"
                self.state.update(wifi_prepared=True, connection="wifi", device={k: v for k, v in info.items() if k != "udid"},
                                  phase="disconnected", message="Wi-Fi prepared. Choose Connect now. Unplug USB only after the Wi-Fi check succeeds.")
                self._save_data()
            self.log("Wi-Fi prepared using your trusted USB iPhone. Check the Wi-Fi connection next.")
        self._begin_job("connecting", "Preparing Wi-Fi over USB. Keep the cable connected …", prepare)

    def start(self, plan):
        if not isinstance(plan, dict) or plan.get("mode") not in MODES:
            raise ValueError("Choose a movement mode.")
        route = Route(plan.get("points"))
        mode = plan["mode"]
        if mode == "pin" and len(route.points) != 1:
            raise ValueError("Use exactly one point for a fixed location.")
        if mode != "pin" and (len(route.points) < 2 or route.total < 1):
            raise ValueError("The route needs at least two different points.")
        speed = float(plan.get("speed", 4.8))
        if not math.isfinite(speed) or not .5 <= speed <= 160:
            raise ValueError("Speed must be between 0.5 and 160 km/h.")
        speed_mode = plan.get("speed_mode", "fixed")
        if speed_mode not in {"auto", "fixed"} or (speed_mode == "auto" and mode != "drive"):
            raise ValueError("Road-aware speed is only available for driving.")
        route.driving_profile = DrivingProfile(route, plan.get("driving_profile")) if speed_mode == "auto" else None
        estimated = route.driving_profile.duration if route.driving_profile else route.total / (speed / 3.6)
        loop = plan.get("loop") is True
        with self.lock:
            if not self._device or not self._connected:
                raise RuntimeError("Connect your iPhone first.")
            if self._needs_clear:
                raise RuntimeError("Finish resetting the location first.")
            if self._busy or self.state["phase"] in ACTIVE:
                raise RuntimeError("A session is already running.")
            self._busy = True
            self.stop_event.clear()
            self._paused = False
            self._sent_attempted = False
            self._speed = speed
            udid = self._device["udid"]
            self.state.update(phase="preparing", message="Preparing the developer interface. First-time setup may take a few minutes.",
                              mode=mode, progress=0, position=None, traveled=0, distance=route.total,
                              elapsed=0, last_sent=None, sent_count=0, speed_mode=speed_mode,
                              current_speed=0, duration=estimated, remaining=estimated)
        self.thread = threading.Thread(target=self._worker, args=(udid, route, mode, loop), name="atlas-location", daemon=True)
        self.thread.start()

    def _worker(self, udid, route, mode, loop):
        failure = None
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        try:
            if self._connection == "usb":
                self.device.mount(udid, cancel=self.stop_event)
            if not self.stop_event.is_set():
                asyncio.run(self._session(udid, route, mode, loop))
        except Exception as exc:
            if not self.stop_event.is_set():
                failure = str(exc)
                self.log(failure, "error")
        finally:
            with self.lock:
                needs_clear = self._needs_clear
            if needs_clear:
                try:
                    self.log("Retrying reset over a new connection …")
                    if self._connection == "wifi":
                        self.device.clear_wifi(udid)
                    else:
                        self.device.clear(udid)
                    with self.lock:
                        self._needs_clear = False
                except Exception as exc:
                    self.log("Reset not confirmed: " + str(exc), "error")
            with self.lock:
                self._busy = False
                self.state["current_speed"] = 0
                if self._needs_clear:
                    self.state.update(phase="error", message="Reset not confirmed. Connect your iPhone and try Reset again; restart the iPhone if needed.")
                elif failure:
                    self._connected = False
                    message = "Session interrupted: " + failure + " Reset command sent; check your real location in Apple Maps." if self._sent_attempted else "Connection failed: " + failure
                    self.state.update(phase="error", message=message)
                else:
                    self.state.update(phase="ready", message="Session stopped. Check your real location in Apple Maps.")
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

    async def _session(self, udid, route, mode, loop):
        from transport import open_tunnel
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
        async with open_tunnel(udid, self._connection) as rsd:
            if rsd.udid != udid:
                raise RuntimeError("The session device identifier does not match.")
            async with DvtProvider(rsd) as dvt, LocationSimulation(dvt) as location:
                began = last = time.monotonic()
                traveled = drive_elapsed = 0.0
                profile = getattr(route, "driving_profile", None)
                try:
                    while not self.stop_event.is_set():
                        now = time.monotonic()
                        delta = min(3, max(0, now - last))
                        last = now
                        with self.lock:
                            paused, speed = self._paused, self._speed
                            self._needs_clear = True  # An attempted send may apply even if its response fails.
                            self._sent_attempted = True
                        if profile:
                            if not paused:
                                drive_elapsed += delta
                            progress, traveled, velocity, remaining = profile.travel(drive_elapsed, loop)
                        else:
                            if mode != "pin" and not paused:
                                traveled += speed / 3.6 * delta
                            if loop and route.total > 0:
                                cycle = traveled % (2 * route.total)
                                progress = cycle if cycle <= route.total else 2 * route.total - cycle
                                remaining = (route.total - cycle if cycle <= route.total else 2 * route.total - cycle) / (speed / 3.6)
                            else:
                                progress = min(traveled, route.total)
                                remaining = (route.total - progress) / (speed / 3.6)
                            velocity = speed / 3.6 if mode != "pin" and (loop or progress < route.total) else 0
                        if paused:
                            velocity = 0
                        point = route.at(progress)
                        await asyncio.wait_for(location.set(*point), timeout=15)
                        with self.lock:
                            phase = "paused" if paused else "holding" if mode == "pin" or (not loop and progress >= route.total) else "running"
                            message = "Paused · holding your current position." if paused else "Holding destination" if phase == "holding" else "Following route"
                            self.state.update(phase=phase, message=message, position=point,
                                              progress=progress / route.total if route.total else 0,
                                              traveled=traveled, elapsed=now - began, last_sent=time.time(),
                                              current_speed=velocity * 3.6, remaining=remaining)
                            self.state["sent_count"] += 1
                        if self.state["sent_count"] == 1:
                            self.log("First location command sent. Check the position in Apple Maps.")
                        # Never wait synchronously on UI input. The tunnel stays scheduled.
                        for _ in range(10):
                            if self.stop_event.is_set():
                                break
                            await asyncio.sleep(.1)
                finally:
                    with self.lock:
                        self.state.update(phase="stopping", message="Stopping the simulation …")
                    try:
                        await asyncio.wait_for(location.clear(), timeout=10)
                        with self.lock:
                            self._needs_clear = False
                        self.log("Reset command sent in the current session. Check your real location in Apple Maps.")
                    except Exception as exc:
                        self.log("Reset in the session failed: " + str(exc), "error")

    def pause(self):
        with self.lock:
            if self.state["phase"] not in {"running", "paused", "holding"}:
                raise RuntimeError("There is no active session to pause.")
            self._paused = not self._paused
            self.state["phase"] = "paused" if self._paused else "running"
            if self._paused:
                self.state["current_speed"] = 0
        self.log("Bewegung pausiert; Position bleibt aktiv." if self._paused else "Bewegung fortgesetzt.")

    def speed(self, value):
        value = float(value)
        if not math.isfinite(value) or not .5 <= value <= 160:
            raise ValueError("Invalid speed.")
        with self.lock:
            if self.state.get("speed_mode") == "auto" and self.state["phase"] in ACTIVE:
                raise RuntimeError("Road-aware speed adjusts automatically. Stop the drive before choosing fixed speed.")
            self._speed = value

    def stop(self):
        with self.lock:
            if self.state["phase"] not in ACTIVE:
                return
            self.state.update(phase="stopping", message="Stopping simulation and sending the reset command …")
        self.stop_event.set()

    def recover(self):
        with self.lock:
            if not self._device:
                raise RuntimeError("Connect the previously used iPhone first.")
            udid = self._device["udid"]
        def clear():
            if self._connection == "wifi":
                self.device.clear_wifi(udid)
            else:
                self.device.mount(udid)
                self.device.clear(udid)
            with self.lock:
                self._needs_clear = False
                self._connected = True
                self.state.update(phase="ready", message="Reset command sent. Check your real location in Apple Maps.")
            self.log("Reset requested. Check the location on your iPhone.")
        self._begin_job("stopping", "Resetting the iPhone location …", clear)

    def favorite(self, name, point, detail=""):
        name = str(name).strip()[:60]
        if not name:
            raise ValueError("Give this place a name.")
        item = {"name": name, "point": coordinate(point), "detail": str(detail)[:100]}
        with self.lock:
            self.favorites = [x for x in self.favorites if x["name"] != name]
            self.favorites.insert(0, item)
            self.favorites = self.favorites[:20]
            self._save_data()

    def _save_data(self):
        temporary = self.data_file.with_suffix(".tmp")
        temporary.write_text(json.dumps({"favorites": self.favorites, "wifi_device": self._wifi_device}, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.data_file)

    def shutdown(self, timeout=15):
        self.stop()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout)
        with self.lock:
            return not self._needs_clear and not (self.thread and self.thread.is_alive())
