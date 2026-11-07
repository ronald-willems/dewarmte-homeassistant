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

The parsing lives in scripts/webapp_bundle.py (shared with dewarmte-watch.py);
nothing hardcodes dart2js symbol names, which change on every DeWarmte deploy.
Findings are written up in docs/WEBAPP_SCHEMA.md -- update that file (and the
bundle hash it records) when this script reports something new.

Requires no credentials and makes one unauthenticated GET.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import webapp_bundle as wb  # noqa: E402

# Repo-side model, for the comparison table.
SETTINGS_MODEL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "custom_components", "dewarmte", "api", "models", "settings.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", help="read a local main.dart.js instead of downloading")
    parser.add_argument("--save", help="write the downloaded bundle to this path")
    parser.add_argument("--dump", action="store_true", help="print the raw deserializer")
    args = parser.parse_args()

    if args.file:
        bundle = wb.Bundle.from_file(args.file)
        origin = args.file
    else:
        bundle = wb.fetch()
        origin = wb.BUNDLE_URL
        if args.save:
            with open(args.save, "wb") as f:
                f.write(bundle.raw)

    print(f"source:        {origin}")
    print(f"last-modified: {bundle.last_modified}")
    print(f"size:          {bundle.size} bytes")
    print(f"sha256:        {bundle.sha256}")
    print(f"dart2js:       map index `.{bundle.index_method}(0,...)`, map literal `{bundle.literal_ctor}([...])`")

    ours = wb.integration_handling(SETTINGS_MODEL)
    print("\n## Settings fields the official web app reads\n")
    print(f"  {'field':40s} {'web app':34s} integration")
    for field, kind in wb.settings_fields(bundle):
        mine = ours.get(field, "-- not read --")
        # Only flag where we are STRICTER than the official client: it accepts a
        # null the integration would crash on. The reverse (we tolerate a field
        # the app requires) is harmless.
        stricter = "nullable" in kind and "null ok" not in mine and mine != "-- not read --"
        print(f"  {field:40s} {kind:34s} {mine}{'   <-- we are stricter' if stricter else ''}")

    print("\n## Enum vocabularies the app maps settings fields through\n")
    for field, values in wb.enum_values(bundle).items():
        print(f"  {field:40s} {', '.join(values)}")

    print("\n## Write bodies per endpoint (what the app sends)\n")
    for endpoint, fields in wb.write_bodies(bundle).items():
        if "/settings/" in endpoint or "/smart-control/" in endpoint:
            print(f"  {endpoint} -> {', '.join(fields) or '(empty body)'}")

    if args.dump:
        print("\n## Raw deserializer\n")
        print(wb.settings_deserializer(bundle))
    return 0


if __name__ == "__main__":
    sys.exit(main())
