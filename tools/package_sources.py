"""Include installed-package notices and copyleft sources in the EXE archive."""
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import re
import sys
from urllib.request import urlopen


def package_sources(destination):
    destination = Path(destination)
    notices = destination / "Third-party" / "licenses"
    sources = destination / "Third-party" / "sources"
    notices.mkdir(parents=True, exist_ok=True)
    sources.mkdir(parents=True, exist_ok=True)
    inventory = []
    for distribution in sorted(distributions(), key=lambda d: d.metadata["Name"].lower()):
        metadata = distribution.metadata
        name, version = metadata["Name"], distribution.version
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        package_notices = notices / safe_name
        package_notices.mkdir(exist_ok=True)
        (package_notices / "METADATA.txt").write_text(distribution.read_text("METADATA") or distribution.read_text("PKG-INFO") or "", encoding="utf-8")
        for item in distribution.files or []:
            path = distribution.locate_file(item)
            if path.is_file() and any(word in path.name.lower() for word in ("license", "copying", "notice")):
                relative = Path(str(item))
                if relative.is_absolute() or ".." in relative.parts:
                    continue
                target = package_notices / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
        license_text = " ".join([metadata.get("License-Expression", ""), metadata.get("License", ""), *metadata.get_all("Classifier", [])])
        record = {"name": name, "version": version, "license": metadata.get("License-Expression", ""), "source": None}
        if "GPL" in license_text or "GNU General" in license_text:
            with urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=45) as response:
                release = json.load(response)
            source = next((file for file in release["urls"] if file["packagetype"] == "sdist"), None)
            if source is None:
                raise RuntimeError(f"No corresponding source archive for {name} {version}")
            with urlopen(source["url"], timeout=45) as response:
                content = response.read()
            digest = hashlib.sha256(content).hexdigest()
            if digest != source["digests"]["sha256"]:
                raise RuntimeError(f"Source archive checksum mismatch for {name}")
            (sources / Path(source["filename"]).name).write_bytes(content)
            record.update(source=source["url"], sha256=digest)
            print(f"Included source: {name} {version}")
        inventory.append(record)
    (destination / "Third-party" / "packages.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")


if __name__ == "__main__":
    package_sources(sys.argv[1])
