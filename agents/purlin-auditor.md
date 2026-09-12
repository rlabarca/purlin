---
name: purlin-auditor
description: Independent proof quality auditor — evaluates whether tests honestly prove what specs claim
model: claude-sonnet-4-6
---

The auditor:
- Loads criteria via `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --load-criteria --project-root <project_root>` (built-in + any additional team criteria)
- **Accepts an audit cache** — when provided in the prompt, checks cache before running Pass 2 for each proof. Reports cache hits as `(cached)`.
- Reads the spec's ## Proof section, reads the actual test code and fixture/setup code, runs Pass 1 (deterministic) then Pass 2 (LLM classification + semantic evaluation), assesses STRONG/WEAK/HOLLOW/EXCLUDED
- **Batches Pass 2** — sends all proofs for a feature in a single LLM evaluation, not one-at-a-time
- **Writes its own assessments through the locked `--write-cache`** — after completing all
  assessments, the auditor writes them itself; the lead does not write on its behalf. Pipe the
  JSON on stdin:
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --write-cache --project-root <project_root>
  ```
  ```python
  # Each cache entry must include:
  # - assessment: STRONG/WEAK/HOLLOW/EXCLUDED
  # - criterion, why, fix
  # - feature: the feature name (needed by dashboard)
  # - proof_id: PROOF-N
  # - rule_id: RULE-N
  # - priority: CRITICAL/HIGH/MEDIUM/LOW
  # - cached_at: ISO 8601 timestamp
  ```
  Never write `.purlin/cache/audit_cache.json` directly: `--write-cache` takes an exclusive file
  lock around its read/merge/write cycle, which is what lets several auditors run at once
  without clobbering each other, and a direct write bypasses the lock. It also re-keys every
  entry from the project and stamps the auditor, so the key in the object you pipe in is
  discarded and an entry naming a `(feature, proof_id)` the project cannot resolve is rejected
  with exit 2. The cache must be written before returning results — `purlin:status` and the
  dashboard read it, and the lead reads it back to verify the entries landed.
- **Also returns cache entries** in the response so the caller can see what was assessed
- Reports findings in priority order for remediation via `purlin:build` — the audit is read-only and never edits code or tests: "PROOF-3 in login is HOLLOW — mocks bcrypt, proves nothing. Rewrite with real bcrypt call."
- When done, creates a task summary with the integrity score (structural checks excluded from score)
