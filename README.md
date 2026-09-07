# 📊 CSVX — a spreadsheet you can read (and diff, and show to an LLM)

**CSVX** is an open, community-driven text format for tabular data: a CSV
with a self-describing frontmatter and lightweight per-cell annotations —
types, formulas, styling, comments, and structured metadata — that survives
round-trips to and from XLSX.

> **Status:** draft proposal · **Spec:** [SPEC.md](SPEC.md) (v0.2.0-draft) ·
> **Progress:** [ROADMAP.md](ROADMAP.md) · **License:** dual (see below)

Think of it as the missing middle between a raw CSV and a binary workbook:

| | CSV | **CSVX** | XLSX |
|---|---|---|---|
| Human-readable | ✅ | ✅ | ❌ |
| Diffable / greppable | ✅ | ✅ | ❌ |
| LLM-friendly | 😐 (untyped, ambiguous) | ✅ (self-describing) | ❌ |
| Types & formats | ❌ | ✅ (`:int:` `:date(dd.MM.yyyy):`) | ✅ |
| Formulas | ❌ | ✅ (stored verbatim) | ✅ |
| Styles / comments | ❌ | ✅ | ✅ |
| Multi-sheet | ❌ | ✅ (`---` dividers) | ✅ |
| No vendor lock-in | ✅ | ✅ | ❌ |

## ✨ Why CSVX?

**LLM tokens cost money — and CSV leaves too much unsaid.** A column of
numbers might be ints, percents, or dates; a cell starting with `=` is a
formula or a typo. CSVX says it out loud, *next to the data*, without
sprinkling escapes everywhere:

```csvx
---
version: "0.2.0"
dialect:
  csv:
    delimiter: "|"
  csvx:
    formula_dialect: xlsx
---
columnA|columnB :int:|columnC :int:

Entry A|+
6 [[color:red;]]|+
10

Entry B|+
10|+
9/*Verify please @user*/

Sum|+
16`=SUM(B2,B3)`|+
19`=SUM(C2,C3)`
```

No `""` noise, no `\` prefixes, no base64. The `+` continuations and blank
lines are layout, not data — a staircase you can read top to bottom, and an
LLM can too.

## 🚀 Key features

- **Self-describing frontmatter** — YAML (or one-line flow YAML for
  machine-written files): dialect, column specs (HF-dataset-card `features`
  style), named styles, custom types, sheets, free metadata.
- **Types that propagate** — declare `:int:` or `:date(dd.MM.yyyy):` once on
  the header; cells inherit it. Cell-level overrides always win.
- **Formulas, byte-for-byte** — `` `=SUM(B2:B3)` `` is stored exactly as the
  spreadsheet had it, so XLSX → CSVX → XLSX keeps formulas working.
- **Inline annotations** — `{{...}}` YAML/JSON metadata, `[[css]]` or named
  styles, `/*comments*/` that convert to spreadsheet notes.
- **Multi-line cells without ugliness** — a `+` at the end of a field
  continues the cell on the next line. Whole cells only, no raw newlines.
- **Multi-sheet workbooks in one file** — `---` dividers, Markdown-style.
- **Special values** — `:nan:` `:inf:` `:na:` `:div0:` `:err(#VALUE!):`
  `:periodic(3):` … the tokens spreadsheets actually contain.
- **Safety first** — CSVX never executes anything; nothing runs on read.

## 🧭 Quick tour

```
csvx/
├── SPEC.md            📜 the normative spec (this is the contract)
├── ROADMAP.md         🗺️ epochs and progress
├── schema/            📋 frontmatter JSON Schema
├── samples/           🧪 one file per feature, verified against the spec
├── benchmarks/        ⏱️ escaping / token / LLM benchmarks (planned, E4)
├── implementations.md 🌐 index of reference + community implementations
├── docs/adr/          📝 decision records (stub)
├── tools/             🔧 proto-packages (rebuilt in E3 per the spec)
└── tests/             🧪 conformance corpus (rebuilt in E4)
```

Start with [samples/README.md](samples/README.md) for a feature-by-feature
tour, then read [SPEC.md](SPEC.md) for the contract.

## 🛑 When NOT to use CSVX

- **Truly messy, deeply nested data** — JSON or YAML alone is better; CSVX's
  sweet spot is uniform tabular rows.
- **Binary content** — images, media, huge blobs; store references, not
  payloads.
- **Formula evaluation** — CSVX stores formulas, it never computes them.
- **If you need guaranteed stock-CSV parsing of the whole file** — the
  frontmatter is enforced, so drop-in CSV compatibility is not the goal
  (the body still *looks* like CSV and parses row-by-row in most cases).

## 🗺️ Status & roadmap

Draft epoch 1 (proposal & decisions) is **done**; all §21 questions are
resolved. Epoch 2 (this repo's scaffolding, samples, schema) is in
progress. See [ROADMAP.md](ROADMAP.md) for the full plan: reference
parsers → conformance + benchmarks → XLSX converters → ratification.

The decisions in SPEC.md §21.1 are *provisional* until benchmark data
(epoch 4) validates them — the escaping and token-economy choices are the
ones most likely to move.

## 🤝 Contribute

CSVX is open and community-driven. The best ways to help right now:

1. **Read [SPEC.md](SPEC.md) and argue with it** — open an issue.
2. **Bring data** — real-world cells that break the escape matrix (§12.3)
   are gold for the benchmarks.
3. **Implement** — the reference parser (E3) and converters (E5) are the
   critical path; see [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

- Spec text, docs, and samples: **CC-BY-4.0**
- Reference implementations (code): **Apache-2.0**

See [LICENSE.md](LICENSE.md). "CSVX" is a working title — availability is
being checked before ratification.
