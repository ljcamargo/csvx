# CSVX changelog

All notable changes. Format follows [Keep a Changelog](https://keepachangelog.com/)
and this project uses the spec-version scheme of [SPEC.md](SPEC.md#19-versioning-and-migration).

## [0.2.0-draft] — Epoch 1, revision 3 (discussion closed)

### Resolved in review rounds 1–2 (recorded in SPEC.md §21.1)

- **CSV-shaped, not CSV-bound** (P1): readability wins over stock-CSV
  compatibility; the enforced frontmatter already rules out drop-in use.
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
- **Frontmatter**: unknown top-level keys always allowed and preserved;
  `{{...}}` content is schema-free.
- **Tools**: proto-packages in `tools/` that graduate to standalone repos;
  spec keeps an implementation index.

### Deferred

- Q26 — custom date-format validation in strict mode (advisory until the
  XLSX converters define a format-token contract, Epoch 5).

## [0.1.0-draft] — Epoch 1, initial proposal

- First complete proposal: anatomy, frontmatter schema, inclusions (types,
  formulas, code, styles, comments), escaping & collision matrix, staircase
  continuation, round-trip guarantees, grammar sketch, security, LLM
  guidance, open questions.
