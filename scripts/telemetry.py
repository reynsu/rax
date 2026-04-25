"""Opt-in telemetry for rax.

DEFAULT: DISABLED. Nothing is sent without explicit `enable`.

When enabled, after each audit rax submits to the configured endpoint:
    - audit_id (UUID, generated locally)
    - codebase_hash (SHA-256 of the file list + sizes; the source code
      is never transmitted)
    - scores produced by rax
    - if the user runs `rax telemetry correct <audit_id> ...`,
      the corrected scores
    - profile, mode, replicates, total runtime, total cost

The endpoint URL defaults to a placeholder; users / forks point it at
their own collector. The collector schema is in `docs/telemetry-schema.md`
and the reference open-source collector implementation is at
github.com/<repo>/rax-telemetry-collector.

This module only handles state (enable/disable + queue) and outbound
posting. The audit pipeline calls `submit_after_audit(...)` which is a
no-op when telemetry is off.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path.home() / ".config" / "rax"
CONFIG_FILE = CONFIG_DIR / "telemetry.json"
QUEUE_FILE = CONFIG_DIR / "telemetry_queue.jsonl"

DEFAULT_ENDPOINT = "https://example.invalid/rax/telemetry"


def _load_config() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"enabled": False, "endpoint": DEFAULT_ENDPOINT}


def _save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def is_enabled() -> bool:
    return bool(_load_config().get("enabled"))


def enable(endpoint: Optional[str] = None) -> None:
    cfg = _load_config()
    cfg["enabled"] = True
    if endpoint:
        cfg["endpoint"] = endpoint
    _save_config(cfg)
    print(
        "Telemetry ENABLED.\n"
        f"  endpoint: {cfg['endpoint']}\n"
        "  what we send: audit_id, codebase_hash (SHA-256 of file list,\n"
        "                NOT the source code), scores, profile, mode,\n"
        "                runtime, cost.\n"
        "  what we don't send: source code, paths, identifying metadata.\n"
        "  disable any time: `rax telemetry disable`."
    )


def disable() -> None:
    cfg = _load_config()
    cfg["enabled"] = False
    _save_config(cfg)
    print("Telemetry DISABLED. Queued submissions remain on disk; clear with `rax telemetry purge`.")


def status() -> None:
    cfg = _load_config()
    queue_n = sum(1 for _ in open(QUEUE_FILE)) if QUEUE_FILE.exists() else 0
    print(json.dumps({
        "enabled": cfg.get("enabled", False),
        "endpoint": cfg.get("endpoint"),
        "queued_submissions": queue_n,
        "config_file": str(CONFIG_FILE),
    }, indent=2))


def purge() -> None:
    if QUEUE_FILE.exists():
        QUEUE_FILE.unlink()
    print("Telemetry queue purged.")


def hash_codebase(target: Path) -> str:
    """Hash file paths + sizes. NEVER hash file CONTENTS — that would let
    a server reconstruct the user's source from the hash."""
    h = hashlib.sha256()
    if target.is_file():
        h.update(str(target.relative_to(target.parent)).encode())
        h.update(str(target.stat().st_size).encode())
        return h.hexdigest()
    for p in sorted(target.rglob("*")):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(target)
        except ValueError:
            continue
        h.update(str(rel).encode())
        h.update(b":")
        h.update(str(p.stat().st_size).encode())
        h.update(b"\n")
    return h.hexdigest()


def submit_after_audit(payload: Dict[str, Any]) -> bool:
    """Append a payload to the local queue, then attempt to flush.

    Returns True if at least the queue write succeeded — outbound POST is
    best-effort. Returns False if telemetry is disabled (no-op).
    """
    if not is_enabled():
        return False

    payload = dict(payload)
    payload.setdefault("audit_id", str(uuid.uuid4()))
    payload.setdefault("submitted_at", datetime.now(timezone.utc).isoformat())

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "a") as f:
        f.write(json.dumps(payload) + "\n")
    flush_queue()
    return True


def flush_queue() -> None:
    if not QUEUE_FILE.exists():
        return
    cfg = _load_config()
    if not cfg.get("enabled"):
        return
    endpoint = cfg.get("endpoint", DEFAULT_ENDPOINT)
    if endpoint == DEFAULT_ENDPOINT:
        return  # don't actually post to placeholder

    queued = QUEUE_FILE.read_text().splitlines()
    remaining: List[str] = []
    for line in queued:
        try:
            req = urllib.request.Request(
                endpoint,
                data=line.encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except (urllib.error.URLError, urllib.error.HTTPError):
            remaining.append(line)
    if remaining:
        QUEUE_FILE.write_text("\n".join(remaining) + "\n")
    else:
        QUEUE_FILE.unlink()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="rax telemetry")
    sub = ap.add_subparsers(dest="cmd", required=True)
    en = sub.add_parser("enable")
    en.add_argument("--endpoint", default=None)
    sub.add_parser("disable")
    sub.add_parser("status")
    sub.add_parser("purge")
    args = ap.parse_args(argv)

    if args.cmd == "enable":
        enable(args.endpoint)
    elif args.cmd == "disable":
        disable()
    elif args.cmd == "status":
        status()
    elif args.cmd == "purge":
        purge()
    return 0


if __name__ == "__main__":
    sys.exit(main())
