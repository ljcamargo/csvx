# csvx-py

Pre-alpha Python reference parser, canonical renderer, and XLSX converter for
the [CSVX draft](../../SPEC.md). The distribution name is `csvx-py`; the Python
package and command are both `csvx`.

## Install from this repository

`csvx-py` is not published to PyPI yet. For development or evaluation:

```bash
cd tools/csvx-py
python -m pip install -e ".[dev]"
```

## CLI

```bash
# Validate or canonicalize CSVX
csvx check workbook.csvx
csvx format workbook.csvx -o canonical.csvx

# Convert by file extension and retain a machine-readable loss report
csvx convert workbook.xlsx -o workbook.csvx --report import-report.json
csvx convert workbook.csvx -o rebuilt.xlsx --report export-report.json
```

XLSX import defaults to `--dimension content`: it preserves A1-relative
positions and interior gaps but trims trailing rows or columns that contain
only styles. Use `--dimension worksheet` to preserve the worksheet's reported
extent. `--strict` rejects any conversion that would report a loss.

## Current fidelity boundary

The converter preserves sheet names, cell values, exposed formula text,
comments, hyperlinks (`{{link: ...}}`), positional blank gaps, and exposed
formula caches when importing. It never evaluates formulas. XLSX export asks
the spreadsheet application to recalculate formulas because cached results
cannot reliably be written with the current library.

Styles, merges, data validation, conditional formatting, charts, drawings,
macros, and annotations other than links are not converted yet. Recognized
unsupported features are aggregated in lenient-mode reports and rejected by
strict mode. This pre-alpha converter does not yet detect every possible OOXML
feature, so strict mode is not a complete fidelity guarantee.

Reviewed real-workbook conversion examples and their reports live in
[`tests/samples/`](../../tests/samples/README.md). Run the package checks with:

```bash
python -m ruff check src tests
python -m pytest
```

Code is Apache-2.0; see the repository [license](../../LICENSE.md).
