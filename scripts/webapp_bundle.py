"""Parsers for the DeWarmte web app bundle (mydewarmte.com/main.dart.js).

`mydewarmte.com` is a Flutter app; `main.dart.js` is its compiled, minified
Dart. The symbol names in it (`u0`, `A.md`, `B.K6`) are regenerated on every
DeWarmte deploy, so nothing here hardcodes them. What survives minification is
string literals: JSON field names, URL paths and enum values. Everything below
is built on those, and the two dart2js helpers we do need (the map-index
method and the map-literal constructor) are detected per bundle by frequency.

Used by:
    scripts/extract-webapp-schema.py   the human-readable settings report
    scripts/dewarmte-watch.py          the change-watch snapshot

Nothing in this module runs the bundle; it is read as text only.
"""
from __future__ import annotations

import collections
import hashlib
import re
import urllib.request
from dataclasses import dataclass

BUNDLE_URL = "https://mydewarmte.com/main.dart.js"

# A field only the settings model reads, used to locate its deserializer.
ANCHOR_FIELD = "advanced_boost_mode_control"

HTTP_METHODS = ("POST", "PATCH", "PUT", "DELETE")

# `b="force_cooling_end"` ... `.h(0,b)`: dart2js hoists repeated literals.
HOISTED_LITERAL = re.compile(r'\b([a-z][a-z0-9]?)="([a-z_0-9]+)"')
# A path literal optionally continued with variables: "/v1/x/"+a.a+"/settings/"
PATH_CHAIN = re.compile(r'"(/[a-z0-9/_-]*)"((?:\+[A-Za-z0-9_.$]+\+"/?[a-z0-9/_-]*")*)')
CHAIN_TAIL = re.compile(r'\+[A-Za-z0-9_.$]+\+"(/?[a-z0-9/_-]*)"')
METHOD_LITERAL = re.compile(r'"(%s)"' % "|".join(HTTP_METHODS))
# The innermost call wrapping a lookup, e.g. the `A.bZ(` of `A.bZ(a8.h(0,"x"))`
# or the `A.md(B.K6,` of an enum lookup. The variable itself is stripped first.
CALL_TOKEN = re.compile(r'([A-Za-z0-9_$]{1,4}\.[A-Za-z0-9_$]{1,4})\((?:[A-Za-z0-9_$.]{1,8},)?$')
FIELD_NAME = re.compile(r"[a-z_0-9]+")


@dataclass
class Bundle:
    """One downloaded (or locally read) main.dart.js."""

    raw: bytes
    source: str
    last_modified: str = "unknown"
    etag: str = ""
    index_method: str = ""   # the minified name of Map.[] e.g. "h" (was "i")
    literal_ctor: str = ""   # the minified map-literal helper e.g. "A.P" (was "A.aa")

    @classmethod
    def from_bytes(cls, raw: bytes, last_modified: str = "unknown", etag: str = "") -> "Bundle":
        source = raw.decode("utf-8", errors="replace")
        bundle = cls(raw, source, last_modified, etag)
        bundle.index_method = _most_common(
            r'\.([A-Za-z_$][A-Za-z0-9_$]{0,2})\(0,"[a-z_0-9]+"\)', source, "map index method")
        bundle.literal_ctor = _most_common(
            r'(A\.[A-Za-z0-9_$]{1,3})\(\["[a-z_0-9]+",', source, "map literal constructor")
        return bundle

    @classmethod
    def from_file(cls, path: str) -> "Bundle":
        with open(path, "rb") as f:
            return cls.from_bytes(f.read(), last_modified="n/a (local file)")

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.raw).hexdigest()

    @property
    def size(self) -> int:
        return len(self.raw)

    def lookup(self, field: str | None = None) -> re.Pattern:
        """Regex for `<var>.<index>(0,"field")`, any field or a given one."""
        name = re.escape(field) if field else "[a-z_0-9]+"
        return re.compile(r'\.%s\(0,"(%s)"\)' % (re.escape(self.index_method), name))

    def inline_hoisted_literals(self, body: str) -> str:
        """Undo literal hoisting inside one function body (or line)."""
        for var, literal in HOISTED_LITERAL.findall(body):
            body = body.replace(f".{self.index_method}(0,{var})", f'.{self.index_method}(0,"{literal}")')
        return body


def _most_common(pattern: str, source: str, what: str) -> str:
    counts = collections.Counter(re.findall(pattern, source))
    if not counts:
        raise SystemExit(f"Could not detect the {what}; the bundle changed shape.")
    return counts.most_common(1)[0][0]


# --------------------------------------------------------------------------- fetch

def head(url: str = BUNDLE_URL) -> dict[str, object]:
    """Cheap change check: Last-Modified, ETag and size without the body."""
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=60) as response:
        return {
            "last_modified": response.headers.get("Last-Modified", "unknown"),
            "etag": response.headers.get("ETag", ""),
            "size": int(response.headers.get("Content-Length") or 0),
        }


def fetch(url: str = BUNDLE_URL) -> Bundle:
    with urllib.request.urlopen(url, timeout=120) as response:
        raw = response.read()
        return Bundle.from_bytes(
            raw,
            response.headers.get("Last-Modified", "unknown"),
            response.headers.get("ETag", ""),
        )


# --------------------------------------------------------------------------- paths

def path_templates(source: str) -> collections.Counter:
    """Every path-like string, with variable segments shown as {id}."""
    out: collections.Counter = collections.Counter()
    for match in PATH_CHAIN.finditer(source):
        parts = [match.group(1)] + CHAIN_TAIL.findall(match.group(2))
        out["{id}".join(parts)] += 1
    return out


def api_endpoints(bundle: Bundle) -> list[str]:
    """API paths the app calls (everything under /v1/)."""
    return sorted(t for t in path_templates(bundle.source) if t.startswith("/v1/"))


def app_routes(bundle: Bundle) -> list[str]:
    """In-app screen routes such as /settings/legionella. A new screen is a
    feature signal even when the API model did not change."""
    return sorted(
        t for t in path_templates(bundle.source)
        if not t.startswith("/v1/") and re.fullmatch(r"(/[a-z0-9-]+)+", t)
    )


# --------------------------------------------------------------------------- writes

def write_bodies(bundle: Bundle) -> dict[str, list[str]]:
    """`METHOD /v1/...` -> the JSON keys the app sends to it.

    dart2js emits each request as `<ctor>([k,v,...]), "POST", ..., url`: the
    body literal precedes the method literal and the URL follows it. The body
    is searched only after the previous request's URL, so a request without a
    literal body cannot borrow its neighbour's.
    """
    source = bundle.source
    ctor = bundle.literal_ctor + "(["
    url_re = re.compile(r'"(/v1/[a-z0-9/_-]*)"((?:\+[A-Za-z0-9_.$]+\+"/?[a-z0-9/_-]*")*)')
    out: dict[str, set[str]] = {}
    floor = 0
    for match in METHOD_LITERAL.finditer(source):
        url = url_re.search(source, match.end(), match.end() + 400)
        if not url:
            continue
        template = "{id}".join([url.group(1)] + CHAIN_TAIL.findall(url.group(2)))
        region = source[max(floor, match.start() - 2000): match.start()]
        floor = url.end()
        fields: list[str] = []
        pos = region.rfind(ctor)
        if pos != -1:
            fields = _literal_keys(region, pos + len(ctor))
        out.setdefault(f"{match.group(1)} {template}", set()).update(fields)
    return {key: sorted(values) for key, values in sorted(out.items())}


def _literal_keys(region: str, start: int) -> list[str]:
    """Keys of the map literal whose `[` was just consumed at `start`."""
    depth, in_string, i = 1, False, start
    while i < len(region) and depth:
        char = region[i]
        if char == '"':
            in_string = not in_string
        elif not in_string:
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
        i += 1
    hoisted = dict(HOISTED_LITERAL.findall(region[:start]))
    keys = []
    for item in _split_top_level(region[start: i - 1])[0::2]:
        item = item.strip()
        if len(item) > 1 and item[0] == item[-1] == '"':
            keys.append(item[1:-1])
        elif item in hoisted:
            keys.append(hoisted[item])
    return [k for k in keys if FIELD_NAME.fullmatch(k)]


def _split_top_level(text: str) -> list[str]:
    items, depth, in_string, current = [], 0, False, []
    for char in text:
        if char == '"':
            in_string = not in_string
        elif not in_string:
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif char == "," and depth == 0:
                items.append("".join(current))
                current = []
                continue
        current.append(char)
    items.append("".join(current))
    return items


# --------------------------------------------------------------------------- reads

def field_groups(bundle: Bundle) -> dict[str, list[str]]:
    """JSON fields read by the app, grouped per compiled function.

    dart2js emits one function per line, so a line is a deserializer. Groups
    are named by their alphabetically first field, which stays stable when
    fields are appended. Functions reading a single field are pooled under
    `_single`, since one field is not enough to tell models apart.
    """
    lookup = bundle.lookup()
    needle = f".{bundle.index_method}(0,"
    groups: dict[str, set[str]] = {}
    for line in bundle.source.split("\n"):
        if needle not in line:
            continue
        fields = set(lookup.findall(bundle.inline_hoisted_literals(line)))
        if not fields:
            continue
        name = min(fields) if len(fields) > 1 else "_single"
        groups.setdefault(name, set()).update(fields)
    return {name: sorted(fields) for name, fields in sorted(groups.items())}


def enum_values(bundle: Bundle) -> dict[str, list[str]]:
    """field -> the enum vocabulary the app maps it through.

    An enum field is read as `A.o6(B.L5, m.h(0,"cooling_control_mode"))` where
    `B.L5` is a constant map `new A.bS([B.xM,"forced",B.f3,"thermostat",...])`.
    """
    pattern = re.compile(
        r'(B\.[A-Za-z0-9_$]{1,4}),[A-Za-z0-9_$]{1,3}\.%s\(0,"([a-z_0-9]+)"\)' % re.escape(bundle.index_method))
    needle = f".{bundle.index_method}(0,"
    consts: dict[str, set[str]] = {}
    for line in bundle.source.split("\n"):
        if needle not in line:
            continue
        for const, field in pattern.findall(bundle.inline_hoisted_literals(line)):
            consts.setdefault(field, set()).add(const)
    out: dict[str, list[str]] = {}
    for field, names in sorted(consts.items()):
        values: list[str] = []
        for const in sorted(names):
            definition = re.search(r"\n%s=new A\.[A-Za-z0-9_$]{1,4}\(\[(.*?)\]," % re.escape(const), bundle.source)
            if definition:
                values += [v for v in re.findall(r'"([a-z_0-9]+)"', definition.group(1)) if v not in values]
        if values:
            out[field] = values
    return out


# --------------------------------------------------------------------------- settings model

def settings_deserializer(bundle: Bundle) -> str:
    """The function body that turns the settings JSON into the app's model."""
    anchor = bundle.source.find(f'.{bundle.index_method}(0,"{ANCHOR_FIELD}")')
    if anchor == -1:
        raise SystemExit(f"Could not find a lookup of {ANCHOR_FIELD!r}; the app changed shape.")
    source = bundle.source
    start = source.rfind("\n", 0, anchor) + 1
    end = source.find("return new A.", anchor)
    end = source.find("\n", end) if end != -1 else anchor + 4000
    return bundle.inline_hoisted_literals(source[start:end])


def classify(bundle: Bundle, body: str, field: str) -> str:
    """Describe how the web app casts one field: required, nullable, list, ..."""
    source, index = bundle.source, bundle.index_method
    lookup = body.find(f'"{field}")')
    before, after = body[:lookup], body[lookup:]
    # `x.h(0,"field")==null?null:...` is an explicit null check by the app;
    # newer builds hoist the null into a variable (`a=null` ... `==null?a:`).
    if re.match(r"==null\?(null|[a-z][a-z0-9]?):", after[len(field) + 3:]):
        return "nullable (explicit null check)"

    # Drop the `<var>.h(0,` that immediately precedes the field literal, so the
    # regex sees the cast helper wrapping it.
    stripped = before[: before.rfind(f".{index}(0,")].rstrip("abcdefghijklmnopqrstuvwxyz0123456789_$")
    match = CALL_TOKEN.search(stripped)
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


def settings_fields(bundle: Bundle) -> list[tuple[str, str]]:
    """(field, classification) for every field the settings model reads."""
    body = settings_deserializer(bundle)
    return [(field, classify(bundle, body, field)) for field in dict.fromkeys(bundle.lookup().findall(body))]


def strip_helper(kind: str) -> str:
    """`required bool (A.dc)` -> `required bool`: the helper name is per-build noise."""
    return re.sub(r"\s*\([^)]*\)$", "", kind)


def integration_handling(settings_model_path: str) -> dict[str, str]:
    """How our own from_api_response reads each field.

    Two separate things matter: whether the key must be present (subscript vs
    `.get()`) and whether a null value is tolerated (an `is not None` guard).
    """
    with open(settings_model_path, encoding="utf-8") as f:
        model = f.read()
    handling = {name: "required key" for name in re.findall(r'data\["([a-z_0-9]+)"\]', model)}
    for name in re.findall(r'data\.get\("([a-z_0-9]+)"', model):
        handling[name] = "optional key"
    for name in re.findall(r'data(?:\["([a-z_0-9]+)"\]|\.get\("([a-z_0-9]+)"\)) is not None', model):
        handling["".join(name)] += ", null ok"
    return handling
