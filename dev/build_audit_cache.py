"""Build audit cache for the 2026-04-06 re-audit."""
import hashlib, json, sys

def proof_hash(feature, proof_id, rule_id):
    return hashlib.sha256(f'{feature}:{proof_id}:{rule_id}'.encode()).hexdigest()[:16]

now = '2026-04-06T00:00:00Z'
cache = {}

def add(feature, proof_id, rule_id, assessment, criterion, why, fix, priority='MEDIUM'):
    h = proof_hash(feature, proof_id, rule_id)
    cache[h] = {
        'assessment': assessment, 'criterion': criterion, 'why': why, 'fix': fix,
        'feature': feature, 'proof_id': proof_id, 'rule_id': rule_id,
        'priority': priority, 'cached_at': now,
    }

# ── purlin_report ─────────────────────────────────────────────────────────────
strong_pr = [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-4','RULE-4'),
             ('PROOF-6','RULE-6'),('PROOF-7','RULE-7'),('PROOF-10','RULE-10'),
             ('PROOF-14','RULE-14'),('PROOF-16','RULE-16'),('PROOF-17','RULE-17'),
             ('PROOF-18','RULE-18'),('PROOF-19','RULE-19'),('PROOF-20','RULE-20'),
             ('PROOF-21','RULE-21'),('PROOF-22','RULE-22'),('PROOF-23','RULE-23'),
             ('PROOF-24','RULE-24'),('PROOF-25','RULE-25')]
for p, r in strong_pr:
    add('purlin_report', p, r, 'STRONG', 'behavioral_assertions',
        'Playwright test uses specific selectors, DOM attribute/text checks, and computed style verification that directly proves the rule.', 'N/A')

hollow_pr = [
    ('PROOF-3','RULE-3','assert incomplete_card is not None is tautological; real assertions follow but Pass 1 flags the whole function.',
     'Remove is not None guard; let subsequent .inner_text() raise if element absent.'),
    ('PROOF-5','RULE-5','assert first_row is not None and assert len > 0 are tautological guards flagged by Pass 1.',
     'Remove is not None guards; let .click() raise on missing element.'),
    ('PROOF-8','RULE-8','assert staleness_text is not None is tautological before .get_attribute() check.',
     'Remove is not None guard; proceed directly to .inner_text() and .get_attribute().'),
    ('PROOF-9','RULE-9','assert staleness_text is not None is tautological.',
     'Remove is not None guard before css_class check.'),
    ('PROOF-11','RULE-11','assert len(ext_icons) > 0 is tautological; title check follows but function is flagged.',
     'Replace with direct ext_icons[0].get_attribute() and assert on the value directly.'),
    ('PROOF-12','RULE-12','assert len(rows_before) == 2 after is not None check causes tautological flag.',
     'Remove the is not None guard; keep the count assertion.'),
    ('PROOF-13','RULE-13','assert footer_link is not None before href check is tautological.',
     'Remove is not None guard; assert href directly.'),
    ('PROOF-15','RULE-15','assert stale_el is not None is the sole meaningful assertion — proves only element presence.',
     'Assert on stale_el.get_attribute("class") to verify amber warning styling.'),
    ('PROOF-26','RULE-26','assert block is not None before real checks is tautological.',
     'Remove is not None guard; proceed to evaluate() calls.'),
    ('PROOF-27','RULE-27','assert title is not None is tautological before content checks.',
     'Assert directly on title attribute content without is not None guard.'),
    ('PROOF-28','RULE-28','assert stale_badge is not None is tautological.',
     'Remove is not None guard.'),
    ('PROOF-29','RULE-29','assert uw_section is not None is tautological guard.',
     'Remove is not None guard; proceed to .inner_text() check.'),
    ('PROOF-30','RULE-30','assert desc_block is not None is tautological.',
     'Remove is not None guard; assert .inner_text() content directly.'),
]
for p, r, w, f in hollow_pr:
    add('purlin_report', p, r, 'HOLLOW', 'tautological_assertion', w, f, 'HIGH')

# ── dashboard_visual ──────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),
             ('PROOF-4','RULE-4'),('PROOF-5','RULE-5'),('PROOF-6','RULE-6'),
             ('PROOF-7','RULE-7'),('PROOF-8','RULE-8'),('PROOF-10','RULE-10'),
             ('PROOF-11','RULE-11')]:
    add('dashboard_visual', p, r, 'STRONG', 'behavioral_assertions',
        'Playwright computed-style verification against exact hex values or CSS class presence directly proves the visual rule.', 'N/A')
add('dashboard_visual','PROOF-9','RULE-9','HOLLOW','tautological_assertion',
    'assert True flagged by Pass 1 — tautological assertion in test body.',
    'Replace bare assert True with actual computed style check for untested/no-proofs badge styling.','HIGH')

# ── drift ─────────────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),
             ('PROOF-4','RULE-4'),('PROOF-5','RULE-5'),('PROOF-6','RULE-6'),
             ('PROOF-7','RULE-7'),('PROOF-10','RULE-10'),('PROOF-11','RULE-11')]:
    add('drift', p, r, 'STRONG', 'behavioral_assertions',
        'Test verifies JSON structure and field values with exact literal assertions, directly proving the rule.', 'N/A')
add('drift','PROOF-8','RULE-8','HOLLOW','tautological_assertion',
    'assert True flagged by Pass 1 in test_coverage_gap_drift_flag.',
    'Replace bare assert True with assertion on behavioral_gap field value in the drift result.','HIGH')
add('drift','PROOF-9','RULE-9','HOLLOW','tautological_assertion',
    'assert True flagged by Pass 1 in test_drift_flags_array.',
    'Assert on actual drift_flags array contents with specific reason field.','HIGH')

# ── report_data ───────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-4','RULE-4'),
             ('PROOF-5','RULE-5'),('PROOF-8','RULE-8'),('PROOF-9','RULE-9'),
             ('PROOF-10','RULE-10'),('PROOF-11','RULE-11'),('PROOF-13','RULE-13'),
             ('PROOF-14','RULE-14'),('PROOF-17','RULE-17'),('PROOF-18','RULE-18'),
             ('PROOF-21','RULE-21')]:
    add('report_data', p, r, 'STRONG', 'behavioral_assertions',
        'Test uses exact literal assertions on computed values, field presence, and counts that directly prove the rule.', 'N/A')
hollow_rd = [
    ('PROOF-3','RULE-3','assert True in test_report_file_is_valid_js_with_json — tautological.',
     'Assert on actual JSON parse result or validate PURLIN_DATA variable presence.'),
    ('PROOF-6','RULE-6','assert True in test_passing_features_have_vhash_others_do_not — tautological.',
     'Assert on specific vhash field values for known features.'),
    ('PROOF-7','RULE-7','assert True in test_receipt_fields_present_when_receipt_file_exists — tautological.',
     'Assert on specific receipt field values (commit, timestamp, stale).'),
    ('PROOF-12','RULE-12','assert True in test_anchor_with_source_includes_source_url — tautological.',
     'Assert on actual source_url field value in anchor feature.'),
    ('PROOF-15','RULE-15','assert True in test_audit_summary_fields_present_and_null_when_no_cache — tautological.',
     'Assert on specific audit_summary field names and null values.'),
    ('PROOF-16','RULE-16','assert True in test_per_feature_audit_populated_from_cache — tautological.',
     'Assert on specific audit field values from the cache.'),
    ('PROOF-20','RULE-20','assert True in test_passing_verified_always_100pct_coverage — tautological.',
     'Assert on proved == total for each PASSING/VERIFIED feature.'),
]
for p, r, w, f in hollow_rd:
    add('report_data', p, r, 'HOLLOW', 'tautological_assertion', w, f, 'HIGH')

# ── config_engine ──────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),
             ('PROOF-4','RULE-4'),('PROOF-5','RULE-5'),('PROOF-6','RULE-6'),
             ('PROOF-7','RULE-7'),('PROOF-9','RULE-9'),('PROOF-10','RULE-10'),
             ('PROOF-11','RULE-4')]:
    add('config_engine', p, r, 'STRONG', 'behavioral_assertions',
        'Test uses literal expected values for all assertions, verifying file operations and config resolution precisely.', 'N/A')
add('config_engine','PROOF-12','RULE-8','HOLLOW','logic_mirroring',
    'test_local_override_wins_in_merge reads shared_before from config.json then asserts shared_after == shared_before — expected derived from same source.',
    'Remove shared_before read; assert config.json content against literal dict {"report": True, "version": "0.9.0"}.','HIGH')
add('config_engine','PROOF-8','RULE-8','HOLLOW','logic_mirroring',
    'test_writes_only_to_local reads shared_mtime before then asserts mtime unchanged after — expected computed by same function.',
    'Remove mtime comparison; verify config.json content unchanged using literal dict comparison.','HIGH')

# ── pre_push_hook ──────────────────────────────────────────────────────────────
add('pre_push_hook','PROOF-15','RULE-8','STRONG','behavioral_assertions',
    'Shell conditional if/else pair — condition is the test, proves hook blocks push on strict required failure.','N/A')
add('pre_push_hook','PROOF-16','RULE-8','STRONG','behavioral_assertions',
    'Shell conditional if/else pair — verifies hook allows push on success.','N/A')

# ── mcp_transport ──────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),
             ('PROOF-4','RULE-4'),('PROOF-5','RULE-5'),('PROOF-6','RULE-6'),('PROOF-7','RULE-7')]:
    add('mcp_transport', p, r, 'STRONG', 'behavioral_assertions',
        'Test verifies exact MCP protocol response fields and values, directly proving transport behavior.', 'N/A')

# ── skill_anchor ───────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),('PROOF-4','RULE-4')]:
    add('skill_anchor', p, r, 'STRONG', 'behavioral_assertions',
        'Test reads actual skill file and asserts specific text content/patterns, proving the rule requirement is present.', 'N/A')

# ── skill_drift ────────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),
             ('PROOF-4','RULE-4'),('PROOF-5','RULE-5')]:
    add('skill_drift', p, r, 'STRONG', 'behavioral_assertions',
        'Test reads actual skill file and asserts specific text content/patterns, proving the rule requirement is present.', 'N/A')

# ── skill_find ─────────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),('PROOF-4','RULE-4')]:
    add('skill_find', p, r, 'STRONG', 'behavioral_assertions',
        'Test reads actual skill file and asserts specific text content/patterns, proving the rule requirement is present.', 'N/A')

# ── skill_rename ───────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3')]:
    add('skill_rename', p, r, 'STRONG', 'behavioral_assertions',
        'Test reads actual skill file and asserts specific text content/patterns, proving the rule requirement is present.', 'N/A')

# ── skill_spec ─────────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),
             ('PROOF-4','RULE-4'),('PROOF-5','RULE-5'),('PROOF-6','RULE-6')]:
    add('skill_spec', p, r, 'STRONG', 'behavioral_assertions',
        'Test reads actual skill file and asserts specific text/regex patterns, proving the rule requirement is present.', 'N/A')

# ── skill_status ───────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),('PROOF-4','RULE-4')]:
    add('skill_status', p, r, 'STRONG', 'behavioral_assertions',
        'Test reads actual skill file and asserts specific text content/patterns, proving the rule requirement is present.', 'N/A')

# ── skill_unit_test ────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),
             ('PROOF-4','RULE-4'),('PROOF-5','RULE-5')]:
    add('skill_unit_test', p, r, 'STRONG', 'behavioral_assertions',
        'Test reads actual skill file and asserts specific text content/patterns, proving the rule requirement is present.', 'N/A')

# ── schema_proof_format ────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),
             ('PROOF-4','RULE-4'),('PROOF-5','RULE-5'),('PROOF-6','RULE-6'),('PROOF-7','RULE-7')]:
    add('schema_proof_format', p, r, 'STRONG', 'behavioral_assertions',
        'Test verifies format enforcement through integration with sync_status or file system checks with literal assertions.', 'N/A')

# ── schema_spec_format ─────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),
             ('PROOF-4','RULE-4'),('PROOF-5','RULE-5'),('PROOF-6','RULE-6'),('PROOF-7','RULE-7')]:
    add('schema_spec_format', p, r, 'STRONG', 'behavioral_assertions',
        'Test verifies spec format enforcement with real assertion on parser output or file content.', 'N/A')

# ── purlin_skills ──────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),
             ('PROOF-4','RULE-4'),('PROOF-5','RULE-5'),('PROOF-6','RULE-6'),
             ('PROOF-7','RULE-7'),('PROOF-8','RULE-8'),('PROOF-9','RULE-9'),
             ('PROOF-10','RULE-10'),('PROOF-11','RULE-11'),('PROOF-12','RULE-12'),
             ('PROOF-13','RULE-13'),('PROOF-14','RULE-14'),('PROOF-15','RULE-15')]:
    add('purlin_skills', p, r, 'STRONG', 'behavioral_assertions',
        'Test reads actual skill files and asserts specific text patterns with regex/literal checks that directly prove the requirement is present.', 'N/A')

# ── purlin_teammate_definitions ────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),('PROOF-4','RULE-4')]:
    add('purlin_teammate_definitions', p, r, 'STRONG', 'behavioral_assertions',
        'Test reads agent definition files and asserts specific frontmatter field presence with literal assertions.', 'N/A')

# ── purlin_config ──────────────────────────────────────────────────────────────
add('purlin_config','PROOF-1','RULE-1','STRONG','behavioral_assertions',
    'Test calls write then read and asserts the round-tripped value matches, proving the MCP tool integrates with update_config.','N/A')

# ── skill_build ────────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),('PROOF-4','RULE-4')]:
    add('skill_build', p, r, 'HOLLOW', 'no_assertions',
        'Test delegates entirely to a helper function with no inline assertions — static checker sees no assert statements in function body.',
        'Add inline assertions directly in the test function body.','HIGH')
for p, r in [('PROOF-5','RULE-5'),('PROOF-6','RULE-6'),('PROOF-7','RULE-7')]:
    add('skill_build', p, r, 'STRONG', 'behavioral_assertions',
        'Test has inline assert statements checking specific text patterns in the build skill file.','N/A')
add('skill_build','PROOF-8','RULE-8','STRONG','behavioral_assertions',
    'Shell conditional if/else with grep check proves build proof fixer mode documentation.','N/A')

# ── skill_verify ───────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3'),('PROOF-4','RULE-4')]:
    add('skill_verify', p, r, 'HOLLOW', 'no_assertions',
        'Test delegates entirely to helper function with no inline assertions — static checker sees no assert statements in function body.',
        'Add inline assertions directly in the test function body.','HIGH')
add('skill_verify','PROOF-5','RULE-5','STRONG','behavioral_assertions',
    'test_verify_prohibits_modifying_files has inline assertion checking for NEVER modify text.','N/A')
add('skill_verify','PROOF-6','RULE-6','STRONG','behavioral_assertions',
    'Shell conditional if/else with grep proves verify Step 4e independent audit documentation.','N/A')

# ── skill_audit ────────────────────────────────────────────────────────────────
for p, r in [('PROOF-1','RULE-1'),('PROOF-2','RULE-2'),('PROOF-3','RULE-3')]:
    add('skill_audit', p, r, 'HOLLOW', 'no_assertions',
        'Test delegates entirely to helper function with no inline assertions — static checker sees no assert statements in function body.',
        'Add inline assertions directly in the test function body.','HIGH')
add('skill_audit','PROOF-6','RULE-6','STRONG','behavioral_assertions',
    'Shell conditional if/else with grep proves re-audit re-check loop documentation.','N/A')
add('skill_audit','PROOF-8','RULE-8','STRONG','behavioral_assertions',
    'Shell conditional if/else with grep proves anchor rule handling documentation.','N/A')
add('skill_audit','PROOF-14','RULE-14','STRONG','behavioral_assertions',
    'Shell e2e test runs all 5 phases of criteria pipeline: built-in active, load_criteria appends, criteria reach LLM, staleness detected, --extra appends.','N/A')

print(json.dumps(cache, indent=2))
sys.stderr.write(f'Total entries: {len(cache)}\n')
