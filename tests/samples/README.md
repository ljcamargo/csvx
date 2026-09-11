# Reviewed XLSX conversion fixtures

This directory contains small real-world XLSX workbooks that have been
reviewed and approved for public release. They are regression fixtures for the
pre-alpha [`csvx-py`](../../tools/csvx-py/) converter, not a claim of complete
XLSX fidelity.

| Fixture | Coverage |
|---|---|
| `untitled.xlsx` | Non-default sheet name, formulas, and a large style-only trailing range |
| `quantum.xlsx` | Two sheets and populated grid ranges |
| `acquire.xlsx` | Dense formulas and a large style-only trailing range |

`converted/` contains the current import (`*.from-xlsx.csvx`), reconstructed
workbook (`*.roundtrip.xlsx`), and JSON reports. The original fixtures are
never overwritten. The converter intentionally trims trailing style-only
extent by default, so reconstructed used ranges can be smaller while content,
sheet names, and formula coordinates remain intact.

To regenerate the artifacts:

```bash
cd tools/csvx-py
for name in untitled quantum acquire; do
  csvx convert "../../tests/samples/$name.xlsx" \
    -o "../../tests/samples/converted/$name.from-xlsx.csvx" \
    --report "../../tests/samples/converted/$name.from-xlsx.report.json"
  csvx convert "../../tests/samples/converted/$name.from-xlsx.csvx" \
    -o "../../tests/samples/converted/$name.roundtrip.xlsx" \
    --report "../../tests/samples/converted/$name.roundtrip.report.json"
done
```
