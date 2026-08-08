#!/usr/bin/env python3
"""Extract the settings schema the official DeWarmte web app expects.

`mydewarmte.com` is a Flutter app; `main.dart.js` is its compiled (minified)
Dart. It contains the official client's own model for
`GET/POST /v1/customer/products/{id}/settings/`, including which fields it
treats as required and which it accepts as null. That is the closest thing we
have to a spec, and it answers questions our own account cannot -- e.g. "does a
pump without cooling still get `thermostat_type`?" (if the official app requires
it, the API must send it, or the web app would break for those users too).

Run from the repo root:
    python scripts/extract-webapp-schema.py              # download + report
    python scripts/extract-webapp-schema.py --dump       # + raw deserializer
    python scripts/extract-webapp-schema.py --file x.js  # use a local copy
    python scripts/extract-webapp-schema.py --save x.js  # keep the download

The dart2js symbol names (`u0`, `A.md`, `B.K6`) are regenerated on every
DeWarmte deploy, so nothing here hardcodes them: the deserializer is found by
the field names it reads, and each cast helper is classified by looking up its
own definition. Findings are written up in docs/WEBAPP_SCHEMA.md -- update that
file (and the bundle hash it records) when this script reports something new.

Requires no credentials and makes one unauthenticated GET.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import urllib.request

BUNDLE_URL = "https://mydewarmte.com/main.dart.js"

# A field only the settings model reads, used to locate the deserializer.
ANCHOR_FIELD = "advanced_boost_mode_control"

# Repo-side model, for the comparison table.
SETTINGS_MODEL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "custom_components", "dewarmte", "api", "models", "settings.py",
)

FIELD_LOOKUP = re.compile(r'\.i\(0,"([a-z_0-9]+)"\)')
HOISTED_LITERAL = re.compile(r'\b([a-z][a-z0-9]?)="([a-z_0-9]+)"')
# The innermost call wrapping a lookup, e.g. the `A.bZ(` of `A.bZ(a8.i(0,"x"))`
# or the `A.md(B.K6,` of an enum lookup. The variable itself is stripped first.
CALL_TOKEN = re.compile(r'([A-Za-z0-9_$]{1,4}\.[A-Za-z0-9_$]{1,4})\((?:[A-Za-z0-9_$.]{1,8},)?$')


def fetch(url: str) -> tuple[bytes, str]:
    """Return the bundle bytes and its Last-Modified header."""
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read(), response.headers.get("Last-Modified", "unknown")


def find_deserializer(source: str) -> tuple[int, int]:
    """Return the (start, end) slice of the settings deserializer function."""
    anchor = source.find(f'"{ANCHOR_FIELD}"')
    if anchor == -1:
        raise SystemExit(f"Could not find {ANCHOR_FIELD!r}; the app changed shape.")
    # Walk back to the start of the enclosing minified function definition.
    start = source.rfind("\n", 0, anchor) + 1
    end = source.find("return new A.", anchor)
    end = source.find("\n", end) if end != -1 else anchor + 4000
    return start, end


def inline_hoisted_literals(body: str) -> str:
    """Undo dart2js literal hoisting (`b="force_cooling_end"` ... `.i(0,b)`)."""
    for var, literal in HOISTED_LITERAL.findall(body):
        body = body.replace(f'.i(0,{var})', f'.i(0,"{literal}")')
    return body


def classify(source: str, body: str, field: str) -> str:
    """Describe how the web app casts one field: required, nullable, list, ..."""
    lookup = body.find(f'"{field}")')
    before, after = body[:lookup], body[lookup:]
    # `x.i(0,"field")==null?null:...` is an explicit null check by the app.
    if after[len(field) + 3:].startswith("==null?null:"):
        return "nullable (explicit null check)"

    # Drop the `<var>.i(0,` that immediately precedes the field literal, so the
    # regex sees the cast helper wrapping it.
    match = CALL_TOKEN.search(before[: before.rfind(".i(0,")].rstrip("abcdefghijklmnopqrstuvwxyz0123456789_$"))
    if not match:
        return "unknown (no recognizable cast)"
    helper = match.group(1)
    if not helper.startswith("A."):
        # e.g. `t.j.a(...)`: a runtime type check for List, which rejects null.
        return f"required list ({helper})"

    definition = re.search(r"\n%s\(a[0-9a-z,]*\)\{" % re.escape(helper[2:]), source)
    if not definition:
        return f"unknown ({helper})"
    impl = source[definition.start(): definition.start() + 400]
    impl = impl[: impl.find("},\n") + 1]
    if "A value must be provided" in impl:
        return f"required enum ({helper})"
    nullable = re.search(r'"(num|bool|String|double|int)\?"', impl)
    if nullable:
        return f"nullable {nullable.group(1)} ({helper})"
    plain = re.search(r'"(num|bool|String|double|int)"', impl)
    if plain:
        return f"required {plain.group(1)} ({helper})"
    return f"unknown ({helper})"


def integration_handling() -> dict[str, str]:
    """How our own from_api_response reads each field.

    Two separate things matter: whether the key must be present (subscript vs
    `.get()`) and whether a null value is tolerated (an `is not None` guard).
    """
    with open(SETTINGS_MODEL, encoding="utf-8") as f:
        model = f.read()
    handling = {name: "required key" for name in re.findall(r'data\["([a-z_0-9]+)"\]', model)}
    for name in re.findall(r'data\.get\("([a-z_0-9]+)"', model):
        handling[name] = "optional key"
    for name in re.findall(r'data\["([a-z_0-9]+)"\] is not None', model):
        handling[name] += ", null ok"
    return handling


def report_write_bodies(source: str) -> None:
    """Print the field list the app POSTs to each settings sub-endpoint."""
    print("\n## Write bodies per endpoint (what the app POSTs)\n")
    seen: set[str] = set()
    for match in re.finditer(r'"/settings/([a-z-]+)/"', source):
        endpoint = match.group(1)
        if endpoint in seen:
            continue
        window = source[max(0, match.start() - 800): match.start()]
        body = window.rfind("A.aa([")
        if body == -1:
            continue
        fields = re.findall(r'"([a-z_0-9]+)"', window[body: window.find("]", body)])
        if fields:
            seen.add(endpoint)
            print(f"  settings/{endpoint}/ -> {', '.join(fields)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", help="read a local main.dart.js instead of downloading")
    parser.add_argument("--save", help="write the downloaded bundle to this path")
    parser.add_argument("--dump", action="store_true", help="print the raw deserializer")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "rb") as f:
            raw = f.read()
        last_modified = "n/a (local file)"
        origin = args.file
    else:
        raw, last_modified = fetch(BUNDLE_URL)
        origin = BUNDLE_URL
        if args.save:
            with open(args.save, "wb") as f:
                f.write(raw)

    print(f"source:        {origin}")
    print(f"last-modified: {last_modified}")
    print(f"size:          {len(raw)} bytes")
    print(f"sha256:        {hashlib.sha256(raw).hexdigest()}")

    source = raw.decode("utf-8", errors="replace")
    start, end = find_deserializer(source)
    body = inline_hoisted_literals(source[start:end])

    ours = integration_handling()
    print("\n## Settings fields the official web app reads\n")
    print(f"  {'field':40s} {'web app':34s} integration")
    for field in dict.fromkeys(FIELD_LOOKUP.findall(body)):
        kind = classify(source, body, field)
        mine = ours.get(field, "-- not read --")
        # Only flag where we are STRICTER than the official client: it accepts a
        # null the integration would crash on. The reverse (we tolerate a field
        # the app requires) is harmless.
        stricter = "nullable" in kind and "null ok" not in mine and mine != "-- not read --"
        print(f"  {field:40s} {kind:34s} {mine}{'   <-- we are stricter' if stricter else ''}")

    report_write_bodies(source)

    if args.dump:
        print("\n## Raw deserializer\n")
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
