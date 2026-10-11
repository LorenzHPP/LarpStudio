"""Deterministic driving timing from OSRM road speeds and route geometry.

OSRM speeds are modeled travel speeds, not a live or authoritative limit feed.
The profile lowers them for curves, acceleration, braking and endpoint stops.
"""
import bisect
import math

MAX_SPEED = 130 / 3.6
ACCELERATION = 1.6
BRAKING = 2.2


class DrivingProfile:
    def __init__(self, route, samples):
        if not isinstance(samples, list) or not 3 <= len(samples) <= 100001:
            raise ValueError("Für Straßentempo die Fahrroute neu planen.")
        self.distances, self.speeds = [], []
        for sample in samples:
            if not isinstance(sample, (list, tuple)) or len(sample) != 2:
                raise ValueError("Ungültiges Fahrprofil. Route neu planen.")
            d, v = map(float, sample)
            if not math.isfinite(d) or not math.isfinite(v) or d < 0 or not 0 <= v <= MAX_SPEED + 1e-6:
                raise ValueError("Ungültiges Fahrprofil. Route neu planen.")
            if self.distances and d <= self.distances[-1]:
                raise ValueError("Die Fahrabschnitte müssen aufeinander folgen.")
            self.distances.append(d)
            self.speeds.append(v)
        if abs(self.distances[0]) > 1e-6 or abs(self.distances[-1] - route.total) > .01:
            raise ValueError("Das Fahrprofil passt nicht zur Route. Route neu planen.")
        if self.speeds[0] != 0 or self.speeds[-1] != 0:
            raise ValueError("Das Fahrprofil muss am Start und Ziel anhalten.")
        self.times = [0.0]
        for i, (a, b) in enumerate(zip(self.distances, self.distances[1:])):
            v0, v1 = self.speeds[i:i + 2]
            if v0 + v1 <= 0:
                raise ValueError("Ein Fahrabschnitt braucht ein gültiges Tempo.")
            dt = 2 * (b - a) / (v0 + v1)
            acceleration = (v1 - v0) / dt
            if acceleration > ACCELERATION + 1e-5 or acceleration < -BRAKING - 1e-5:
                raise ValueError("Das Fahrprofil beschleunigt oder bremst zu stark.")
            self.times.append(self.times[-1] + dt)
        self.total = route.total
        self.duration = self.times[-1]

    def at(self, seconds):
        if seconds <= 0:
            return 0.0, 0.0
        if seconds >= self.duration:
            return self.total, 0.0
        i = bisect.bisect_right(self.times, seconds) - 1
        dt = self.times[i + 1] - self.times[i]
        t = seconds - self.times[i]
        v0, v1 = self.speeds[i:i + 2]
        acceleration = (v1 - v0) / dt
        return self.distances[i] + v0 * t + .5 * acceleration * t * t, v0 + acceleration * t

    def travel(self, seconds, loop=False):
        """Position distance, total traveled, speed and time to the next endpoint."""
        if not loop:
            d, v = self.at(seconds)
            return d, d, v, max(0.0, self.duration - seconds)
        cycles, cycle = divmod(max(0.0, seconds), 2 * self.duration)
        forward = cycle <= self.duration
        d, v = self.at(cycle if forward else 2 * self.duration - cycle)
        traveled = cycles * 2 * self.total + (d if forward else 2 * self.total - d)
        remaining = self.duration - cycle if forward else 2 * self.duration - cycle
        return d, traveled, v, remaining

    def export(self):
        return [[d, v] for d, v in zip(self.distances, self.speeds)]


def bearing(a, b):
    lat1, lat2 = map(math.radians, (a[0], b[0]))
    lon = math.radians((b[1] - a[1] + 180) % 360 - 180)
    return math.atan2(math.sin(lon) * math.cos(lat2),
                      math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon))


def build_driving_profile(route, legs):
    """Use every annotated road segment; reject missing or unaligned data."""
    caps = []
    for leg in legs:
        annotation = leg.get("annotation", {})
        lengths, durations, speeds = (annotation.get(k) for k in ("distance", "duration", "speed"))
        if not all(isinstance(x, list) for x in (lengths, durations, speeds)) or not len(lengths) == len(durations) == len(speeds):
            raise ValueError("Der Routendienst liefert keine Abschnittsgeschwindigkeiten.")
        for d, t, v in zip(lengths, durations, speeds):
            d, t, v = float(d), float(t), float(v)
            if not all(math.isfinite(n) for n in (d, t, v)) or min(d, t, v) < 0 or (d > 0 and min(t, v) <= 0):
                raise ValueError("Der Routendienst liefert ungültige Fahrabschnitte.")
            caps.append(min(MAX_SPEED, v, d / t) if d > 0 else MAX_SPEED)
    if len(caps) != len(route.points) - 1 or route.total < 1:
        raise ValueError("Straßentempo kann dieser Route nicht sicher zugeordnet werden.")
    # Keep every original road boundary. Add samples for smooth transitions;
    # bound the number of extra samples on unusually long world-map routes.
    count = max(2, min(40000, math.ceil(route.total / 10)))
    positions = sorted(set(route.lengths + [route.total * i / count for i in range(count + 1)]))
    velocities = []
    for d in positions:
        edge = min(len(caps) - 1, bisect.bisect_right(route.lengths, d) - 1)
        cap = caps[edge]
        if edge > 0 and abs(d - route.lengths[edge]) < 1e-6:
            cap = min(cap, caps[edge - 1])
        before, after = max(0, d - 12), min(route.total, d + 12)
        if d - before > .5 and after - d > .5:
            a, b, c = route.at(before), route.at(d), route.at(after)
            angle = abs((bearing(b, c) - bearing(a, b) + math.pi) % (2 * math.pi) - math.pi)
            if angle > .03:
                radius = (after - before) / (2 * angle)
                cap = min(cap, math.sqrt(2.0 * radius))
        velocities.append(cap)
    velocities[0] = velocities[-1] = 0.0
    for i in range(1, len(positions)):
        velocities[i] = min(velocities[i], math.sqrt(velocities[i - 1] ** 2 + 2 * ACCELERATION * (positions[i] - positions[i - 1])))
    for i in range(len(positions) - 2, -1, -1):
        velocities[i] = min(velocities[i], math.sqrt(velocities[i + 1] ** 2 + 2 * BRAKING * (positions[i + 1] - positions[i])))
    return DrivingProfile(route, [[d, v] for d, v in zip(positions, velocities)])
