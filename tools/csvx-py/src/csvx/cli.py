"""Command-line interface for csvx-py."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .parser import CsvxError, parse, render
from .xlsx import ConversionError, csvx_to_xlsx, xlsx_to_csvx


def _report(report, path: str | None) -> None:
    if path: Path(path).write_text(json.dumps(report.as_dict(), indent=2) + "\n", encoding="utf-8")
    for issue in report.warnings:
        where = "/".join(x for x in (issue.sheet, issue.cell) if x)
        print(f"csvx: warning: {where + ': ' if where else ''}{issue.feature}: {issue.message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="csvx", description="CSVX format tools")
    sub = parser.add_subparsers(dest="command", required=True)
    convert = sub.add_parser("convert", help="convert based on input/output extensions")
    convert.add_argument("input"); convert.add_argument("-o", "--output", required=True)
    convert.add_argument("--strict", action="store_true"); convert.add_argument("--report")
    convert.add_argument("--dimension", choices=["content", "worksheet", "compact", "fidelity"], default="content",
                         help="content trims trailing style-only extent; worksheet preserves reported extent")
    convert.add_argument("--materialize-dimensions", action="store_true")
    check = sub.add_parser("check", help="parse and validate CSVX")
    check.add_argument("input")
    fmt = sub.add_parser("format", help="write canonical CSVX")
    fmt.add_argument("input"); fmt.add_argument("-o", "--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "convert":
            source, target = Path(args.input).suffix.lower(), Path(args.output).suffix.lower()
            options = {"strict": args.strict, "dimension": args.dimension, "materialize_dimensions": args.materialize_dimensions}
            if source == ".xlsx" and target == ".csvx": report = xlsx_to_csvx(args.input, args.output, **options)
            elif source == ".csvx" and target == ".xlsx": report = csvx_to_xlsx(args.input, args.output, **options)
            else: raise ConversionError("supported pairs: .xlsx → .csvx and .csvx → .xlsx")
            _report(report, args.report); return 0
        document = parse(Path(args.input).read_text(encoding="utf-8"), strict=True)
        if args.command == "format": Path(args.output).write_text(render(document), encoding="utf-8")
        else: print(f"OK: {len(document.sheets)} sheet(s)")
        return 0
    except (CsvxError, ConversionError, OSError) as error:
        print(f"csvx: error: {error}", file=sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
