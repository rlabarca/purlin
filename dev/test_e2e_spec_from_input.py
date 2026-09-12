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

SKILL_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '..', 'skills', 'spec-from-code', 'SKILL.md'))

# The inputs the scenario specs below stand in for. Generation is agent work,
# so these are quoted here to name what each spec was written from.
PLAIN_DESCRIPTION_INPUT = (
    "Users reset their password through an emailed link. The link is valid for "
    "24 hours; after that it returns an error."
)

VAGUE_DESCRIPTION_INPUT = (
    "We need password reset. Make the link expire quickly and handle expiry."
)

# Each complaint and the literal the rule answering it must carry.
CUSTOMER_COMPLAINTS = [
    ("Search takes forever, I wait several seconds for results", "500ms"),
    ("Search does not handle typos: 'pyhton' finds nothing", "fuzzy matching"),
]


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


def _skill_text():
    """The skill definition under test (this spec's Scope)."""
    with open(SKILL_PATH, encoding='utf-8') as f:
        return f.read()


def _feature_block(output, name):
    """The lines of sync_status output that belong to one feature's section."""
    block = []
    capture = False
    for line in output.splitlines():
        if re.match(r'^[A-Za-z_][\w-]*: ', line):
            capture = line.startswith(name + ': ')
        if capture:
            block.append(line)
    return '\n'.join(block)


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
        """The rule ids sync_status reads back run RULE-1..RULE-4 with no gap."""
        assert '24 hours' in PLAIN_DESCRIPTION_INPUT, \
            "The plain-description input states its values explicitly"

        block = _feature_block(sync_status(self.tmp_dir), 'password_reset')
        assert 'password_reset: 0/4 rules proved' in block, \
            f"Expected 4 rules read back from the generated spec, got:\n{block}"
        printed = re.findall(r'^  (RULE-\d+):', block, re.MULTILINE)
        assert printed == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4'], \
            f"Rule ids should run 1..4 in order with no gap, got {printed}"

        skill = _skill_text()
        assert ('- RULE-1: <Behavioral constraint extracted from code>\n'
                '- RULE-2: <Another constraint>') in skill, \
            "SKILL.md step 6 template must number feature rules RULE-1 then RULE-2"

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
        """Explicit input: no (assumed) line; vague input: two of them."""
        assert '(assumed' not in PLAIN_DESCRIPTION_SPEC, \
            "Spec generated from explicit values should carry no (assumed) tag"
        _make_project(self.tmp_dir, specs={
            'specs/auth/password_reset_vague.md': VAGUE_DESCRIPTION_SPEC,
        })

        result = sync_status(self.tmp_dir)
        plain = _feature_block(result, 'password_reset')
        assert '(assumed) values' not in plain, \
            f"The explicit-values feature should draw no assumed advisory, got:\n{plain}"
        vague = _feature_block(result, 'password_reset_vague')
        assert '\u26a0 2 rules have (assumed) values \u2014 PM should confirm' in vague, \
            f"The vague-input feature should report its 2 assumed rules, got:\n{vague}"


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
        """Only the (assumed \u2014 <context>) form is counted; a bare tag is not."""
        assert 'quickly' in VAGUE_DESCRIPTION_INPUT, "The vague input states no values"
        tagged = re.findall(r'\(assumed \u2014 user said "([^"]+)"\)', VAGUE_DESCRIPTION_SPEC)
        assert len(tagged) == 2, f"Expected 2 context-carrying tags, got {tagged}"
        assert all(context.strip() for context in tagged), f"Empty context in {tagged}"

        block = _feature_block(sync_status(self.tmp_dir), 'password_reset_vague')
        assert '\u26a0 2 rules have (assumed) values \u2014 PM should confirm' in block, \
            f"Both context-carrying tags should be counted, got:\n{block}"

        # Same two rules, context stripped: the bare form RULE-16 forbids.
        bare = re.sub(r'\(assumed \u2014 [^)]*\)', '(assumed)', VAGUE_DESCRIPTION_SPEC)
        assert bare.count('(assumed)') == 2, "The stripped fixture should carry 2 bare tags"
        bare_dir = tempfile.mkdtemp()
        try:
            _make_project(bare_dir, specs={
                'specs/auth/password_reset_vague.md': bare,
            })
            bare_block = _feature_block(sync_status(bare_dir), 'password_reset_vague')
            assert '(assumed) values' not in bare_block, \
                f"A bare (assumed) with no context must not count, got:\n{bare_block}"
        finally:
            shutil.rmtree(bare_dir)

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
        """Each quoted complaint lands on a rule carrying its threshold."""
        block = _feature_block(sync_status(self.tmp_dir), 'search_improvements')
        assert 'search_improvements: 0/4 rules proved' in block, \
            f"Expected the 4 rules the complaints became, got:\n{block}"

        rules = dict(re.findall(r'^- (RULE-\d+): (.+)$', CUSTOMER_FEEDBACK_SPEC, re.MULTILINE))
        # The slowness complaint becomes a numeric latency bound.
        latency = re.search(r'under (\d+)ms', rules['RULE-1'])
        assert latency and latency.group(1) == '500', \
            f"RULE-1 should bound search latency at 500ms, got: {rules['RULE-1']!r}"
        # Every complaint is answered by exactly one rule carrying its literal.
        for complaint, expected in CUSTOMER_COMPLAINTS:
            matches = [rid for rid, text in rules.items() if expected in text]
            assert len(matches) == 1, \
                (f"Complaint {complaint!r} should map to one rule carrying "
                 f"{expected!r}, got {matches}")


# ---------------------------------------------------------------------------
# Tests: Cross-Scenario Validation
# ---------------------------------------------------------------------------

# Planned-proof lines sync_status prints for the five fixtures: 4 for the plain
# spec, 8 for the PRD spec (6 own rules plus the 2 rules of the anchor it
# requires), 4 for the vague spec and 4 for the feedback spec.
PLANNED_PROOF_COUNT = 20


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
        """Every planned proof parses to a valid tier; a doubled tag is rejected."""
        result = sync_status(self.tmp_dir)
        planned = re.findall(r'^\s+planned (PROOF-\d+): (.*)$', result, re.MULTILINE)
        assert len(planned) == PLANNED_PROOF_COUNT, \
            f"Expected {PLANNED_PROOF_COUNT} planned proofs, got {len(planned)}"
        for proof_id, desc in planned:
            if '@' in desc:
                assert re.search(r'@(integration|e2e|manual)(\([^)]*\))?$', desc), \
                    f"{proof_id} ends with something other than a tier tag: {desc!r}"
        assert 'WARNING' not in result, \
            f"Well-tagged proofs should draw no tag warning, got:\n{result}"

        # Two tier tags on one line: the grammar RULE-19 allows is one or none.
        doubled = PLAIN_DESCRIPTION_SPEC.replace(
            '- PROOF-1 (RULE-1): POST /reset with registered email; verify 200 '
            'and email sent @integration',
            '- PROOF-1 (RULE-1): POST /reset with registered email; verify 200 '
            'and email sent @e2e @integration',
        )
        assert doubled != PLAIN_DESCRIPTION_SPEC, "The doubled-tag fixture did not apply"
        broken_dir = tempfile.mkdtemp()
        try:
            _make_project(broken_dir, specs={
                'specs/auth/password_reset.md': doubled,
            })
            broken_out = sync_status(broken_dir)
            assert ('WARNING: PROOF-1: a second tier tag @e2e precedes @integration'
                    in broken_out), \
                f"A doubled tier tag should be flagged, got:\n{broken_out}"
        finally:
            shutil.rmtree(broken_dir)

        skill = _skill_text()
        assert 'Does the proof need a browser or full app stack? \u2192 append `@e2e`' in skill, \
            "SKILL.md step 7 must route browser/full-stack proofs to @e2e"
        assert ('Does the proof shell out to git, subprocess, or call an external '
                'service? \u2192 append `@integration`') in skill, \
            "SKILL.md step 7 must route external-dependency proofs to @integration"

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
