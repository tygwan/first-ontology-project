#!/usr/bin/env bash
# check_dev_standards_sync.sh — Verify project memory dir follows dev-standards.
#
# Compares $DEV_STANDARDS_DIR/memory/ (source of truth) against this project's
# Claude Code memory dir. Reports:
#   - Missing files (in dev-standards but not installed)
#   - Diverged files (installed but content differs from upstream)
#   - Project-specific files (installed but not in dev-standards) — informational
#
# Exit codes:
#   0 — fully in sync (no missing, no diverged)
#   1 — drift detected
#   2 — setup error (missing dirs/args)
#
# Usage:
#   bash scripts/check_dev_standards_sync.sh              # default paths
#   DEV_STANDARDS_DIR=/path/to/repo bash scripts/...      # override source
#
# Runs in O(few ms). Safe to invoke from CI or a Claude Code hook.

set -euo pipefail

DEV_STANDARDS_DIR="${DEV_STANDARDS_DIR:-$HOME/dev/dev-standards}"
PROJECT_SLUG="-home-taegwan-dev-dev-first-ontology-project"
PROJECT_MEMORY_DIR="${PROJECT_MEMORY_DIR:-$HOME/.claude/projects/$PROJECT_SLUG/memory}"

SRC="$DEV_STANDARDS_DIR/memory"

if [[ ! -d "$SRC" ]]; then
  echo "ERROR: dev-standards memory dir not found: $SRC" >&2
  echo "       Set DEV_STANDARDS_DIR to the repo root." >&2
  exit 2
fi

if [[ ! -d "$PROJECT_MEMORY_DIR" ]]; then
  echo "ERROR: project memory dir not found: $PROJECT_MEMORY_DIR" >&2
  exit 2
fi

echo "dev-standards source : $SRC"
echo "project memory       : $PROJECT_MEMORY_DIR"
echo ""

MISSING=()
DIVERGED=()
OK=()
EXTRA=()

while IFS= read -r -d '' src_file; do
  name="$(basename "$src_file")"
  [[ "$name" == "MEMORY.md" ]] && continue  # index file is project-customized
  dst="$PROJECT_MEMORY_DIR/$name"
  if [[ ! -f "$dst" ]]; then
    MISSING+=("$name")
  elif ! diff -q "$src_file" "$dst" >/dev/null 2>&1; then
    DIVERGED+=("$name")
  else
    OK+=("$name")
  fi
done < <(find "$SRC" -maxdepth 1 -name "feedback_*.md" -print0)

while IFS= read -r -d '' dst_file; do
  name="$(basename "$dst_file")"
  [[ "$name" == "MEMORY.md" ]] && continue
  if [[ ! -f "$SRC/$name" ]]; then
    EXTRA+=("$name")
  fi
done < <(find "$PROJECT_MEMORY_DIR" -maxdepth 1 -name "feedback_*.md" -print0)

if [[ ${#OK[@]} -gt 0 ]]; then
  echo "[OK] in sync (${#OK[@]}):"
  printf '  - %s\n' "${OK[@]}"
fi

if [[ ${#EXTRA[@]} -gt 0 ]]; then
  echo ""
  echo "[INFO] project-specific (not in dev-standards, ${#EXTRA[@]}):"
  printf '  - %s\n' "${EXTRA[@]}"
fi

DRIFT=0

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo ""
  echo "[MISSING] files in dev-standards but not installed (${#MISSING[@]}):"
  printf '  - %s\n' "${MISSING[@]}"
  echo "  fix: cp $SRC/<file> $PROJECT_MEMORY_DIR/"
  DRIFT=1
fi

if [[ ${#DIVERGED[@]} -gt 0 ]]; then
  echo ""
  echo "[DIVERGED] installed content differs from upstream (${#DIVERGED[@]}):"
  for f in "${DIVERGED[@]}"; do
    echo "  - $f"
    echo "    diff: diff $SRC/$f $PROJECT_MEMORY_DIR/$f"
  done
  DRIFT=1
fi

echo ""
if [[ $DRIFT -eq 0 ]]; then
  echo "SYNC OK — project memory matches dev-standards@$(cd "$DEV_STANDARDS_DIR" && git describe --always --dirty 2>/dev/null || echo HEAD)"
  exit 0
else
  echo "DRIFT DETECTED — see messages above."
  exit 1
fi
