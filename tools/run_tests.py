#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""csvx conformance tests: round-trip + validation over tests/cases and samples.

For every case file we assert:
  1. strict parse succeeds (unless the case is marked lenient),
  2. render -> reparse is exactly equal to the first parse (reversibility),
  3. spot-check assertions defined below for critical cases.
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import csvx  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "tests", "cases")
SAMPLES = os.path.join(ROOT, "samples")

LENIENT = {"ragged.csvx", "comments.csvx"}  # cases parsed in lenient mode


def check_roundtrip(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    name = os.path.basename(path)
    strict = name not in LENIENT
    doc = csvx.parse(text, strict=strict)
    rendered = csvx.render(doc)
    doc2 = csvx.parse(rendered, strict=True)
    if doc2.as_dict() != doc.as_dict():
        return False, ("roundtrip mismatch:\n--- render ---\n%s\n--- orig ---\n%s\n--- reparsed ---\n%s"
                       % (rendered, json.dumps(doc.as_dict(), ensure_ascii=False, indent=1),
                          json.dumps(doc2.as_dict(), ensure_ascii=False, indent=1)))
    return True, None


def spot_checks():
    """Explicit assertions on critical cases (fail loudly on regression)."""
    def parse(name):
        with open(os.path.join(CASES, name), encoding="utf-8") as fh:
            return csvx.parse(fh.read(), strict=True)

    # --- escapes: every escape in the matrix must round-trip literally ---
    doc = parse("escapes.csvx")
    row = doc.rows[0]
    assert row.cells[0].value == "a\\b", row
    assert row.cells[1].value == "a`b", row
    assert row.cells[2].value == "a{{b}}", row
    assert row.cells[3].value == "a[[b]]", row
    assert row.cells[4].value == "a/*b*/", row
    assert row.cells[5].value == "5+", row
    assert row.cells[6].value == "a b ", row            # escaped trailing space
    assert row.cells[7].value == "# tag", row           # escaped leading '#'
    assert row.cells[8].value == "key:value:", row      # escaped type-like text
    assert row.cells[9].value == "a:b:c:", row

    # --- nested JSON code inclusion (brace balancing) ---
    doc = parse("code-nested.csvx")
    assert doc.rows[0].cells[0].code == '{"a": {"b": 2}}', doc.rows[0]
    assert doc.rows[0].cells[1].code == 'highlight: {"color": "yellow"}', doc.rows[0]
    assert doc.rows[1].cells[0].code == '{"s": "a}}b"}', doc.rows[1]  # escaped }}
    assert doc.rows[0].cells[0].value == "x"

    # --- continuation edge cases ---
    doc = parse("continuation-edge.csvx")
    rows = doc.rows
    assert rows[0].cells[0].value == "A\nB\nC", rows[0]
    assert rows[0].cells[1].value == "x\ny", rows[0]
    assert rows[1].cells[0].value == "no", rows[1]
    assert rows[1].cells[1].value == "trail+", rows[1]       # escaped trailing +
    assert rows[1].cells[2].value == "q+\ncont", rows[1]     # quoted field w/ cont
    assert rows[2].cells[0].value == "a\n\nb", rows[2]       # bare + = blank line
    assert rows[3].cells[0].value == "X\nY", rows[3]
    assert rows[3].cells[1].value == "Z", rows[3]            # pending skipped a line

    # --- null vs empty vs quoted-empty ---
    doc = parse("null-vs-empty.csvx")
    assert doc.rows[0].cells[0].value is None, doc.rows[0]
    assert doc.rows[0].cells[1].value == "", doc.rows[0]
    assert doc.rows[0].cells[2].value is None, doc.rows[0]   # :null:
    assert doc.rows[0].cells[3].value == "", doc.rows[0]     # :empty:

    # --- types: custom regex + enum ---
    doc = parse("types.csvx")
    assert doc.rows[0].cells[0].value == "#ff0000", doc.rows[0]
    assert doc.rows[0].cells[1].value == "Mon", doc.rows[0]

    # --- markdown view sanity ---
    md = csvx.to_markdown(doc)
    assert "|" in md and ":" in md

    # --- user example: the reference sample ---
    with open(os.path.join(SAMPLES, "user-example.csvx"), encoding="utf-8") as fh:
        doc = csvx.parse(fh.read(), strict=True)
    assert doc.rows[2].cells[1].formula == "=SUM(B2,B3)", doc.rows[2]
    assert doc.rows[0].cells[1].style == "color:red;", doc.rows[0]
    assert doc.rows[1].cells[2].comment == "Verify please @user", doc.rows[1]
    assert doc.rows[0].cells[1].dtype is None, "cell-level type stays explicit"
    assert doc.column_dtypes()[1] == "int", doc.column_dtypes()


def main():
    passed = failed = 0
    failures = []
    for path in sorted(glob.glob(os.path.join(CASES, "*.csvx"))):
        name = os.path.basename(path)
        try:
            ok, msg = check_roundtrip(path)
        except csvx.CsvxError as e:
            ok, msg = False, "parse error: %s" % e
        if ok:
            passed += 1
            print("PASS  %s" % name)
        else:
            failed += 1
            failures.append(name)
            print("FAIL  %s" % name)
            print("      %s" % str(msg).replace("\n", "\n      "))
    for path in sorted(glob.glob(os.path.join(SAMPLES, "*.csvx"))):
        name = os.path.basename(path)
        try:
            ok, msg = check_roundtrip(path)
        except csvx.CsvxError as e:
            ok, msg = False, "parse error: %s" % e
        if ok:
            passed += 1
            print("PASS  samples/%s" % name)
        else:
            failed += 1
            failures.append("samples/%s" % name)
            print("FAIL  samples/%s" % name)
            print("      %s" % str(msg).replace("\n", "\n      "))

    try:
        spot_checks()
        print("PASS  spot-checks")
        passed += 1
    except AssertionError as e:
        failed += 1
        failures.append("spot-checks")
        print("FAIL  spot-checks: %s" % e)

    print("\n%d passed, %d failed" % (passed, failed))
    if failures:
        print("failed: %s" % ", ".join(failures))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
