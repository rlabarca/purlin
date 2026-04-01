# SFC Taxonomy — Purlin Framework

## Anchors

1. **schema_spec_format** (schema/) — 3-section spec format: required sections, RULE-N/PROOF-N numbering, metadata fields (Requires, Scope, Stack). Governs all specs and the sync_status parser.
2. **schema_proof_format** (schema/) — Proof file JSON schema + marker syntax. JSON structure, feature-scoped overwrite merge, tier values. Governs all 3 proof plugins and sync_status.
3. **security_no_dangerous_patterns** (schema/) — No eval/exec, no shell=True, no hardcoded credentials. Grep-based negative assertions.

## Categories

### hooks/ (2 features)
| File name | Description | Anchors |
|-----------|-------------|---------|
| gate_hook | Invariant write protection with bypass lock mechanism | security_no_dangerous_patterns |
| session_start | Runtime state cleanup on session init | security_no_dangerous_patterns |

### mcp/ (2 features)
| File name | Description | Anchors |
|-----------|-------------|---------|
| mcp_server | JSON-RPC 2.0 stdio server — transport, tool dispatch, error handling, manifest | schema_spec_format, schema_proof_format, security_no_dangerous_patterns |
| config_engine | Two-file config resolution with copy-on-first-access | security_no_dangerous_patterns |

### proof/ (1 consolidated feature)
| File name | Description | Anchors |
|-----------|-------------|---------|
| proof_plugins | Proof collection across pytest, Jest, and shell — marker parsing, feature-scoped overwrite, JSON emit. Per-implementation rules for each framework. | schema_proof_format, security_no_dangerous_patterns |

### instructions/ (3 features)
| File name | Description | Anchors |
|-----------|-------------|---------|
| purlin_agent | Agent definition structure — core loop, spec format, hard gates, skill routing | schema_spec_format |
| purlin_skills | 12 skill SKILL.md files — structural validation of required sections | — |
| purlin_references | 8 reference docs — format specs, quality guide, conventions | schema_spec_format, schema_proof_format |

## Summary

- **Anchors:** 3
- **Categories:** 4 (hooks, mcp, proof, instructions)
- **Features:** 8
- **Total specs to generate:** 11
