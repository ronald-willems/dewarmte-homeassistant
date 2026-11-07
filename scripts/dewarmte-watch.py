#!/usr/bin/env python3
"""Watch the DeWarmte web app and API for changes we have not handled yet.

DeWarmte ships new features without telling anyone; we usually hear about them
as feature requests. This routine turns their deploys into a reviewable diff:

  1. `fetch`        HEAD the bundle; download it when Last-Modified or size
                    differ from the committed snapshot. Kept in .cache/.
  2. `snapshot`     Rewrite snapshots/ from the bundle (endpoints, write
                    bodies, fields read, enum vocabularies, settings model)
                    and, when tests/secrets.yaml exists, from the live API
                    (response key sets and OPTIONS choices, never values).
  3. `diff`         Compare the working tree snapshot with the one in HEAD.
  4. `draft`        Write one draft issue per changed topic (all sections a
                    feature such as `legionella` touches, together) into
                    .cache/dewarmte-watch/issues/. Delete a draft to reject it.
  5. `file-issues`  Post the remaining drafts with `gh issue create`.
                    Dry run unless --yes. Never files the same change twice.

`run` chains 1-4 and stops early when the bundle did not change. Commit
snapshots/ afterwards: the commit is the record that this version was reviewed.

    python scripts/dewarmte-watch.py run            # the manual routine
    python scripts/dewarmte-watch.py run --force    # even if unchanged
    python scripts/dewarmte-watch.py diff           # just show changes
    python scripts/dewarmte-watch.py diff --base v2.4.3   # against any commit or tag
    python scripts/dewarmte-watch.py file-issues    # list what would be filed
    python scripts/dewarmte-watch.py file-issues --yes

Classification of a change (explainable on purpose):
  - an item removed or changed upstream whose name our code uses (as a
    string, attribute or identifier; comments do not count) is a `bug`
    candidate: we depend on it, so we probably break;
  - an item added upstream whose name our code does not use is an
    `enhancement` candidate;
  - anything else is listed in the diff but gets no draft.

Exit codes: 0 no change, 1 changes found, 2 no committed baseline yet.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))

import webapp_bundle as wb  # noqa: E402

SNAPSHOTS = REPO / "snapshots"
CACHE = REPO / ".cache" / "dewarmte-watch"
BUNDLES = CACHE / "bundles"
ISSUES = CACHE / "issues"
INTEGRATION = REPO / "custom_components" / "dewarmte"
SECRETS = REPO / "tests" / "secrets.yaml"
KEEP_BUNDLES = 5
LABEL = "upstream-change"
MARKER = "dewarmte-watch"

# Words in a change key that say nothing about which feature it belongs to.
GENERIC_WORDS = {
    "v1", "customer", "products", "id", "settings", "results", "status",
    "get", "post", "patch", "put", "delete", "options",
    "required", "optional", "nullable", "unknown", "choice", "field", "string",
    "boolean", "integer", "float", "decimal", "list", "enum", "num", "bool",
    "double", "int", "datetime", "date", "time", "key", "single",
}


# --------------------------------------------------------------------------- helpers

def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_lines(relpath: str, lines: list[str]) -> None:
    path = SNAPSHOTS / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, cwd=REPO)
    if result.returncode != 0:
        raise SystemExit(f"gh {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return result.stdout


def latest_bundle_path() -> Path | None:
    pointer = BUNDLES / "latest"
    if not pointer.exists():
        return None
    path = BUNDLES / pointer.read_text().strip()
    return path if path.exists() else None


def load_bundle(args: argparse.Namespace) -> wb.Bundle:
    if getattr(args, "file", None):
        return wb.Bundle.from_file(args.file)
    path = latest_bundle_path()
    if path is None:
        raise SystemExit("No cached bundle; run `fetch` first or pass --file.")
    meta = read_json(BUNDLES / f"{path.stem}.json")
    bundle = wb.Bundle.from_file(str(path))
    bundle.last_modified = meta.get("last_modified", bundle.last_modified)
    bundle.etag = meta.get("etag", "")
    return bundle


# --------------------------------------------------------------------------- fetch

def cmd_fetch(args: argparse.Namespace) -> bool:
    """Download the bundle when it changed. Returns True when a new one was stored."""
    meta = read_json(SNAPSHOTS / "bundle.json")
    probe = wb.head()
    unchanged = (
        meta
        and probe["last_modified"] == meta.get("last_modified")
        and probe["size"] == meta.get("size")
    )
    if unchanged and not args.force:
        print(f"bundle unchanged: Last-Modified {probe['last_modified']}, {probe['size']} bytes")
        return False

    bundle = wb.fetch()
    BUNDLES.mkdir(parents=True, exist_ok=True)
    path = BUNDLES / f"{bundle.sha256[:12]}.js"
    path.write_bytes(bundle.raw)
    (BUNDLES / f"{path.stem}.json").write_text(json.dumps({
        "last_modified": bundle.last_modified, "etag": bundle.etag, "sha256": bundle.sha256,
        "size": bundle.size, "fetched": dt.date.today().isoformat(),
    }, indent=2))
    (BUNDLES / "latest").write_text(path.name)
    for old in sorted(BUNDLES.glob("*.js"), key=lambda p: p.stat().st_mtime)[:-KEEP_BUNDLES]:
        old.unlink()
        (BUNDLES / f"{old.stem}.json").unlink(missing_ok=True)
    print(f"fetched {bundle.size} bytes, Last-Modified {bundle.last_modified}, "
          f"sha256 {bundle.sha256[:12]} -> {path.relative_to(REPO)}")
    if meta:
        print(f"previous: Last-Modified {meta.get('last_modified')}, {meta.get('size')} bytes")
    return True


# --------------------------------------------------------------------------- snapshot

def cmd_snapshot(args: argparse.Namespace) -> int:
    bundle = load_bundle(args)
    SNAPSHOTS.mkdir(exist_ok=True)
    (SNAPSHOTS / "bundle.json").write_text(json.dumps({
        "url": wb.BUNDLE_URL,
        "last_modified": bundle.last_modified,
        "etag": bundle.etag,
        "size": bundle.size,
        "sha256": bundle.sha256,
        "snapshot_date": dt.date.today().isoformat(),
    }, indent=2) + "\n")

    write_lines("endpoints.txt", wb.api_endpoints(bundle))
    write_lines("routes.txt", wb.app_routes(bundle))
    write_lines("write-bodies.txt", [f"{k}: {', '.join(v)}" for k, v in wb.write_bodies(bundle).items()])
    write_lines("fields.txt", [f"{k}: {', '.join(v)}" for k, v in wb.field_groups(bundle).items()])
    write_lines("enums.txt", [f"{k}: {', '.join(v)}" for k, v in wb.enum_values(bundle).items()])
    write_lines("settings-model.txt",
                [f"{f}: {wb.strip_helper(kind)}" for f, kind in sorted(wb.settings_fields(bundle))])
    print(f"snapshot written to {SNAPSHOTS.relative_to(REPO)}/ "
          f"(bundle {bundle.sha256[:12]}, Last-Modified {bundle.last_modified})")

    if args.no_api:
        return 0
    if not SECRETS.exists():
        print("tests/secrets.yaml not found; API snapshot skipped")
        return 0
    try:
        files = asyncio.run(api_snapshot())
    except Exception as err:  # noqa: BLE001 - report and keep the previous files
        print(f"API snapshot failed, previous api/ files kept: {err}")
        return 0
    for relpath, lines in files.items():
        write_lines(relpath, lines)
    print(f"API snapshot written: {', '.join(sorted(files))}")
    return 0


def shape(obj: object) -> list[str]:
    """Key paths of a JSON document, never its values. Keys that look like ids
    become {key} so no device id lands in the repo."""
    paths: set[str] = set()

    def walk(node: object, prefix: str) -> None:
        if isinstance(node, dict):
            if not node:
                paths.add(prefix or "{}")
            for key, value in node.items():
                key = "{key}" if re.fullmatch(r"[0-9a-fA-F-]{8,}|\d+", str(key)) else str(key)
                walk(value, f"{prefix}.{key}" if prefix else key)
        elif isinstance(node, list):
            if not node:
                paths.add(f"{prefix}[]")
            for item in node:
                walk(item, f"{prefix}[]")
        else:
            paths.add(prefix or "(scalar)")

    walk(obj, "")
    return sorted(paths)


async def api_snapshot() -> dict[str, list[str]]:
    """Key sets of the live GET responses and the OPTIONS metadata of every
    write endpoint, for the first device of each product type."""
    import aiohttp
    import yaml

    from custom_components.dewarmte.api.auth import DeWarmteAuth
    from custom_components.dewarmte.api.models.settings import SETTING_GROUPS

    creds = yaml.safe_load(SECRETS.read_text(encoding="utf-8"))["dewarmte"]
    files: dict[str, list[str]] = {}
    async with aiohttp.ClientSession() as session:
        auth = DeWarmteAuth(creds["username"], creds["password"], session)
        if not await auth.ensure_token():
            raise RuntimeError("login failed")

        async def request(method: str, path: str) -> dict:
            async with session.request(method, f"{auth.base_url}/{path}", headers=auth.headers) as response:
                if response.status != 200:
                    raise RuntimeError(f"{method} {path}: HTTP {response.status}")
                return await response.json()

        products = await request("GET", "customer/products/")
        files["api/products.txt"] = shape(products)
        files["api/tb-status.txt"] = shape(await request("GET", "customer/products/tb-status/"))

        first_of_type: dict[str, str] = {}
        for product in products.get("results", []):
            first_of_type.setdefault(product.get("type", "unknown"), product["id"])

        for ptype, pid in sorted(first_of_type.items()):
            files[f"api/settings.{ptype}.txt"] = shape(await request("GET", f"customer/products/{pid}/settings/"))
            if ptype == "PT":
                files[f"api/smart-control.{ptype}.txt"] = shape(
                    await request("GET", f"customer/products/{pid}/smart-control/"))
            choices: list[str] = []
            for group in SETTING_GROUPS.values():
                path = group.path or f"settings/{group.endpoint}/"
                try:
                    options = await request("OPTIONS", f"customer/products/{pid}/{path}")
                except RuntimeError as err:
                    choices.append(f"{path}: {err}")
                    continue
                for method, fields in sorted((options.get("actions") or {}).items()):
                    for name, meta in sorted(fields.items()):
                        head = (f"{method} {path} {name} ({meta.get('type')}, "
                                f"{'required' if meta.get('required') else 'optional'})")
                        values = [str(c.get("value")) for c in meta.get("choices", [])]
                        choices.append(f"{head}: {', '.join(values)}" if values else head)
            files[f"api/choices.{ptype}.txt"] = choices
    return files


# --------------------------------------------------------------------------- diff

@dataclass
class Change:
    section: str          # snapshot file without extension, e.g. "write-bodies"
    kind: str             # added | removed | changed
    key: str
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)

    @property
    def marker(self) -> str:
        return f"{self.section}:{self.key}"

    def describe(self) -> str:
        if self.kind == "changed":
            parts = [f"+{x}" for x in self.added] + [f"-{x}" for x in self.removed]
            return f"~ {self.key}: {' '.join(parts)}"
        return f"{'+' if self.kind == 'added' else '-'} {self.key}"


def parse_lines(lines: list[str]) -> dict[str, list[str] | None]:
    """`key: a, b` -> key with items; a bare line -> key without items."""
    out: dict[str, list[str] | None] = {}
    for line in lines:
        line = line.rstrip("\n")
        if not line:
            continue
        if ": " in line or line.endswith(":"):
            key, _, rest = line.partition(":")
            out[key] = [x for x in rest.strip().split(", ") if x]
        else:
            out[line] = None
    return out


def baseline_lines(relpath: str, base: str) -> list[str] | None:
    result = git("show", f"{base}:snapshots/{relpath}")
    return result.stdout.splitlines() if result.returncode == 0 else None


def compute_changes(base: str) -> tuple[list[Change], bool]:
    """All changes between the snapshot in `base` (a commit, tag or tree) and
    the working tree's."""
    if not SNAPSHOTS.exists():
        raise SystemExit("No snapshots/ directory; run `snapshot` first.")
    has_baseline = git("cat-file", "-e", f"{base}:snapshots/bundle.json").returncode == 0
    changes: list[Change] = []
    for path in sorted(SNAPSHOTS.rglob("*.txt")):
        relpath = str(path.relative_to(SNAPSHOTS))
        section = relpath[:-4]
        current = parse_lines(path.read_text(encoding="utf-8").splitlines())
        old_lines = baseline_lines(relpath, base)
        previous = parse_lines(old_lines) if old_lines is not None else {}
        for key in sorted(set(current) | set(previous)):
            if key not in previous:
                changes.append(Change(section, "added", key, added=current[key] or []))
            elif key not in current:
                changes.append(Change(section, "removed", key, removed=previous[key] or []))
            elif current[key] != previous[key]:
                now, before = set(current[key] or []), set(previous[key] or [])
                changes.append(Change(section, "changed", key,
                                      added=sorted(now - before), removed=sorted(before - now)))
    return changes, has_baseline


def print_changes(changes: list[Change], base: str) -> None:
    meta_now = read_json(SNAPSHOTS / "bundle.json")
    old = git("show", f"{base}:snapshots/bundle.json")
    meta_old = json.loads(old.stdout) if old.returncode == 0 else {}
    if meta_old.get("sha256") != meta_now.get("sha256"):
        print(f"bundle: {meta_old.get('last_modified', '(none)')} -> {meta_now.get('last_modified')}, "
              f"{meta_old.get('size', '?')} -> {meta_now.get('size')} bytes")
    else:
        print(f"bundle: unchanged ({meta_now.get('last_modified')})")
    if not changes:
        print("no snapshot changes")
        return
    by_section: dict[str, list[Change]] = {}
    for change in changes:
        by_section.setdefault(change.section, []).append(change)
    for section, items in by_section.items():
        counts = {k: sum(1 for c in items if c.kind == k) for k in ("added", "removed", "changed")}
        print(f"\n== {section} (+{counts['added']} -{counts['removed']} ~{counts['changed']})")
        for change in items:
            print(f"  {change.describe()}")


def cmd_diff(args: argparse.Namespace) -> int:
    changes, has_baseline = compute_changes(args.base)
    if not has_baseline:
        print(f"No snapshot in {args.base}: commit snapshots/ to make it the reference.")
        print_changes([], args.base)
        return 2
    print_changes(changes, args.base)
    return 1 if changes else 0


# --------------------------------------------------------------------------- draft

_SOURCE_CACHE: str | None = None


def integration_source() -> str:
    """Our Python source with `#` comments stripped, so prose does not count."""
    global _SOURCE_CACHE
    if _SOURCE_CACHE is None:
        lines = []
        for path in INTEGRATION.rglob("*.py"):
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                lines.append(line.split("#", 1)[0])
        _SOURCE_CACHE = "\n".join(lines)
    return _SOURCE_CACHE


def used_by_integration(token: str) -> bool:
    """True when the token appears as a string literal, attribute or identifier
    in our code. A mention in a docstring ("scheduled vs manual") does not count."""
    escaped = re.escape(token)
    pattern = r"""(["'])%s\1|\.%s\b|\b%s\s*[=:(]""" % (escaped, escaped, escaped)
    return re.search(pattern, integration_source()) is not None


def tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z][a-z0-9_]+", text.lower())
    return [w for w in dict.fromkeys(words) if w not in GENERIC_WORDS and len(w) > 2]


def topic(change: Change) -> str:
    """The first meaningful word of a change key: `legionella` for both
    `/settings/legionella/` and `legionella_protection_day`, so the changes
    one upstream feature causes across sections land in one draft."""
    words = [w for w in re.split(r"[^a-z0-9]+", change.key.lower())
             if w and w not in GENERIC_WORDS and len(w) > 2]
    return words[0] if words else slug(change.key)


def label_for(change: Change) -> tuple[str, str] | None:
    """(label, reasoning) or None when the change needs no issue."""
    if change.kind == "removed":
        hits = [t for t in tokens(change.key) if used_by_integration(t)]
        if hits:
            return "bug", f"disappeared upstream and our source uses {', '.join(hits)}"
        return None
    if change.kind == "added":
        hits = [t for t in tokens(change.key) if used_by_integration(t)]
        if not hits:
            return "enhancement", "new upstream and nothing in our source uses it"
        return None
    # changed: judge by the items that moved
    removed_hits = [t for item in change.removed for t in tokens(item) if used_by_integration(t)]
    if removed_hits or (change.section == "settings-model" and change.removed
                        and used_by_integration(change.key)):
        return "bug", (f"lost {', '.join(change.removed)} upstream and our source uses "
                       f"{', '.join(dict.fromkeys(removed_hits)) or change.key}")
    new_items = [item for item in change.added if not any(used_by_integration(t) for t in tokens(item))]
    if new_items:
        return "enhancement", f"gained {', '.join(new_items)} upstream, which our source does not use"
    return None


def draft_text(name: str, items: list[tuple[Change, str, str]], label: str, base: str, key: str) -> str:
    meta = read_json(SNAPSHOTS / "bundle.json")
    base_commit = git("rev-parse", "--short", base).stdout.strip()
    title = f"Upstream change: {name} ({len(items)} change{'s' if len(items) > 1 else ''})"
    lines = []
    for change, change_label, why in items:
        lines.append(f"- `snapshots/{change.section}.txt`: {change.describe()}")
        if change.kind != "changed" and (change.added or change.removed):
            lines.append(f"  - {'now' if change.kind == 'added' else 'was'}: "
                         f"{', '.join(change.added or change.removed)}")
        lines.append(f"  - {change_label}: {why}")
    return f"""title: {title}
labels: {LABEL}, {label}
key: {key}
---
The DeWarmte web app or API changed around **{name}** in a way this integration does not handle yet.

{chr(10).join(lines)}

**Evidence:** web app bundle `main.dart.js`, Last-Modified {meta.get('last_modified')},
sha256 `{meta.get('sha256', '')[:12]}`, compared with the snapshot in commit {base_commit}.
Run `python scripts/dewarmte-watch.py diff` to reproduce.

<!-- {MARKER}: {key} -->
"""


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def existing_markers() -> set[str]:
    markers = set()
    for path in ISSUES.glob("*.md"):
        match = re.search(r"^key: (.+)$", path.read_text(encoding="utf-8"), re.M)
        if match:
            markers.add(match.group(1).strip())
    return markers


def cmd_draft(args: argparse.Namespace) -> int:
    changes, has_baseline = compute_changes(args.base)
    if not has_baseline:
        print(f"No snapshot in {args.base}; nothing to draft. Commit snapshots/ first.")
        return 2
    ISSUES.mkdir(parents=True, exist_ok=True)
    known = existing_markers()
    groups: dict[str, list[tuple[Change, str, str]]] = {}
    for change in changes:
        verdict = label_for(change)
        if verdict is not None:
            groups.setdefault(topic(change), []).append((change, *verdict))
    written, skipped = 0, 0
    for name, items in sorted(groups.items()):
        fingerprint = hashlib.sha1("\n".join(sorted(c.marker for c, _, _ in items)).encode()).hexdigest()[:10]
        key = f"{name}@{fingerprint}"
        if key in known:
            skipped += 1
            continue
        label = "bug" if any(l == "bug" for _, l, _ in items) else "enhancement"
        path = ISSUES / f"{len(known) + written + 1:03d}-{label}-{slug(name)}.md"
        path.write_text(draft_text(name, items, label, args.base, key), encoding="utf-8")
        written += 1
        print(f"draft [{label}] {path.relative_to(REPO)}  ({len(items)} change(s))")
    print(f"{written} draft(s) written, {skipped} already drafted; "
          f"review in {ISSUES.relative_to(REPO)}/ and delete the ones you reject")
    return 0


# --------------------------------------------------------------------------- file-issues

def parse_draft(path: Path) -> tuple[dict[str, str], str]:
    header, _, body = path.read_text(encoding="utf-8").partition("\n---\n")
    fields = dict(line.split(": ", 1) for line in header.splitlines() if ": " in line)
    return fields, body


def ensure_label() -> None:
    names = {row["name"] for row in json.loads(gh("label", "list", "--json", "name", "--limit", "200"))}
    if LABEL not in names:
        gh("label", "create", LABEL, "--color", "5319E7",
           "--description", "Change in the DeWarmte web app or API detected by dewarmte-watch")
        print(f"created label {LABEL}")


def cmd_file_issues(args: argparse.Namespace) -> int:
    drafts = sorted(ISSUES.glob("*.md")) if ISSUES.exists() else []
    if not drafts:
        print("no drafts")
        return 0
    if args.yes:
        ensure_label()
    for path in drafts:
        fields, body = parse_draft(path)
        if "filed" in fields:
            continue
        marker = f"{MARKER}: {fields['key']}"
        found = json.loads(gh("issue", "list", "--state", "all", "--limit", "5",
                              "--search", f'"{marker}" in:body', "--json", "url"))
        if found:
            url = found[0]["url"]
            print(f"already filed: {url}  ({path.name})")
            _mark_filed(path, url)
            continue
        if not args.yes:
            print(f"would file: [{fields['labels']}] {fields['title']}  ({path.name})")
            continue
        url = gh("issue", "create", "--title", fields["title"],
                 "--label", fields["labels"].replace(" ", ""), "--body", body).strip()
        _mark_filed(path, url)
        print(f"filed: {url}  ({path.name})")
    if not args.yes:
        print("dry run; pass --yes to create the issues above")
    return 0


def _mark_filed(path: Path, url: str) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("\n---\n", f"\nfiled: {url}\n---\n", 1), encoding="utf-8")


# --------------------------------------------------------------------------- run

def cmd_run(args: argparse.Namespace) -> int:
    if not cmd_fetch(args) and not args.force:
        print("nothing to do")
        return 0
    cmd_snapshot(args)
    print()
    code = cmd_diff(args)
    if code == 1:
        print()
        cmd_draft(args)
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch", help="download the bundle when it changed")
    p.add_argument("--force", action="store_true", help="download even if unchanged")
    p.set_defaults(func=lambda a: (cmd_fetch(a), 0)[1])

    p = sub.add_parser("snapshot", help="rewrite snapshots/ from the cached bundle and live API")
    p.add_argument("--file", help="use this local main.dart.js instead of the cached one")
    p.add_argument("--no-api", action="store_true", help="skip the live API part")
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("diff", help="compare the working tree snapshot with the committed one")
    p.add_argument("--base", default="HEAD", help="commit, tag or tree to compare with (default HEAD)")
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("draft", help="write draft issues for actionable changes")
    p.add_argument("--base", default="HEAD", help="commit, tag or tree to compare with (default HEAD)")
    p.set_defaults(func=cmd_draft)

    p = sub.add_parser("file-issues", help="create GitHub issues from the remaining drafts")
    p.add_argument("--yes", action="store_true", help="actually create them (default: dry run)")
    p.set_defaults(func=cmd_file_issues)

    p = sub.add_parser("run", help="fetch, snapshot, diff and draft in one go")
    p.add_argument("--force", action="store_true", help="continue even when the bundle is unchanged")
    p.add_argument("--no-api", action="store_true", help="skip the live API part")
    p.add_argument("--base", default="HEAD", help="commit, tag or tree to compare with (default HEAD)")
    p.set_defaults(func=cmd_run, file=None)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
