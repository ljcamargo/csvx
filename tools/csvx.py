#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""csvx — reference parser / serializer for the CSVX open format (draft v0.1.0).

CSVX = CSV + frontmatter (YAML) + cell-level inclusions
       (types, formulas, code, styles, comments) + multi-line continuations.

This is the reference implementation of the draft spec (see SPEC.md).
It has zero hard dependencies: PyYAML is used when available, otherwise a
documented YAML subset parser is used for the frontmatter.

CLI:
    python3 csvx.py parse    file.csvx    # JSON view of the parsed document
    python3 csvx.py render   file.csvx    # canonical round-trip rendering
    python3 csvx.py check    file.csvx    # validate, print issues
    python3 csvx.py md       file.csvx    # render as a markdown table
    python3 csvx.py json     file.csvx    # alias of parse
    python3 csvx.py roundtrip file.csvx   # parse -> render -> parse, compare

Flags: --lenient (best-effort recovery instead of raising), --quiet.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

try:
    import yaml as _yaml
except Exception:  # pragma: no cover
    _yaml = None

VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class CsvxError(Exception):
    """Fatal CSVX error (strict mode)."""


# ---------------------------------------------------------------------------
# Defaults and registries
# ---------------------------------------------------------------------------
DEFAULT_CSV = {"delimiter": "|", "quote": '"', "encoding": "utf-8"}
DEFAULT_CSVX = {
    "continuation": "+", "line_comment": "#", "escape": "\\",
    "formula_dialect": "xlsx", "code_format": "yaml", "style_format": "css",
}
DEFAULT_TABLE = {
    "header": True, "type_propagation": "column", "default_dtype": "string",
    "null_policy": "null", "allow_ragged": False, "blank_row": None,
}

TYPE_ALIASES = {
    "str": "string", "integer": "int", "number": "float", "real": "float",
    "double": "float", "boolean": "bool", "uri": "url",
}

_TYPE_INT = re.compile(r"[+-]?\d+$")
_TYPE_FLOAT = re.compile(r"[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?$")
_TYPE_DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
_TYPE_DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$")
_TYPE_TIME = re.compile(r"\d{2}:\d{2}(:\d{2}(\.\d+)?)?$")
_TYPE_UUID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_TYPE_URL = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://\S+$")
_TYPE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TYPE_BYTES = re.compile(r"^\d+(\.\d+)?\s*(B|KB|MB|GB|TB|KiB|MiB|GiB|TiB)?$", re.I)


def _is_float(v):
    return bool(_TYPE_FLOAT.match(v))


def _is_json(v):
    try:
        json.loads(v)
        return True
    except Exception:
        return False


def _is_yaml(v):
    if _yaml is not None:
        try:
            _yaml.safe_load(v)
            return True
        except Exception:
            return False
    try:
        _parse_mini_yaml(v)
        return True
    except Exception:
        return False


TYPE_VALIDATORS = {
    "string": lambda v: True,
    "text": lambda v: True,
    "int": lambda v: bool(_TYPE_INT.match(v)),
    "float": _is_float,
    "bool": lambda v: v.lower() in ("true", "false", "1", "0", "yes", "no", "y", "n", "on", "off"),
    "date": lambda v: bool(_TYPE_DATE.match(v)),
    "datetime": lambda v: bool(_TYPE_DATETIME.match(v)),
    "time": lambda v: bool(_TYPE_TIME.match(v)),
    "duration": lambda v: True,
    "percent": lambda v: _is_float(v.rstrip("%")),
    "currency": lambda v: True,
    "url": lambda v: bool(_TYPE_URL.match(v)),
    "email": lambda v: bool(_TYPE_EMAIL.match(v)),
    "phone": lambda v: True,
    "uuid": lambda v: bool(_TYPE_UUID.match(v)),
    "json": _is_json,
    "yaml": _is_yaml,
    "bytes": lambda v: bool(_TYPE_BYTES.match(v)),
    "audio": lambda v: v != "",
    "image": lambda v: v != "",
    "video": lambda v: v != "",
    "any": lambda v: True,
    "null": lambda v: v == "",
    "empty": lambda v: v == "",
}

# :name:  — type inclusion marker (name = registry or frontmatter-declared type)
TYPE_RE = re.compile(r":([A-Za-z_][A-Za-z0-9_.\-]*):")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
class Cell:
    __slots__ = ("value", "dtype", "formula", "code", "style", "comment")

    def __init__(self, value=None, dtype=None, formula=None, code=None,
                 style=None, comment=None):
        self.value = value          # str or None (None == null)
        self.dtype = dtype          # explicit cell-level type (canonical name)
        self.formula = formula      # raw formula string
        self.code = code            # structured annotation (yaml/json text)
        self.style = style          # css declarations or named-style refs
        self.comment = comment      # inline comment text

    def as_dict(self):
        d = {}
        if self.value is not None:
            d["value"] = self.value
        if self.dtype:
            d["dtype"] = self.dtype
        if self.formula is not None:
            d["formula"] = self.formula
        if self.code is not None:
            d["code"] = self.code
        if self.style is not None:
            d["style"] = self.style
        if self.comment is not None:
            d["comment"] = self.comment
        return d

    def __repr__(self):
        return "Cell(%s)" % ", ".join("%s=%r" % (k, v) for k, v in self.as_dict().items())


class Row:
    __slots__ = ("cells", "line")

    def __init__(self, cells, line=0):
        self.cells = cells
        self.line = line

    def as_dict(self):
        return [c.as_dict() for c in self.cells]


class Document:
    def __init__(self, frontmatter=None, conf=None, columns=None, types=None,
                 styles=None, header=None, rows=None, warnings=None):
        self.frontmatter = frontmatter or {}
        self.conf = conf or {}
        self.columns = columns or []     # list of dicts (name/dtype/...)
        self.types = types or {}         # custom types
        self.styles = styles or {}       # named styles
        self.header = header             # Row | None
        self.rows = rows or []           # list[Row]
        self.warnings = warnings or []

    def as_dict(self):
        return {
            "frontmatter": self.frontmatter,
            "columns": self.columns,
            "header": self.header.as_dict() if self.header else None,
            "rows": [r.as_dict() for r in self.rows],
        }

    def column_dtypes(self):
        """Effective per-column dtype: frontmatter columns > header > default."""
        out = []
        ncols = len(self.header.cells) if self.header else 0
        named = {}
        for c in self.columns:
            named[c.get("name")] = c.get("dtype")
        for i in range(ncols):
            dtype = None
            if self.header is not None and i < len(self.header.cells):
                dtype = self.header.cells[i].dtype
            if self.conf.get("type_propagation") != "column":
                dtype = None
            out.append(dtype or named.get(
                self.header.cells[i].value if self.header else None) or
                self.conf.get("default_dtype", "string"))
        return out


# ---------------------------------------------------------------------------
# YAML subset: parser (fallback) and canonical emitter
# ---------------------------------------------------------------------------
class _YamlSubsetError(Exception):
    pass


def _yaml_scalar(s):
    s = s.strip()
    if s == "" or s.lower() in ("null", "~", "none"):
        return None
    if s.lower() in ("true", "yes", "on"):
        return True
    if s.lower() in ("false", "no", "off"):
        return False
    if s.startswith('"') and s.endswith('"') and len(s) >= 2:
        body = s[1:-1]
        return (body.replace('\\"', '"').replace("\\\\", "\\")
                .replace("\\n", "\n").replace("\\t", "\t"))
    if s.startswith("'") and s.endswith("'") and len(s) >= 2:
        return s[1:-1].replace("''", "'")
    if re.fullmatch(r"[+-]?\d+", s):
        return int(s)
    if re.fullmatch(r"[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?", s):
        return float(s)
    return s


def _parse_mini_yaml(text):
    """Minimal YAML-subset parser (maps/lists/scalars, 2-space indents).

    Used only when PyYAML is unavailable. Not a full YAML implementation.
    """
    lines = []
    for raw in text.split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        s = raw.strip()
        if " #" in s:
            s = s.split(" #", 1)[0].rstrip()
        if not s:
            continue
        lines.append((len(raw) - len(raw.lstrip(" ")), s))

    pos = [0]

    def peek():
        return lines[pos[0]] if pos[0] < len(lines) else None

    def parse_map(level):
        m = {}
        while pos[0] < len(lines):
            ind, s = lines[pos[0]]
            if ind < level:
                break
            if ind > level:
                raise _YamlSubsetError("bad indent near %r" % s)
            if s.startswith("- "):
                raise _YamlSubsetError("unexpected list item near %r" % s)
            if ": " not in s and not s.endswith(":"):
                raise _YamlSubsetError("expected 'key: value' near %r" % s)
            k, v = s.split(":", 1)
            k, v = k.strip(), v.strip()
            pos[0] += 1
            if v == "":
                nxt = peek()
                if nxt is not None and nxt[0] > ind:
                    if nxt[1].startswith("- "):
                        m[k] = parse_list(nxt[0])
                    else:
                        m[k] = parse_map(nxt[0])
                else:
                    m[k] = None
            else:
                m[k] = _yaml_scalar(v)
        return m

    def parse_list(level):
        lst = []
        while pos[0] < len(lines):
            ind, s = lines[pos[0]]
            if ind < level:
                break
            if ind > level:
                raise _YamlSubsetError("bad indent in list near %r" % s)
            if not s.startswith("- "):
                raise _YamlSubsetError("expected list item near %r" % s)
            rest = s[2:].strip()
            pos[0] += 1
            if rest == "":
                nxt = peek()
                if nxt is not None and nxt[0] > ind:
                    if nxt[1].startswith("- "):
                        lst.append(parse_list(nxt[0]))
                    else:
                        lst.append(parse_map(nxt[0]))
                else:
                    lst.append(None)
            elif ": " in rest or rest.endswith(":"):
                k, v = rest.split(":", 1)
                k, v = k.strip(), v.strip()
                item = {}
                item[k] = _yaml_scalar(v) if v.strip() else None
                nxt = peek()
                if nxt is not None and nxt[0] > ind and not nxt[1].startswith("- "):
                    item.update(parse_map(nxt[0]))
                lst.append(item)
            else:
                lst.append(_yaml_scalar(rest))
        return lst

    if not lines:
        return {}
    return parse_map(0)


def _yaml_needs_quotes(s):
    if s == "":
        return True
    if s != s.strip():
        return True
    if s.lower() in ("null", "~", "none", "true", "false", "yes", "no", "on", "off"):
        return True
    if re.fullmatch(r"[+-]?\d+(\.\d+)?([eE][+-]?\d+)?", s):
        return True
    for ch in "\n\t:#{}[]&*!|>'\"%@`":
        if ch in s:
            return True
    if s.startswith(("- ", "? ", " ")):
        return True
    return False


def _yaml_quote(s):
    return '"' + (s.replace("\\", "\\\\").replace('"', '\\"')
                  .replace("\n", "\\n").replace("\t", "\\t")) + '"'


def _emit_yaml(obj, ind, lines):
    pad = "  " * ind

    def scalar(v):
        if v is None:
            return "null"
        if v is True:
            return "true"
        if v is False:
            return "false"
        if isinstance(v, (int, float)):
            return repr(v)
        s = str(v)
        return _yaml_quote(s) if _yaml_needs_quotes(s) else s

    if isinstance(obj, dict):
        if not obj:
            lines.append(pad + "{}")
            return
        for k, v in obj.items():
            ks = _yaml_quote(k) if _yaml_needs_quotes(k) else k
            if isinstance(v, dict):
                if not v:
                    lines.append("%s%s: {}" % (pad, ks))
                else:
                    lines.append("%s%s:" % (pad, ks))
                    _emit_yaml(v, ind + 1, lines)
            elif isinstance(v, list):
                lines.append("%s%s:" % (pad, ks))
                _emit_yaml(v, ind + 1, lines)
            else:
                lines.append("%s%s: %s" % (pad, ks, scalar(v)))
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                if not item:
                    lines.append(pad + "- {}")
                    continue
                first = True
                for k, v in item.items():
                    ks = _yaml_quote(k) if _yaml_needs_quotes(k) else k
                    if first:
                        lines.append("%s- %s: %s" % (pad, ks, scalar(v)))
                        first = False
                    elif isinstance(v, dict):
                        lines.append("%s  %s:" % (pad, ks))
                        _emit_yaml(v, ind + 2, lines)
                    elif isinstance(v, list):
                        lines.append("%s  %s:" % (pad, ks))
                        _emit_yaml(v, ind + 2, lines)
                    else:
                        lines.append("%s  %s: %s" % (pad, ks, scalar(v)))
            elif isinstance(item, list):
                lines.append(pad + "-")
                _emit_yaml(item, ind + 1, lines)
            else:
                lines.append("%s- %s" % (pad, scalar(item)))
    else:
        lines.append(pad + scalar(obj))


def emit_yaml(obj):
    lines = []
    _emit_yaml(obj, 0, lines)
    return "\n".join(lines) + "\n"


def parse_frontmatter_yaml(text):
    if _yaml is not None:
        try:
            return _yaml.safe_load(text)
        except Exception as e:
            raise CsvxError("frontmatter is not valid YAML: %s" % e)
    try:
        return _parse_mini_yaml(text)
    except _YamlSubsetError as e:
        raise CsvxError("frontmatter YAML subset parse failed: %s "
                        "(install PyYAML for full YAML support)" % e)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_config(frontmatter, strict=True):
    conf = dict(DEFAULT_CSV)
    conf.update(DEFAULT_CSVX)
    conf.update(DEFAULT_TABLE)
    fm_ok = isinstance(frontmatter, dict)
    if not fm_ok:
        raise CsvxError("frontmatter must be a YAML mapping at the top level")

    known_top = {"version", "dialect", "table", "columns", "features",
                 "types", "styles", "meta"}
    for k in frontmatter:
        if k not in known_top and strict:
            raise CsvxError("unknown frontmatter key %r (strict mode); "
                            "known: %s" % (k, ", ".join(sorted(known_top))))

    version = frontmatter.get("version")
    if version is not None and not re.fullmatch(r"\d+\.\d+\.\d+", str(version)):
        raise CsvxError("frontmatter 'version' must look like 0.1.0, got %r" % version)

    if "columns" in frontmatter and "features" in frontmatter:
        raise CsvxError("use either 'columns' or 'features', not both")

    dialect = frontmatter.get("dialect") or {}
    if not isinstance(dialect, dict):
        raise CsvxError("'dialect' must be a mapping")
    csvc = dialect.get("csv") or {}
    csvx = dialect.get("csvx") or {}
    if not isinstance(csvc, dict) or not isinstance(csvx, dict):
        raise CsvxError("'dialect.csv' and 'dialect.csvx' must be mappings")

    for key in ("delimiter", "quote"):
        if key in csvc:
            v = csvc[key]
            if not isinstance(v, str) or len(v) != 1:
                raise CsvxError("dialect.csv.%s must be a single character" % key)
            conf[key] = v
    if conf["quote"] == conf["delimiter"]:
        raise CsvxError("quote and delimiter must differ")
    if csvc.get("encoding"):
        conf["encoding"] = str(csvc["encoding"])

    if "continuation" in csvx:
        v = csvx["continuation"]
        if not isinstance(v, str) or len(v) != 1:
            raise CsvxError("dialect.csvx.continuation must be a single character")
        conf["continuation"] = v
    if "escape" in csvx:
        v = csvx["escape"]
        if not isinstance(v, str) or len(v) != 1:
            raise CsvxError("dialect.csvx.escape must be a single character")
        conf["escape"] = v
    if "line_comment" in csvx:
        v = csvx["line_comment"]
        if v is not None and (not isinstance(v, str) or len(v) != 1):
            raise CsvxError("dialect.csvx.line_comment must be one char or null")
        conf["line_comment"] = v

    if "formula_dialect" in csvx:
        v = str(csvx["formula_dialect"])
        if v not in ("xlsx", "sheets", "ods", "none"):
            raise CsvxError("dialect.csvx.formula_dialect must be "
                            "xlsx|sheets|ods|none")
        conf["formula_dialect"] = v
    if "code_format" in csvx:
        v = str(csvx["code_format"])
        if v not in ("yaml", "json"):
            raise CsvxError("dialect.csvx.code_format must be yaml|json")
        conf["code_format"] = v
    if "style_format" in csvx:
        v = str(csvx["style_format"])
        if v != "css":
            raise CsvxError("dialect.csvx.style_format must be css")
        conf["style_format"] = v

    table = frontmatter.get("table") or {}
    if not isinstance(table, dict):
        raise CsvxError("'table' must be a mapping")
    if "header" in table:
        conf["header"] = bool(table["header"])
    if "type_propagation" in table:
        v = str(table["type_propagation"])
        if v not in ("column", "none"):
            raise CsvxError("table.type_propagation must be column|none")
        conf["type_propagation"] = v
    if "default_dtype" in table:
        conf["default_dtype"] = str(table["default_dtype"])
    if "null_policy" in table:
        v = str(table["null_policy"])
        if v not in ("null", "string"):
            raise CsvxError("table.null_policy must be null|string")
        conf["null_policy"] = v
    if "allow_ragged" in table:
        conf["allow_ragged"] = bool(table["allow_ragged"])
    if "blank_row" in table:
        v = table["blank_row"]
        if v is not None and (not isinstance(v, str) or len(v) != 1):
            raise CsvxError("table.blank_row must be one char or null")
        conf["blank_row"] = v

    columns = frontmatter.get("columns", frontmatter.get("features")) or []
    if not isinstance(columns, list):
        raise CsvxError("'columns'/'features' must be a list")
    types = frontmatter.get("types") or {}
    if not isinstance(types, dict):
        raise CsvxError("'types' must be a mapping")
    styles = frontmatter.get("styles") or {}
    if not isinstance(styles, dict):
        raise CsvxError("'styles' must be a mapping")

    known = set(TYPE_VALIDATORS) | set(TYPE_ALIASES) | set(types)
    conf["_known_types"] = known
    return conf, columns, types, styles


# ---------------------------------------------------------------------------
# Field tokenizer (CSV layer) and continuation split
# ---------------------------------------------------------------------------
def _tokenize_line(line, conf, strict):
    """Split one physical line into (text, was_quoted) fields.

    Implements RFC 4180 quoting with doubled-quote escapes and enforces the
    CSVX restriction that fields must not contain literal newlines.
    """
    delim = conf["delimiter"]
    q = conf["quote"]
    fields = []
    buf = []
    i, n = 0, len(line)
    in_q = False
    field_quoted = False
    field_started = False
    while i < n:
        c = line[i]
        if in_q:
            if c == q:
                if i + 1 < n and line[i + 1] == q:
                    buf.append(q)
                    i += 2
                    continue
                in_q = False
                i += 1
                continue
            buf.append(c)
            i += 1
            continue
        if c == q and not field_started:
            in_q = True
            field_quoted = True
            field_started = True
            i += 1
            continue
        if c == delim:
            fields.append(("".join(buf), field_quoted))
            buf = []
            field_quoted = False
            field_started = False
            i += 1
            continue
        if c == q and field_started:
            if strict:
                raise CsvxError("quote character inside an unquoted field")
            buf.append(c)
            i += 1
            continue
        if not field_started and c in " \t":
            buf.append(c)
            i += 1
            continue
        buf.append(c)
        field_started = True
        i += 1
    if in_q:
        if strict:
            raise CsvxError("unterminated quoted field")
        fields.append(("".join(buf), field_quoted))
    else:
        fields.append(("".join(buf), field_quoted))
    return fields


def _rstrip_unescaped(text, conf):
    """Strip trailing spaces/tabs that are not backslash-escaped."""
    esc = conf["escape"]
    i = len(text)
    while i > 0 and text[i - 1] in " \t":
        bs = 0
        j = i - 2
        while j >= 0 and text[j] == esc:
            bs += 1
            j -= 1
        if bs % 2 == 1:  # escaped whitespace: stop
            break
        i -= 1
    return text[:i]


def _split_continuation(field, conf, strict):
    """Detect the trailing continuation marker.

    Marker = last non-space char equal to conf['continuation'] with an even
    number of preceding escape chars. Applies equally to quoted and unquoted
    fields (the marker sits inside the quotes for quoted fields).
    Returns (content_without_marker, is_continuation).
    """
    marker = conf["continuation"]
    esc = conf["escape"]
    text = field
    i = len(text) - 1
    while i >= 0 and text[i] in " \t":
        i -= 1
    if i >= 0 and text[i] == marker:
        bs = 0
        j = i - 1
        while j >= 0 and text[j] == esc:
            bs += 1
            j -= 1
        if bs % 2 == 0:
            return text[:i], True
    return text, False


def _unescape(text, conf):
    esc = conf["escape"]
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == esc:
            if i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            raise CsvxError("dangling escape character at end of field")
        out.append(c)
        i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Inclusion regions
# ---------------------------------------------------------------------------
def _find_close_plain(text, start, close, name, strict):
    """Find the first unescaped occurrence of `close` from start."""
    esc = "\\"
    i = text.find(close, start)
    while i != -1:
        bs = 0
        j = i - 1
        while j >= 0 and text[j] == esc:
            bs += 1
            j -= 1
        if bs % 2 == 0:
            return i
        i = text.find(close, i + 1)
    if strict:
        raise CsvxError("unclosed %s inclusion" % name)
    return -1


def _unescape_region(text, specials, conf):
    """Unescape inside formula/code/style/comment regions.

    specials: set of chars that may be escaped with the escape char.
    Other backslash sequences are preserved verbatim (e.g. regex \d).
    """
    esc = conf["escape"]
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == esc and i + 1 < n and text[i + 1] in specials:
            out.append(text[i + 1])
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _code_balance_ok(content):
    """True if content's braces balance (after removing \{ \} \\ escapes)."""
    depth = 0
    i, n = 0, len(content)
    while i < n:
        c = content[i]
        if c == "\\":
            if i + 1 < n and content[i + 1] in "{}":
                i += 2
                continue
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return depth == 0


def _rest_looks_like_inclusions(rest):
    r = rest.strip()
    if not r:
        return True
    return (r.startswith("`") or r.startswith("{{") or r.startswith("[[")
            or r.startswith("/*") or bool(TYPE_RE.match(r)))


def _find_code_close(text, start, strict):
    """Locate the `}}` that closes a {{...}} code inclusion.

    Strategy: try every `}}` occurrence left to right; accept the first one
    whose content is brace-balanced (after escapes) and whose remainder can
    itself continue as inclusions. This resolves the ambiguity of nested
    JSON/YAML braces, e.g.  {{ {"a": {"b": 2}} }}
    """
    i = start + 2
    j = text.find("}}", i)
    while j != -1:
        content = text[i:j]
        if _code_balance_ok(content) and _rest_looks_like_inclusions(text[j + 2:]):
            return j, _unescape_region(content, "{}", {"escape": "\\"})
        j = text.find("}}", j + 2)
    if strict:
        raise CsvxError("unclosed or unbalanced {{...}} code inclusion")
    return -1, None


def parse_field(text, conf, strict=True, known=None):
    """Parse one assembled field (value + inclusions) into a Cell."""
    known = known if known is not None else set(TYPE_VALIDATORS) | set(TYPE_ALIASES)
    value_chars = []
    i, n = 0, len(text)
    first_marker = None
    while i < n:
        c = text[i]
        if c == conf["escape"]:
            if i + 1 < n:
                value_chars.append(text[i + 1])
                i += 2
                continue
            if strict:
                raise CsvxError("dangling escape character in field")
            break
        m = TYPE_RE.match(text, i)
        if m is not None:
            name = m.group(1)
            canon = TYPE_ALIASES.get(name, name)
            if canon in known:
                first_marker = (i, "type")
                break
            if strict:
                raise CsvxError("unknown type %r (declare it in frontmatter "
                                "'types' or escape it \\:name:)" % name)
            value_chars.append(c)
            i += 1
            continue
        if c == "`" or text.startswith("{{", i) or text.startswith("[[", i) \
                or text.startswith("/*", i):
            first_marker = (i, "inclusion")
            break
        value_chars.append(c)
        i += 1

    if first_marker is None:
        return Cell(value=_unescape("".join(value_chars), conf))

    value_raw = "".join(value_chars)
    value_raw = _rstrip_unescaped(value_raw, conf)
    value = _unescape(value_raw, conf)

    cell = Cell(value=value)
    i = first_marker[0]
    while i < n:
        if text[i] in " \t":
            i += 1
            continue
        c = text[i]
        if c == "`":
            j = _find_close_plain(text, i + 1, "`", "formula", strict)
            if j < 0:
                cell.value = (cell.value or "") + text[i + 1:]
                break
            cell.formula = _unescape_region(text[i + 1:j], "`", conf)
            i = j + 1
        elif text.startswith("{{", i):
            j, content = _find_code_close(text, i, strict)
            if j < 0:
                cell.value = (cell.value or "") + text[i:]
                break
            cell.code = content
            i = j + 2
        elif text.startswith("[[", i):
            j = _find_close_plain(text, i + 2, "]]", "style", strict)
            if j < 0:
                cell.value = (cell.value or "") + text[i:]
                break
            cell.style = _unescape_region(text[i + 2:j], "]", conf)
            i = j + 2
        elif text.startswith("/*", i):
            j = _find_close_plain(text, i + 2, "*/", "comment", strict)
            if j < 0:
                cell.value = (cell.value or "") + text[i:]
                break
            cell.comment = _unescape_region(text[i + 2:j], "*", conf)
            i = j + 2
        else:
            m = TYPE_RE.match(text, i)
            if m is not None:
                name = m.group(1)
                canon = TYPE_ALIASES.get(name, name)
                if canon not in known:
                    if strict:
                        raise CsvxError("unknown type %r" % name)
                    cell.value = (cell.value or "") + m.group(0)
                    i = m.end()
                    continue
                cell.dtype = canon
                i = m.end()
                continue
            if strict:
                raise CsvxError("unexpected token %r after inclusions "
                                "(escape literal markers with \\)" % text[i:i + 12])
            while i < n and text[i] not in " \t":
                i += 1
    return cell


# ---------------------------------------------------------------------------
# Document parsing
# ---------------------------------------------------------------------------
def _split_frontmatter(text, strict):
    if not text.startswith("---\n"):
        return None, text
    lines = text.split("\n")
    for idx in range(1, len(lines)):
        if lines[idx] == "---":
            return "\n".join(lines[1:idx]), "\n".join(lines[idx + 1:])
    if strict:
        raise CsvxError("unclosed frontmatter (missing closing '---')")
    return None, text


def _blank_line(line):
    return line.strip() == ""


def _comment_line(line, conf):
    lc = conf.get("line_comment")
    if not lc:
        return False
    s = line.lstrip(" \t")
    return s.startswith(lc) and (len(s) == 1 or s[1] in " \t")


def _apply_null_policy(cell, was_quoted, conf):
    if cell.dtype == "null":
        cell.value = None
        return
    if cell.dtype == "empty":
        cell.value = ""
        return
    if cell.value == "" and not was_quoted and not cell.formula \
            and not cell.code and not cell.style and not cell.comment:
        if conf["null_policy"] == "null":
            cell.value = None


def parse(text, strict=True):
    """Parse a full CSVX document. Raises CsvxError in strict mode."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("\ufeff"):
        text = text[1:]
    fm_text, body = _split_frontmatter(text, strict)
    frontmatter = {}
    if fm_text is not None and fm_text.strip():
        frontmatter = parse_frontmatter_yaml(fm_text)
        if not isinstance(frontmatter, dict):
            raise CsvxError("frontmatter must be a YAML mapping")
    conf, columns, types, styles = load_config(frontmatter, strict)
    known = conf["_known_types"]
    doc = Document(frontmatter=frontmatter, conf=conf, columns=columns,
                   types=types, styles=styles)

    lines = body.split("\n")
    rows = []
    current = []          # list of dicts {segments:[...]}
    pending = []          # open (continued) fields, in order
    row_line = 0

    def finalize():
        nonlocal current
        cells = []
        for slot in current:
            segs = slot["segs"]
            quoted0 = slot["quoted"]
            # An empty UNQUOTED first segment is a placeholder for a
            # continued cell that starts on a later line (e.g. `Entry A|+`);
            # it contributes no newline. A QUOTED empty first segment
            # ("+") is a genuine leading newline.
            if len(segs) > 1 and segs[0] == "" and not quoted0:
                segs = segs[1:]
            raw = "\n".join(segs)
            cell = parse_field(raw, conf, strict, known)
            _apply_null_policy(cell, quoted0, conf)
            cells.append(cell)
        rows.append(Row(cells, row_line))
        current = []

    for ln, line in enumerate(lines, start=1):
        if _blank_line(line):
            continue
        if _comment_line(line, conf):
            continue
        fields = _tokenize_line(line, conf, strict)
        # blank-row marker
        if conf["blank_row"] is not None and not pending \
                and len(fields) == 1 and fields[0][0] == conf["blank_row"] \
                and not fields[0][1]:
            rows.append(Row(None, ln))  # expanded once the width is known
            continue
        if not pending:
            row_line = ln
        # fill pending fields first, then open new ones
        fi = 0
        new_pending = []
        for slot in pending:
            if fi >= len(fields):
                new_pending.append(slot)
                continue
            content, was_quoted = fields[fi]
            fi += 1
            content, cont = _split_continuation(content, conf, strict)
            slot["segs"].append(content)
            if cont:
                new_pending.append(slot)
        while fi < len(fields):
            content, was_quoted = fields[fi]
            fi += 1
            content, cont = _split_continuation(content, conf, strict)
            slot = {"segs": [content], "quoted": was_quoted}
            current.append(slot)
            if cont:
                new_pending.append(slot)
        pending = new_pending
        if not pending:
            finalize()

    if pending:
        if strict:
            raise CsvxError("row ends with unresolved continuation (line %d)"
                            % row_line)
        finalize()

    # header / ragged handling
    if conf["header"] and rows:
        doc.header = rows.pop(0)
    ncols = len(doc.header.cells) if doc.header else (
        len(columns) if columns else None)
    fixed = []
    for row in rows:
        if row.cells is None:
            row.cells = [Cell(value=None) for _ in range(ncols or 1)]
            fixed.append(row)
            continue
        if ncols is not None and len(row.cells) != ncols:
            msg = "row at line %d has %d fields, expected %d" % (
                row.line, len(row.cells), ncols)
            if not conf["allow_ragged"] and strict:
                raise CsvxError(msg)
            doc.warnings.append(msg)
            if len(row.cells) > ncols:
                row.cells = row.cells[:ncols]
            else:
                row.cells = row.cells + [Cell(value=None)
                                         for _ in range(ncols - len(row.cells))]
        fixed.append(row)
    doc.rows = fixed

    # custom type registration + validation
    for name, spec in types.items():
        if isinstance(spec, dict) and "enum" in spec and isinstance(spec["enum"], list):
            pass
        elif isinstance(spec, str):
            try:
                re.compile(spec)
            except re.error as e:
                raise CsvxError("custom type %r has invalid regex: %s" % (name, e))
        else:
            raise CsvxError("custom type %r must be a regex string or {enum: [...]}"
                            % name)
    validate(doc, strict)
    return doc


def _cell_effective_dtype(cell, col_dtype):
    if cell.dtype:
        return cell.dtype
    return col_dtype or "string"


def validate(doc, strict=True):
    """Return list of issues; raise on first issue in strict mode."""
    issues = []
    conf = doc.conf
    col_dtypes = doc.column_dtypes()
    for row in doc.rows:
        for idx, cell in enumerate(row.cells):
            dtype = _cell_effective_dtype(cell,
                                          col_dtypes[idx] if idx < len(col_dtypes) else None)
            if cell.value in (None, ""):
                continue
            canon = TYPE_ALIASES.get(dtype, dtype)
            if canon in doc.types:
                spec = doc.types[canon]
                ok = False
                if isinstance(spec, dict) and "enum" in spec:
                    ok = cell.value in spec["enum"]
                else:
                    ok = re.fullmatch(spec, cell.value) is not None
                if not ok:
                    issues.append("cell at line %d, col %d: value %r does not "
                                  "match custom type %r" % (row.line, idx + 1,
                                                            cell.value, canon))
            elif canon in TYPE_VALIDATORS:
                if not TYPE_VALIDATORS[canon](cell.value):
                    issues.append("cell at line %d, col %d: %r is not a valid "
                                  "%s" % (row.line, idx + 1, cell.value, canon))
            elif canon not in conf["_known_types"]:
                issues.append("cell at line %d, col %d: unknown type %r"
                              % (row.line, idx + 1, canon))
    if strict and issues:
        raise CsvxError(issues[0])
    return issues


# ---------------------------------------------------------------------------
# Rendering (canonical)
# ---------------------------------------------------------------------------
def _escape_value(text, conf, trailing_context):
    """Escape value text so it round-trips.

    trailing_context: True when the value is followed by an inclusion or a
    continuation marker (trailing spaces must then be escaped).
    """
    esc = conf["escape"]
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == esc:
            out.append(esc * 2)
            i += 1
            continue
        m = TYPE_RE.match(text, i)
        if m is not None:
            out.append(esc + m.group(0))
            i = m.end()
            continue
        if c == "`" or text.startswith("{{", i) or text.startswith("[[", i) \
                or text.startswith("/*", i):
            out.append(esc + c)
            i += 1
            continue
        out.append(c)
        i += 1
    if trailing_context:
        j = len(out)
        while j > 0 and out[j - 1] in (" ", "\t"):
            j -= 1
        for k in range(j, len(out)):
            out[k] = esc + out[k]
    return "".join(out)


def _escape_region(text, specials, conf):
    esc = conf["escape"]
    out = []
    for c in text:
        if c in specials or c == esc:
            out.append(esc + c)
        else:
            out.append(c)
    return "".join(out)


def _needs_quoting(text, conf):
    delim = conf["delimiter"]
    q = conf["quote"]
    if not text:
        return True
    if text[0] in " \t" or text[-1] in " \t":
        return True
    return any(ch in text for ch in (delim, q, "\n", "\r"))


def _quote_field(text, conf):
    q = conf["quote"]
    return q + text.replace(q, q * 2) + q


def render_cell_segments(cell, conf):
    """Canonical segments (without continuation markers) for one cell.

    Inclusions are attached to the first segment; the value is split on \n.
    """
    value = cell.value
    if value is None:
        value = ""
    segs = value.split("\n")
    first = _escape_value(segs[0], conf,
                          trailing_context=len(segs) > 1
                          or cell.dtype or cell.formula is not None
                          or cell.code is not None or cell.style is not None
                          or cell.comment is not None)
    if cell.dtype:
        first += " :%s:" % cell.dtype
    if cell.formula is not None:
        first += " `%s`" % _escape_region(cell.formula, "`", conf)
    if cell.code is not None:
        first += " {{%s}}" % _escape_region(cell.code, "{}", conf)
    if cell.style is not None:
        first += " [[%s]]" % _escape_region(cell.style, "]", conf)
    if cell.comment is not None:
        first += " /*%s*/" % _escape_region(cell.comment, "*", conf)
    segs[0] = first
    for k in range(1, len(segs)):
        segs[k] = _escape_value(segs[k], conf, trailing_context=False)
    if cell.value is None:
        if conf["null_policy"] == "string" and not cell.dtype:
            segs = [":null:"]
        elif not cell.dtype:
            segs = [""]
    elif cell.value == "":
        segs = ['""']
    return segs


def _render_field(field_text, conf):
    if field_text == "":
        return ""
    if _needs_quoting(field_text, conf):
        return _quote_field(field_text, conf)
    return field_text


def render_row(row, conf):
    """Canonical rendering of one row, using staircase continuation lines."""
    seg_lists = [render_cell_segments(c, conf) for c in row.cells]
    n = max(len(s) for s in seg_lists) if seg_lists else 0
    marker = conf["continuation"]
    lines = []
    for k in range(n):
        fields = []
        for segs in seg_lists:
            if k < len(segs):
                text = segs[k]
                if k + 1 < len(segs):
                    if _needs_quoting(text, conf):
                        # continuation marker goes INSIDE the quotes
                        text = _quote_field(text + marker, conf)
                    else:
                        text = _render_field(text, conf) + marker
                else:
                    text = _render_field(text, conf)
                fields.append(text)
        line = conf["delimiter"].join(fields)
        if fields and fields[0].startswith(conf["line_comment"] or "\x00") \
                and (len(fields[0]) == 1 or fields[0][1] in " \t"):
            line = conf["escape"] + line
        lines.append(line)
    return lines


def render(doc):
    out = []
    if doc.frontmatter:
        out.append("---")
        out.append(emit_yaml(doc.frontmatter).rstrip("\n"))
        out.append("---")
    rows = ([doc.header] if doc.header else []) + doc.rows
    for row in rows:
        if all(c.value is None and not c.dtype and not c.formula
               and not c.code and not c.style and not c.comment
               for c in row.cells):
            marker = doc.conf.get("blank_row")
            if marker:
                out.append(marker)
            elif len(row.cells) == 1:
                out.append("")  # lossy for single-column all-null rows; see SPEC
            else:
                out.append(doc.conf["delimiter"] * (len(row.cells) - 1))
            continue
        out.extend(render_row(row, doc.conf))
    return "\n".join(out) + ("\n" if out else "")


# ---------------------------------------------------------------------------
# Markdown view (LLM/human friendly)
# ---------------------------------------------------------------------------
def to_markdown(doc):
    def esc(s):
        return (s.replace("\\", "\\\\").replace("|", "\\|")
                .replace("\n", "<br>"))

    def cell_md(cell, dtype=None):
        parts = []
        if cell.value is not None and cell.value != "":
            parts.append(esc(cell.value))
        elif cell.value == "":
            parts.append('""')
        if cell.dtype or dtype:
            parts.append(":%s:" % (cell.dtype or dtype))
        if cell.formula is not None:
            parts.append("`%s`" % esc(cell.formula))
        if cell.style is not None:
            parts.append("[[%s]]" % esc(cell.style))
        if cell.comment is not None:
            parts.append("/*%s*/" % esc(cell.comment))
        return " ".join(parts)

    col_dtypes = doc.column_dtypes()
    if doc.header:
        head = [cell_md(c) for c in doc.header.cells]
    else:
        head = [c.get("name", "col%d" % (i + 1)) for i, c in enumerate(doc.columns)]
        head = [h if h else "col%d" % (i + 1) for i, h in enumerate(head)]
    out = ["| " + " | ".join(head) + " |",
           "|" + "|".join(["---"] * len(head)) + "|"]
    for row in doc.rows:
        cells = []
        for i, c in enumerate(row.cells):
            dt = col_dtypes[i] if i < len(col_dtypes) else None
            cells.append(cell_md(c, dt))
        while len(cells) < len(head):
            cells.append("")
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="csvx", description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=["parse", "render", "check", "md",
                                        "json", "roundtrip"])
    ap.add_argument("file")
    ap.add_argument("--lenient", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    text = _load(args.file)
    try:
        doc = parse(text, strict=not args.lenient)
    except CsvxError as e:
        print("csvx: error: %s" % e, file=sys.stderr)
        return 2

    if args.command in ("parse", "json"):
        print(json.dumps(doc.as_dict(), ensure_ascii=False, indent=2))
    elif args.command == "render":
        sys.stdout.write(render(doc))
    elif args.command == "check":
        issues = validate(doc, strict=False)
        for w in doc.warnings:
            print("warning: %s" % w)
        for msg in issues:
            print("issue: %s" % msg)
        if not issues and not doc.warnings:
            print("OK: %d rows, %d columns" % (
                len(doc.rows),
                len(doc.header.cells) if doc.header else 0))
        return 1 if issues else 0
    elif args.command == "md":
        print(to_markdown(doc))
    elif args.command == "roundtrip":
        r1 = render(doc)
        doc2 = parse(r1, strict=True)
        if doc2.as_dict() == doc.as_dict():
            print("roundtrip OK (%d bytes)" % len(r1.encode("utf-8")))
        else:
            print("roundtrip MISMATCH", file=sys.stderr)
            print("--- canonical render ---", file=sys.stderr)
            print(r1, file=sys.stderr)
            print("--- original ---", file=sys.stderr)
            print(json.dumps(doc.as_dict(), ensure_ascii=False, indent=2,
                             default=str), file=sys.stderr)
            print("--- reparsed ---", file=sys.stderr)
            print(json.dumps(doc2.as_dict(), ensure_ascii=False, indent=2,
                             default=str), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
