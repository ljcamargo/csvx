# Generated conversion comparisons

These artifacts are generated from the adjacent real-world XLSX fixtures and
do not overwrite their sources:

```text
<name>.xlsx
  → converted/<name>.from-xlsx.csvx
  → converted/<name>.roundtrip.xlsx
```

The current converter trims trailing style-only worksheet extent by default.
Accordingly, `untitled` and `acquire` reconstruct with smaller reported used
ranges while preserving their meaningful content, sheet names, and formula
locations. Styles are intentionally not converted yet; see each JSON report.
Cached formula values are imported into CSVX when available, but the rebuilt
XLSX requests recalculation rather than writing cached results.
