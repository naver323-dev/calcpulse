#!/usr/bin/env python3
"""Copy the three free vault samples into the site, or check that they still match.

The samples on /vault/ are copies of files from the product build (`../p2-ai-vault`).
Two copies of the same text always drift; this script is the thing that notices.

    python3 scripts/sync_vault_samples.py --check   # exit 1 if a copy differs (used by npm test)
    python3 scripts/sync_vault_samples.py --write    # copy the files from the product build

The product build is not part of this repository, so --check reports "skipped" and
exits 0 when it is absent: CI must not fail on a checkout that only has the site.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SOURCE = HERE.parent / "p2-ai-vault"
TARGET = HERE / "src" / "data" / "vault-samples"

# (source path inside the product build, name used on the site)
SAMPLES = (
    ("prompts/02-meeting-notes-to-actions.md", "02-meeting-notes-to-actions.md"),
    ("prompts/10-prompt-compressor.md", "10-prompt-compressor.md"),
    ("snippets/python/04_retry_backoff.py", "04_retry_backoff.py"),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync or verify the free vault samples.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="fail if a sample differs")
    group.add_argument("--write", action="store_true", help="copy samples from the product")
    args = parser.parse_args(argv)

    if not SOURCE.is_dir():
        if args.check:
            print(f"skipped: no product build at {SOURCE}")
            return 0
        print(f"no product build at {SOURCE}", file=sys.stderr)
        return 2

    if args.write:
        TARGET.mkdir(parents=True, exist_ok=True)

    problems = 0
    for origin, name in SAMPLES:
        src = SOURCE / origin
        dst = TARGET / name
        if not src.is_file():
            print(f"missing in product: {origin}", file=sys.stderr)
            problems += 1
            continue
        if args.write:
            shutil.copyfile(src, dst)
            print(f"wrote {dst.relative_to(HERE)}")
            continue
        if not dst.is_file():
            print(f"missing on site: {dst.relative_to(HERE)} — run --write", file=sys.stderr)
            problems += 1
            continue
        if digest(src) != digest(dst):
            print(f"drifted: {name} — the site copy differs from the product", file=sys.stderr)
            problems += 1
        else:
            print(f"ok: {name}")

    if args.check and problems:
        print(f"{problems} sample(s) out of sync: run python3 scripts/sync_vault_samples.py --write")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
