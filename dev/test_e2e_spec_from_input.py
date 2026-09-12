"""Tests for spec output from the four documented input scenarios.

Generation is agent work: no script in this repository turns a plain
description, a PRD, a vague request or a page of customer feedback into a spec.
So the rules about how a generated spec is shaped (RULE-10 to RULE-12) are
document-content rules about what `skills/spec-from-code/SKILL.md` instructs,
and their tests here are greps of that file naming the section and the literal.

The rules a real mechanism can be driven against (RULE-13 to RULE-22) stay
behavioural: a scenario spec is written into a temp project and `sync_status`
plus the dashboard payload are asserted on.

Run with: python3 -m pytest dev/test_e2e_spec_from_input.py -q
"""

import json
import os
import re
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
from purlin_server import sync_status, read_report_payload

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

# The six separate requirements the PRD scenario was written from.
PRD_REQUIREMENTS = [
    "The cart page lists every item with quantities and subtotals",
    "Removing an item updates the total without a reload",
    "The card number is Luhn-checked before submission",
    "Stripe is reached over TLS 1.2 or higher",
    "A successful payment creates a confirmed order",
    "A failed payment shows the processor error and creates no order",
]

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

# Scenario 3 corrected: both (assumed) tags replaced with explicit values
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

# Anchor the PRD scenario names in its > Requires: line
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

# The rule the PM corrects in the vague scenario, and its explicit replacement.
TAGGED_RULE_2 = '- RULE-2: Link expires after 24 hours (assumed — user said "quickly")'
EXPLICIT_RULE_2 = '- RULE-2: Link expires after 1 hour'

ASSUMED_ADVISORY_2 = '⚠ 2 rules have (assumed) values — PM should confirm'
ASSUMED_ADVISORY_1 = '⚠ 1 rule has (assumed) values — PM should confirm'

# name -> (spec path, content, rule total including required anchor rules)
ALL_SCENARIOS = {
    'password_reset': ('specs/auth/password_reset.md', PLAIN_DESCRIPTION_SPEC, 4),
    'checkout_flow': ('specs/checkout/checkout_flow.md', PRD_SPEC, 8),
    'password_reset_vague': ('specs/auth/password_reset_vague.md',
                             VAGUE_DESCRIPTION_SPEC, 4),
    'search_improvements': ('specs/search/search_improvements.md',
                            CUSTOMER_FEEDBACK_SPEC, 4),
}

# Planned-proof lines sync_status prints for the five fixtures: 4 for the plain
# spec, 8 for the PRD spec (6 own rules plus the 2 rules of the anchor it
# requires), 4 for the vague spec and 4 for the feedback spec.
PLANNED_PROOF_COUNT = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(tmp_dir, specs=None):
    """Create a minimal Purlin project with given specs.

    specs: dict of {relative_path: content} for spec files.
    """
    tmp_dir = str(tmp_dir)
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


def _parse_rules(content):
    """Return (rule_id, rule_text) pairs from spec content."""
    return re.findall(r'^- (RULE-\d+): (.+)$', content, re.MULTILINE)


def _skill_text():
    """The skill definition under test (this spec's Scope)."""
    with open(SKILL_PATH, encoding='utf-8') as f:
        return f.read()


def _require(skill, section, literal):
    """The skill text must carry `literal` in `section`.

    The failure message names both, so a mutation that removes or rewords the
    instruction says which section lost which literal.
    """
    assert literal in skill, (
        f"skills/spec-from-code/SKILL.md {section} must carry the literal "
        f"{literal!r}"
    )


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


def _own_rule_ids(block):
    """The feature's own rule ids, in the order sync_status prints them."""
    return re.findall(r'^  (RULE-\d+):', block, re.MULTILINE)


def _planned_proofs(block):
    """The planned-proof ids sync_status prints for one feature."""
    return re.findall(r'^\s+planned (PROOF-\d+):', block, re.MULTILINE)


def _payload_feature(project_root, name):
    """One feature record from the project's dashboard payload."""
    payload = read_report_payload(str(project_root))
    assert payload, 'read_report_payload returned nothing for the fixture project'
    by_name = {f['name']: f for f in payload['features']}
    assert name in by_name, f'{name} missing from the dashboard payload: {sorted(by_name)}'
    return by_name[name]


def _all_scenarios_project(tmp_dir):
    specs = {path: content for path, content, _total in ALL_SCENARIOS.values()}
    specs['specs/_anchors/api_rest_conventions.md'] = API_ANCHOR_SPEC
    _make_project(tmp_dir, specs=specs)


# ---------------------------------------------------------------------------
# Tests: RULE-10 to RULE-12, the shape SKILL.md tells the agent to generate
#
# Nothing in the repository generates a spec, so the honest proof of these
# rules is a grep of the instruction the agent follows.
# ---------------------------------------------------------------------------


@pytest.mark.proof("skill_spec_from_code", "PROOF-19", "RULE-10", tier="unit")
def test_skill_template_numbers_rules_sequentially():
    """Phase 3 step 6's template numbers rules RULE-1 then RULE-2."""
    assert '24 hours' in PLAIN_DESCRIPTION_INPUT, \
        "The plain-description input states its values explicitly"
    skill = _skill_text()
    _require(skill, 'Phase 3 step 6',
             '- RULE-1: <Behavioral constraint extracted from code>\n'
             '- RULE-2: <Another constraint>')


@pytest.mark.proof("skill_spec_from_code", "PROOF-20", "RULE-11", tier="unit")
def test_skill_template_pairs_every_rule_with_a_proof():
    """Phase 3 step 6's template pairs the rules; step 11 reads the pairing back."""
    skill = _skill_text()
    _require(skill, 'Phase 3 step 6',
             '- PROOF-1 (RULE-1): <Observable assertion>\n'
             '- PROOF-2 (RULE-2): <Observable assertion>')
    _require(skill, 'Phase 3 step 11',
             '`## Proof` contains at least one `PROOF-N (RULE-N):` line')


@pytest.mark.proof("skill_spec_from_code", "PROOF-21", "RULE-12", tier="unit")
def test_skill_forbids_the_assumed_tag():
    """The Guidelines forbid `(assumed)` on a rule extracted from code."""
    assert '(assumed' not in PLAIN_DESCRIPTION_SPEC, \
        "A spec generated from explicit values carries no (assumed) tag"
    skill = _skill_text()
    _require(skill, 'Guidelines', '**Do not use the `(assumed)` tag.**')
    _require(skill, 'Guidelines',
             'Rules extracted from code are observed behavior, not assumptions')


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
    def test_prd_scenario_reads_back_six_rules(self):
        """The PRD's 6 requirements read back as RULE-1 to RULE-6."""
        assert len(PRD_REQUIREMENTS) == 6, "The PRD scenario input names 6 requirements"
        block = _feature_block(sync_status(self.tmp_dir), 'checkout_flow')
        printed = _own_rule_ids(block)
        assert printed == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4', 'RULE-5', 'RULE-6'], \
            f"The PRD spec's own rules should read back as RULE-1..RULE-6, got {printed}"
        assert len(printed) >= 5, \
            f"RULE-13's floor for a multi-requirement PRD is 5 rules, got {len(printed)}"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-23", "RULE-14", tier="e2e")
    def test_prd_scenario_metadata_is_load_bearing(self):
        """Description, Stack and Scope each change what a reader is told."""
        sync_status(self.tmp_dir)
        feature = _payload_feature(self.tmp_dir, 'checkout_flow')
        assert feature['description'] == (
            'Three-step checkout process extracted from the checkout PRD.'), \
            f"> Description: should reach the payload verbatim, got {feature['description']!r}"
        assert feature['stack'] == 'python/django, stripe, postgres', \
            f"> Stack: should reach the payload verbatim, got {feature['stack']!r}"

        # Each field dropped in turn: the payload reports its absence, so a
        # migration that lost the line is visible rather than silent.
        no_desc = PRD_SPEC.replace(
            '> Description: Three-step checkout process extracted from the '
            'checkout PRD.\n', '')
        assert no_desc != PRD_SPEC, "the no-Description fixture did not apply"
        stripped = tempfile.mkdtemp()
        try:
            _make_project(stripped, specs={'specs/checkout/checkout_flow.md': no_desc})
            sync_status(stripped)
            assert _payload_feature(stripped, 'checkout_flow')['description'] is None, \
                "A spec with no > Description: should report no description"
        finally:
            shutil.rmtree(stripped)

        no_stack = PRD_SPEC.replace('> Stack: python/django, stripe, postgres\n', '')
        assert no_stack != PRD_SPEC, "the no-Stack fixture did not apply"
        stackless = tempfile.mkdtemp()
        try:
            _make_project(stackless, specs={'specs/checkout/checkout_flow.md': no_stack})
            sync_status(stackless)
            assert _payload_feature(stackless, 'checkout_flow')['stack'] is None, \
                "A spec with no > Stack: should report no stack"
        finally:
            shutil.rmtree(stackless)

        # > Scope: flips the next-step directive: with a scope file on disk the
        # feature is built and needs tests, without one it needs building.
        built = tempfile.mkdtemp()
        try:
            _make_project(built, specs={
                'specs/checkout/checkout_flow.md': PRD_SPEC,
                'specs/_anchors/api_rest_conventions.md': API_ANCHOR_SPEC,
            })
            os.makedirs(os.path.join(built, 'src', 'checkout'), exist_ok=True)
            with open(os.path.join(built, 'src', 'checkout', 'cart.py'), 'w') as f:
                f.write('def cart():\n    return True\n')
            built_block = _feature_block(sync_status(built), 'checkout_flow')
            assert '→ Run: purlin:test' in built_block, \
                f"With a > Scope: file on disk the directive is purlin:test, got:\n{built_block}"
        finally:
            shutil.rmtree(built)

        unbuilt_block = _feature_block(sync_status(self.tmp_dir), 'checkout_flow')
        assert '→ Run: purlin:build checkout_flow' in unbuilt_block, \
            f"With no > Scope: file on disk the directive is purlin:build, got:\n{unbuilt_block}"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-24", "RULE-15", tier="e2e")
    def test_prd_scenario_requires_anchor_counts_toward_coverage(self):
        """The required anchor's 2 rules join the feature's denominator."""
        block = _feature_block(sync_status(self.tmp_dir), 'checkout_flow')
        assert 'checkout_flow: 0/8 rules proved' in block, \
            f"6 own rules plus the anchor's 2 should read 0/8, got:\n{block}"
        assert 'api_rest_conventions/RULE-1: NO PROOF (required)' in block, \
            f"The required anchor's RULE-1 should be listed, got:\n{block}"
        assert 'api_rest_conventions/RULE-2: NO PROOF (required)' in block, \
            f"The required anchor's RULE-2 should be listed, got:\n{block}"

        # The same spec with the > Requires: line gone: the anchor rules leave
        # the denominator, so the line is load-bearing and not decoration.
        no_req = PRD_SPEC.replace('> Requires: api_rest_conventions\n', '')
        assert no_req != PRD_SPEC, "the no-Requires fixture did not apply"
        solo = tempfile.mkdtemp()
        try:
            _make_project(solo, specs={
                'specs/checkout/checkout_flow.md': no_req,
                'specs/_anchors/api_rest_conventions.md': API_ANCHOR_SPEC,
            })
            solo_block = _feature_block(sync_status(solo), 'checkout_flow')
            assert 'checkout_flow: 0/6 rules proved' in solo_block, \
                f"Without > Requires: the feature counts its own 6 rules, got:\n{solo_block}"
            assert 'api_rest_conventions/RULE-' not in solo_block, \
                f"Without > Requires: no anchor rule should be listed, got:\n{solo_block}"
        finally:
            shutil.rmtree(solo)


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
        """Only the (assumed — <context>) form is counted; a bare tag is not."""
        assert 'quickly' in VAGUE_DESCRIPTION_INPUT, "The vague input states no values"
        tagged = re.findall(r'\(assumed — user said "([^"]+)"\)', VAGUE_DESCRIPTION_SPEC)
        assert len(tagged) == 2, f"Expected 2 context-carrying tags, got {tagged}"
        assert all(context.strip() for context in tagged), f"Empty context in {tagged}"

        block = _feature_block(sync_status(self.tmp_dir), 'password_reset_vague')
        assert ASSUMED_ADVISORY_2 in block, \
            f"Both context-carrying tags should be counted, got:\n{block}"

        # Same two rules, context stripped: the bare form RULE-16 forbids.
        bare = re.sub(r'\(assumed — [^)]*\)', '(assumed)', VAGUE_DESCRIPTION_SPEC)
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
    def test_assumed_tagged_rules_still_parse(self):
        """A rule carrying an (assumed) tag is still counted, printed and planned."""
        tagged = re.findall(r'\(assumed — user said "([^"]+)"\)', VAGUE_DESCRIPTION_SPEC)
        assert len(tagged) == 2, f"Expected 2 tagged rules in the fixture, got {tagged}"

        block = _feature_block(sync_status(self.tmp_dir), 'password_reset_vague')
        assert 'password_reset_vague: 0/4 rules proved' in block, \
            f"All 4 rules should be counted, tags and all, got:\n{block}"
        printed = _own_rule_ids(block)
        assert printed == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4'], \
            f"No tagged rule should be dropped, got {printed}"
        planned = _planned_proofs(block)
        assert planned == ['PROOF-1', 'PROOF-2', 'PROOF-3', 'PROOF-4'], \
            f"Each rule keeps its planned proof, got {planned}"
        assert ASSUMED_ADVISORY_2 in block, \
            f"The 2 tagged rules should draw the assumed advisory, got:\n{block}"


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

        rules = dict(_parse_rules(CUSTOMER_FEEDBACK_SPEC))
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

class TestCrossScenario:

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        _all_scenarios_project(self.tmp_dir)

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
        _require(skill, 'Phase 3 step 7',
                 'Does the proof need a browser or full app stack? → append `@e2e`')
        _require(skill, 'Phase 3 step 7',
                 'Does the proof shell out to git, subprocess, or call an external '
                 'service? → append `@integration`')

    @pytest.mark.proof("skill_spec_from_code", "PROOF-29", "RULE-20", tier="e2e")
    def test_sync_status_parses_all_scenarios(self):
        """All four scenario specs parse, each with its own rule count, all UNTESTED."""
        result = sync_status(self.tmp_dir)
        assert 'ERROR' not in result, f"sync_status produced errors:\n{result}"

        for name, (_path, _content, total) in ALL_SCENARIOS.items():
            assert f'{name}: 0/{total} rules proved' in result, \
                f"{name} should report 0/{total} rules proved in:\n{result}"
        assert result.count('UNTESTED') == len(ALL_SCENARIOS), \
            (f"Each of the {len(ALL_SCENARIOS)} features should read UNTESTED, "
             f"got {result.count('UNTESTED')}")

    @pytest.mark.proof("skill_spec_from_code", "PROOF-30", "RULE-21", tier="e2e")
    def test_all_specs_have_rules_and_proof_sections(self):
        """Both sections are load-bearing: drop either and sync_status says so."""
        result = sync_status(self.tmp_dir)
        for name, (_path, content, total) in ALL_SCENARIOS.items():
            block = _feature_block(result, name)
            assert f'{name}: 0/{total} rules proved' in block, \
                f"{name} should report its {total} rules, got:\n{block}"
            own = re.findall(r'^- (PROOF-\d+) ', content, re.MULTILINE)
            assert _planned_proofs(block)[:len(own)] == own, \
                f"{name} should plan {own}, got {_planned_proofs(block)}"

        # No ## Rules section: the feature has no rules to prove at all.
        cut = PLAIN_DESCRIPTION_SPEC[
            PLAIN_DESCRIPTION_SPEC.index('## Rules'):
            PLAIN_DESCRIPTION_SPEC.index('## Proof')]
        no_rules = PLAIN_DESCRIPTION_SPEC.replace(cut, '')
        assert no_rules != PLAIN_DESCRIPTION_SPEC, "the no-Rules fixture did not apply"
        ruleless = tempfile.mkdtemp()
        try:
            _make_project(ruleless, specs={'specs/auth/password_reset.md': no_rules})
            ruleless_block = _feature_block(sync_status(ruleless), 'password_reset')
            assert 'password_reset: no rules defined' in ruleless_block, \
                f"A spec with no ## Rules section has no rules, got:\n{ruleless_block}"
            assert 'WARNING: No ## Rules section found.' in ruleless_block, \
                f"A missing ## Rules section should be flagged, got:\n{ruleless_block}"
        finally:
            shutil.rmtree(ruleless)

        # No ## Proof section: the rules still count, but nothing is planned.
        no_proof = PLAIN_DESCRIPTION_SPEC.split('## Proof')[0]
        assert no_proof != PLAIN_DESCRIPTION_SPEC, "the no-Proof fixture did not apply"
        proofless = tempfile.mkdtemp()
        try:
            _make_project(proofless, specs={'specs/auth/password_reset.md': no_proof})
            proofless_block = _feature_block(sync_status(proofless), 'password_reset')
            assert 'password_reset: 0/4 rules proved' in proofless_block, \
                f"The 4 rules still count without a ## Proof section, got:\n{proofless_block}"
            assert _planned_proofs(proofless_block) == [], \
                f"A spec with no ## Proof section can plan no proof, got:\n{proofless_block}"
            assert '"PROOF-N", "RULE-1"' in proofless_block, \
                f"Missing ## Proof should leave the PROOF-N placeholder, got:\n{proofless_block}"
        finally:
            shutil.rmtree(proofless)


# ---------------------------------------------------------------------------
# Tests: Assumption Correction Flow
# ---------------------------------------------------------------------------

class TestAssumedCorrection:

    @pytest.mark.proof("skill_spec_from_code", "PROOF-31", "RULE-22", tier="e2e")
    def test_corrected_assumed_rule_is_valid(self):
        """Replacing the tag with an explicit value keeps the rule and drops the count."""
        before = tempfile.mkdtemp()
        one_left = tempfile.mkdtemp()
        corrected = tempfile.mkdtemp()
        try:
            _make_project(before, specs={
                'specs/auth/password_reset_vague.md': VAGUE_DESCRIPTION_SPEC,
            })
            before_block = _feature_block(sync_status(before), 'password_reset_vague')
            assert ASSUMED_ADVISORY_2 in before_block, \
                f"The fixture should start with 2 assumed rules, got:\n{before_block}"

            # One tag replaced with the value the PM confirmed.
            updated = VAGUE_DESCRIPTION_SPEC.replace(TAGGED_RULE_2, EXPLICIT_RULE_2)
            assert updated != VAGUE_DESCRIPTION_SPEC, \
                "the explicit-value fixture did not apply"
            assert '(assumed' not in EXPLICIT_RULE_2, "The updated rule carries no tag"
            _make_project(one_left, specs={
                'specs/auth/password_reset_vague.md': updated,
            })
            one_block = _feature_block(sync_status(one_left), 'password_reset_vague')
            assert 'password_reset_vague: 0/4 rules proved' in one_block, \
                f"The updated rule must stay a countable RULE-N, got:\n{one_block}"
            assert 'RULE-2: NO PROOF (own)' in one_block, \
                f"RULE-2 should still be read back after the update, got:\n{one_block}"
            assert 'PROOF-2' in _planned_proofs(one_block), \
                f"RULE-2 should still carry its planned proof, got:\n{one_block}"
            assert ASSUMED_ADVISORY_1 in one_block, \
                f"One tag removed leaves 1 assumed rule, got:\n{one_block}"

            # Both tags replaced: the advisory goes away entirely.
            _make_project(corrected, specs={
                'specs/auth/password_reset_vague.md': VAGUE_CORRECTED_SPEC,
            })
            corrected_block = _feature_block(
                sync_status(corrected), 'password_reset_vague')
            assert 'password_reset_vague: 0/4 rules proved' in corrected_block, \
                f"The corrected spec keeps all 4 rules, got:\n{corrected_block}"
            assert '1 hour' in VAGUE_CORRECTED_SPEC, \
                "The corrected spec should carry the explicit '1 hour' value"
            assert '(assumed) values' not in corrected_block, \
                f"With no tag left there is no advisory, got:\n{corrected_block}"
        finally:
            for path in (before, one_left, corrected):
                shutil.rmtree(path)
