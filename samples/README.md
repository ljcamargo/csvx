# CSVX samples

One file per feature, each written against [SPEC.md](../SPEC.md) (draft
0.2.0). Conformance checking against these files lands with the reference
parser in Epoch 3 — for now they are the *targets* the parser must satisfy.

| Sample | Shows | Spec sections |
|---|---|---|
| [hello.csvx](hello.csvx) | minimal file, no frontmatter, defaults | §7.2 |
| [user-example.csvx](user-example.csvx) | the running example: header types, formulas, style, comment, staircase | §2.1, §9.2, §11, §13 |
| [types.csvx](types.csvx) | HF-style `features`, dtype params `:date(dd.MM.yyyy):`, `:audio:`, specials `:na:` `:err(code):` | §7.4, §11.1 |
| [formulas.csvx](formulas.csvx) | comma dialect, formulas verbatim, wrapped field with backtick protection (`"`+`,` inside a formula) | §8, §11.2 |
| [styling.csvx](styling.csvx) | raw CSS, named styles `[[#negative]]`, CSS class `[[.small]]` | §11.4 |
| [code-inclusions.csvx](code-inclusions.csvx) | schema-free `{{...}}` YAML, quote alternation (`'` under `"` wrapper), nested brace balancing | §8.1, §11.3 |
| [comments.csvx](comments.csvx) | `#` line comments (CSVX-only) vs `/* */` cell comments (@-mentions) | §9.3, §11.5 |
| [continuation.csvx](continuation.csvx) | staircases, empty segments (blank line inside a cell), quoted fields with the `+` outside the wrapper, whole-cell rule | §13 |
| [dialects.csvx](dialects.csvx) | `,` delimiter + `'` wrapper → inclusions use `"` | §8.1 |
| [sheets.csvx](sheets.csvx) | multi-sheet: `sheets:` config in main frontmatter, `---` dividers | §9.7 |
| [oneline.csvx](oneline.csvx) | one-line flow-YAML frontmatter | §6.1 |
| [specials.csvx](specials.csvx) | `:nan:` `:inf:` `:ninf:` `:na:` `:err(#DIV/0!):` `:div0:` `:nref:` `:periodic(3):` | §11.1.5 |
| [escapes.csvx](escapes.csvx) | every escape in the collision matrix round-trips (§12.3): `\\` `\`` `\{\{` `\[[` `/\*` `\:` `\#` `"5+"` `\ ` `"---"` | §12.3 |
| [quotes.csvx](quotes.csvx) | mid-field `"` literal in unwrapped fields, `""` doubling in wrapped fields, wrapped field with continuation | §8 |
| [kitchen-sink.csvx](kitchen-sink.csvx) | everything at once (Appendix C of the spec) | Appendix C |
| [headerless.csvx](headerless.csvx) | `header: false` + declared `cols` | §7.1, §9.6 |

## Grammar conformance checklist

Every grammar production in §15 is exercised by at least one sample:

| Production | Covered by |
|---|---|
| frontmatter (block form) | most samples |
| frontmatter (one-line form) | oneline.csvx |
| divider-line | sheets.csvx |
| wrapped-field (doubling) | quotes.csvx |
| wrapped-field (backtick protection) | formulas.csvx |
| bare-field (mid-field quote literal) | quotes.csvx, code-inclusions.csvx |
| type-marker with params | types.csvx, specials.csvx |
| formula | user-example.csvx, formulas.csvx |
| code (balanced braces) | code-inclusions.csvx |
| style | styling.csvx |
| comment | comments.csvx |
| cont-marker (outside wrapper) | continuation.csvx, quotes.csvx, kitchen-sink.csvx |
| escapes (all rows) | escapes.csvx |

> Note: samples that use YAML block scalars (`meta.note: >`) require a
> full YAML parser for the frontmatter (PyYAML); the documented YAML-subset
> fallback does not implement block scalars.
