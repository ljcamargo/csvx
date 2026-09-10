# Contributing to CSVX

CSVX is an open, community-driven standard. The spec is the contract; this
repo hosts it plus reference tooling. Everyone is welcome — reporters,
data donors, implementers, reviewers.

## How to contribute

1. **Read [SPEC.md](SPEC.md)** and [ROADMAP.md](ROADMAP.md) first.
2. **Open an issue** for:
   - bugs or ambiguities in the spec text;
   - real-world cells that break the escape matrix (§12.3) — these are gold
     for the benchmarks;
   - proposals for new registries (types, tokens, annotation keys) or grammar.
3. **Pull requests** for: spec text, samples, schema, reference parsers,
   converters, benchmarks, docs. Small, focused PRs review faster.

## Decision records

Every normative change to the spec needs a decision record (see
[docs/adr](docs/adr/README.md) for the template once populated):

**context → decision → consequences → alternatives**

Until `docs/adr/` is populated, decisions are recorded inline in
[SPEC.md §21.1](SPEC.md#21-open-questions) with a `[RESOLVED]` marker and a
pointer to the discussion.

## Conformance

- Spec text changes must not break existing `[RESOLVED]` decisions without
  a new decision record and a version bump.
- Reference implementations must pass the conformance corpus (Epoch 4) and
  the round-trip property `parse(render(parse(x))) == parse(x)`.
- New samples must be spec-valid and listed in
  [samples/README.md](samples/README.md) with their spec-section pointers.

## Licensing

- Spec text, docs, and samples: **CC-BY-4.0**.
- Code: **Apache-2.0** (SPDX headers in each file).
- By contributing you agree to license your contributions accordingly.

## Code of conduct

Be constructive. Spec arguments are welcome; personal ones are not.
(Full CoC TBD before ratification.)
