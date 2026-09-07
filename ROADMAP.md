# CSVX — Roadmap

Tracking progress from draft proposal toward a ratified open standard.
Spec: `SPEC.md` (current: **0.2.0-draft**, Epoch 1 — discussion closed).
All design decisions from the review rounds are recorded in `SPEC.md §21.1`.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## Epoch 1 — Proposal & decisions (current)

Goal: a stable, discussable specification. **No implementation work.**

- [x] Spec draft v0.1.0 — full proposal (anatomy, schema, inclusions,
      escaping matrix, continuation, round-trip, security, LLM guidance)
- [x] Review round 1 — resolving: CSV-shaped not CSV-bound; quote
      alternation; one-line frontmatter; multi-sheet; null/specials;
      date formats; continuation outside the wrapper; no per-sheet
      frontmatter; flow-YAML one-line; `:periodic(n):`; error sugar tokens
- [x] Review round 2 — formula byte-fidelity (backtick-protected regions,
      never re-quoted); no-escape continuation; coordinate-agnostic
      `table.rows`/`cols`; relaxed YAML/JSON/CSS quoting
- [x] All §21 open questions resolved (deferred: Q26 date-format
      validation, to be decided with the converters)
- [x] ROADMAP.md created

**Exit criteria for Epoch 1:** spec text agreed by the community;
`[PROPOSED]`/`[RESOLVED]` markers audited; name "CSVX" availability checked.

---

## Epoch 2 — Repo scaffolding, README, samples & schema (next)

- [ ] `README.md` — global synoptic: catchy hero, why, key features, quick
      tour, when-not-to-use, repo map, status (inspired by toon-format's
      README; OpenAPI-style pro sections)
- [ ] Repo scaffolding: `CONTRIBUTING.md`, `LICENSE.md`, `CHANGELOG.md`,
      `implementations.md` (stub), `benchmarks/` (stub), `docs/adr/` (stub)
- [ ] `samples/` corpus — one file per feature, each verified against the
      spec (hello, user-example, types+dates, formulas, styling, code
      inclusions, comments, continuation staircases, dialects incl. TAB
      and `'`-wrapper, multi-sheet, one-line frontmatter, special values,
      kitchen sink)
- [ ] `samples/README.md` — tour of every feature with pointers to spec
      sections
- [ ] `schema/csvx-frontmatter.schema.json` — JSON Schema for the
      frontmatter (version, dialect, table, columns/features, sheets,
      types, styles, meta)
- [ ] Grammar conformance checklist — map every grammar production (§15)
      to at least one sample/test case
- [ ] Open items raised by repo review: media type & file extension
      (`.csvx`, IANA registration — see TOON's practice), "when not to
      use" guidance, spec-version badge in README

## Epoch 3 — Reference parser (proto-package `tools/csvx-py`)

- [ ] Strict + lenient parse; canonical render; round-trip verification
- [ ] New rules implemented: field-start-only wrapper; mid-field literal
      wrapper chars; backtick-protected regions in wrapped fields;
      marker-outside-wrapper continuation; `:name(params):` type markers
      (date/time formats); brace-balanced `{{…}}` with backtracking
- [ ] CLI: `parse | render | check | md | json | roundtrip`
- [ ] Multi-sheet parsing (dividers, `sheets:` config, inferred dims)
- [ ] One-line flow-YAML frontmatter
- [ ] `tools/csvx-js` proto-package (parallel implementation) — optional,
      only if a second implementation is wanted for cross-checking

## Epoch 4 — Conformance & benchmarks

- [ ] `tests/cases/` adversarial corpus — every escape in §12.3, wrapper
      edge cases, staircase well-formedness, brace balancing, unicode,
      dialects, sheets, one-line frontmatter
- [ ] Round-trip property tests: `parse(render(parse(x))) == parse(x)`
- [ ] Escaping benchmark — schemes A/B/C over realistic + adversarial
      corpora: parse-failure rate, reversibility, byte & token overhead,
      throughput. Re-validates the §12 decisions with data
- [ ] LLM benchmark — token cost + comprehension (Markdown-table
      resemblance baseline), per §17/§18
- [ ] Performance targets: line-based streaming for large datasets

## Epoch 5 — Converters & fidelity contract

- [ ] XLSX → CSVX (sheets, grid, formulas verbatim, comments, styles,
      date formats, merges, special values)
- [ ] CSVX → XLSX (inverse, same grid so formulas keep working)
- [ ] ODS support (stretch)
- [ ] Q26 resolved here: date/number format-token contract between xlsx
      `numFmt` and `:date(fmt):` / `{{format: …}}`

## Epoch 6 — Packaging, skill & ratification

- [ ] Graduate proto-packages to standalone repos; publish to PyPI/npm
- [ ] `implementations.md` — index of reference + community implementations
- [ ] `skill/csvx/SKILL.md` — agent skill for writing/editing CSVX
- [ ] Naming check: registry/GitHub/trademark availability; rename if needed
- [ ] Community review of the full spec; freeze **v1.0.0-rc**
- [ ] Conformance suite green for two independent implementations
- [ ] Ratify **CSVX 1.0.0**

---

## Open / deferred items

- **Q26** — custom date-format validation (deferred to Epoch 5, converters)
- **Escaping benchmark results** may reopen scheme-A/B spacing or the
  trailing-`+` choice (§12.1, §12.3 soft spots) — decisions are
  provisional until Epoch 4 data exists
- **`:periodic:`** xlsx mapping (expanded decimal vs format note) — decide
  in Epoch 5
- **LLM token metrics** may reopen token-economy choices (P3)

## How decisions are recorded

Normative changes to the spec get a decision record in `SPEC.md §21.1`
(and, once adopted, in `docs/adr/`): context → decision → consequences →
alternatives.
