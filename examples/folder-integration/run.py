"""Poll an explicitly synthetic demo folder; no recursive scans or symlinks."""
import argparse
import os
import time
from pathlib import Path
from morrowdock_integrations import build_item, provenance, verification
from morrowdock_integrations.client import Client


def scan(folder, client, seen):
    if (folder / "SYNTHETIC_ONLY").read_text().strip() != "fixture-only":
        raise ValueError("Requires an authored synthetic demo folder")
    for path in sorted(folder.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in (".pdf", ".md"):
            continue
        key = (path.name, path.stat().st_mtime_ns, path.stat().st_size)
        if key in seen:
            continue
        attachment = client.upload(path, "application/pdf" if path.suffix.lower() == ".pdf" else "text/markdown")
        client.send(build_item(kind="material", course="TEST 101", title=path.name,
                              summary="Synthetic folder demo material.", synthetic=True,
                              source=provenance("manual"), verification={"/title": verification("verified", "fixture")},
                              attachments=[attachment]))
        seen.add(key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    client, seen = Client(os.environ["MORROWDOCK_BASE_URL"]), set()
    while True:
        scan(args.folder, client, seen)
        if args.once:
            break
        time.sleep(2)
