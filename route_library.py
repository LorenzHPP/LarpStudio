"""A small local route library, independent of the live device session."""
import json
import math
from pathlib import Path
import threading


def validate_routes(routes):
    if not isinstance(routes, list) or len(routes) > 20:
        raise ValueError("Save up to 20 routes.")
    clean = []
    for route in routes:
        if not isinstance(route, dict) or route.get("mode") not in {"walk", "run", "drive"}:
            raise ValueError("Invalid route mode.")
        name = route.get("name")
        points = route.get("points")
        if not isinstance(name, str) or not name.strip() or len(name) > 60:
            raise ValueError("Choose a route name with up to 60 characters.")
        if not isinstance(points, list) or not 2 <= len(points) <= 12:
            raise ValueError("A saved route needs 2 to 12 points.")
        items = []
        for item in points:
            if not isinstance(item, dict) or not isinstance(item.get("title"), str) or len(item["title"]) > 120:
                raise ValueError("Invalid point name.")
            point = item.get("point")
            if (not isinstance(point, list) or len(point) != 2
                    or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in point)
                    or abs(point[0]) > 90 or abs(point[1]) > 180):
                raise ValueError("Invalid route coordinates.")
            items.append({"title": item["title"], "point": point[:]})
        clean.append({"name": name.strip(), "mode": route["mode"], "points": items})
    return clean


class RouteLibrary:
    def __init__(self, root):
        self.path = Path(root) / ".larp-routes.json"
        self.lock = threading.Lock()

    def load(self):
        with self.lock:
            if not self.path.exists():
                return []
            if self.path.stat().st_size > 512 * 1024:
                raise ValueError("The local route library is too large.")
            return validate_routes(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, routes):
        clean = validate_routes(routes)
        with self.lock:
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps(clean, ensure_ascii=False), encoding="utf-8")
            temp.replace(self.path)
        return clean
