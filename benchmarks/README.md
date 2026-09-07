# Benchmarks (planned — Epoch 4)

This directory will hold the reproducible benchmark harnesses defined in
[SPEC.md §18](SPEC.md#18-conformance-and-testing-plan-tooling-to-be-built-after-approval)
and tracked in [ROADMAP.md](../ROADMAP.md). Nothing here yet.

Planned, each with a seeded, reproducible corpus and JSON/Markdown output:

1. **Escaping benchmark** — schemes A/B/C (§12.1) over realistic +
   adversarial cells: parse-failure rate, reversibility, byte & token
   overhead, throughput. Expected to *validate or reopen* the §12
   decisions (spacing, trailing `+`).
2. **Token benchmark** — CSVX vs plain CSV vs XLSX-rendered, measured with
   real LLM tokenizers (tiktoken et al.).
3. **LLM comprehension benchmark** — prompt tasks over the same data in
   each format, with Markdown-table resemblance as the baseline (§17).

Corpus donors: real-world cells that stress the escape matrix (§12.3) are
especially welcome — open an issue or PR.
