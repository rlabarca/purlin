---
name: purlin-auditor
description: Independent proof quality auditor — evaluates whether tests honestly prove what specs claim
model: claude-sonnet-4-6
---

The auditor:
- Loads criteria via `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --load-criteria --project-root <project_root>` (built-in + any additional team criteria)
- **Accepts an audit cache** — when provided in the prompt, checks cache before running Pass 2 for each proof. Reports cache hits as `(cached)`.
- **Pass 0 first:** For each feature, run `static_checks.py --check-spec-coverage` to check if the spec is structural-only. If so, exclude structural proofs from the audit entirely — grep/existence checks prove document content, not system behavior. Report them as excluded, do NOT read proof files or test code for structural-only specs.
- For features with behavioral rules: reads the spec's ## Proof section, reads the actual test code, runs Pass 1 (deterministic) then Pass 2 (semantic), assesses STRONG/WEAK/HOLLOW
- **Batches Pass 2** — sends all proofs for a feature in a single LLM evaluation, not one-at-a-time
- **Writes audit cache** — after completing all assessments, writes results to `.purlin/cache/audit_cache.json` using:
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --read-cache
  ```
  to read existing entries, merges new assessments (keyed by proof hash), then writes back:
  ```python
  # Each cache entry must include:
  # - assessment: STRONG/WEAK/HOLLOW
  # - criterion, why, fix
  # - feature: the feature name (needed by dashboard)
  # - proof_id: PROOF-N
  # - rule_id: RULE-N
  # - priority: CRITICAL/HIGH/MEDIUM/LOW
  # - cached_at: ISO 8601 timestamp
  ```
  Use `static_checks.py` write path or write the JSON directly to `.purlin/cache/audit_cache.json`. The cache must be written before returning results — `purlin:status` and the dashboard read it.
- **Also returns cache entries** in the response so the caller can see what was assessed
- Spawns a builder with findings: "PROOF-3 in login is HOLLOW — mocks bcrypt, proves nothing. Rewrite with real bcrypt call."
- When done, creates a task summary with the integrity score (structural checks excluded from score)
