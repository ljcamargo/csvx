# CSVX — Draft Open Specification

**Version:** 0.2.0 (Draft, "Epoch 1, revision 2")
**Status:** Proposal for community discussion — *not ratified*
**License (proposal):** Spec text CC-BY-4.0, reference implementations Apache-2.0
**Scope:** A CSV-enriched, human-readable and LLM-readable format for tabular
data, intended as a plain-text alternative to XLSX that preserves a meaningful
subset of spreadsheet capabilities (types, formulas, styling, annotations,
multi-line cells, multi-sheet workbooks, structured metadata).

> This document is a *proposal*. Every decision below is marked as
> `[PROPOSED]` and carries its rationale, alternatives, and caveats. Nothing
> is final until the community discusses and ratifies it. Open questions are
> collected in §21 (resolved items from the first review round are listed in
> §21.1; items still under discussion in §21.2).

---

## 1. Status & governance

- CSVX is an **open, community-driven standard**. There is no single vendor.
- This draft is published for discussion. Feedback happens via issues, pull
  requests, and (eventually) a mailing list or discussion forum.
- The spec follows a lightweight RFC-style process: **draft epochs** →
  **candidate** → **ratified**. Each ratified version is frozen and
  semantically versioned (SemVer). Tools must declare the spec version they
  implement.
- Conformance: a file is *conformant* if it parses under the grammar of §15
  and validates under §7–§11 with no errors in strict mode. A conformance
  suite (test corpus + reference parser) will be maintained alongside the
  spec.
- **Naming caveat:** "CSVX" is a working title. Availability must be checked
  (package registries, GitHub orgs, trademarks) before ratification.

## 2. What CSVX is

CSVX is a text format for tables. It is:

1. **A CSV-shaped body** — any declared dialect (default delimiter `|`,
   wrapper quote `"` or `'`), line-oriented, so a stock CSV reader can still
   consume the body row-by-row for the declared dialect in most cases.
2. **With a YAML/JSON frontmatter** (like Markdown or Hugging Face dataset
   cards) declaring dialect, table-level configuration, column specs, named
   styles, sheets, and free-form metadata. The frontmatter is *enforced* —
   this is what makes the file self-describing, and it means out-of-the-box
   compatibility with existing CSV libraries is **not** a goal (see P1).
3. **With per-cell inclusions** — types, formulas, structured annotations
   (inline YAML/JSON), CSS styling, and comments — attached directly to cell
   values with compact markers that avoid generalized escaping.
4. **With explicit multi-line cells** via a continuation marker, so long text
   stays readable without raw newlines inside quoted fields.
5. **Optionally multi-sheet** — sheets are separated by `---` dividers,
   Markdown-style, with per-sheet configuration.

### 2.1 First contact (the running example)

```csvx
---
version: "0.2.0"
dialect:
  csv:
    delimiter: "|"
  csvx:
    formula_dialect: xlsx
meta:
  title: Quarterly report
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

Semantics: three columns (`columnB`, `columnC` are typed `int` in the header
and the type propagates down the column); three data rows; the `Sum` row
carries Excel-dialect formulas and a comment on `9`. Blank lines are
formatting and are ignored. The `+` continuations are explained in §13.

## 3. Goals and non-goals

**Goals**
- Human-readable and editable in any text editor; diffable and greppable.
- LLM-readable: resembles Markdown tables (where LLMs excel), low token
  overhead, unambiguous, self-describing.
- Round-trip safe: parse → render → parse must be lossless (see §14).
- Preserve a useful subset of spreadsheet capabilities: types, formulas,
  styling, annotations, multi-line cells, column metadata, named styles,
  multi-sheet workbooks, merged-cell metadata.
- Convert cleanly to and from XLSX/ODS, preserving the grid (rows, columns,
  sheet names/order) so formulas keep working on their home platform.
- Deterministic, versioned, testable.

**Non-goals (v0.x)**
- No formula *evaluation* — formulas are stored verbatim as annotations and
  never touched by CSVX tools (§11.2, §18).
- No charts, images, pivot tables, macros.
- No binary encoding; no compression; no streaming formats.
- No general-purpose schema *validation* of `{{...}}` content — code
  inclusions are schema-free structured metadata (§11.3).

## 4. Design principles

| # | Principle | Meaning |
|---|-----------|---------|
| P1 | **CSV-shaped, not CSV-bound** | The body must *look* like CSV and parse row-by-row with a stock reader for the declared dialect in the common case. But readability is not sacrificed for compatibility: the enforced frontmatter already rules out drop-in use, and features like continuation are inherently non-standard. |
| P2 | **Reversibility** | Parse∘Render∘Parse = Parse. Canonical rendering exists (§14). |
| P3 | **Token economy** | Inclusions cost as few characters as possible; escaping is *on demand*, never mandatory prefixes. |
| P4 | **LLM-first legibility** | The syntax reads like annotated prose and resembles Markdown tables; markers are visually distinct; no noise characters around every value. |
| P5 | **Quote alternation** | When a field must be wrapped, string literals inside inclusions use the *opposite* quote of the cell wrapper, so wrappers never need escaping inside inclusions. |
| P6 | **Safety** | Data is inert text; nothing executes on read (see §16). |
| P7 | **Minimal core** | A small, orthogonal grammar; features are added by registration, not by syntax growth. |

## 5. Related work

- **RFC 4180** — the CSV baseline. CSVX keeps RFC quoting *rules* (doubling)
  for wrapped fields but relaxes the "quote must be doubled everywhere"
  strictness (mid-field wrapper chars are literal in unwrapped fields, §8).
- **CSV on the Web (CSVW, W3C)** — metadata-as-sidecar; CSVX embeds
  metadata in frontmatter instead.
- **Frictionless Data / Table Schema** — column descriptors and type
  registry; CSVX's `columns`/`features` is a light version.
- **Fenced CSV** (```csv blocks in Markdown) — frontmatter + CSV in one
  file; CSVX adds cell-level inclusions, continuations, and sheets.
- **Hugging Face dataset cards** — the `features:` list (name + dtype) is the
  direct inspiration for CSVX column specs; CSVX accepts `features` as an
  alias of `columns` (§7.4).
- **XLSX/ODS** — the capability baseline CSVX approximates in text (types,
  formats, formulas, styles, merges, sheets, comments).

## 6. File anatomy

```
<UTF-8 text>
[---                        <- frontmatter open (must be byte 0, own line)
 YAML mapping               <- block form
---]
   — or —
[--- {flow YAML or JSON} ---]       <- one-line form (see §6.1)
<body>
<body> may contain:        <- sheets (see §9.7)
---                         <- sheet divider (own line, exactly "---")
```

- Encoding: **UTF-8** is mandatory for conformant files (the only sanctioned
  `encoding` value). A leading BOM is tolerated and stripped; canonical form
  has no BOM `[PROPOSED]`.
- Newlines: CRLF and CR are normalized to LF on read; canonical form is LF.
- A line containing exactly `---` inside the body is a **sheet divider**, not
  data (a literal `---` cell must be quoted or escaped, §12.3).

### 6.1 Frontmatter forms: block and one-line

Two spellings are defined `[RESOLVED]`:

- **Block form** (default for authored files): `---` … `---` on their own
  lines, content is a YAML mapping (may be multi-line).
- **One-line form** (default for generated/streamed files): a single line
  `--- <flow YAML> ---`. **Flow YAML is the canonical spelling** (JSON is
  accepted as input because it is a YAML subset) `[RESOLVED]`. Rationale:
  for very large datasets, line-based access (line 1 = frontmatter,
  line 2 = first row) is O(1) instead of O(frontmatter height), and
  streaming parsers can start emitting rows immediately. Caveats: flow
  syntax is harder to author by hand and long configs become unreadable;
  recommend one-line only for machine-written files. The frontmatter
  *content model* is identical in both forms.

## 7. Frontmatter (the schema of expected features)

The frontmatter is a YAML mapping (JSON is a YAML subset). **Unknown
top-level keys are always allowed and preserved** — metadata must be
extensible and future versions must not break older files `[RESOLVED]`.

### 7.1 Full schema (normative keys)

```yaml
version: "0.2.0"          # [PROPOSED] recommended: spec version this file targets
dialect:
  csv:                    # CSV layer (defaults shown)
    delimiter: "|"        #   any single char, incl. "\t"; "|" default
    quote: '"'            #   wrapper quote: '"' or "'" ONLY (backtick reserved)
    encoding: utf-8       #   informational; UTF-8 is the only sanctioned value
  csvx:                   # CSVX layer (defaults shown)
    continuation: "+"     #   single char; end-of-field continuation marker
    line_comment: "#"     #   single char or null; "# " + space/EOL = comment line
    escape: "\\"          #   single char; the CSVX escape character
    formula_dialect: xlsx #   xlsx | sheets | ods | none
    code_format: yaml     #   yaml | json (informational hint for consumers)
    style_format: css     #   css (only value for now)
table:
  header: true            #   first body row of each sheet is the header
  type_propagation: column#   column | none (see §9.2)
  default_dtype: string   #   applied when nothing else declares a type
  null_policy: null       #   null | string (see §9.4)
  allow_ragged: false     #   strictness for uneven rows (see §9.5)
  blank_row: null         #   single char or null; optional marker for an empty row
  rows: null              #   declared data-row count (advisory)
  cols: null              #   declared column count (advisory; from columns/features when set)
columns: []               #   column specs, in order (see §7.3)
features: []              #   alias of columns (HF-dataset-card style)
sheets: []                #   sheet list (see §9.7); enables multi-sheet mode
types: {}                 #   custom types (see §11.1.4)
styles: {}                #   named styles (see §11.4.2)
meta: {}                  #   free-form; anything (title, license, provenance…)
```

### 7.2 Dialect auto-detection

`[PROPOSED]` If the file has no frontmatter, the defaults apply
(`|` delimiter, `"` wrapper, `+` continuation, `#` line comments). No
heuristic sniffing of unknown dialects — dialect is *declared, not guessed*
(guessing is a known source of data corruption in the CSV world).

### 7.3 Column specs

```yaml
columns:
- name: qty
  dtype: int
  width: 12            # advisory, informational
  format: "#,##0"      # advisory display format
  description: ...     # free text; LLM/human documentation
```

`dtype` is a registry type (§11.1.1) or a custom type (§11.1.4). A dtype
may carry parameters in the same `name(params)` notation as cell markers —
`dtype: date(dd.MM.yyyy)` is equivalent to writing `:date(dd.MM.yyyy):` on
the header cell (a header marker overrides the column spec). Column specs
are *advisory* in v0.x (they document and default, they do not coerce).

### 7.4 `features` (HF-style alias)

```yaml
features:
- name: code
  dtype: string
- name: audio
  dtype: audio
```

`columns` and `features` are aliases; declaring both is an error. A column's
`dtype` may also be declared in the header row itself (`columnB :int:`) —
see §9.2 for precedence.

## 8. The CSV layer

The CSV layer follows RFC 4180's quoting model with deliberate relaxations:

1. **Wrapper quotes are `"` or `'` only.** The wrapper is declared in
   `dialect.csv.quote`; **backtick is not a valid wrapper** — it is reserved
   for the formula marker. `[RESOLVED]`
2. **The wrapper char is recognized only at field start.** If a field begins
   with the wrapper char, it is a wrapped field and RFC doubling applies
   inside it (`""` for a `"` wrapper, `''` for a `'` wrapper). Anywhere else
   in an *unwrapped* field, the wrapper char is plain literal content:
   `say "hi"` and `` =CONCAT("a","b") `` need no doubling and no escaping.
   `[RESOLVED]` This is the change that makes formulas and prose cheap.
3. **Backtick regions are wrapper-protected.** Inside a *wrapped* field, a
   bare backtick opens a protected region that ends at the matching bare
   backtick; inside it, the wrapper char is literal and no doubling is ever
   applied. This is what guarantees formula byte-fidelity (§11.2). A literal
   backtick inside a wrapped field must be escaped (`\``). `[PROPOSED]`
4. **Fields must not contain literal newlines** — even inside wrappers. Use
   the continuation marker (§13) for multi-line content.
5. Wrapped fields must be well-formed: the wrapper opens at field start; the
   closing wrapper must be followed by a delimiter or end of line; junk
   after the closing wrapper is a strict-mode error (so `"a"[[CSS]]` stays
   invalid — see §12.2).

Default delimiter is `|` — not `,` — because `|` is rare in real data,
matches Markdown-table familiarity, and avoids the European-decimal
collision (`3,14`). `,`, `;`, TAB, or any single character can be declared;
with TAB delimiters, embedded tabs in values require wrapping, and the
continuation marker is unaffected `[RESOLVED]`.

### 8.1 Quote alternation (P5)

When a field must be wrapped (it contains the delimiter, a wrapper char to
escape, or leading/trailing spaces), string literals *inside inclusions*
(YAML/JSON in `{{…}}`, CSS in `[[…]]`, formulas) should use the **opposite
quote** of the wrapper, so the wrapper char never needs doubling:

- wrapper `"` → inclusions use `'`:
  `"1{{{'key':'value'}}}[[color:'#ffffff']]"` — no `""` doubling anywhere
- wrapper `'` → inclusions use `"`:
  `'1{{{"key":"value"}}}[[color:"#ffffff"]]'`

In practice, fields only need wrapping when they contain the delimiter or a
literal newline; an unwrapped field may contain either quote freely:

```
1{{{'key':'value'}}}[[color:'#ffffff']]     # unwrapped: no escaping at all
```

This convention is a SHOULD, not enforced — the parser only needs the
field-start rule above. Consequences `[PROPOSED]`:
- With `code_format: yaml` (default) alternation is free: YAML accepts both
  quote styles.
- With `code_format: json` under a `"` wrapper, single-quoted strings are
  accepted by CSVX parsers (relaxed); consumers may re-quote as needed
  `[RESOLVED]`.

**Formulas are excluded from alternation** — a formula is stored
byte-for-byte as it appeared in the source spreadsheet
(`=CONCAT("a","b")` keeps its double quotes), because spreadsheet dialects
differ in what quoting they accept. Alternation is a writing convention for
YAML/JSON/CSS only (§11.2).

## 9. The table layer

### 9.1 Header

`table.header: true` (default): the first body row of each sheet is the
header. Header cells may carry inclusions, most importantly `:type:`
(propagates, §9.2) and `[[style]]` (advisory).

### 9.2 Type propagation and precedence

`[PROPOSED, RESOLVED]` With `type_propagation: column` (default), each
*data* cell's effective type is resolved in this order:

1. cell-level `:type:` (explicit, wins always);
2. `columns`/`features` spec for the column;
3. header cell type (`columnB :int:`);
4. `table.default_dtype` (default `string`).

**The header cell itself is exempt from the column type** — a header named
`columnB :date(...):` is a *string* (the name), not a date; the type applies
to data cells only. This is the "natural but data-level illogical" behavior
you flagged: propagation is a column default for data, never a coercion of
the header `[RESOLVED]`.

**Only types propagate by default.** Styles and display formats do *not*
propagate from the header (headers are commonly bold while cells are not);
propagation of styles/formats is opt-in via frontmatter
`table.propagate: [type]` or `[type, style]` (future) `[RESOLVED]`.

With `type_propagation: none`, header types are ignored (only cell-level and
column specs apply). Types are metadata + validation targets; they never
coerce values (§11.1.3).

### 9.3 Blank lines and line comments

Blank lines (only whitespace) and `#`-comment lines are **ignored** in the
body. They exist purely for human/LLM readability. A line that is only
whitespace is never a data row.

Line comments (`#`) are CSVX-only: they are *not* part of the spreadsheet
model and are dropped on XLSX conversion. Cell comments (`/*…*/`) *are* part
of the model and convert to spreadsheet comments/notes `[RESOLVED]` (§11.5).

### 9.4 Null, empty, and special values

`[PROPOSED]`

- An *empty unquoted field* is **null** (with `null_policy: null`, default)
  or empty string (with `null_policy: string`).
- An *empty wrapped field* (`""`) is always an empty string.
- `:null:` and `:empty:` are explicit, policy-independent spellings.
- **The literal string "null" is never null.** It is a plain string value
  (in German, "null" means zero). Null is expressed structurally (empty
  field) or via the `:null:` token — never by word-matching a cell's text
  `[RESOLVED]`. The alternative token `__null__` was considered and
  rejected: `:null:` is shorter and consistent with the type syntax.
- Spreadsheet specials have dedicated tokens (see §11.1.5): `:nan:`,
  `:inf:`, `:ninf:`, `:na:`, `:err:`, `:err(code):`, `:periodic(...):`.

| Written | With `null_policy: null` | With `null_policy: string` |
|---|---|---|
| *(empty field)* | null | `""` |
| `""` | `""` | `""` |
| `:null:` | null | null |
| `:empty:` | `""` | `""` |
| `null` (text) | the string `"null"` | the string `"null"` |

### 9.5 Ragged rows

Rows must match the header/columns width. Mismatch: error in strict mode;
pad-with-null or truncate in lenient mode. `table.allow_ragged: true`
silences the strict error and keeps the row as-is.

### 9.6 Blank rows and declared dimensions

A row of all-null cells is expressible as:
- a line of only delimiters (`||` for 3 columns), or
- a single cell `:null:` in a single-column table (explicit spelling).

The `table.blank_row` marker (a lone character on a line) is *optional
sugar* for all-null rows; its default is **disabled**, so a single-column
cell containing `-` is never misread `[RESOLVED]`. When the marker is
enabled, a literal marker value must be escaped.

`table.rows` and `table.cols` declare the expected data-row and column
counts — numeric and **coordinate-agnostic**: CSVX has no cell-coordinate
system of its own. Formula references (A1-style) are opaque text inside
formula strings, in the formula's own dialect; CSVX never interprets them.
The counts are advisory but give tools and validators context to resolve
ambiguity (e.g. blank-row counts) and to verify XLSX round-trip fidelity.
Converters may derive an xlsx-style range (`A1:D20`) from them; that is a
converter concern, not a CSVX concept `[RESOLVED]`. (A Markdown-like
alphabetic row "superheader" (`A|B|C|…`) was considered and rejected:
column labels already come from the header row or `columns`/`features`, and
coordinates add nothing for humans or LLMs.)

### 9.7 Multi-sheet workbooks

`[RESOLVED]` CSVX is a single file that may contain multiple sheets:

- A body line containing exactly `---` is a **sheet divider**.
- **All sheet configuration lives in the main frontmatter** `sheets:` list
  (names + per-sheet overrides). There is **no per-sheet frontmatter** —
  sheets that need no configuration declare nothing and fall back to
  defaults (and to inferred row/column counts). `[RESOLVED]`
- `types` and `styles` are file-wide registries. `dialect`, `table`,
  `columns`/`features` are per-sheet-able via `sheets:` entries: global
  values act as defaults for every sheet.
- Sheets without a declared name are named `Sheet1`, `Sheet2`, … in order.

```csvx
---
version: "0.2.0"
sheets:
- name: Sales
- name: Notes
  table:
    header: false
---
region|qty :int:
EU|12
---
Notes
Just a free-form sheet.
```

Rules `[RESOLVED]`:
- A `---` line is a divider *always* (not only when `sheets:` is declared);
  a literal `---` cell must be quoted (`"---"`) or escaped (`\---`).
- A divider carries no configuration of its own — anything sheet-specific
  is declared in `sheets:`.

## 10. The cell model

A cell is: **value first, inclusions after.** The value is the text before
the first inclusion marker; every inclusion is a distinct, self-delimiting
region. Inclusions may appear in any order and may be separated by single
spaces or nothing (both parse; canonical form uses single spaces).

```
VALUE :type(params): `formula` {{code}} [[style]] /*comment*/
```

Cell-level inclusion reference (all `[PROPOSED]`):

| Inclusion | Syntax | Carries | Examples |
|---|---|---|---|
| type | `:name:` / `:name(params):` | dtype (+ params) | `:int:` `:float:` `:date(dd.MM.yyyy):` |
| formula | `` `...` `` | formula string | `` `=SUM(B2,B3)` `` |
| code | `{{...}}` | structured annotation | `{{link: "https://…"}}` `{{{"colspan": 2}}}` |
| style | `[[...]]` | CSS / named refs | `[[color: red;]]` `[[#negative]]` |
| comment | `/*...*/` | note | `/*Verify please @user*/` |

Examples:

```
columnB :int:            # header cell: name "columnB", column type int
6 [[color:red;]]         # value 6, styled
16`=SUM(B2,B3)`          # value 16, formula
9/*Verify please @user*/ # value 9, comment
:null:                   # empty value, explicit null
:inf:                    # special value: +infinity
31.12.2024 :date(dd.MM.yyyy):   # formatted date
{{"colspan": 2}}         # empty value, code annotation only
```

## 11. Inclusions in detail

### 11.1 Types — `:name:` and `:name(params):`

#### 11.1.1 Registry (v0.x, `[PROPOSED]`)

| Type | Aliases | Value contract (strict-mode validation) |
|---|---|---|
| `string` | `str` | any text |
| `text` | | any text (long-form; same contract as string) |
| `int` | `integer` | `[+-]?\d+` |
| `float` | `number`, `real`, `double` | decimal, optional exponent |
| `bool` | `boolean` | true/false/1/0/yes/no/on/off (case-insensitive) |
| `date` | | `YYYY-MM-DD` (ISO) — see §11.1.2 for formats |
| `datetime` | | `YYYY-MM-DD[T ]HH:MM[:SS[.fff]]` |
| `time` | | `HH:MM[:SS[.fff]]` |
| `duration` | | advisory (ISO 8601 duration or free text) |
| `percent` | | number, optional trailing `%` |
| `currency` | | advisory (number with optional symbol/code) |
| `url` | `uri` | `scheme://…` |
| `email` | | simple address form |
| `phone` | | advisory |
| `uuid` | | canonical 8-4-4-4-12 hex |
| `json` | | parses as JSON (relaxed: single quotes accepted, §8.1) |
| `yaml` | | parses as YAML |
| `bytes` | | number with optional unit (B, KB, KiB, …) |
| `audio` | | non-empty (path/URI/data ref) — HF-style |
| `image` | | non-empty |
| `video` | | non-empty |
| `any` | | anything |
| `null` | | value must be empty; denotes explicit null |
| `empty` | | value must be empty; denotes explicit empty string |

Special value tokens are registry types too — see §11.1.5.

Validation applies to *non-empty* values only. In lenient mode, type
violations are warnings. `audio`/`image`/`video` stay; future tools may
sniff encodings (base64, JSON-like) but that is out of scope for v0.x
`[RESOLVED]`.

#### 11.1.2 Date/time formats — `:date(fmt):` (the one typed specialization)

`[PROPOSED]` XLSX tables are rich in date/time formats, so `date`,
`datetime`, and `time` accept an optional **format parameter** using the
spreadsheet format-string notation (Excel number-format tokens like
`dd.MM.yyyy`, `HH:mm:ss`, `yyyy-mm-dd`):

```
31.12.2024 :date(dd.MM.yyyy):
14:30 :time(HH:mm):
2024-12-31 14:30:00 :datetime(yyyy-mm-dd HH:MM:SS):
```

- `:date:` with no parameter means ISO `YYYY-MM-DD` and *is* validated in
  strict mode. With a parameter, the format is **advisory** (display/parse
  spec for converters); strict validation per custom format is deferred —
  format tokens are locale-dependent (see §21.2 Q26).
- The parameter is part of the type marker: `:name(params):` — params may
  contain `:` (time formats) but **not** `(` or `)`; the marker ends at the
  first `):`. (Format strings never need parentheses; if they ever do, use
  the code-inclusion form `{{format: "…"}}` instead.)
- `[RESOLVED]` `:date(fmt):` is canonical for date/time formats; `{{format:
  …}}` remains available for other display formats (numbers, currency) —
  see §11.3.1.
- **Collision note:** a value containing type-shaped text with parentheses,
  e.g. `x:date(2024):y`, is ambiguous with a parameterized type — escape it
  (`\:date(2024):`) or rely on strict mode's loud error, exactly like the
  plain `key:value:` case (§12.3).

#### 11.1.3 Unknown type names

A `:name:` whose name is neither a registry type nor a frontmatter custom
type is an **error in strict mode** ("escape it or declare it") and is
treated as literal text in lenient mode. This is the collision policy for
real-world text like `key:value:` (§12.3).

#### 11.1.4 Types never coerce

`:int:` validates and annotates; it does not convert `"007"` to `7`. Values
stay strings; consumers coerce. This keeps round-tripping exact.

#### 11.1.5 Special value tokens

`[PROPOSED]` Spreadsheets carry values that are not plain data. CSVX models
them as types applied to (usually empty) values:

| Token | Meaning | XLSX mapping (converter) |
|---|---|---|
| `:nan:` | not a number | `#NUM!` / NaN cell |
| `:inf:` | +∞ | `1.7976931348623157E+308` or `#NUM!` (no native ∞) |
| `:ninf:` | −∞ | same, negative |
| `:na:` | not available | `#N/A` |
| `:err:` | generic error | error cell |
| `:err(#DIV/0!):` … | specific error code (any `#…!` or `#…?` string) | that error |
| `:div0:` | `#DIV/0!` (sugar for `:err(#DIV/0!):`) | that error |
| `:nref:` | `#REF!` | that error |
| `:nvalue:` | `#VALUE!` | that error |
| `:nname:` | `#NAME?` | that error |
| `:nnum:` | `#NUM!` | that error |
| `:periodic:` / `:periodic(3):` | recurring/repeating decimal: value is the prefix, param the repetend — `0.1 :periodic(3):` = 0.1(3) | expanded decimal or format note |

The token list is deliberately small; extensions are registered, not
invented. The classic Excel error set gets sugar tokens; any other `#…!`
code uses the general `:err(code):` form `[RESOLVED]`. No math constants
(`:pi:`, `:e:`, …) are defined — represent them as ordinary float values;
constant tokens would open an unbounded registry for no format benefit
`[RESOLVED]`. `:periodic(repetend):` is the canonical spelling
(`0.1 :periodic(3):` = 0.1(3)); a `:p(3):` alias was considered and
rejected — the long form is clearer for humans and LLMs, and the token
cost is two characters `[RESOLVED]`.

#### 11.1.6 Custom types

```yaml
types:
  hexcolor: "^#[0-9a-fA-F]{6}$"   # regex, fullmatch
  weekday:
    enum: [Mon, Tue, Wed, Thu, Fri]
```

Complex constraints (min/max/pattern) do **not** go here — they belong in
the cell's code inclusion, which is the schema-free home for validation
metadata `[RESOLVED]`:

```
7 :int: {{min: 0, max: 10}}
```

### 11.2 Formulas — `` `...` ``

- Content is stored **verbatim** (after the CSVX-layer unescaping of
  `` \` `` → `` ` ``); CSVX never evaluates, rewrites, or validates
  formulas `[RESOLVED]`.
- The formula dialect is a *file-level* declaration
  (`dialect.csvx.formula_dialect: xlsx | sheets | ods | none`), because
  mixing dialects in one file is a footgun.
- References (A1-style, e.g. `=SUM(B2:B3)`) refer to the rendered table
  position: header = row 1, first data row = row 2.
- **Converter fidelity:** for formulas to keep working after XLSX ↔ CSVX ↔
  XLSX round-trips, converters must preserve the grid — same row/column
  count, same sheet names and order, same cell positions (§18).
- Formula strings commonly contain `"` (`=CONCAT("a","b")`); under §8.2
  these are literal in unwrapped fields, so no escaping or doubling is
  needed. Only in a *wrapped* field containing a `"`-wrapper do they need
  doubling (rare; accepted).
- Inside a formula, only `` \` `` is an escape; backslashes are otherwise
  preserved verbatim (important for regex formulas like
  `` `=REGEXMATCH(A2,"\d+")` ``).
- **Never re-quoted.** CSVX stores the formula exactly as found; alternation
  does not apply to formulas (§8.1). Inside a wrapped field, backtick
  regions are wrapper-protected (§8), so formula text never needs doubling.
  XLSX → CSVX → XLSX round-trips therefore reproduce the original formula
  bytes, whatever quoting the source software uses `[RESOLVED]`.

### 11.3 Code inclusions — `{{...}}` (structured, schema-free annotations)

Structured annotations, default inline YAML, configurable to JSON. The
content is **schema-free** — it is broad metadata, and complex consumer
features (e.g. conditional formatting) may be expressed there without the
core spec growing `[RESOLVED]`.

- **Brace balancing:** the region closes at the first `}}` whose content is
  brace-balanced and whose remainder parses as more inclusions. Normal
  YAML/JSON needs **no escapes**: `{{{"a": {"b": 2}}}}` parses with content
  `{"a": {"b": 2}}`.
- Escapes are needed **only for unbalanced braces**, enforced because region
  termination must be unambiguous — almost always a string containing `}}`:
  `{{{"s": "a\}\}b"}}}` → content `{"s": "a}}b"}`. Escapes are a CSVX-layer
  concern; they are removed before the block is handed to the YAML/JSON
  consumer.
- **Quote alternation applies** (§8.1): with a `"` wrapper, write YAML with
  `'` strings (`{{'key': 'value'}}`); JSON under a `"` wrapper is the one
  awkward case (§8.1, §21.2 Q18).
- A field containing `"` does not need wrapping (§8.2) — `{{{"key":"value"}}}`
  unwrapped is valid JSON with zero escaping.

#### 11.3.1 Standard keys (advisory registry)

`format` (display format), `link`/`url`, `tags`, `note`, `colspan`,
`rowspan`, `sort`, `validate` (regex), `min`, `max`, `pattern`, `enum`,
`icon`, `id`, `meta` (free). Unknown keys are preserved; prefixed keys
(`x-…`) are encouraged for private extensions. These keys are *advisory*:
importers may honor them (e.g. `colspan` → merged cells, `min`/`max` →
validation rules); CSVX itself only guarantees the block is well-delimited.

### 11.4 Styles — `[[...]]`

#### 11.4.1 Inline CSS

`[[color: blue; font-size: 18px; font-weight: bold;]]` — CSS declarations.
With a `"` wrapper, prefer `'` for CSS strings: `[[color:'#ffffff']]`
(§8.1). Escapes: `\]` `\\`. CSS blocks (`{}`) are not allowed inside inline
style regions — use a named style (§11.4.2) or a code inclusion.

#### 11.4.2 Named styles and CSS classes

Frontmatter:

```yaml
styles:
  negative: "color: #c00; font-weight: bold;"
  header: "font-weight: bold; background: #f0f0f0;"
```

Cell: `[[#negative]]` (named style) **and** `[[.some-css-class]]` (opaque
CSS class name, kept verbatim for downstream styling engines) — both are
supported `[RESOLVED]`.

**Rule:** a style region whose first token starts with `#` or `.` and which
contains no `:` is a *reference*; otherwise it is raw CSS. Mixing
(`[[#negative, color: blue;]]`) is *not* supported — use two inclusions:
`[[#negative]] [[color: blue;]]`.

### 11.5 Comments — `/*...*/`

- Content is free text; escapes `\*` `\\`. Comments cannot nest.
- `/*` inside a comment is literal text; the region closes at the first
  unescaped `*/`.
- `@mentions` and `#tags` inside comments work naturally.
- **Conversion:** cell comments are part of the model and map to spreadsheet
  comments/notes in XLSX; `#` line comments are CSVX-only and are dropped on
  conversion `[RESOLVED]` (§9.3).
- Line-level comments are separate: a body line whose first non-space char
  is `#` followed by a space/EOL is ignored (§9.3). A data cell that starts
  with `# ` must escape the `#` (`\# `).

## 12. Escaping and collisions — minimized by design

The design goal is: **almost nothing needs escaping, ever.** Three moves
achieve this: quote alternation (§8.1), field-start-only wrapper recognition
(§8.2), and on-demand escaping (§12.3).

### 12.1 Spacing between inclusions

| Scheme | Example | Pros | Cons |
|---|---|---|---|
| **A. Adjacent** (no spaces) | `6:float:\`=F()\`{{c}}[[s]]/*x*/` | densest | Unreadable; markers blur together; token savings vs B are tiny |
| **B. Spaced** *(recommended)* | `6 :float: \`=F()\` {{c}} [[s]] /*x*/` | Reads like annotated prose; LLM-friendly; still compact | +N spaces per cell vs A |
| **C. Escape-prefixed** (the `VALUE\{{YAML}}[[STYLE]]\` idea) | `6\:float:\`=F()\`\{{c}}\[[s]]\/*x*/` | "obviously" escaped | **Rejected.** Every cell pays escape chars even when no collision exists; doubles token cost on typical data; backslash before *every* marker trains readers to ignore escapes; does not even resolve ambiguity on the closing delimiters |

**Decision [PROPOSED]: B, with A accepted on input.** The parser accepts
both; canonical rendering uses single spaces. Escaping is *on demand*
(§12.3) and costs nothing when no collision exists — this is what makes
CSVX cheap on tokens (P3).

### 12.2 Quote policy (revised)

- **`"a"[[CSS]]` remains invalid** — junk after a closing wrapper is a
  strict-mode error — but for a different reason than before: it is a
  *broken wrapped field*, not a compatibility rule.
- Inclusions inside a wrapped field use the opposite quote (§8.1), so the
  wrapper never needs escaping inside inclusions.
- Mid-field wrapper chars in unwrapped fields are literal content; no
  doubling, no escaping, no error.
- Backtick is not a wrapper; it belongs to formulas.

### 12.3 The collision matrix (when is escaping needed?)

The escape character is `\` (`dialect.csvx.escape`). This is the *complete*
list — everything else passes through untouched:

| Context | Raw text you want | Write | Why |
|---|---|---|---|
| value | `` a`b `` | `` a\`b `` | `` ` `` would open a formula |
| value | `a{{b}}` | `a\{\{b\}\}` | `{{` would open a code region |
| value | `a[[b]]` | `a\[[b\]]` | `[[` would open a style region |
| value | `a/*b*/` | `a/\*b\*/` | `/*` would open a comment |
| value | `key:value:` (type-shaped) | `key\:value:` | `:value:` looks like a type |
| value | `x:date(2024):y` (param type-shaped) | `x\:date(2024):y` | `:date(2024):` looks like a typed date |
| value, field end | `5+` | `"5+"` *(canonical: wrap it)* or `5\+` | a trailing `+` on the raw field means continuation; wrapped, `+` is literal |
| value, line start | `# tag` | `\# tag` | `#`+space means comment line |
| value, own line | `---` | `"---"` or `\---` | `---` is a sheet divider |
| value, before an inclusion | `a ` (trailing space) | `a\ ` | trailing spaces before a marker are separators |
| value | `a\b` | `a\\b` | `\` is the escape itself |
| formula | `` a`b `` | `` a\`b `` | only escape inside formulas |
| code | `{"s": "a}}b"}` | `{"s": "a\}\}b"}` | unbalanced `}}` would close the region |
| style | `a]]b` | `a\]\]b` | `]]` closes the region |
| comment | `a*/b` | `a\*/b` | `*/` closes the region |

**Gone from the matrix** (no longer needed): doubling or escaping of `"` in
values and formulas (field-start-only wrapper rule), `'` in values (never
special), `""` inside YAML/JSON under a `"` wrapper (alternation).

**Known soft spots (worth discussing):**

1. **Trailing `+`** — unwrapped data like `5+`, `c++` at *field end* must be
   escaped (`5\+`). Inside a field, or wrapped (`"5+"`), `+` is literal —
   the marker lives *outside* the wrapper (§13.4). **Verdict: keep; bench
   the real frequency of trailing `+` in data.**
2. **Type-shaped text** — `12:30:` is safe (digits aren't identifiers);
   `key:value:` and `x:date(…):` need escaping in strict mode, which errors
   loudly and actionably.
3. **Escaped-space at value end** — rare, needed for exactness.
4. **JSON strings containing `}}`** — must be escaped inside the code region
   (§11.3). Rare, error is clear.

### 12.4 Why backslash (not doubling or %-encoding)

- `""` doubling is already taken by the CSV layer.
- `%XX`-style encoding is URL-ish noise, hostile to LLM token economy.
- Backslash is the convention users already know from Markdown (`\|`) and
  shell; it degrades gracefully in prose.

## 13. Multi-line cells (continuation)

### 13.1 The marker

A field whose **last non-space character** is the continuation marker
(`+`, configurable) continues on the next line. The marker is stripped
before value parsing; continuation segments are joined with `\n`.

```
columnA|columnB :int:|columnC :int:

Entry A|+
6 [[color:red;]]|+
10
```

Column B's cell is `6 [[color:red;]]` (value `6`, style `color:red;`); the
empty base segment is a *placeholder* and contributes no newline.

Continuation applies to **whole cells**: each field on a line is exactly
one segment; a cell never breaks in the middle of a line.

### 13.2 Staircase semantics

Fields of a continuation line fill the *pending* (unfinished) fields of the
current row, **left to right, in order**; extra fields on a line open new
columns. A row ends when its last line leaves nothing pending. Walkthrough
of the running example:

```
Sum|+              # row starts: f1="Sum", f2 pending (empty base), f3 pending
16`=SUM(B2,B3)`|+  # fills f2 ("16" + formula), f3 still pending
19`=SUM(C2,C3)`    # fills f3
```

### 13.3 Blank lines and empty segments

- A fully blank line is always ignored (never a segment).
- A line whose only field is `+` contributes an *empty segment* → a blank
  line inside the cell:

```
a|+
+
b                  # cell value: "a\n\nb"
```

### 13.4 The marker lives outside the wrapper — no escaping needed

`[RESOLVED]` Continuation is inherently non-standard, so it owes nothing to
stock CSV parsers. The marker is the last character of the *raw field* —
after the closing wrapper if the field is wrapped:

```
5+|+              # field 1: value "5", continues; field 2: empty, continues
"5+"|+            # field 1: literal "5+" (wrapped → + is content); field 2 continues
"a|b"+|+          # field 1: "a|b", continues (wrapped because of the |)
"c|d"|done        # field 1: "a|b\nc|d" (filled), field 2: "done"
```

Consequences:
- `+` inside a wrapper is plain content: `"5+"` and `"c++"` need **no
  escaping**. A literal trailing `+` is expressed by wrapping the field —
  this is canonical; the `\+` escape remains as an optional fallback for
  unwrapped fields.
- The one ambiguous spelling is a *bare unwrapped* field ending in `+`
  (`5+` on its own): that *is* a continuation by definition — wrap or
  escape to mean the literal string.
- `"a|b"+` (marker outside) is valid; `"a|b+"` is the literal string
  `a|b+`.

### 13.5 Well-formedness

- Every pending field must be resolved by the end of the row (else:
  strict error "unresolved continuation").
- A literal trailing `+` in unwrapped content must be escaped (`5\+`).
- There is no limit on continuation depth; rows stay aligned to columns
  positionally, not visually — the staircase is a *reading aid*, not an
  alignment contract.

## 14. Round-trip and canonical form

### 14.1 Guarantee

`parse(render(parse(x))) == parse(x)` — i.e., canonical rendering is
idempotent and lossless. The guarantee covers the *document model* (values,
inclusions, frontmatter, column spec, sheets). **It does not promise
byte-identical output to the input**: blank lines are removed,
continuations are minimized (flattened to single lines where possible),
unnecessary wrappers are dropped, and CRLF becomes LF. Canonical form exists
so diffs and hashes are stable.

### 14.2 Strict vs lenient

- **Strict (default for tools):** any violation is an error — malformed
  wrappers, unclosed inclusions, unknown types, ragged rows, dangling
  escapes, unresolved continuations. **Unknown frontmatter keys are never
  errors** `[RESOLVED]`.
- **Lenient:** best-effort recovery; violations become warnings (unknown
  types → literal text, unclosed inclusions → literal text, ragged rows →
  pad/truncate).

### 14.3 Known lossy edges (must discuss)

1. Single-column tables: an all-null row renders as a blank line, which
   reparses as *no row*. Explicit spellings exist (`:null:` row, `||`,
   optional `blank_row` marker) — canonical render should warn when it has
   to emit a blank line.
2. Line comments (`#`) and blank lines are not part of the model — they are
   dropped on render. If comments must survive round-trips, put them in
   `meta`, in `columns[].description`, or in cell comments.

## 15. Grammar sketch (informative)

```
csvx-file   = [ frontmatter ] body
frontmatter = "---" newline yaml-mapping "---" newline     (* block form *)
            / "--- " (json | flow-yaml) " ---" newline      (* one-line form *)
body        = { line }
line        = [ comment-line / blank-line / divider-line / data-line ] newline
divider-line= "---"                                              (* sheet divider *)
data-line   = field { delim field }
field       = wrapped-field / bare-field
wrapped-field = quote { char / quote quote / "\" escape } quote
bare-field  = { char / escape-char }                       (* quote = literal *)
cell        = value { inclusion }                          (* value first *)
inclusion   = type-marker / formula / code / style / comment
type-marker = ":" identifier [ "(" param ")" ] ":"         (* param: no ( ) *)
formula     = "`" { char / "\`" } "`"
code        = "{{" balanced-braces "}}"                    (* with backtracking close *)
style       = "[[" { char / "\]" } "]]"
comment     = "/*" { char / "\*" } "*/"
cont-marker = "+"                                          (* after last non-space char;
                                                              outside wrapper *)
```

The reference parser is normative over this sketch.

## 16. Security considerations

- **CSV/formula injection:** CSVX itself never executes anything, but tools
  that re-export to spreadsheet formats must treat `=`, `+`, `-`, `@` at the
  start of *untyped* values as potentially hostile (classic CSV injection).
  CSVX's formula marker makes intent explicit; exporters should export
  formulas as formulas only when `formula_dialect` is set and the user asked
  for it.
- **YAML safety:** frontmatter and `{{...}}` blocks must be parsed with a
  safe YAML loader (no object construction, no `!!python/...` tags). The
  reference implementation uses `safe_load`.
- **Size:** a conformant parser should impose configurable limits on field
  length, line count, and nesting depth (brace balancing is O(n) but
  pathological inputs should be bounded).
- **ReDoS:** custom-type regexes are user-supplied; validators must not run
  them on untrusted data without care (or should time-box them).

## 17. LLM guidance

Why CSVX is LLM-friendly: it deliberately resembles Markdown tables (the
form LLMs read and edit best), the frontmatter is self-describing, markers
are visually scannable, escaping noise is rare, and the line-based structure
survives continuation and sheet dividers. Practical guidance:

- Prefer `|` delimiter and spaced inclusions (scheme B) — densest readable
  form.
- Use `features:`/`columns:` dtypes and header types; they let a model
  reason about columns without guessing.
- Use cell comments and `#` line comments for provenance notes instead of
  inventing columns.
- For large blobs (JSON, long text), use continuations rather than
  base64 or single-line escapes.
- Use the one-line frontmatter for machine-generated files (line-based
  access), block form for authored files.
- **To measure, not assume:** token-cost comparison vs equivalent XLSX/CSV
  and vs scheme A/C should be part of the acceptance benchmarks (planned
  tooling, §18) — including with real LLM tokenizers.

## 18. Tooling plan (to be built after approval)

1. **Reference parser/serializer** (strict + lenient), CLI: parse, render,
   check, markdown view, JSON view, round-trip verification.
2. **Conformance corpus** — adversarial cases: every escape in §12.3, every
   dialect variant, staircase edge cases, unicode, wrapper interplay,
   brace-balancing cases, sheet dividers, one-line frontmatter.
3. **Escaping benchmark** — generated corpus of realistic + adversarial
   cells; measures for each candidate scheme: parse failure rate,
   reversibility, byte overhead, token overhead (real tokenizers), and
   throughput. This decides scheme A vs B quantitatively and validates the
   collision matrix.
4. **LLM benchmark** — prompt-comprehension and token-cost experiments
   (CSVX vs CSV vs XLSX-rendered), using Markdown-table resemblance as the
   comprehension baseline (§21.2 Q15).
5. **XLSX ↔ CSVX converters** with a fidelity contract: same grid (rows,
   columns), same sheet names/order, formulas verbatim at the same cell
   addresses, comments ↔ cell comments/notes, styles ↔ CSS/named styles,
   date formats ↔ `:date(fmt):` / `{{format: …}}`, merges ↔
   `{{colspan/rowspan}}` (§11.3.1), special values ↔ `:nan:`/`:inf:`/…
   tokens. Converters are the *proof* of the style/code/date specs.
6. **Packaging:** `tools/` hosts *proto-packages* — reference
   implementations used for conformance testing (`tools/csvx-py` with its
   own pyproject, `tools/csvx-js` with its own package.json). They are
   expected to graduate into standalone repositories; the spec maintains an
   **implementation index** listing them and community implementations. The
   spec is the contract — tools may be replaced freely `[RESOLVED]`.

## 19. Versioning and migration

- Spec versions are SemVer; files may declare `version:` in frontmatter.
- Within 0.x, breaking changes are allowed with loud tool warnings.
- New inclusions and registry entries are additive; grammar changes are
  breaking.
- A migration appendix will be maintained for each breaking version.

## 20. How to contribute (proposal)

1. Discuss in issues/PRs; every normative change needs a decision record
   (context → decision → consequences → alternatives).
2. Spec text and decision records are CC-BY-4.0; reference implementations
   are Apache-2.0.
3. Ratification: maintainer group + a comment period; the conformance suite
   must pass before a version is frozen.

## 21. Open questions

### 21.1 Resolved this epoch (from first review round)

- Q1 — `|` is the default delimiter; `,`, `;`, TAB, etc. are declared per
  file. TAB caveats documented (§8).
- Q2/Q3 — continuation stays `+`; `#` line comments stay (CSVX-only, not
  converted; cell comments convert) (§9.3, §13.4).
- Q4 — only types propagate by default; styles/formats opt-in (§9.2).
- Q5 — `blank_row` marker optional and disabled by default; explicit
  spellings exist (`:null:` row, `||`); `table.range` declared (§9.6).
- Q6 — unknown frontmatter keys are allowed and preserved, never errors
  (§7).
- Q7 — `{{…}}` content is schema-free; complex features (conditional
  formatting) may live there without spec growth (§11.3).
- Q8 — header types propagate by default; header cells are exempt from the
  column type (§9.2).
- Q9 — both named styles `#name` and CSS classes `.class` (§11.4).
- Q10 — `audio`/`image`/`video` stay; encoding sniffing is future work.
- Q11 — complex constraints live in code inclusions (`{{min: 0, max: 10}}`);
  date-format spelling still open (Q17).
- Q12 — formulas are never touched; converter fidelity (grid + sheet
  names/order) guarantees formulas keep working (§11.2, §18).
- Q13 — single file, `---` sheet dividers, configs in main frontmatter
  (`sheets:`) *and* per-sheet frontmatters (§9.7).
- Q14 — `colspan`/`rowspan` advisory; converters map to merges; Markdown
  view may render spanned titles (§11.3.1).
- Q15 — "LLM-readable" is defined as Markdown-table resemblance; benchmarks
  will measure it (§17, §18).
- Q16 — monorepo with per-tool packages; split later if needed (§18).
- Q17 — `:date(fmt):` stays in-type; colons inside params
  (`:date(hh:mm:ss):`) do **not** collide: param mode runs until the first
  `):` (§11.1.2).
- Q18 — YAML/JSON/CSS quoting inside inclusions is relaxed (both quote
  styles accepted by parsers); formulas are excluded from alternation and
  stored verbatim (§8.1, §11.2).
- Q20 — the `---` divider is always active; converters name unnamed sheets
  `Sheet1`, `Sheet2`, … (xlsx convention) (§9.7).
- Q22 — error sugar tokens added: `:div0:` `:nref:` `:nvalue:` `:nname:`
  `:nnum:`; any other code uses `:err(code):` (§11.1.5).
- Q23 — backtick regions are wrapper-protected, so formulas never need
  doubling (§8, §11.2).
- Q24 — tools are proto-packages that graduate to standalone repos; the
  spec maintains an implementation index (§18).
- #2/#4 — formulas are never re-quoted; the continuation marker never needs
  escaping (literal trailing `+` = wrap the field) (§8, §11.2, §13.4).
- #10 — `table.rows`/`table.cols` (numeric, coordinate-agnostic) replace
  the xlsx-style range (§9.6).
- Q19 — no per-sheet frontmatter: all sheet configuration lives in the main
  frontmatter `sheets:` list; unconfigured sheets use defaults (§9.7).
- Q21 — one-line frontmatter canonical spelling is flow YAML; JSON is
  accepted as input (YAML subset) (§6.1).
- Q25 — `:periodic(repetend):` canonical (`0.1 :periodic(3):` = 0.1(3)); no
  `:p(3):` alias, no math constants (§11.1.5).
- Q26 — custom date formats stay advisory in strict mode until the XLSX
  converters define a format-token contract (§11.1.2, §21.2).
- Continuation — confirmed: bare unwrapped `5+` is a continuation by
  definition; `"5+"` or `5\+` is the literal string (§13.4).

### 21.2 Closed this epoch

All questions from the review rounds are resolved (§21.1). New questions
raised by later epochs are tracked in ROADMAP.md. One item is deliberately
deferred, not decided:

- Q26 — custom date-format validation in strict mode: ISO default formats
  are validated; custom formats stay advisory until the XLSX converters
  land and define a format-token contract (§11.1.2).

---

## Appendix A — Type registry quick reference

`string text int float bool date datetime time duration percent currency url
email phone uuid json yaml bytes audio image video any null empty`
(aliases: `str integer number real double boolean uri`) — see §11.1.1.
Special tokens: `nan inf ninf na err err(code) div0 nref nvalue nname nnum periodic(repetend)` — §11.1.5.
Date/time accept format params: `date(fmt) datetime(fmt) time(fmt)` —
§11.1.2.

## Appendix B — Code-inclusion key registry (advisory)

`format link url tags note colspan rowspan sort validate min max pattern
enum icon id meta` — see §11.3.1.

## Appendix C — Annotated kitchen-sink example

```csvx
---
version: "0.2.0"
dialect:
  csv:
    delimiter: "|"
  csvx:
    formula_dialect: xlsx
    code_format: yaml
styles:
  negative: "color: #c00;"
  header: "font-weight: bold; background: #f0f0f0;"
types:
  hexcolor: "^#[0-9a-fA-F]{6}$"
features:
- name: item
  dtype: string
- name: qty
  dtype: int
- name: unit_price
  dtype: float
- name: total
  dtype: float
meta:
  title: Kitchen sink
---
item|qty|unit_price|total
Widget|12|3.50|42`=B2*C2`
Gadget|7|9.99|69.93`=B3*C3`
"Bolt, M4"|150|0.05|7.50`=B4*C4`
# formatting note: totals are computed by the spreadsheet app
Subtotal|+
17|+
10.49|154.43`=SUM(D2:D4)`
Tint|5|0.80|4.00 [[#negative]]/*check price @lsjcp*/
Config|`=VLOOKUP("Tint",A2:D6,4,FALSE)`|{{note: "computed"}}|[[#header]]
31.12.2024 :date(dd.MM.yyyy):|:inf:|{{min: 0, max: 10}}|{{'link': 'https://example.com'}}
```

Notes: header types are omitted because `features:` declares them;
`"Bolt, M4"` is wrapped because it contains the delimiter; the `Subtotal`
row is a staircase continuation; `[[#negative]]` references a named style;
the `#` line is CSVX-only; the last row shows a formatted date, a special
value, validation metadata in the code inclusion, and quote alternation
(`'` strings under a `"` wrapper).
