# CSVX

<p align="center">
  <img src="images/csvx_imagotype.svg" alt="CSVX wordmark" width="512">
</p>

> **The spreadsheet format for the AI era.**
>
> CSVX is a human- and AI-readable spreadsheet format: CSV-shaped tables that
> retain types, formulas, formatting, comments, structured annotations, and
> sheets as plain text.

[![Specification status: draft](https://img.shields.io/badge/specification-0.2.0--draft-6b7280)](SPEC.md)
[![Documentation: CC-BY-4.0](https://img.shields.io/badge/docs-CC--BY--4.0-7c3aed)](LICENSE.md)
[![Reference code: Apache-2.0](https://img.shields.io/badge/code-Apache--2.0-2563eb)](LICENSE.md)

CSVX is an open, community-driven proposal for tabular data and spreadsheet
workbooks. It can be understood in two complementary ways:

- **A readable spreadsheet format:** a plain-text representation of useful
  workbook features that humans and AI systems can inspect, edit, review, and
  convert without handling a binary XLSX package.
- **An expressive CSV-shaped table:** a familiar delimited grid that can carry
  types, formulas, display information, comments, structured annotations,
  multi-line cells, and multiple sheets without abandoning readability.

> **Status:** draft proposal · **Specification:** [SPEC.md](SPEC.md)
> (v0.2.0-draft) · **Roadmap:** [ROADMAP.md](ROADMAP.md) · **Examples:**
> [samples/](samples/) · **License:** dual; see [LICENSE.md](LICENSE.md)

## CSV, CSVX, and XLSX

CSVX occupies the space between a minimal delimited export and an opaque
workbook file. CSV is excellent for a rectangular grid, but it does not carry
spreadsheet context. XLSX carries that context, but it is not designed for a
meaningful text diff or direct review.

| Capability | CSV | **CSVX** | XLSX |
|---|:---:|:---:|:---:|
| Plain text; editable in any editor | Yes | Yes | No |
| Useful diffs, search, and code review | Yes | Yes | Limited |
| Clear to people and AI systems | Limited | Yes | No |
| Types and display formats | No | Yes | Yes |
| Formulas preserved verbatim | No | Yes | Yes |
| Styles, comments, and annotations | No | Yes | Yes |
| Multi-line cells | Limited | Yes | Yes |
| Multiple sheets in one file | No | Yes | Yes |
| Vendor-neutral source representation | Yes | Yes | No |

CSVX does not evaluate formulas or replace spreadsheet applications. It stores
formula text and workbook context so dedicated tools can preserve them during
conversion and spreadsheet applications can evaluate them in their native
environment.

## Why CSVX?

A plain CSV value such as `03/04/2025` is ambiguous. A value beginning with
`=` might be a formula, or it might be text. A note, style, link, validation
rule, and formula normally require separate application state—or disappear in
a CSV export.

CSVX writes that context next to the data while keeping the grid recognizable:

```csvx
workstream|owner|planned :int:|actual :int:|variance :int:|status
Research|Ada|12|10|-2 `=D2-C2` [[color: #b42318;]] /*confirm remaining budget*/|On track
Implementation|Grace|18|21|3 `=D3-C3`|At risk
Data cleanup|Lin|8|7|-1 `=D4-C4`|On track
Security review|Mina|10|10|0 `=D5-C5`|Complete
Documentation|Noor|6|5|-1 `=D6-C6` {{link: 'https://example.com/guide'}}|In review
```

The header declares integer columns once. Each variance cell preserves both
its displayed value and its exact formula. The first row also demonstrates an
inline style and a spreadsheet comment; the final row carries a structured
link annotation. None of those require a sidecar file or a hidden workbook
object.

Long text remains readable through continuation staircases rather than raw
newlines inside quoted CSV fields:

```csvx
ticket|owner|summary|status
SUP-17|Mina|+|+
Customer sees "payment declined"+|+
after a card update.|Investigating
SUP-21|Noor|+|+
First paragraph of the handover.+|+
+|Waiting for logs
Second paragraph follows the blank line.
```

Here `+` continues a whole cell on the next physical line. A line containing
only `+` contributes an empty segment, producing a blank line inside the
cell; ordinary blank lines remain layout and are ignored.

## Key features

- **Optional, self-describing frontmatter** — default tables need no
  frontmatter. Add YAML or flow-YAML only for non-default syntax, schemas,
  named styles, sheet configuration, custom types, or document metadata.
- **Types that propagate** — declare `:int:` or `:date(dd.MM.yyyy):` in a
  header or schema; data cells inherit the type while explicit cell types win.
- **Formula fidelity** — `` `=SUM(B2:B3)` `` is stored byte-for-byte. CSVX
  does not re-quote, evaluate, or rewrite the formula.
- **Structured annotations** — `{{...}}` carries schema-free YAML/JSON-like
  metadata; `[[...]]` carries inline CSS, named styles, or CSS classes; and
  `/*...*/` carries spreadsheet comments/notes.
- **Readable multi-line cells** — continuation markers represent long text
  without literal newlines inside fields and without escape-heavy encoding.
- **Multi-sheet workbooks** — `---` separates sheets. Names and intrinsic
  table/schema overrides live in the one document frontmatter.
- **Spreadsheet special values** — `:nan:`, `:inf:`, `:na:`, `:div0:`,
  `:err(#VALUE!):`, and `:periodic(3):` represent values that ordinary CSV
  cannot distinguish reliably.
- **Safety and interoperability** — data is inert on read; formula export is
  explicit; UTF-8 is required; syntax, formula language, and annotation
  format are declared once per file when defaults are not enough.

A default file is intentionally short. Its frontmatter can be omitted:

```csvx
name|team|score :int:
Ada|Research|42
Grace|Platform|73
```

When configuration is needed, the flat frontmatter remains compact:

```csvx
---
delimiter: ","
quote: "'"
formula_language: openformula
table:
  header: false
---
Ada,42,active
Grace,73,active
```

## Quick tour

```text
csvx/
├── SPEC.md            The normative format specification
├── ROADMAP.md         Design and implementation epochs
├── schema/            JSON Schema for optional frontmatter
├── samples/           Realistic canonical, configuration, and edge examples
├── benchmarks/        Reproducible escaping and LLM benchmarks (planned)
├── implementations.md Reference and community implementation index
├── docs/adr/          Decision records
├── tools/             Future reference proto-packages
└── tests/             Future conformance corpus
```

Start with [samples/README.md](samples/README.md) for a guided set of use
cases, then consult [SPEC.md](SPEC.md) for normative syntax, semantics,
escape rules, and round-trip requirements.

## Status and roadmap

The proposal and its initial design decisions are documented in
[SPEC.md](SPEC.md). Repository scaffolding, examples, and the frontmatter
schema are in place. The next stages are a reference parser, a conformance
corpus and benchmarks, XLSX/ODS converters, and community ratification.

Several decisions remain deliberately evidence-driven: token and escaping
trade-offs will be benchmarked, and date/number format validation will be
settled with the converter fidelity contract. See [ROADMAP.md](ROADMAP.md)
for the complete plan.

## Contribute

CSVX is open and community-driven. Useful contributions now include:

1. **Review the specification** — identify ambiguities, missing use cases, or
   design trade-offs in [SPEC.md](SPEC.md).
2. **Contribute real data** — unusual values that stress escaping, quoting,
   continuations, and spreadsheet conversion are valuable benchmark material.
3. **Improve examples and schema** — propose concise, realistic cases that
   make the format easier to understand and implement.
4. **Implement the format** — the reference parser and XLSX converters are
   the critical path; see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

- Specification text, documentation, schema, and samples: **CC-BY-4.0**
- Reference implementations and benchmark code: **Apache-2.0**

See [LICENSE.md](LICENSE.md). “CSVX” remains a working title pending
availability and trademark checks before ratification.
