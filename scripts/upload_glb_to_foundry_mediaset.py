"""Upload 8,219 GLB files to a Foundry Media Set.

The Foundry Developer Tier Media Set (with auto-commit transaction policy)
does not require explicit transaction management — each upload commits
individually. This simplifies resumability.

Usage:
    export FOUNDRY_TOKEN=...
    python scripts/upload_glb_to_foundry_mediaset.py \\
        --media-set-rid ri.mio.main.media-set.xxx \\
        [--limit 10] [--dry-run] [--skip-existing]
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from foundry_sdk import FoundryClient, UserTokenAuth

DEFAULT_MESH_DIR = Path("data/raw/dxtnavis/2026-04-12/mesh")
HOSTNAME = "datayoon.usw-18.palantirfoundry.com"


def format_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--media-set-rid", required=True,
                    help="Media Set RID (ri.mio.main.media-set.xxx)")
    ap.add_argument("--mesh-dir", type=Path, default=DEFAULT_MESH_DIR,
                    help=f"Directory with .glb files (default: {DEFAULT_MESH_DIR})")
    ap.add_argument("--limit", type=int, default=None,
                    help="Upload only first N files (debug)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Count files only, do not upload")
    ap.add_argument("--progress-every", type=int, default=50,
                    help="Log progress every N uploads (default 50)")
    ap.add_argument("--resume-log", type=Path,
                    default=Path("temp/mediaset_upload_log.txt"),
                    help="Append successfully uploaded filenames here for resume")
    ap.add_argument("--workers", type=int, default=10,
                    help="Parallel upload workers (default 10)")
    args = ap.parse_args()

    token = os.environ.get("FOUNDRY_TOKEN")
    if not token:
        sys.exit("FOUNDRY_TOKEN env var required")

    if not args.mesh_dir.exists():
        sys.exit(f"Mesh dir not found: {args.mesh_dir}")

    glb_files = sorted(args.mesh_dir.glob("*.glb"))
    if args.limit:
        glb_files = glb_files[:args.limit]

    # Resume: skip already-uploaded files
    already_uploaded: set[str] = set()
    if args.resume_log.exists():
        already_uploaded = set(args.resume_log.read_text().splitlines())
        print(f"Resume log found: {len(already_uploaded):,} previously uploaded")

    remaining = [f for f in glb_files if f.name not in already_uploaded]
    total_bytes = sum(f.stat().st_size for f in remaining)

    print(f"Mesh dir: {args.mesh_dir}")
    print(f"Total GLB files: {len(glb_files):,}")
    print(f"Remaining to upload: {len(remaining):,} ({format_bytes(total_bytes)})")
    print(f"Media Set: {args.media_set_rid}")

    if args.dry_run:
        print("\n[DRY RUN] No uploads performed.")
        return

    if not remaining:
        print("\nNothing to upload.")
        return

    # Connect
    auth = UserTokenAuth(token=token)
    client = FoundryClient(auth=auth, hostname=HOSTNAME)
    ms = client.media_sets.MediaSet

    # Ensure log file exists
    args.resume_log.parent.mkdir(parents=True, exist_ok=True)
    log_file = args.resume_log.open("a")
    log_lock = threading.Lock()

    uploaded = 0
    failed: list[tuple[str, str]] = []
    counter_lock = threading.Lock()
    start = time.time()

    def upload_one(glb_path: Path) -> tuple[str, str | None]:
        """Upload a single GLB. Returns (filename, error_msg_or_None)."""
        try:
            body = glb_path.read_bytes()
            ms.upload(
                args.media_set_rid,
                body=body,
                media_item_path=f"{glb_path.stem}.glb",
                preview=True,
            )
            return (glb_path.name, None)
        except Exception as e:
            return (glb_path.name, str(e)[:150])

    print(f"Workers: {args.workers}")
    print("Uploading...\n")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(upload_one, p): p for p in remaining}
        for future in as_completed(futures):
            filename, err = future.result()
            with counter_lock:
                if err is None:
                    uploaded += 1
                    with log_lock:
                        log_file.write(f"{filename}\n")
                        log_file.flush()
                else:
                    failed.append((filename, err))

                done = uploaded + len(failed)
                if done % args.progress_every == 0 or done == len(remaining):
                    elapsed = time.time() - start
                    rate = done / elapsed if elapsed > 0 else 0
                    eta = (len(remaining) - done) / rate if rate > 0 else 0
                    print(f"  {done:,}/{len(remaining):,} "
                          f"(ok={uploaded:,}, fail={len(failed)})  "
                          f"{rate:.1f}/s, ETA {eta/60:.1f}min")

    log_file.close()

    elapsed = time.time() - start
    print(f"\n=== Done in {elapsed/60:.1f}min ===")
    print(f"  Uploaded: {uploaded:,}")
    print(f"  Failed:   {len(failed)}")
    if failed:
        print(f"\nFirst 5 failures:")
        for name, err in failed[:5]:
            print(f"  {name}: {err}")


if __name__ == "__main__":
    main()
