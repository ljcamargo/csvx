# CSVX examples

These examples are organized for reading before testing. Start with the three
body-first files below; frontmatter appears only where an example needs
non-default document configuration or a registry.

The files are normative examples for the current draft. Automated conformance
checking is planned with the reference parser; until then, they are targets
for that work rather than a verified test suite.

## Start here

| Example | What to notice |
|---|---|
| [hello.csvx](hello.csvx) | A default CSVX table has no frontmatter. |
| [user-example.csvx](user-example.csvx) | Header types, formulas, styles, comments, and a readable staircase in one small report. |
| [continuation.csvx](continuation.csvx) | Multi-line cells, an empty segment, and a wrapped continuation. |

## Core annotations

| Example | What it demonstrates | Spec |
|---|---|---|
| [types.csvx](types.csvx) | `features:` for a real column schema, type propagation, dates, media references, and errors. | §7.3–§7.4, §11.1 |
| [formulas.csvx](formulas.csvx) | Formulas stored verbatim, including a wrapped formula containing `|` and `"`. | §8, §11.2 |
| [styling.csvx](styling.csvx) | Named styles, an inline style, and a CSS class. | §11.4 |
| [annotations.csvx](annotations.csvx) | YAML/JSON-like cell metadata, links, validation, and nested maps. | §8.1, §11.3 |
| [comments.csvx](comments.csvx) | CSVX-only line comments versus cell comments that map to notes. | §9.3, §11.5 |
| [specials.csvx](specials.csvx) | Spreadsheet special values and error tokens. | §11.1.5 |

## Configuration and layout

| Example | Why it has frontmatter | Spec |
|---|---|---|
| [syntax.csvx](syntax.csvx) | It changes the file-wide delimiter and wrapper quote. | §8.1 |
| [sheets.csvx](sheets.csvx) | It names and configures sheets. | §9.7 |
| [oneline.csvx](oneline.csvx) | It shows generated one-line flow-YAML frontmatter. | §6.1 |
| [headerless.csvx](headerless.csvx) | It disables the default header and declares a width. | §7.1, §9.6 |

## Precision and integration cases

| Example | What it demonstrates | Spec |
|---|---|---|
| [quotes.csvx](quotes.csvx) | Literal mid-field quotes, RFC doubling, and a wrapped field continued outside its wrapper. | §8, §13.4 |
| [escapes.csvx](escapes.csvx) | The collision matrix: every necessary escape, and no generalized escaping. | §12.3 |
| [kitchen-sink.csvx](kitchen-sink.csvx) | A compact integration example with a schema, named style, formula, annotation, and subtotal staircase. | Appendix C |

## Grammar coverage

The future conformance suite will cover malformed input as well as these valid
examples. The valid grammar productions are represented here:

| Production | Example |
|---|---|
| optional, block, and one-line frontmatter | hello.csvx; styles.csvx/types.csvx; oneline.csvx |
| sheet divider | sheets.csvx |
| wrapped field, doubling, protected backticks | quotes.csvx; formulas.csvx |
| type marker with parameters | types.csvx; specials.csvx |
| formula, annotation, style, comment | formulas.csvx; annotations.csvx; styling.csvx; comments.csvx |
| continuation marker outside a wrapper | continuation.csvx; quotes.csvx |
| collision escapes | escapes.csvx |
