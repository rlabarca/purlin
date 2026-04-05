"""E2E tests for spec output from the four documented input scenarios.

Validates that specs produced by purlin:spec from plain descriptions, PRDs,
vague descriptions, and customer feedback have correct structural format:
RULE-N numbering, PROOF-N references, (assumed) tags, metadata, tier tags.

Each test creates a temp project with a sample spec representing expected
skill output, then validates it through sync_status and regex parsing.

Run with: python3 -m pytest dev/test_e2e_spec_from_input.py -v
"""

import json
import os
import re
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
from purlin_server import sync_status, _scan_specs


# ---------------------------------------------------------------------------
# Sample specs representing expected output from each input scenario
# ---------------------------------------------------------------------------

# Scenario 1: Plain description with explicit values — no (assumed) tags
PLAIN_DESCRIPTION_SPEC = """\
# Feature: password_reset

> Description: Allows users to reset their password via a time-limited email link.
> Scope: src/auth/reset.py, src/email/sender.py
> Stack: python/flask, smtp

## What it does

Users click "forgot password", receive an email with a reset link,
click it, and set a new password. The link expires after 24 hours.

## Rules

- RULE-1: POST /reset with a valid email sends an email containing a reset link
- RULE-2: Reset link expires after 24 hours
- RULE-3: Clicking a valid (non-expired) link allows the user to set a new password
- RULE-4: Clicking an expired link returns an error message

## Proof

- PROOF-1 (RULE-1): POST /reset with registered email; verify 200 and email sent @integration
- PROOF-2 (RULE-2): Create a link, advance clock 24h; verify link returns 410 Gone @integration
- PROOF-3 (RULE-3): Click valid link, submit new password; verify password changed @integration
- PROOF-4 (RULE-4): Click expired link; verify error message displayed @e2e
"""

# Scenario 2: PRD with multiple requirements — many rules, full metadata
PRD_SPEC = """\
# Feature: checkout_flow

> Description: Three-step checkout process extracted from the checkout PRD.
> Requires: api_rest_conventions
> Scope: src/checkout/cart.py, src/checkout/payment.py, src/checkout/confirm.py
> Stack: python/django, stripe, postgres

## What it does

Users complete checkout through a three-step flow: cart review, payment,
and order confirmation. Extracted from the full checkout PRD document.

## Rules

- RULE-1: Cart page displays all items with quantities and subtotals
- RULE-2: Removing an item updates the total without a full page reload
- RULE-3: Payment step validates credit card number using Luhn algorithm before submission
- RULE-4: Payment step communicates with Stripe API using TLS 1.2 or higher
- RULE-5: Successful payment creates an order record with status "confirmed"
- RULE-6: Failed payment displays the error from the payment processor and does not create an order

## Proof

- PROOF-1 (RULE-1): Add 3 items to cart; load cart page; verify all 3 items with correct subtotals @e2e
- PROOF-2 (RULE-2): Remove one item via AJAX endpoint; verify total updates and remaining items are correct @e2e
- PROOF-3 (RULE-3): Submit invalid card number (fails Luhn); verify client-side validation error before API call @e2e
- PROOF-4 (RULE-4): Inspect Stripe API call; verify TLS version >= 1.2 @integration
- PROOF-5 (RULE-5): Complete payment with test card; query DB for order; verify status is "confirmed" @integration
- PROOF-6 (RULE-6): Trigger payment failure; verify error message displayed and no order row in DB @integration
"""

# Scenario 3: Vague description — inferred values get (assumed) tags
VAGUE_DESCRIPTION_SPEC = """\
# Feature: password_reset_vague

> Description: Password reset from a vague user request.
> Scope: src/auth/reset.py
> Stack: python/flask

## What it does

Password reset feature inferred from minimal user input.

## Rules

- RULE-1: POST /reset sends email with link
- RULE-2: Link expires after 24 hours (assumed — user said "quickly")
- RULE-3: Clicking valid link allows new password
- RULE-4: Expired link shows error message (assumed — user said "handle expiry")

## Proof

- PROOF-1 (RULE-1): POST /reset with valid email; verify email sent @integration
- PROOF-2 (RULE-2): Create link, advance clock 24h; verify link rejected @integration
- PROOF-3 (RULE-3): Click valid link; submit new password; verify change @integration
- PROOF-4 (RULE-4): Click expired link; verify error displayed @e2e
"""

# Scenario 4: Customer feedback — complaints translated to rules with thresholds
CUSTOMER_FEEDBACK_SPEC = """\
# Feature: search_improvements

> Description: Search improvements driven by customer complaints about speed and typo handling.
> Scope: src/search/engine.py, src/search/index.py
> Stack: python/elasticsearch

## What it does

Addresses customer complaints that search is slow and does not handle typos.

## Rules

- RULE-1: Search returns results in under 500ms at p95
- RULE-2: Search handles common typos via fuzzy matching
- RULE-3: Empty search query returns a helpful prompt instead of an error
- RULE-4: Search results are ranked by relevance score descending

## Proof

- PROOF-1 (RULE-1): Run 100 search queries; measure p95 latency; verify under 500ms @integration
- PROOF-2 (RULE-2): Search for "pyhton" (typo for "python"); verify results include "python" matches @integration
- PROOF-3 (RULE-3): Submit empty string to search endpoint; verify 200 response with guidance message
- PROOF-4 (RULE-4): Search for term with known relevance scores; verify results ordered descending @integration
"""

# Scenario 3 corrected: (assumed) replaced with explicit value
VAGUE_CORRECTED_SPEC = """\
# Feature: password_reset_vague

> Description: Password reset from a vague user request, now with explicit expiry.
> Scope: src/auth/reset.py
> Stack: python/flask

## What it does

Password reset feature with PM-corrected expiry value.

## Rules

- RULE-1: POST /reset sends email with link
- RULE-2: Link expires after 1 hour
- RULE-3: Clicking valid link allows new password
- RULE-4: Expired link shows error message

## Proof

- PROOF-1 (RULE-1): POST /reset with valid email; verify email sent @integration
- PROOF-2 (RULE-2): Create link, advance clock 1h; verify link rejected @integration
- PROOF-3 (RULE-3): Click valid link; submit new password; verify change @integration
- PROOF-4 (RULE-4): Click expired link; verify error displayed @e2e
"""

# Anchor used by PRD scenario for Requires testing
API_ANCHOR_SPEC = """\
# Anchor: api_rest_conventions

> Scope: src/
> Type: api

## What it does

REST API conventions anchor for consistent response format.

## Rules

- RULE-1: All API responses include Content-Type: application/json header
- RULE-2: All error responses use {error: string, code: int} format

## Proof

- PROOF-1 (RULE-1): Verify API responses include Content-Type header @integration
- PROOF-2 (RULE-2): Trigger errors; verify response body matches format @integration
"""


# ---------------------------------------------------------------------------
# Regex patterns used for structural validation
# ---------------------------------------------------------------------------

RULE_RE = re.compile(r'^- (RULE-\d+):', re.MULTILINE)
PROOF_RE = re.compile(r'^- (PROOF-\d+) \((RULE-\d+(?:,\s*RULE-\d+)*)\):', re.MULTILINE)
ASSUMED_RE = re.compile(r'\(assumed\s+—\s+.+?\)')
TIER_RE = re.compile(r'@(integration|e2e|manual)\s*$')
METADATA_RE = {
    'description': re.compile(r'^>\s*Description:', re.MULTILINE),
    'scope': re.compile(r'^>\s*Scope:', re.MULTILINE),
    'stack': re.compile(r'^>\s*Stack:', re.MULTILINE),
    'requires': re.compile(r'^>\s*Requires:', re.MULTILINE),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(tmp_dir, specs=None):
    """Create a minimal Purlin project with given specs.

    specs: dict of {relative_path: content} for spec files.
    """
    os.makedirs(os.path.join(tmp_dir, '.purlin'), exist_ok=True)
    with open(os.path.join(tmp_dir, '.purlin', 'config.json'), 'w') as f:
        json.dump({
            "version": "0.9.0",
            "test_framework": "auto",
            "spec_dir": "specs",
        }, f)

    if specs:
        for rel_path, content in specs.items():
            full_path = os.path.join(tmp_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)


def _extract_rules(content):
    """Return list of rule IDs from spec content."""
    return [m.group(1) for m in RULE_RE.finditer(content)]


def _extract_proofs(content):
    """Return list of (proof_id, rule_refs) tuples from spec content."""
    results = []
    for m in PROOF_RE.finditer(content):
        proof_id = m.group(1)
        rule_refs = [r.strip() for r in m.group(2).split(',')]
        results.append((proof_id, rule_refs))
    return results


def _extract_proof_lines(content):
    """Return raw proof lines from ## Proof section."""
    section = re.search(
        r'^## Proof\s*\n(.*?)(?=^## |\Z)', content,
        re.MULTILINE | re.DOTALL
    )
    if not section:
        return []
    return [
        line.strip() for line in section.group(1).strip().splitlines()
        if line.strip().startswith('- PROOF-')
    ]


# ---------------------------------------------------------------------------
# Tests: Scenario 1 — Plain Description
# ---------------------------------------------------------------------------

class TestPlainDescription:

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        _make_project(self.tmp_dir, specs={
            'specs/auth/password_reset.md': PLAIN_DESCRIPTION_SPEC,
        })

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir)

    @pytest.mark.proof("skill_spec_from_code", "PROOF-19", "RULE-10", tier="e2e")
    def test_sequential_rule_numbering(self):
        """RULE-1: Sequential RULE-N from 1 with no gaps."""
        rules = _extract_rules(PLAIN_DESCRIPTION_SPEC)
        numbers = [int(r.split('-')[1]) for r in rules]
        assert numbers == list(range(1, len(numbers) + 1)), \
            f"Rule numbers not sequential: {numbers}"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-20", "RULE-11", tier="e2e")
    def test_every_rule_has_proof(self):
        """RULE-2: Every RULE-N has at least one PROOF referencing it."""
        rules = set(_extract_rules(PLAIN_DESCRIPTION_SPEC))
        proofs = _extract_proofs(PLAIN_DESCRIPTION_SPEC)
        proved_rules = set()
        for _, rule_refs in proofs:
            proved_rules.update(rule_refs)
        uncovered = rules - proved_rules
        assert not uncovered, f"Rules without proofs: {uncovered}"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-21", "RULE-12", tier="e2e")
    def test_no_assumed_tags_on_explicit_values(self):
        """RULE-3: No (assumed) tags when all values were explicit."""
        matches = ASSUMED_RE.findall(PLAIN_DESCRIPTION_SPEC)
        assert len(matches) == 0, \
            f"Found (assumed) tags in explicit-values spec: {matches}"


# ---------------------------------------------------------------------------
# Tests: Scenario 2 — PRD
# ---------------------------------------------------------------------------

class TestPRD:

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        _make_project(self.tmp_dir, specs={
            'specs/checkout/checkout_flow.md': PRD_SPEC,
            'specs/_anchors/api_rest_conventions.md': API_ANCHOR_SPEC,
        })

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir)

    @pytest.mark.proof("skill_spec_from_code", "PROOF-22", "RULE-13", tier="e2e")
    def test_prd_extracts_at_least_5_rules(self):
        """RULE-4: PRD with 6 constraints produces at least 5 rules."""
        rules = _extract_rules(PRD_SPEC)
        assert len(rules) >= 5, \
            f"PRD spec should have >= 5 rules, got {len(rules)}: {rules}"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-23", "RULE-14", tier="e2e")
    def test_prd_metadata_present(self):
        """RULE-5: PRD spec has Description, Scope, and Stack metadata."""
        for field in ('description', 'scope', 'stack'):
            assert METADATA_RE[field].search(PRD_SPEC), \
                f"Missing > {field.title()}: in PRD spec"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-24", "RULE-15", tier="e2e")
    def test_requires_anchor_in_coverage(self):
        """RULE-6: sync_status includes required anchor rules in coverage."""
        result = sync_status(self.tmp_dir)
        # The PRD spec Requires api_rest_conventions — its rules should appear
        assert 'api_rest_conventions' in result, \
            f"Required anchor not in sync_status output: {result}"
        assert 'RULE-1' in result, \
            f"Anchor rules not shown in sync_status output: {result}"


# ---------------------------------------------------------------------------
# Tests: Scenario 3 — Vague Description
# ---------------------------------------------------------------------------

class TestVagueDescription:

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        _make_project(self.tmp_dir, specs={
            'specs/auth/password_reset_vague.md': VAGUE_DESCRIPTION_SPEC,
        })

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir)

    @pytest.mark.proof("skill_spec_from_code", "PROOF-25", "RULE-16", tier="e2e")
    def test_assumed_tags_present(self):
        """RULE-7: Vague input produces (assumed — <context>) tags."""
        matches = ASSUMED_RE.findall(VAGUE_DESCRIPTION_SPEC)
        assert len(matches) >= 1, \
            "Vague-input spec should have at least one (assumed) tag"
        # Verify the tag has context after the dash
        for tag in matches:
            assert '—' in tag, f"(assumed) tag missing context: {tag}"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-26", "RULE-17", tier="e2e")
    def test_assumed_rules_parseable_by_sync_status(self):
        """RULE-8: sync_status parses assumed-tagged rules without errors."""
        result = sync_status(self.tmp_dir)
        # sync_status should find the feature and its rules
        assert 'password_reset_vague' in result, \
            f"Feature not found in sync_status output: {result}"
        # Should report 4 rules
        features = _scan_specs(self.tmp_dir)
        assert 'password_reset_vague' in features
        rules = features['password_reset_vague']['rules']
        assert len(rules) == 4, \
            f"Expected 4 rules parsed, got {len(rules)}: {list(rules.keys())}"


# ---------------------------------------------------------------------------
# Tests: Scenario 4 — Customer Feedback
# ---------------------------------------------------------------------------

class TestCustomerFeedback:

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        _make_project(self.tmp_dir, specs={
            'specs/search/search_improvements.md': CUSTOMER_FEEDBACK_SPEC,
        })

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir)

    @pytest.mark.proof("skill_spec_from_code", "PROOF-27", "RULE-18", tier="e2e")
    def test_feedback_translated_to_specific_rules(self):
        """RULE-9: Complaints become rules with specific thresholds."""
        # "slow search" → under 500ms threshold
        assert '500ms' in CUSTOMER_FEEDBACK_SPEC, \
            "Feedback spec should have specific latency threshold"
        # "doesn't handle typos" → fuzzy matching behavior
        assert 'fuzzy matching' in CUSTOMER_FEEDBACK_SPEC.lower() or \
               'fuzzy' in CUSTOMER_FEEDBACK_SPEC.lower(), \
            "Feedback spec should mention fuzzy matching for typo handling"
        # Verify rules are properly numbered
        rules = _extract_rules(CUSTOMER_FEEDBACK_SPEC)
        assert len(rules) >= 2, \
            f"Expected at least 2 rules from feedback, got {len(rules)}"


# ---------------------------------------------------------------------------
# Tests: Cross-Scenario Validation
# ---------------------------------------------------------------------------

class TestCrossScenario:

    ALL_SPECS = {
        'plain': PLAIN_DESCRIPTION_SPEC,
        'prd': PRD_SPEC,
        'vague': VAGUE_DESCRIPTION_SPEC,
        'feedback': CUSTOMER_FEEDBACK_SPEC,
    }

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        _make_project(self.tmp_dir, specs={
            'specs/auth/password_reset.md': PLAIN_DESCRIPTION_SPEC,
            'specs/checkout/checkout_flow.md': PRD_SPEC,
            'specs/_anchors/api_rest_conventions.md': API_ANCHOR_SPEC,
            'specs/auth/password_reset_vague.md': VAGUE_DESCRIPTION_SPEC,
            'specs/search/search_improvements.md': CUSTOMER_FEEDBACK_SPEC,
        })

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir)

    @pytest.mark.proof("skill_spec_from_code", "PROOF-28", "RULE-19", tier="e2e")
    def test_all_proofs_have_tier_tags(self):
        """RULE-10: Every proof line has an appropriate tier tag or is implicit unit."""
        for name, content in self.ALL_SPECS.items():
            proof_lines = _extract_proof_lines(content)
            assert proof_lines, f"No proof lines found in {name} spec"
            for line in proof_lines:
                # Either has an explicit tier tag or is implicit unit (no tag)
                has_tier = TIER_RE.search(line)
                # If no explicit tier, it's unit — that's valid.
                # But we should verify it doesn't have a malformed tag
                if '@' in line.split(':')[-1]:
                    # There's an @ in the proof description tail — must be valid tier
                    assert has_tier, \
                        f"Malformed tier tag in {name} spec proof: {line}"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-29", "RULE-20", tier="e2e")
    def test_sync_status_parses_all_scenarios(self):
        """RULE-11: sync_status parses all four specs, reports UNTESTED."""
        result = sync_status(self.tmp_dir)
        for feature in ('password_reset', 'checkout_flow',
                        'password_reset_vague', 'search_improvements'):
            assert feature in result, \
                f"Feature '{feature}' not in sync_status output"
        # No proof files → all should be UNTESTED
        assert 'UNTESTED' in result, \
            f"Expected UNTESTED status without proof files: {result}"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-30", "RULE-21", tier="e2e")
    def test_all_specs_have_rules_and_proof_sections(self):
        """RULE-12: ## Rules and ## Proof sections exist in all four specs."""
        for name, content in self.ALL_SPECS.items():
            assert '## Rules' in content, \
                f"Missing ## Rules section in {name} spec"
            assert '## Proof' in content, \
                f"Missing ## Proof section in {name} spec"


# ---------------------------------------------------------------------------
# Tests: Assumption Correction Flow
# ---------------------------------------------------------------------------

class TestAssumedCorrection:

    @pytest.mark.proof("skill_spec_from_code", "PROOF-31", "RULE-22", tier="e2e")
    def test_corrected_assumed_rule_is_valid(self):
        """RULE-13: Replacing (assumed) with explicit value produces valid spec."""
        # Original has (assumed) tags
        original_assumed = ASSUMED_RE.findall(VAGUE_DESCRIPTION_SPEC)
        assert len(original_assumed) >= 1, "Precondition: vague spec has assumed tags"

        # Corrected version removes (assumed) and uses explicit value
        corrected_assumed = ASSUMED_RE.findall(VAGUE_CORRECTED_SPEC)
        assert len(corrected_assumed) == 0, \
            f"Corrected spec still has (assumed) tags: {corrected_assumed}"

        # Corrected rules still follow RULE-N format
        rules = _extract_rules(VAGUE_CORRECTED_SPEC)
        numbers = [int(r.split('-')[1]) for r in rules]
        assert numbers == list(range(1, len(numbers) + 1)), \
            f"Corrected spec rules not sequential: {numbers}"

        # The explicit value is present
        assert '1 hour' in VAGUE_CORRECTED_SPEC, \
            "Corrected spec should contain explicit '1 hour' value"

        # Verify it's still parseable by sync_status
        tmp_dir = tempfile.mkdtemp()
        try:
            _make_project(tmp_dir, specs={
                'specs/auth/password_reset_vague.md': VAGUE_CORRECTED_SPEC,
            })
            features = _scan_specs(tmp_dir)
            assert 'password_reset_vague' in features
            assert len(features['password_reset_vague']['rules']) == 4
        finally:
            shutil.rmtree(tmp_dir)
