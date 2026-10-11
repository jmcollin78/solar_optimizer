#!/usr/bin/env python3
"""Install and persist development Lovelace dashboards.

Dashboard files stored in .devcontainer/lovelace.* are the Git-tracked source of
truth. Home Assistant writes its storage files atomically, which replaces symbolic
links; dashboards are therefore copied into .storage at startup and copied back
when Home Assistant exits.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import select
import struct
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / ".devcontainer"
STORAGE_DIR = ROOT / "config" / ".storage"
DASHBOARDS_REGISTRY = STORAGE_DIR / "lovelace_dashboards"
DASHBOARD_PREFIX = "lovelace."
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_TO = 0x00000080


def dashboard_sources() -> list[Path]:
    """Return all Git-tracked development dashboard files."""
    return sorted(
        path
        for path in SOURCE_DIR.glob(f"{DASHBOARD_PREFIX}*")
        if path.is_file()
    )


def read_json(path: Path) -> dict:
    """Read a Home Assistant JSON storage file."""
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: dict) -> None:
    """Write formatted JSON so dashboard registry changes remain inspectable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def files_have_same_content(first: Path, second: Path) -> bool:
    """Return whether two files have identical content."""
    return first.is_file() and second.is_file() and first.read_bytes() == second.read_bytes()


def dashboard_metadata(source: Path) -> tuple[str, str, str]:
    """Derive the dashboard id, URL path, and title from its storage key."""
    key = read_json(source).get("key", source.name)
    if not isinstance(key, str) or not key.startswith(DASHBOARD_PREFIX):
        raise ValueError(f"{source} must define a key starting with {DASHBOARD_PREFIX}")

    dashboard_id = key.removeprefix(DASHBOARD_PREFIX)
    if not dashboard_id:
        raise ValueError(f"{source} must define a non-empty dashboard id")

    return (
        dashboard_id,
        dashboard_id.replace("_", "-"),
        dashboard_id.replace("_", " ").title(),
    )


def install() -> None:
    """Copy development dashboards into storage and register them in the sidebar."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    sources = dashboard_sources()
    print(f"[dashboards] Installation de {len(sources)} dashboard(s) de développement.")
    registry = (
        read_json(DASHBOARDS_REGISTRY)
        if DASHBOARDS_REGISTRY.exists()
        else {
            "version": 1,
            "minor_version": 1,
            "key": "lovelace_dashboards",
            "data": {"items": []},
        }
    )
    items = registry.setdefault("data", {}).setdefault("items", [])

    for source in sources:
        dashboard_id, url_path, title = dashboard_metadata(source)
        target = STORAGE_DIR / source.name
        if files_have_same_content(source, target):
            print(f"[dashboards] {source.name} est déjà à jour.")
        else:
            shutil.copy2(source, target)
            print(f"[dashboards] {source.name} copié vers {target}.")

        item = next((item for item in items if item.get("id") == dashboard_id), None)
        if item is None:
            items.append(
                {
                    "id": dashboard_id,
                    "icon": "mdi:solar-power",
                    "title": title,
                    "url_path": url_path,
                    "mode": "storage",
                    "require_admin": False,
                    "show_in_sidebar": True,
                }
            )
            print(f"[dashboards] Dashboard /{url_path} ajouté à la barre latérale.")
        else:
            item.update(
                {
                    "title": title,
                    "url_path": url_path,
                    "mode": "storage",
                    "show_in_sidebar": True,
                }
            )
            print(f"[dashboards] Dashboard /{url_path} déjà enregistré.")

    write_json(DASHBOARDS_REGISTRY, registry)
    print("[dashboards] Installation terminée.")


def sync(quiet: bool = False) -> None:
    """Copy dashboard changes made by Home Assistant back to Git-tracked files."""
    sources = dashboard_sources()
    if not quiet:
        print(f"[dashboards] Sauvegarde de {len(sources)} dashboard(s) vers Git.")
    for source in sources:
        target = STORAGE_DIR / source.name
        if not target.is_file():
            if not quiet:
                print(f"[dashboards] {target} absent : aucune sauvegarde.")
        elif files_have_same_content(source, target):
            if not quiet:
                print(f"[dashboards] {source.name} ne contient aucune modification.")
        else:
            shutil.copy2(target, source)
            print(f"[dashboards] Modifications sauvegardées dans {source}.")
    if not quiet:
        print("[dashboards] Sauvegarde terminée.")


def watch() -> None:
    """Synchronize dashboards only when Home Assistant writes to storage."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    source_names = {source.name for source in dashboard_sources()}
    if not source_names:
        print("[dashboards] Aucun dashboard de développement à surveiller.")
        return

    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    file_descriptor = libc.inotify_init1(0)
    if file_descriptor < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))

    watch_descriptor = libc.inotify_add_watch(
        file_descriptor,
        os.fsencode(STORAGE_DIR),
        IN_CLOSE_WRITE | IN_MOVED_TO,
    )
    if watch_descriptor < 0:
        error = ctypes.get_errno()
        os.close(file_descriptor)
        raise OSError(error, os.strerror(error))

    print(
        "[dashboards] Surveillance des modifications Home Assistant activée "
        "(sans polling)."
    )
    try:
        while True:
            select.select([file_descriptor], [], [])
            events = os.read(file_descriptor, 4096)
            offset = 0
            while offset < len(events):
                _, _, _, name_length = struct.unpack_from("iIII", events, offset)
                offset += struct.calcsize("iIII")
                name = events[offset : offset + name_length].rstrip(b"\0").decode()
                offset += name_length
                if name in source_names:
                    sync(quiet=True)
    finally:
        os.close(file_descriptor)


def main() -> None:
    """Run the requested dashboard operation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "sync", "watch"))
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="N'afficher que les dashboards effectivement synchronisés.",
    )
    args = parser.parse_args()

    if args.action == "install":
        install()
    elif args.action == "sync":
        sync(args.quiet)
    else:
        watch()


if __name__ == "__main__":
    main()
