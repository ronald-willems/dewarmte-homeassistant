#!/usr/bin/env bash
# Release: bump manifest.json, commit, tag, push, and create the GitHub release.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MANIFEST="custom_components/dewarmte/manifest.json"

usage() {
  cat <<'EOF'
Usage: scripts/release.sh <version> --title "<title>" --notes-file <file> [--prerelease] [--draft] [--yes]

Bumps custom_components/dewarmte/manifest.json to <version>, commits
"Release v<version>" on main, tags v<version>, pushes main and the tag, and
creates the GitHub release with the given title and notes.

  <version>        X.Y.Z (a leading "v" is accepted)
  --title          Release title shown on GitHub and in HACS
  --notes-file     Markdown file with the release notes
  --prerelease     Mark as pre-release (HACS only offers it to users who opt in)
  --draft          Create the release unpublished, to publish from the GitHub UI
  --yes            Skip the confirmation prompt

Refuses to run unless: on main, working tree clean, not behind origin/main,
the tag does not exist yet, <version> is higher than the manifest's, and the
tests pass. Requires: git, gh (authenticated), python with pytest.
EOF
}

VERSION=""
TITLE=""
NOTES_FILE=""
GH_FLAGS=()
ASSUME_YES=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --title) TITLE="${2:-}"; shift 2 ;;
    --notes-file) NOTES_FILE="${2:-}"; shift 2 ;;
    --prerelease) GH_FLAGS+=(--prerelease); shift ;;
    --draft) GH_FLAGS+=(--draft); shift ;;
    --yes) ASSUME_YES=1; shift ;;
    -*) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    *) VERSION="${1#v}"; shift ;;
  esac
done

fail() { echo "Error: $*" >&2; exit 1; }

[[ -n "$VERSION" && -n "$TITLE" && -n "$NOTES_FILE" ]] || { usage >&2; exit 1; }
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "version must be X.Y.Z, got '$VERSION'"
[[ -s "$NOTES_FILE" ]] || fail "notes file '$NOTES_FILE' is missing or empty"
TAG="v$VERSION"

PYTHON="python3"
[[ -x "$ROOT/.venv/bin/python" ]] && PYTHON="$ROOT/.venv/bin/python"

# --- Preconditions -----------------------------------------------------------
[[ "$(git branch --show-current)" == "main" ]] || fail "not on main"
[[ -z "$(git status --porcelain)" ]] || fail "working tree is not clean"
gh auth status >/dev/null 2>&1 || fail "gh is not authenticated (run: gh auth login)"

git fetch --quiet --tags origin main
[[ "$(git rev-list --count HEAD..origin/main)" == "0" ]] || fail "main is behind origin/main; pull first"
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null && fail "tag $TAG already exists"

CURRENT="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$MANIFEST")"
"$PYTHON" - "$CURRENT" "$VERSION" <<'EOF' || fail "$VERSION is not higher than the manifest version $CURRENT"
import sys
current, new = (tuple(int(p) for p in v.split(".")) for v in sys.argv[1:3])
sys.exit(0 if new > current else 1)
EOF

echo "Running tests..."
"$PYTHON" -m pytest tests/ -q >/dev/null || fail "tests failed (run: $PYTHON -m pytest tests/ -q)"

# --- Confirm -----------------------------------------------------------------
echo
echo "Release $TAG  (manifest $CURRENT -> $VERSION)  ${GH_FLAGS[*]:-}"
echo "Title: $TITLE"
echo "Notes:"
sed 's/^/  | /' "$NOTES_FILE"
echo
if [[ "$ASSUME_YES" != 1 ]]; then
  read -r -p "Commit, tag, push and publish? [y/N] " answer
  [[ "$answer" == "y" || "$answer" == "Y" ]] || { echo "Aborted."; exit 1; }
fi

# --- Bump, commit, tag, push, release ----------------------------------------
# Replace only the version line so the rest of the file keeps its formatting.
"$PYTHON" - "$MANIFEST" "$VERSION" <<'EOF'
import re, sys
path, version = sys.argv[1:3]
text = open(path, encoding="utf-8").read()
text, count = re.subn(r'("version":\s*")[^"]*(")', rf'\g<1>{version}\g<2>', text, count=1)
if count != 1:
    sys.exit("version field not found in manifest.json")
open(path, "w", encoding="utf-8").write(text)
EOF

git add "$MANIFEST"
git commit --quiet -m "Release $TAG"
git tag -a "$TAG" -m "$TITLE"
git push --quiet origin main
git push --quiet origin "$TAG"

gh release create "$TAG" --verify-tag --title "$TITLE" --notes-file "$NOTES_FILE" ${GH_FLAGS[@]+"${GH_FLAGS[@]}"}
