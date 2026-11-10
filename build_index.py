#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generates extera-plugins.json repository index for exteraGram plugin catalog.
"""

import ast
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "extera-plugins.json"

REPOSITORY = {
    "schema": 1,
    "name": "koresent Plugins",
    "description": "Personal collection of plugins for exteraGram and its forks.",
    "author": "@koresent",
    "homepage": "https://github.com/koresent/telegram-plugins",
}

FIELDS = (
    "id",
    "name",
    "description",
    "author",
    "version",
    "icon",
    "app_version",
    "sdk_version",
    "requirements",
    "category",
)


def read_plugin_file(path: Path):
    meta = {}
    content = path.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id.startswith("__") and target.id.endswith("__"):
            key = target.id[2:-2]
            if key in FIELDS:
                try:
                    meta[key] = ast.literal_eval(node.value)
                except Exception:
                    pass
    return meta


def main():
    previous = {}
    if INDEX.exists():
        try:
            previous = {p["id"]: p for p in json.loads(INDEX.read_text(encoding="utf-8")).get("plugins", [])}
        except Exception:
            previous = {}

    plugins = []
    for path in sorted(ROOT.rglob("*.plugin")):
        if not path.is_file() or ".git" in path.parts:
            continue

        meta = read_plugin_file(path)
        missing = [key for key in ("id", "name", "version") if not meta.get(key)]
        if missing:
            print(f"Skipping {path}: missing {', '.join(missing)}", file=sys.stderr)
            continue

        if isinstance(meta.get("requirements"), list):
            meta["requirements"] = ", ".join(meta["requirements"])

        data = path.read_bytes()
        entry = {
            **meta,
            "file": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }

        old = previous.get(meta["id"], {})
        if old.get("sha256") == entry["sha256"] and old.get("updated_at"):
            entry["updated_at"] = old["updated_at"]
        else:
            entry["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        plugins.append(entry)

    # Sort plugins by id
    plugins.sort(key=lambda x: x["id"])

    index_data = {
        **REPOSITORY,
        "plugins": plugins,
    }

    INDEX.write_text(json.dumps(index_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {INDEX.name} with {len(plugins)} plugins.")


if __name__ == "__main__":
    main()
