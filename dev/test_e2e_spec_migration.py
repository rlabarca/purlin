"""Tests for skill_spec_from_code: the SKILL.md instructions, and spec parsing.

`purlin:spec-from-code` runs as agent prose. No script in this repository
detects migration candidates, migrates a legacy `features/` spec, or generates
a spec from an input document, so the rules about those phases (RULE-5 to
RULE-12, RULE-25 to RULE-27) are document-content rules about what
`skills/spec-from-code/SKILL.md` instructs. Their tests here are greps of that
file, each naming the section and the literal the instruction must carry.

The rules a real mechanism can be driven against (RULE-13 to RULE-22) stay
behavioural: a scenario spec is written into a temp project and `sync_status`
plus the dashboard payload are asserted on.

Run with: python3 -m pytest dev/test_e2e_spec_migration.py -q
"""

import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
from purlin_server import sync_status, read_report_payload

SKILL_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '..', 'skills', 'spec-from-code', 'SKILL.md'))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(tmp_dir, specs=None, features=None):
    """Create a minimal Purlin project in tmp_dir."""
    tmp_dir = str(tmp_dir)
    os.makedirs(os.path.join(tmp_dir, '.purlin'), exist_ok=True)
    with open(os.path.join(tmp_dir, '.purlin', 'config.json'), 'w') as f:
        json.dump({"version": "0.9.0", "test_framework": "pytest", "spec_dir": "specs"}, f)
    os.makedirs(os.path.join(tmp_dir, 'specs', '_anchors'), exist_ok=True)

    for group in (specs, features):
        if not group:
            continue
        for path, content in group.items():
            full = os.path.join(tmp_dir, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, 'w') as f:
                f.write(content)


def _parse_rules(content):
    """Extract RULE-N lines from spec content."""
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


def _without_section(spec, section, next_section):
    """The same spec with one section's body removed."""
    cut = spec[spec.index(section):spec.index(next_section)]
    stripped = spec.replace(cut, '')
    assert stripped != spec, f"the {section} fixture did not apply"
    return stripped


# ---------------------------------------------------------------------------
# Tests: RULE-5 to RULE-12, the Phase 1 / Phase 3 / Phase 4 instructions
#
# Each of these rules is a statement about what SKILL.md tells the agent to do.
# Nothing in the repository performs the detection, migration or generation
# they describe, so the honest proof is a grep of the instruction.
# ---------------------------------------------------------------------------


@pytest.mark.proof("skill_spec_from_code", "PROOF-10", "RULE-5", tier="unit")
def test_skill_orders_the_recursive_legacy_read():
    """Phase 1 step 3a reads features/ recursively and skips the companions."""
    skill = _skill_text()
    _require(skill, 'Phase 1 step 3a',
             'Read all `.md` files recursively (excluding `.impl.md` and '
             '`.discoveries.md`')
    _require(skill, 'Phase 1 step 3a', 'scenarios (Given/When/Then blocks)')


@pytest.mark.proof("skill_spec_from_code", "PROOF-11", "RULE-6", tier="unit")
def test_skill_lists_the_outdated_format_criterion():
    """Phase 1 step 3b names the outdated format and what survives from it."""
    skill = _skill_text()
    _require(skill, 'Phase 1 step 3b',
             'Uses an outdated format (e.g., Given/When/Then scenarios instead '
             'of Rules/Proof)')
    _require(skill, 'Phase 1 step 3b',
             'existing rules (even if unnumbered), existing proofs, description')


@pytest.mark.proof("skill_spec_from_code", "PROOF-12", "RULE-6", tier="unit")
def test_skill_orders_the_missing_description_fixed():
    """Phase 3 step 3 fills the metadata the step 3b criterion flags."""
    skill = _skill_text()
    _require(skill, 'Phase 3 step 3',
             'Fix compliance issues: add missing `> Description:`')


@pytest.mark.proof("skill_spec_from_code", "PROOF-13", "RULE-6", tier="unit")
def test_skill_orders_the_other_three_criteria_fixed():
    """Phase 3 step 3 numbers rules, adds ## Proof and converts scenarios."""
    skill = _skill_text()
    _require(skill, 'Phase 3 step 3',
             'number unnumbered rules, add missing `## Proof` section, convert '
             'any Given/When/Then scenarios to Rules/Proof format')


@pytest.mark.proof("skill_spec_from_code", "PROOF-14", "RULE-7", tier="unit")
def test_skill_writes_only_candidates_to_the_ledger():
    """Phase 1 step 3 saves the candidates, and counts only those."""
    skill = _skill_text()
    _require(skill, 'Phase 1 step 3',
             'Save all migration candidates to `.purlin/cache/sfc_existing.md`')
    _require(skill, 'Phase 1 step 3',
             'Found N specs to migrate: X from features/, Y non-compliant in specs/.')


@pytest.mark.proof("skill_spec_from_code", "PROOF-15", "RULE-7", tier="unit")
def test_skill_gates_migration_on_the_ledger():
    """Phase 3 step 3 consults the ledger before it rewrites anything."""
    skill = _skill_text()
    _require(skill, 'Phase 3 step 3',
             'check if this feature has a migration candidate in '
             '`.purlin/cache/sfc_existing.md`')
    _require(skill, 'Phase 3 step 3',
             'If no migration candidate exists, generate from code alone')


@pytest.mark.proof("skill_spec_from_code", "PROOF-16", "RULE-8", tier="unit")
def test_skill_orders_existing_metadata_preserved():
    """Phase 3 step 3 keeps the rules, proofs and metadata already correct."""
    skill = _skill_text()
    _require(skill, 'Phase 3 step 3',
             'Preserve all content that is already correct: existing rules '
             '(renumber if needed), existing proofs, existing metadata '
             '(`> Scope:`, `> Stack:`, `> Requires:`)')


@pytest.mark.proof("skill_spec_from_code", "PROOF-17", "RULE-5", tier="unit")
def test_skill_maps_features_path_to_specs_path():
    """The source path in step 3 and the destination path in step 6."""
    skill = _skill_text()
    _require(skill, 'Phase 3 step 3',
             'Read the original `features/<category>/<name>.md` file in full')
    _require(skill, 'Phase 3 step 6', 'specs/<category>/<name>.md')


@pytest.mark.proof("skill_spec_from_code", "PROOF-18", "RULE-8", tier="unit")
def test_skill_orders_divergence_flagged_and_the_spec_marked():
    """Phase 3 step 3 flags drift from the code and marks the migrated spec."""
    skill = _skill_text()
    _require(skill, 'Phase 3 step 3',
             'If the code has diverged, flag the discrepancy for the user in '
             'the review step')
    _require(skill, 'Phase 3 step 3',
             '<!-- Migrated by purlin:spec-from-code. Review and refine. -->')


@pytest.mark.proof("skill_spec_from_code", "PROOF-19", "RULE-10", tier="unit")
def test_skill_template_numbers_rules_sequentially():
    """Phase 3 step 6's template numbers rules RULE-1 then RULE-2."""
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
    skill = _skill_text()
    _require(skill, 'Guidelines', '**Do not use the `(assumed)` tag.**')
    _require(skill, 'Guidelines',
             'Rules extracted from code are observed behavior, not assumptions')


# ---------------------------------------------------------------------------
# Scenario specs: the four documented input scenarios, parsed by sync_status
# ---------------------------------------------------------------------------

PLAIN_DESCRIPTION_SPEC = """\
# Feature: file_upload

> Description: Handles file uploads with size and type validation.
> Scope: src/upload/handler.py
> Stack: python/flask, werkzeug

## What it does

Accepts file uploads, validates size and type, stores to disk.

## Rules

- RULE-1: Accepts uploads under 10MB
- RULE-2: Rejects files over 10MB with HTTP 413
- RULE-3: Accepts only JPEG, PNG, and PDF file types
- RULE-4: Rejects disallowed file types with HTTP 415

## Proof

- PROOF-1 (RULE-1): Upload a 5MB JPEG; verify 200 response @integration
- PROOF-2 (RULE-2): Upload a 15MB file; verify 413 response @integration
- PROOF-3 (RULE-3): Upload a PNG; verify 200. Upload a PDF; verify 200 @integration
- PROOF-4 (RULE-4): Upload a .exe file; verify 415 response @integration
"""

PRD_SPEC = """\
# Feature: checkout

> Description: Three-step checkout flow with cart review, payment, and confirmation.
> Scope: src/checkout/flow.py, src/checkout/payment.py
> Stack: python/flask, stripe, redis
> Requires: api_conventions

## What it does

Implements a three-step checkout: cart review, payment entry, and order confirmation.

## Rules

- RULE-1: Step 1 displays cart items with prices and total
- RULE-2: Step 2 collects payment info via Stripe Elements
- RULE-3: Step 3 shows order confirmation with order number
- RULE-4: Payment failure returns user to Step 2 with error message
- RULE-5: Cart contents are preserved across payment retries
- RULE-6: Order confirmation email is sent within 60 seconds

## Proof

- PROOF-1 (RULE-1): Load checkout with 3 items; verify items and total displayed @e2e
- PROOF-2 (RULE-2): Proceed to payment step; verify Stripe Elements form renders @e2e
- PROOF-3 (RULE-3): Complete payment; verify confirmation page with order number @e2e
- PROOF-4 (RULE-4): Submit declined card; verify error on Step 2 @e2e
- PROOF-5 (RULE-5): Fail payment then retry; verify cart still has original items @e2e
- PROOF-6 (RULE-6): Complete checkout; poll inbox for 60s; verify email with order number @e2e
"""

API_ANCHOR_SPEC = """\
# Anchor: api_conventions

> Description: REST API conventions.

## Rules

- RULE-1: All responses use JSON envelope
- RULE-2: Errors include error code and message

## Proof

- PROOF-1 (RULE-1): Grep the response builder for the JSON envelope
- PROOF-2 (RULE-2): Trigger an error; verify error code and message
"""

VAGUE_INPUT_SPEC = """\
# Feature: search

> Description: Product search with filtering and sorting.
> Scope: src/search/engine.py
> Stack: python/elasticsearch

## What it does

Searches products by keyword with filters for category and price range.

## Rules

- RULE-1: Keyword search returns matching products ordered by relevance
- RULE-2: Category filter restricts results to selected category (assumed — user said "let people narrow it down")
- RULE-3: Price range filter excludes products outside min/max bounds
- RULE-4: Search returns in under 500ms (assumed — user said "fast")
- RULE-5: Empty query returns no results

## Proof

- PROOF-1 (RULE-1): Search "laptop"; verify results contain "laptop" in name or description @integration
- PROOF-2 (RULE-2): Search with category=electronics; verify all results are electronics @integration
- PROOF-3 (RULE-3): Search with price_min=100, price_max=500; verify all prices in range @integration
- PROOF-4 (RULE-4): Search "laptop"; measure response time; verify under 500ms @integration
- PROOF-5 (RULE-5): Search with empty string; verify empty results
"""

CUSTOMER_FEEDBACK_SPEC = """\
# Feature: dashboard_load

> Description: Dashboard performance optimization based on customer complaints.
> Scope: src/dashboard/loader.py
> Stack: python/flask, sqlalchemy, redis (cache)

## What it does

Loads the main dashboard with cached data and pagination to meet performance SLAs.

## Rules

- RULE-1: Dashboard initial load completes in under 2 seconds with up to 100 features
- RULE-2: Feature list is paginated at 25 items per page
- RULE-3: Subsequent page loads complete in under 500ms using cached data
- RULE-4: Cache invalidation occurs within 30 seconds of a feature update

## Proof

- PROOF-1 (RULE-1): Load dashboard with 100 features; measure time; verify under 2s @integration
- PROOF-2 (RULE-2): Load dashboard with 50 features; verify first page shows 25; verify page 2 shows remaining 25 @integration
- PROOF-3 (RULE-3): Load page 1 then page 2; measure page 2 time; verify under 500ms @integration
- PROOF-4 (RULE-4): Update a feature; wait 30s; reload dashboard; verify updated data visible @integration
"""

# The inputs the four scenario specs stand in for. Generation is agent work,
# so these are quoted here to name what each spec was written from.
PLAIN_DESCRIPTION_INPUT = (
    "Uploads are accepted up to 10MB; anything bigger gets HTTP 413. "
    "Only JPEG, PNG and PDF are allowed; anything else gets HTTP 415."
)

VAGUE_DESCRIPTION_INPUT = (
    "Product search with filters. Make it fast and let people narrow it down."
)

# The six separate requirements the PRD scenario was written from.
PRD_REQUIREMENTS = [
    "Step 1 reviews the cart",
    "Step 2 takes payment through Stripe Elements",
    "Step 3 confirms the order with an order number",
    "A declined card returns the shopper to Step 2",
    "The cart survives a payment retry",
    "The confirmation email goes out within a minute",
]

# Each complaint and the literal the rule answering it must carry.
CUSTOMER_COMPLAINTS = [
    ("The dashboard takes forever to load once I have a lot of features", "2 seconds"),
    ("Paging through the feature list reloads everything", "25 items per page"),
]

ALL_SCENARIOS = {
    'plain': ('file_upload', 'specs/upload/file_upload.md', PLAIN_DESCRIPTION_SPEC, 4),
    'prd': ('checkout', 'specs/checkout/checkout.md', PRD_SPEC, 6),
    'vague': ('search', 'specs/search/search.md', VAGUE_INPUT_SPEC, 5),
    'feedback': ('dashboard_load', 'specs/dashboard/dashboard_load.md',
                 CUSTOMER_FEEDBACK_SPEC, 4),
}

ASSUMED_ADVISORY_2 = '⚠ 2 rules have (assumed) values — PM should confirm'
ASSUMED_ADVISORY_1 = '⚠ 1 rule has (assumed) values — PM should confirm'

TAGGED_RULE_4 = '- RULE-4: Search returns in under 500ms (assumed — user said "fast")'
EXPLICIT_RULE_4 = '- RULE-4: Search returns in under 200ms'


def _all_scenarios_project(tmp_dir):
    _make_project(tmp_dir, specs={
        path: content for _name, path, content, _n in ALL_SCENARIOS.values()
    })


# ---------------------------------------------------------------------------
# Tests: RULE-13 to RULE-22, driven through sync_status
# ---------------------------------------------------------------------------


@pytest.mark.proof("skill_spec_from_code", "PROOF-22", "RULE-13", tier="e2e")
def test_prd_scenario_reads_back_six_rules(tmp_path):
    """The PRD's 6 requirements read back as RULE-1 to RULE-6, over the floor of 5."""
    assert len(PRD_REQUIREMENTS) == 6, "The PRD scenario input names 6 requirements"
    _make_project(tmp_path, specs={
        'specs/checkout/checkout.md': PRD_SPEC,
        'specs/_anchors/api_conventions.md': API_ANCHOR_SPEC,
    })

    block = _feature_block(sync_status(str(tmp_path)), 'checkout')
    printed = _own_rule_ids(block)
    assert printed == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4', 'RULE-5', 'RULE-6'], (
        f"The PRD spec's own rules should read back as RULE-1..RULE-6, got {printed}"
    )
    assert len(printed) >= 5, (
        f"RULE-13's floor for a multi-requirement PRD is 5 rules, got {len(printed)}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-23", "RULE-14", tier="e2e")
def test_prd_scenario_metadata_is_load_bearing(tmp_path):
    """Description, Stack and Scope each change what a reader is told."""
    full = tmp_path / 'full'
    _make_project(full, specs={
        'specs/checkout/checkout.md': PRD_SPEC,
        'specs/_anchors/api_conventions.md': API_ANCHOR_SPEC,
    })
    sync_status(str(full))
    feature = _payload_feature(full, 'checkout')
    assert feature['description'] == (
        'Three-step checkout flow with cart review, payment, and confirmation.'), (
        f"> Description: should reach the payload verbatim, got {feature['description']!r}"
    )
    assert feature['stack'] == 'python/flask, stripe, redis', (
        f"> Stack: should reach the payload verbatim, got {feature['stack']!r}"
    )

    # Each field dropped in turn: the payload reports its absence, so a
    # migration that lost the line is visible rather than silent.
    no_desc = PRD_SPEC.replace(
        '> Description: Three-step checkout flow with cart review, payment, '
        'and confirmation.\n', '')
    assert no_desc != PRD_SPEC, "the no-Description fixture did not apply"
    stripped = tmp_path / 'no_desc'
    _make_project(stripped, specs={'specs/checkout/checkout.md': no_desc})
    sync_status(str(stripped))
    assert _payload_feature(stripped, 'checkout')['description'] is None, (
        "A spec with no > Description: should report no description"
    )

    no_stack = PRD_SPEC.replace('> Stack: python/flask, stripe, redis\n', '')
    assert no_stack != PRD_SPEC, "the no-Stack fixture did not apply"
    stackless = tmp_path / 'no_stack'
    _make_project(stackless, specs={'specs/checkout/checkout.md': no_stack})
    sync_status(str(stackless))
    assert _payload_feature(stackless, 'checkout')['stack'] is None, (
        "A spec with no > Stack: should report no stack"
    )

    # > Scope: flips the next-step directive: with a scope file on disk the
    # feature is built and needs tests, without one it needs building.
    built = tmp_path / 'built'
    _make_project(built, specs={'specs/checkout/checkout.md': PRD_SPEC,
                                'specs/_anchors/api_conventions.md': API_ANCHOR_SPEC})
    os.makedirs(os.path.join(str(built), 'src', 'checkout'), exist_ok=True)
    with open(os.path.join(str(built), 'src', 'checkout', 'flow.py'), 'w') as f:
        f.write('def flow():\n    return True\n')
    built_block = _feature_block(sync_status(str(built)), 'checkout')
    assert '→ Run: purlin:test' in built_block, (
        f"With a > Scope: file on disk the directive is purlin:test, got:\n{built_block}"
    )
    unbuilt_block = _feature_block(sync_status(str(full)), 'checkout')
    assert '→ Run: purlin:build checkout' in unbuilt_block, (
        f"With no > Scope: file on disk the directive is purlin:build, got:\n{unbuilt_block}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-24", "RULE-15", tier="e2e")
def test_prd_scenario_requires_anchor_counts_toward_coverage(tmp_path):
    """The required anchor's 2 rules join the feature's denominator."""
    _make_project(tmp_path, specs={
        'specs/checkout/checkout.md': PRD_SPEC,
        'specs/_anchors/api_conventions.md': API_ANCHOR_SPEC,
    })
    block = _feature_block(sync_status(str(tmp_path)), 'checkout')
    assert 'checkout: 0/8 rules proved' in block, (
        f"6 own rules plus the anchor's 2 should read 0/8, got:\n{block}"
    )
    assert 'api_conventions/RULE-1: NO PROOF (required)' in block, (
        f"The required anchor's RULE-1 should be listed, got:\n{block}"
    )
    assert 'api_conventions/RULE-2: NO PROOF (required)' in block, (
        f"The required anchor's RULE-2 should be listed, got:\n{block}"
    )

    # The same spec with the > Requires: line gone: the anchor rules leave the
    # denominator, so the line is load-bearing and not decoration.
    no_req = PRD_SPEC.replace('> Requires: api_conventions\n', '')
    assert no_req != PRD_SPEC, "the no-Requires fixture did not apply"
    solo = tmp_path / 'solo'
    _make_project(solo, specs={
        'specs/checkout/checkout.md': no_req,
        'specs/_anchors/api_conventions.md': API_ANCHOR_SPEC,
    })
    solo_block = _feature_block(sync_status(str(solo)), 'checkout')
    assert 'checkout: 0/6 rules proved' in solo_block, (
        f"Without > Requires: the feature counts its own 6 rules, got:\n{solo_block}"
    )
    assert 'api_conventions/RULE-' not in solo_block, (
        f"Without > Requires: no anchor rule should be listed, got:\n{solo_block}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-25", "RULE-16", tier="e2e")
def test_vague_input_assumed_tags_carry_context(tmp_path):
    """Only the (assumed — <context>) form is counted; a bare tag is not."""
    assert 'fast' in VAGUE_DESCRIPTION_INPUT, "The vague input states no values"
    tagged = re.findall(r'\(assumed — user said "([^"]+)"\)', VAGUE_INPUT_SPEC)
    assert len(tagged) == 2, f"Expected 2 context-carrying tags, got {tagged}"
    assert all(context.strip() for context in tagged), f"Empty context in {tagged}"

    with_context = tmp_path / 'with_context'
    _make_project(with_context, specs={'specs/search/search.md': VAGUE_INPUT_SPEC})
    block = _feature_block(sync_status(str(with_context)), 'search')
    assert ASSUMED_ADVISORY_2 in block, (
        f"Both context-carrying tags should be counted, got:\n{block}"
    )

    # Same two rules, context stripped: the bare form RULE-16 forbids.
    bare = re.sub(r'\(assumed — [^)]*\)', '(assumed)', VAGUE_INPUT_SPEC)
    assert bare.count('(assumed)') == 2, "The stripped fixture should carry 2 bare tags"
    without_context = tmp_path / 'without_context'
    _make_project(without_context, specs={'specs/search/search.md': bare})
    bare_block = _feature_block(sync_status(str(without_context)), 'search')
    assert '(assumed) values' not in bare_block, (
        f"A bare (assumed) with no context must not count, got:\n{bare_block}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-26", "RULE-17", tier="e2e")
def test_assumed_tagged_rules_still_parse(tmp_path):
    """A rule carrying an (assumed) tag is still counted, printed and planned."""
    _make_project(tmp_path, specs={'specs/search/search.md': VAGUE_INPUT_SPEC})
    tagged = re.findall(r'\(assumed — user said "([^"]+)"\)', VAGUE_INPUT_SPEC)
    assert len(tagged) == 2, f"Expected 2 tagged rules in the fixture, got {tagged}"

    block = _feature_block(sync_status(str(tmp_path)), 'search')
    assert 'search: 0/5 rules proved' in block, (
        f"All 5 rules should be counted, tags and all, got:\n{block}"
    )
    printed = _own_rule_ids(block)
    assert printed == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4', 'RULE-5'], (
        f"No tagged rule should be dropped, got {printed}"
    )
    planned = _planned_proofs(block)
    assert planned == ['PROOF-1', 'PROOF-2', 'PROOF-3', 'PROOF-4', 'PROOF-5'], (
        f"Each rule keeps its planned proof, got {planned}"
    )
    assert ASSUMED_ADVISORY_2 in block, (
        f"The 2 tagged rules should draw the assumed advisory, got:\n{block}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-27", "RULE-18", tier="e2e")
def test_customer_feedback_has_specific_thresholds(tmp_path):
    """Each quoted complaint lands on a rule carrying its threshold."""
    _make_project(tmp_path, specs={
        'specs/dashboard/dashboard_load.md': CUSTOMER_FEEDBACK_SPEC,
    })
    block = _feature_block(sync_status(str(tmp_path)), 'dashboard_load')
    assert 'dashboard_load: 0/4 rules proved' in block, (
        f"Expected the 4 rules the complaints became, got:\n{block}"
    )

    rules = dict(_parse_rules(CUSTOMER_FEEDBACK_SPEC))
    # The slowness complaint becomes a numeric latency bound.
    latency = re.search(r'under (\d+) seconds', rules['RULE-1'])
    assert latency and latency.group(1) == '2', (
        f"RULE-1 should bound the slow load at 2 seconds, got: {rules['RULE-1']!r}"
    )
    # Every complaint is answered by exactly one rule carrying its literal.
    for complaint, expected in CUSTOMER_COMPLAINTS:
        matches = [rid for rid, text in rules.items() if expected in text]
        assert len(matches) == 1, (
            f"Complaint {complaint!r} should map to one rule carrying {expected!r}, "
            f"got {matches}"
        )
    # No complaint survives as prose: every rule carries a number.
    for rule_id, rule_text in rules.items():
        assert re.search(r'\d', rule_text), (
            f"{rule_id} carries no threshold: {rule_text!r}"
        )


@pytest.mark.proof("skill_spec_from_code", "PROOF-28", "RULE-19", tier="e2e")
def test_all_scenarios_have_tier_tags(tmp_path):
    """Every planned proof parses to a valid tier; a doubled tag is rejected."""
    clean = tmp_path / 'clean'
    _all_scenarios_project(clean)
    result = sync_status(str(clean))

    planned = re.findall(r'^\s+planned (PROOF-\d+): (.*)$', result, re.MULTILINE)
    assert len(planned) == 19, f"Expected the 19 planned proofs, got {len(planned)}"
    for proof_id, desc in planned:
        if '@' in desc:
            assert re.search(r'@(integration|e2e|manual)(\([^)]*\))?$', desc), (
                f"{proof_id} ends with something other than a tier tag: {desc!r}"
            )
    assert 'WARNING' not in result, (
        f"Well-tagged proofs should draw no tag warning, got:\n{result}"
    )

    # Two tier tags on one line: the grammar RULE-19 allows is one or none.
    doubled = PLAIN_DESCRIPTION_SPEC.replace(
        '- PROOF-1 (RULE-1): Upload a 5MB JPEG; verify 200 response @integration',
        '- PROOF-1 (RULE-1): Upload a 5MB JPEG; verify 200 response @e2e @integration',
    )
    assert doubled != PLAIN_DESCRIPTION_SPEC, "The doubled-tag fixture did not apply"
    broken = tmp_path / 'broken'
    _make_project(broken, specs={'specs/upload/file_upload.md': doubled})
    broken_out = sync_status(str(broken))
    assert ('WARNING: PROOF-1: a second tier tag @e2e precedes @integration'
            in broken_out), (
        f"A doubled tier tag should be flagged, got:\n{broken_out}"
    )

    skill = _skill_text()
    _require(skill, 'Phase 3 step 7',
             'Does the proof need a browser or full app stack? → append `@e2e`')
    _require(skill, 'Phase 3 step 7',
             'Does the proof shell out to git, subprocess, or call an external '
             'service? → append `@integration`')


@pytest.mark.proof("skill_spec_from_code", "PROOF-29", "RULE-20", tier="e2e")
def test_sync_status_parses_all_scenarios(tmp_path):
    """All four scenario specs parse, each with its own rule count, all UNTESTED."""
    _all_scenarios_project(tmp_path)
    result = sync_status(str(tmp_path))
    assert 'ERROR' not in result, f"sync_status produced errors:\n{result}"

    for _label, (name, _path, _content, count) in ALL_SCENARIOS.items():
        assert f'{name}: 0/{count} rules proved' in result, (
            f"{name} should report 0/{count} rules proved in:\n{result}"
        )
    assert result.count('UNTESTED') == len(ALL_SCENARIOS), (
        f"Each of the {len(ALL_SCENARIOS)} features should read UNTESTED, "
        f"got {result.count('UNTESTED')}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-30", "RULE-21", tier="e2e")
def test_all_scenarios_have_rules_and_proof_sections(tmp_path):
    """Both sections are load-bearing: drop either and sync_status says so."""
    both = tmp_path / 'both'
    _all_scenarios_project(both)
    result = sync_status(str(both))
    for _label, (name, _path, content, count) in ALL_SCENARIOS.items():
        block = _feature_block(result, name)
        assert f'{name}: 0/{count} rules proved' in block, (
            f"{name} should report its {count} rules, got:\n{block}"
        )
        expected = re.findall(r'^- (PROOF-\d+) ', content, re.MULTILINE)
        assert _planned_proofs(block) == expected, (
            f"{name} should plan {expected}, got {_planned_proofs(block)}"
        )

    # No ## Rules section: the feature has no rules to prove at all.
    no_rules = _without_section(PLAIN_DESCRIPTION_SPEC, '## Rules', '## Proof')
    ruleless = tmp_path / 'no_rules'
    _make_project(ruleless, specs={'specs/upload/file_upload.md': no_rules})
    ruleless_block = _feature_block(sync_status(str(ruleless)), 'file_upload')
    assert 'file_upload: no rules defined' in ruleless_block, (
        f"A spec with no ## Rules section has no rules, got:\n{ruleless_block}"
    )
    assert 'WARNING: No ## Rules section found.' in ruleless_block, (
        f"A missing ## Rules section should be flagged, got:\n{ruleless_block}"
    )

    # No ## Proof section: the rules still count, but nothing is planned.
    no_proof = PLAIN_DESCRIPTION_SPEC.split('## Proof')[0]
    assert no_proof != PLAIN_DESCRIPTION_SPEC, "the no-Proof fixture did not apply"
    proofless = tmp_path / 'no_proof'
    _make_project(proofless, specs={'specs/upload/file_upload.md': no_proof})
    proofless_block = _feature_block(sync_status(str(proofless)), 'file_upload')
    assert 'file_upload: 0/4 rules proved' in proofless_block, (
        f"The 4 rules still count without a ## Proof section, got:\n{proofless_block}"
    )
    assert _planned_proofs(proofless_block) == [], (
        f"A spec with no ## Proof section can plan no proof, got:\n{proofless_block}"
    )
    assert '"PROOF-N", "RULE-1"' in proofless_block, (
        f"Missing ## Proof should leave the PROOF-N placeholder, got:\n{proofless_block}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-31", "RULE-22", tier="e2e")
def test_assumed_tag_removal_on_explicit_update(tmp_path):
    """Replacing the tag with an explicit value keeps the rule and drops the count."""
    before = tmp_path / 'before'
    _make_project(before, specs={'specs/search/search.md': VAGUE_INPUT_SPEC})
    before_block = _feature_block(sync_status(str(before)), 'search')
    assert ASSUMED_ADVISORY_2 in before_block, (
        f"The fixture should start with 2 assumed rules, got:\n{before_block}"
    )

    updated = VAGUE_INPUT_SPEC.replace(TAGGED_RULE_4, EXPLICIT_RULE_4)
    assert updated != VAGUE_INPUT_SPEC, "the explicit-value fixture did not apply"
    assert '(assumed' not in EXPLICIT_RULE_4, "The updated rule carries no tag"
    after = tmp_path / 'after'
    _make_project(after, specs={'specs/search/search.md': updated})
    after_block = _feature_block(sync_status(str(after)), 'search')

    assert 'search: 0/5 rules proved' in after_block, (
        f"The updated rule must stay a countable RULE-N, got:\n{after_block}"
    )
    assert 'RULE-4: NO PROOF (own)' in after_block, (
        f"RULE-4 should still be read back after the update, got:\n{after_block}"
    )
    assert 'PROOF-4' in _planned_proofs(after_block), (
        f"RULE-4 should still carry its planned proof, got:\n{after_block}"
    )
    assert ASSUMED_ADVISORY_1 in after_block, (
        f"One tag removed leaves 1 assumed rule, got:\n{after_block}"
    )
    assert ASSUMED_ADVISORY_2 not in after_block, (
        f"The 2-rule advisory should be gone, got:\n{after_block}"
    )
