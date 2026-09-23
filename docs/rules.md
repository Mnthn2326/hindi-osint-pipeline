# Rules — Behavioral Boundaries for the Coding Agent

## 1. Scope discipline

- Build only what the current prompt in `implementation_plan.md` specifies. Do not
  add "nice to have" features (retry queues, caching layers, extra endpoints,
  extra config options) unless explicitly asked. Extra unrequested code is extra
  surface area for a 4-person team to debug under deadline.
- Do not silently expand a stage's scope to include a later phase's work (e.g. do
  not add Celery/Redis scheduling while building Prompt 3's ingestion connector —
  that's a later phase per `prd.md`).
- If a prompt is ambiguous, implement the narrowest reasonable interpretation and
  state the assumption in a code comment at the top of the file — do not guess
  silently and do not add speculative flexibility for cases not asked about.

## 2. Code standards

- Python: follow PEP 8. Type-hint all function signatures. No bare `except:` —
  catch specific exceptions.
- Every batch job (ingestion, preprocessing, clustering, extraction, classification,
  consensus) must be runnable as a standalone CLI script (`python -m <module>`)
  with no dependency on any other stage being run in the same process.
- Every batch job must be idempotent: running it twice on the same input must not
  create duplicate rows. Use `content_hash` / existing-row checks per
  `architecture.md`'s data contracts.
- No hardcoded credentials, API keys, or DB connection strings in source files —
  always load from `.env` via `python-dotenv`. `.env` itself is gitignored;
  `.env.example` documents required vars with placeholder values.
- No print-statement debugging left in committed code — use the `logging` module
  at INFO level for pipeline progress, DEBUG for verbose internals.

## 3. Error handling

- External API calls (Reddit, RSS fetches) must handle rate-limit and network
  errors with a retry-with-backoff (max 3 attempts), then log and skip the item
  rather than crashing the whole batch job.
- Model inference calls (NER, NLI) must catch and log per-item failures without
  aborting the batch — one malformed post should not stop processing of the rest.
- Database writes must use transactions per batch (not per-row) for performance,
  but must roll back cleanly on failure rather than leaving partial writes.
- Never silently swallow an exception — always log it, even if the code continues.

## 4. What to avoid

- Do not introduce a new framework, library, or service not listed in
  `tech_stack.md` without flagging it first — this includes swapping the pretrained
  model choices for a "better" alternative found online without checking with the
  team.
- Do not build streaming/real-time infrastructure (Celery Beat, Redis Streams,
  scheduled jobs) in this phase — batch scripts only, per `prd.md` scope.
- Do not build OCR, ASR, or YouTube ingestion in this phase.
- Do not fine-tune any model in this phase — all models are used pretrained,
  zero-shot or off-the-shelf.
- Do not add authentication/authorization to the API or dashboard — this is an
  internal demo tool, not a deployed product, for this phase.
- Do not optimize prematurely (no caching layers, no async rewrites) — get the
  batch pipeline correct and readable first; performance is not a constraint at
  this data scale (see `prd.md` capacity estimation: ~20,000 items/day raw).

## 5. Verification requirement

- No stage is "done" without running it against real data (not synthetic/mocked
  data) and confirming output matches the "Verify" step defined for that prompt
  in `implementation_plan.md`.
- The consensus/disagreement module additionally requires passing unit tests on
  synthetic label distributions (all-agree, 50/50 split, 3-way split) before being
  considered complete — this is the core research contribution and must be
  provably correct, not just "runs without error."

## 6. Communication back to the user

- If a pretrained model fails to load, is gated behind a HuggingFace access
  request, or produces clearly degenerate output (e.g. one label 100% of the
  time), stop and report this rather than proceeding with a broken component
  silently included in the "done" pipeline.
- If a Verify step in `implementation_plan.md` fails, do not move to the next
  prompt — report the failure and the specific check that didn't pass.
