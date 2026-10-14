"""Keep the standalone EXE's settings outside the download folder."""
import json
import os
from pathlib import Path
import sys


def data_directory(source_root):
    if not getattr(sys, "frozen", False):
        return Path(source_root)
    base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    destination = Path(base) / "Larp Studio"
    destination.mkdir(parents=True, exist_ok=True)
    previous = Path(sys.executable).resolve().parent
    for filename in (".atlas-data.json", ".larp-routes.json"):
        old, new = previous / filename, destination / filename
        if new.exists() or not old.is_file():
            continue
        try:
            if old.stat().st_size > 512 * 1024:
                continue
            content = old.read_bytes()
            parsed = json.loads(content)
            if filename == ".atlas-data.json":
                if not isinstance(parsed, dict) or not isinstance(parsed.get("favorites"), list):
                    continue
            else:
                from route_library import validate_routes
                validate_routes(parsed)
            # Exclusive creation also preserves settings if two copies start together.
            with new.open("xb") as target:
                target.write(content)
        except (OSError, ValueError, TypeError, KeyError):
            # An unreadable old file must not prevent starting the new app.
            continue
    return destination
