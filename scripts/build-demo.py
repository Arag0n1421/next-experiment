#!/usr/bin/env python3
"""Copy only the verified, non-secret scientific records into the local demo."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = {
    "candidate": "452fda4c1e084b9d9b1ae4fea2e1e39f",
    "guide-check": "d8edc9f95f0c4934ae9b4358fd89e98f",
    "decision": "9640dbe6abbb44d7b72e9141e4c1f1ac",
}


def build(root: Path = ROOT) -> dict:
    out = root / "demo" / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"mode": "replay_of_saved_verified_execution", "records": {}}
    for name, record_id in RECORDS.items():
        source = root / "runs" / "live" / f"{record_id}.json"
        raw = source.read_bytes()
        record = json.loads(raw)
        if record["id"] != record_id:
            raise ValueError("Evidence identity mismatch")
        # These records contain measured scientific output, not session exports,
        # model conversations, credentials, or workstation configuration.
        public = {key: record[key] for key in ("id", "kind", "created_utc", "payload")}
        public["payload"].pop("artifact_paths", None)
        encoded = json.dumps(public, ensure_ascii=False, indent=2) + "\n"
        if any(marker in encoded for marker in ("/Users/", "/Volumes/", "/private/")):
            raise ValueError("Local path detected in public evidence")
        (out / f"{name}.json").write_text(encoded)
        manifest["records"][name] = {
            "id": record_id,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "demo_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    build()
    print("Built 3 verified evidence records and their integrity manifest.")
