# CSVX changelog

All notable changes. Format follows [Keep a Changelog](https://keepachangelog.com/)
and this project uses the spec-version scheme of [SPEC.md](SPEC.md#19-versioning-and-migration).

## [Unreleased]

### Reference tooling

- Added `tools/csvx-py`, the Apache-2.0 pre-alpha Python reference package:
  CSVX parsing/rendering, `csvx check` / `csvx format`, extension-driven XLSX
  conversion, JSON loss reports, and strict rejection of lossy conversion.
- Baseline XLSX conversion preserves sheets and names, values, formula text,
  exposed cached values on import, comments, hyperlinks, and positional gaps.
  It never evaluates formulas; rebuilt workbooks request recalculation.
- XLSX import now trims trailing style-only worksheet extent by default while
  preserving meaningful leading and interior gaps. `--dimension worksheet`
  retains the reported worksheet extent.
- Added reviewed public real-workbook fixtures and non-destructive conversion
  comparisons under `tests/samples/`. Style and formula-cache losses are
  reported once per sheet rather than once per affected cell.
- Removed the superseded top-level legacy Python script and test runner.

### Known limitations

- Styles, merges, validations, conditional formatting, charts, drawings,
  macros, and non-link annotations are not converted yet. Style conversion is
  the next critical fidelity milestone.

## [0.2.0-draft] — Epoch 1, revision 5 (discussion closed)

### Resolved in review rounds 1–2 (recorded in SPEC.md §21.1)

- **CSV-shaped, not CSV-bound** (P1): readability wins over stock-CSV
  compatibility; optional frontmatter and continuation mean whole-document
  drop-in CSV compatibility is not a goal.
- **Quote policy**: wrappers are `"` or `'` only (backtick reserved for
  formulas); wrapper char recognized only at field start (mid-field is
  literal); **quote alternation** inside inclusions; **backtick-protected
  regions** in wrapped fields → formulas stored byte-for-byte, never
  re-quoted.
- **Continuation**: marker lives at the end of the raw field (outside any
  wrapper) → `"5+"` is literal `5+`, no escaping needed; whole-cell only.
- **One-line frontmatter**: flow YAML canonical, JSON accepted (subset).
- **Multi-sheet**: single file, `---` dividers, all config in the main
  `sheets:` list, no per-sheet frontmatter; unnamed sheets → `Sheet1…`.
- **Types**: `:name(params):` (dates: `:date(dd.MM.yyyy):`); special tokens
  `:nan:` `:inf:` `:ninf:` `:na:` `:err:` `:err(code):` `:div0:` `:nref:`
  `:nvalue:` `:nname:` `:nnum:` `:periodic(n):`; no math constants.
- **Table**: types propagate by default, header cells exempt; styles do not
  propagate; `table.rows`/`table.cols` (coordinate-agnostic); literal
  "null" is never null.
- **Frontmatter**: optional; body-only files use the default settings.
  Canonical syntax settings are flat root keys (`delimiter`, `quote`,
  `continuation`, `escape`, `formula_language`, `annotation_format`);
  nested `dialect` input is deprecated during 0.x. When present, unknown
  top-level keys are always allowed and preserved; `{{...}}` content is
  schema-free.
- **Tools**: proto-packages in `tools/` that graduate to standalone repos;
  spec keeps an implementation index.

### Documentation and examples

- Reworked the README and sample guide around small, body-first canonical
  examples; default-only samples omit frontmatter.
- Corrected stale cross-references and quote/formula wording in the spec.

### Deferred

- Q26 — custom date-format validation in strict mode (advisory until the
  XLSX converters define a format-token contract, Epoch 5).

## [0.1.0-draft] — Epoch 1, initial proposal

- First complete proposal: anatomy, frontmatter schema, inclusions (types,
  formulas, annotations, styles, comments), escaping & collision matrix, staircase
  continuation, round-trip guarantees, grammar sketch, security, LLM
  guidance, open questions.
