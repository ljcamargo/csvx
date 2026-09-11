"""CSVX parser and canonical renderer for the current draft syntax."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from .model import Cell, Document, Sheet

DEFAULTS = {"delimiter": "|", "quote": '"', "continuation": "+",
            "line_comment": "#", "escape": "\\", "formula_language": "ooxml",
            "annotation_format": "yaml"}
TABLE_DEFAULTS = {"header": True, "null_policy": "null", "allow_ragged": False,
                  "default_dtype": "string", "type_propagation": "column"}
TYPE_RE = re.compile(r":([A-Za-z_][\w.-]*)(?:\(([^()]*)\))?:")


class CsvxError(ValueError):
    pass


@dataclass(slots=True)
class RawField:
    text: str
    quoted: bool
    continuation: bool


def _frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if text.startswith("--- "):
        line, _, body = text.partition("\n")
        if not line.endswith(" ---"):
            raise CsvxError("invalid one-line frontmatter")
        data = yaml.safe_load(line[4:-4]) or {}
        if not isinstance(data, dict):
            raise CsvxError("frontmatter must be a mapping")
        return data, body
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        raise CsvxError("unclosed frontmatter")
    data = yaml.safe_load(text[4:end]) or {}
    if not isinstance(data, dict):
        raise CsvxError("frontmatter must be a mapping")
    return data, text[end + 5:]


def _config(frontmatter: dict[str, Any], strict: bool) -> dict[str, Any]:
    conf = dict(DEFAULTS)
    legacy = frontmatter.get("dialect")
    flat = set(DEFAULTS) & set(frontmatter)
    if legacy is not None:
        if flat:
            raise CsvxError("cannot mix deprecated 'dialect' and flat syntax keys")
        if not isinstance(legacy, dict):
            raise CsvxError("legacy dialect must be a mapping")
        csv, csvx = legacy.get("csv", {}), legacy.get("csvx", {})
        if not isinstance(csv, dict) or not isinstance(csvx, dict):
            raise CsvxError("legacy dialect.csv and dialect.csvx must be mappings")
        conf.update({k: csv[k] for k in ("delimiter", "quote") if k in csv})
        conf.update({k: csvx[k] for k in ("continuation", "line_comment", "escape") if k in csvx})
        formulas = {"xlsx": "ooxml", "ods": "openformula", "sheets": "google-sheets"}
        if "formula_dialect" in csvx:
            conf["formula_language"] = formulas.get(csvx["formula_dialect"], csvx["formula_dialect"])
        if "code_format" in csvx:
            conf["annotation_format"] = csvx["code_format"]
    else:
        conf.update({k: frontmatter[k] for k in DEFAULTS if k in frontmatter})
    for key in ("delimiter", "quote", "continuation", "escape"):
        if not isinstance(conf[key], str) or len(conf[key]) != 1:
            raise CsvxError(f"{key} must be one character")
    if conf["quote"] not in {'"', "'"}:
        raise CsvxError("quote must be double or single quote")
    if conf["formula_language"] not in {"ooxml", "openformula", "google-sheets", "none"}:
        raise CsvxError("unknown formula_language")
    if conf["annotation_format"] not in {"yaml", "json"}:
        raise CsvxError("annotation_format must be yaml or json")
    return conf


def _flatten_legacy_frontmatter(frontmatter: dict[str, Any]) -> dict[str, Any]:
    """Return canonical flat frontmatter after _config has validated legacy input."""
    if "dialect" not in frontmatter:
        return frontmatter
    result = dict(frontmatter)
    legacy = result.pop("dialect")
    csv, csvx = legacy.get("csv", {}), legacy.get("csvx", {})
    for key in ("delimiter", "quote"):
        if key in csv:
            result[key] = csv[key]
    for key in ("continuation", "line_comment", "escape"):
        if key in csvx:
            result[key] = csvx[key]
    formulas = {"xlsx": "ooxml", "ods": "openformula", "sheets": "google-sheets"}
    if "formula_dialect" in csvx:
        result["formula_language"] = formulas.get(csvx["formula_dialect"], csvx["formula_dialect"])
    if "code_format" in csvx:
        result["annotation_format"] = csvx["code_format"]
    return result


def _split_fields(line: str, conf: dict[str, Any]) -> list[RawField]:
    delim, quote, marker = conf["delimiter"], conf["quote"], conf["continuation"]
    fields: list[RawField] = []
    i = 0
    while True:
        start = i
        quoted = i < len(line) and line[i] == quote
        if quoted:
            i += 1
            protected = False
            while i < len(line):
                char = line[i]
                if char == "\\":
                    i += 2
                    continue
                if char == "`":
                    protected = not protected
                    i += 1
                    continue
                if char == quote and not protected:
                    if i + 1 < len(line) and line[i + 1] == quote:
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            else:
                raise CsvxError("unterminated wrapped field")
            raw = line[start + 1:i - 1]
            raw = raw.replace(quote * 2, quote)
            tail = ""
            while i < len(line) and line[i] != delim:
                tail += line[i]
                i += 1
            if tail.strip() not in {"", marker}:
                raise CsvxError("content after closing wrapper")
            continuation = tail.strip() == marker
        else:
            while i < len(line) and line[i] != delim:
                i += 1
            raw = line[start:i]
            continuation = raw.rstrip().endswith(marker) and not raw.rstrip().endswith("\\" + marker)
            if continuation:
                raw = raw.rstrip()[:-1]
        fields.append(RawField(raw, quoted, continuation))
        if i >= len(line):
            return fields
        i += 1


def _close(text: str, start: int, close: str) -> int:
    i = start
    while True:
        i = text.find(close, i)
        if i < 0:
            return -1
        if i == 0 or text[i - 1] != "\\":
            return i
        i += 1


def _annotation_close(text: str, start: int) -> int:
    depth, i = 0, start + 2
    while i < len(text) - 1:
        if text[i] == "\\":
            i += 2; continue
        if text[i] == "{": depth += 1
        elif text[i] == "}":
            if depth: depth -= 1
            elif text[i + 1] == "}": return i
        i += 1
    return -1


def _cell(raw: str, quoted: bool, conf: dict[str, Any]) -> Cell:
    value, pos = [], 0
    while pos < len(raw):
        if raw[pos] == "\\" and pos + 1 < len(raw):
            value.append(raw[pos + 1]); pos += 2; continue
        if raw[pos] == "`" or raw.startswith("{{", pos) or raw.startswith("[[", pos) or raw.startswith("/*", pos) or TYPE_RE.match(raw, pos):
            break
        value.append(raw[pos]); pos += 1
    cell = Cell(value="".join(value).rstrip() or None, quoted=quoted)
    while pos < len(raw):
        while pos < len(raw) and raw[pos].isspace(): pos += 1
        if pos >= len(raw): break
        if raw[pos] == "`":
            end = _close(raw, pos + 1, "`")
            if end < 0: raise CsvxError("unclosed formula")
            cell.formula = raw[pos + 1:end].replace("\\`", "`"); pos = end + 1
        elif raw.startswith("{{", pos):
            end = _annotation_close(raw, pos)
            if end < 0: raise CsvxError("unclosed annotation")
            cell.annotation = raw[pos + 2:end].replace("\\}", "}"); pos = end + 2
        elif raw.startswith("[[", pos):
            end = _close(raw, pos + 2, "]]" )
            if end < 0: raise CsvxError("unclosed style")
            cell.styles.append(raw[pos + 2:end].replace("\\]", "]")); pos = end + 2
        elif raw.startswith("/*", pos):
            end = _close(raw, pos + 2, "*/")
            if end < 0: raise CsvxError("unclosed comment")
            cell.comment = raw[pos + 2:end].replace("\\*", "*"); pos = end + 2
        else:
            match = TYPE_RE.match(raw, pos)
            if not match: raise CsvxError(f"unexpected inclusion content near {raw[pos:pos+12]!r}")
            cell.dtype = match.group(1) + (f"({match.group(2)})" if match.group(2) is not None else "")
            pos = match.end()
    if cell.dtype == "null": cell.value = None
    elif cell.dtype == "empty": cell.value = ""
    elif cell.value is None and quoted: cell.value = ""
    return cell


def _parse_sheet(lines: list[str], name: str, table: dict[str, Any], columns: list[dict[str, Any]], conf: dict[str, Any]) -> Sheet:
    active = [line for line in lines if line.strip() and not (conf["line_comment"] and line.lstrip().startswith(conf["line_comment"] + " "))]
    sheet = Sheet(name, table=table, columns=columns)
    if not active: return sheet
    header_enabled = table.get("header", True)
    first = _split_fields(active[0], conf)
    width = len(first) if header_enabled else (table.get("cols") or len(first))
    start = 1 if header_enabled else 0
    if header_enabled:
        if any(x.continuation for x in first): raise CsvxError("header cannot continue")
        sheet.header = [_cell(x.text, x.quoted, conf) for x in first]
    pending: list[int] = []
    slots: list[list[RawField]] = []
    for line in active[start:]:
        fields = _split_fields(line, conf)
        if not pending:
            if len(fields) > width: raise CsvxError(f"row in {name} exceeds width {width}")
            slots = [[field] for field in fields]
            # Missing trailing cells become pending placeholders when a row
            # uses a staircase; later physical lines fill them left-to-right.
            slots.extend([] for _ in range(len(fields), width))
            pending = [i for i, field in enumerate(fields) if field.continuation] + list(range(len(fields), width))
        else:
            if len(fields) > len(pending): raise CsvxError(f"too many continuation fields in {name}")
            old = pending
            for index, field in enumerate(fields):
                slots[old[index]].append(field)
            pending = [old[i] for i, field in enumerate(fields) if field.continuation] + old[len(fields):]
        if not pending:
            if len(slots) != width and not table.get("allow_ragged", False):
                raise CsvxError(f"row in {name} has {len(slots)} fields; expected {width}")
            row = []
            for segment_list in slots:
                first_seg = segment_list[0]
                parts = [x.text for x in segment_list]
                if len(parts) > 1 and not first_seg.quoted and parts[0] == "": parts.pop(0)
                row.append(_cell("\n".join(parts), first_seg.quoted, conf))
            sheet.rows.append(row)
            slots = []
    if pending: raise CsvxError(f"unresolved continuation in {name}")
    return sheet


def parse(text: str, *, strict: bool = True) -> Document:
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    frontmatter, body = _frontmatter(text)
    legacy_frontmatter = "dialect" in frontmatter
    conf = _config(frontmatter, strict)
    frontmatter = _flatten_legacy_frontmatter(frontmatter)
    chunks, current = [], []
    for line in body.split("\n"):
        if line == "---": chunks.append(current); current = []
        else: current.append(line)
    chunks.append(current)
    declarations = frontmatter.get("sheets", []) or []
    if not isinstance(declarations, list): raise CsvxError("sheets must be a list")
    doc = Document(frontmatter=frontmatter)
    if legacy_frontmatter:
        doc.warnings.append("deprecated nested dialect frontmatter was normalized to flat keys")
    for index, chunk in enumerate(chunks):
        override = declarations[index] if index < len(declarations) else {}
        if not isinstance(override, dict): raise CsvxError("sheet entry must be a mapping")
        forbidden = set(DEFAULTS) | {"dialect"}
        if forbidden & set(override): raise CsvxError("syntax settings cannot be overridden per sheet")
        table = {**TABLE_DEFAULTS, **(frontmatter.get("table") or {}), **(override.get("table") or {})}
        columns = override.get("columns", override.get("features", frontmatter.get("columns", frontmatter.get("features", [])))) or []
        doc.sheets.append(_parse_sheet(chunk, override.get("name", f"Sheet{index + 1}"), table, columns, conf))
    return doc


def _escape_value(value: str, conf: dict[str, Any]) -> str:
    """Escape only syntax collisions in a literal value."""
    esc = conf["escape"]
    value = value.replace(esc, esc + esc)
    value = value.replace("`", esc + "`").replace("{{", esc + "{{")
    value = value.replace("[[", esc + "[[").replace("/*", "/" + esc + "*")
    value = TYPE_RE.sub(lambda match: esc + match.group(0), value)
    marker = conf["line_comment"]
    if marker and value.startswith(marker + " "):
        value = esc + value
    return value


def _field(cell: Cell, value: str, conf: dict[str, Any], *, inclusions: bool,
           continuation: bool) -> str:
    text = _escape_value(value, conf)
    if inclusions:
        def add(part: str) -> None:
            nonlocal text
            text += (" " if text else "") + part
        if cell.dtype: add(f":{cell.dtype}:")
        if cell.formula is not None:
            add("`" + cell.formula.replace("`", "\\`") + "`")
        if cell.annotation is not None: add("{{" + cell.annotation + "}}")
        for style in cell.styles: add(f"[[{style}]]")
        if cell.comment is not None: add(f"/*{cell.comment}*/")
    q = conf["quote"]
    empty_string = not text and cell.value == "" and inclusions
    wrapped = (empty_string or text == "---" or text.rstrip().endswith(conf["continuation"]) or
               any(c in text for c in (conf["delimiter"], q)) or text[:1].isspace() or text[-1:].isspace())
    if wrapped:
        protected, out = False, []
        for char in text:
            if char == "`": protected = not protected
            out.append(char if protected or char != q else q + q)
        return q + "".join(out) + q + (conf["continuation"] if continuation else "")
    return text + (conf["continuation"] if continuation else "")


def _render_row(row: list[Cell], conf: dict[str, Any]) -> list[str]:
    segments = [("" if cell.value is None else cell.value).split("\n") for cell in row]
    positions = [0] * len(row)
    pending = list(range(len(row)))
    lines: list[str] = []
    first = True
    while pending:
        fields, next_pending = [], []
        for index in pending:
            cell, part = row[index], segments[index][positions[index]]
            more = positions[index] + 1 < len(segments[index])
            fields.append(_field(cell, part, conf, inclusions=first, continuation=more))
            if more:
                positions[index] += 1
                next_pending.append(index)
        lines.append(conf["delimiter"].join(fields))
        pending, first = next_pending, False
    return lines


def render(document: Document) -> str:
    conf = _config(document.frontmatter, True)
    out: list[str] = []
    if document.frontmatter:
        out.extend(["---", yaml.safe_dump(document.frontmatter, allow_unicode=True, sort_keys=False).rstrip(), "---"])
    for number, sheet in enumerate(document.sheets):
        if number: out.append("---")
        if sheet.header is not None: out.extend(_render_row(sheet.header, conf))
        for row in sheet.rows: out.extend(_render_row(row, conf))
    return "\n".join(out) + "\n"
