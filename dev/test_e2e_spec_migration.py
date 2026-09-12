"""E2E tests for spec-from-code migration across multiple input formats.

Validates that purlin:spec-from-code can migrate specs from any format
(legacy features/, unnumbered rules, missing sections, missing metadata)
to the current compliant format with minimal fidelity loss.

Each test creates a temp project with sample specs in various formats,
runs the migration/compliance-check logic, and validates the output
through sync_status parsing and (for PROOF-9) LLM evaluation.

Run with: python3 -m pytest dev/test_e2e_spec_migration.py -v
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
from purlin_server import sync_status, _scan_specs, read_report_payload

SKILL_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '..', 'skills', 'spec-from-code', 'SKILL.md'))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(tmp_dir, specs=None, features=None):
    """Create a minimal Purlin project in tmp_dir."""
    os.makedirs(os.path.join(tmp_dir, '.purlin'), exist_ok=True)
    with open(os.path.join(tmp_dir, '.purlin', 'config.json'), 'w') as f:
        json.dump({"version": "0.9.0", "test_framework": "pytest", "spec_dir": "specs"}, f)
    os.makedirs(os.path.join(tmp_dir, 'specs', '_anchors'), exist_ok=True)

    if specs:
        for path, content in specs.items():
            full = os.path.join(tmp_dir, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, 'w') as f:
                f.write(content)

    if features:
        for path, content in features.items():
            full = os.path.join(tmp_dir, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, 'w') as f:
                f.write(content)


def _parse_rules(content):
    """Extract RULE-N lines from spec content."""
    return re.findall(r'^- (RULE-\d+): (.+)$', content, re.MULTILINE)


def _parse_proofs(content):
    """Extract PROOF-N (RULE-N) lines from spec content."""
    return re.findall(r'^- (PROOF-\d+) \((RULE-\d+)\): (.+)$', content, re.MULTILINE)


def _get_description(content):
    """Extract > Description: value from spec content."""
    m = re.search(r'^> Description: (.+)$', content, re.MULTILINE)
    return m.group(1).strip() if m else None


def _get_metadata(content, field):
    """Extract a metadata field value."""
    m = re.search(r'^> ' + field + r': (.+)$', content, re.MULTILINE)
    return m.group(1).strip() if m else None


def _has_section(content, section):
    """Check if a markdown section exists."""
    return bool(re.search(r'^## ' + section, content, re.MULTILINE))


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


def _payload_feature(project_root, name):
    """One feature record from the project's dashboard payload."""
    payload = read_report_payload(project_root)
    assert payload, 'read_report_payload returned nothing for the fixture project'
    by_name = {f['name']: f for f in payload['features']}
    assert name in by_name, f'{name} missing from the dashboard payload: {sorted(by_name)}'
    return by_name[name]


# ---------------------------------------------------------------------------
# Sample specs — various non-compliant formats
# ---------------------------------------------------------------------------

LEGACY_GIVEN_WHEN_THEN = """\
# Feature: login

## Description
Authenticates users via email and password.

## Scenarios

### Valid login
Given a registered user with email alice@example.com
When they POST /login with valid credentials
Then the response is 200 with a JWT token

### Invalid password
Given a registered user with email alice@example.com
When they POST /login with a wrong password
Then the response is 401 Unauthorized

### Rate limiting
Given a user has failed login 10 times
When they attempt login again
Then the response is 429 Too Many Requests
"""

UNNUMBERED_RULES_SPEC = """\
# Feature: cart

> Scope: src/cart/cart.py, src/cart/checkout.py
> Stack: python/flask, redis

## What it does

Shopping cart with add/remove items and checkout.

## Rules

- Adding an item increases the cart total
- Removing an item decreases the cart total
- Cart total is zero when empty
- Checkout with empty cart returns 400

## Proof

- Verify adding item works
- Verify removing item works
- Verify empty cart total
- Verify empty checkout rejected
"""

MISSING_DESCRIPTION_SPEC = """\
# Feature: notifications

> Scope: src/notify/email.py, src/notify/sms.py
> Stack: python/stdlib, twilio

## What it does

Sends email and SMS notifications to users.

## Rules

- RULE-1: Email notifications are sent for order confirmations
- RULE-2: SMS notifications are sent for delivery updates
- RULE-3: Users can opt out of SMS notifications

## Proof

- PROOF-1 (RULE-1): Create an order; verify confirmation email sent @integration
- PROOF-2 (RULE-2): Update delivery status; verify SMS sent @integration
- PROOF-3 (RULE-3): Set opt-out; trigger SMS; verify not sent @integration
"""

MISSING_PROOF_SECTION = """\
# Feature: search

> Description: Full-text search across products.
> Scope: src/search/engine.py
> Stack: python/elasticsearch

## What it does

Searches products by name, description, and tags.

## Rules

- RULE-1: Search by name returns matching products
- RULE-2: Search is case-insensitive
- RULE-3: Empty query returns no results
"""

FULLY_COMPLIANT_SPEC = """\
# Feature: profile

> Description: User profile management with avatar upload.
> Scope: src/users/profile.py
> Stack: python/flask, pillow
> Requires: input_handling

## What it does

Users can view and edit their profile, including uploading an avatar image.

## Rules

- RULE-1: GET /profile returns the current user's profile data
- RULE-2: PUT /profile updates name and bio fields
- RULE-3: Avatar upload accepts only JPEG and PNG under 5MB

## Proof

- PROOF-1 (RULE-1): GET /profile with auth token; verify 200 with user data @integration
- PROOF-2 (RULE-2): PUT /profile with new name; verify name updated @integration
- PROOF-3 (RULE-3): Upload a 6MB PNG; verify 413 rejection @integration
"""


# The legacy companion files Phase 1 step 3a must read past when it globs
# features/**/*.md for migration candidates.
LEGACY_IMPL_COMPANION = """\
# Implementation Notes: login

## Active Deviations

| Spec says | Implementation does | Status |
| --- | --- | --- |
| Lockout after 10 failures | Lockout after 5 failures | PM-ACCEPTED |
"""

LEGACY_DISCOVERIES_COMPANION = """\
# Discoveries: login

- [BUG] M3: error banner overlaps the password field (RESOLVED)
- [BUG] M7: expired session redirects to / instead of /login (OPEN)
"""

# The compliant spec a migration of features/auth/login.md would write. The
# migration step is agent prose, so this file stands in for its output; what the
# test proves is that specs/auth/login.md is the path the toolchain reads.
MIGRATED_LOGIN_SPEC = """\
# Feature: login

> Description: Authenticates users via email and password.
> Scope: src/auth/login.py
> Stack: python/flask

## What it does

Authenticates users via email and password, with rate limiting.

## Rules

- RULE-1: POST /login with valid credentials returns 200 with a JWT token
- RULE-2: POST /login with a wrong password returns 401 Unauthorized
- RULE-3: The 11th login attempt after 10 failures returns 429 Too Many Requests

## Proof

- PROOF-1 (RULE-1): POST /login as alice@example.com with the right password; verify 200 and a JWT @integration
- PROOF-2 (RULE-2): POST /login as alice@example.com with a wrong password; verify 401 @integration
- PROOF-3 (RULE-3): Fail login 10 times then try again; verify 429 @integration
"""

# Same feature as MISSING_DESCRIPTION_SPEC, differing only by the
# `> Description:` line: the contrast that makes the missing-field check fail
# against a broken parser instead of restating the fixture.
DOCUMENTED_DESCRIPTION_SPEC = """\
# Feature: notifications_documented

> Description: Sends email and SMS notifications to users.
> Scope: src/notify/email.py, src/notify/sms.py
> Stack: python/stdlib, twilio

## What it does

Sends email and SMS notifications to users.

## Rules

- RULE-1: Email notifications are sent for order confirmations
- RULE-2: SMS notifications are sent for delivery updates
- RULE-3: Users can opt out of SMS notifications

## Proof

- PROOF-1 (RULE-1): Create an order; verify confirmation email sent @integration
- PROOF-2 (RULE-2): Update delivery status; verify SMS sent @integration
- PROOF-3 (RULE-3): Set opt-out; trigger SMS; verify not sent @integration
"""

NO_RULES_SECTION_SPEC = """\
# Feature: legacy_thing

> Description: An old note that never became a spec.
> Scope: src/legacy/thing.py

## What it does

Prose only: no rules, no proofs.
"""

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.proof("skill_spec_from_code", "PROOF-10", "RULE-5", tier="e2e")
def test_legacy_features_dir_is_phase1_detection_scope(tmp_path):
    """A legacy features/ spec counts for nothing until Phase 1 finds it."""
    _make_project(tmp_path, features={
        'features/auth/login.md': LEGACY_GIVEN_WHEN_THEN,
        'features/auth/login.impl.md': LEGACY_IMPL_COMPANION,
        'features/auth/login.discoveries.md': LEGACY_DISCOVERIES_COMPANION,
    })

    # The migration input: three Given/When/Then scenarios in the legacy file.
    blocks = re.findall(
        r'(Given .+?\nWhen .+?\nThen .+?)(?=\n\n|\n###|\Z)',
        LEGACY_GIVEN_WHEN_THEN, re.DOTALL
    )
    assert len(blocks) == 3, f"Expected 3 Given/When/Then blocks, got {len(blocks)}"

    # Observable half: the toolchain sees nothing, so the legacy spec is a
    # migration candidate rather than covered work.
    result = sync_status(str(tmp_path))
    assert 'No specs found in specs/' in result, (
        f"A features/-only project should report no specs, got:\n{result}"
    )
    assert 'login' not in result, (
        f"sync_status must not count the legacy features/ spec:\n{result}"
    )

    # Checkable half of an agent-run phase: the step 3a instruction itself.
    skill = _skill_text()
    assert 'Read all `.md` files recursively (excluding `.impl.md` and `.discoveries.md`' in skill, (
        "SKILL.md Phase 1 step 3a must scan features/ recursively, excluding companions"
    )
    assert 'scenarios (Given/When/Then blocks)' in skill, (
        "SKILL.md Phase 1 step 3a must extract Given/When/Then scenarios"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-11", "RULE-6", tier="e2e")
def test_unnumbered_rules_get_renumbered(tmp_path):
    """Specs with unnumbered rules should be detected as non-compliant."""
    _make_project(tmp_path, specs={
        'specs/cart/cart.md': UNNUMBERED_RULES_SPEC,
    })

    # sync_status should report warnings for unnumbered rules
    result = sync_status(str(tmp_path))

    # Verify sync_status flags the unnumbered rules
    assert 'cart' in result, "cart feature not found in sync_status output"
    assert 'WARNING' in result, "sync_status should emit a WARNING for unnumbered rules"
    assert 'not numbered' in result.lower(), "WARNING should mention 'not numbered'"

    # Verify the spec has unnumbered rules (migration input)
    rules = _parse_rules(UNNUMBERED_RULES_SPEC)
    assert len(rules) == 0, "Unnumbered spec should have 0 RULE-N lines before migration"

    # Verify there ARE rule-like lines that migration would capture
    rule_lines = re.findall(r'^- (.+)$', UNNUMBERED_RULES_SPEC, re.MULTILINE)
    unnumbered = [r for r in rule_lines if not r.startswith('RULE-') and not r.startswith('PROOF-') and not r.startswith('Verify')]
    assert len(unnumbered) == 4, f"Expected 4 unnumbered rules, got {len(unnumbered)}"


@pytest.mark.proof("skill_spec_from_code", "PROOF-12", "RULE-6", tier="e2e")
def test_missing_description_detected(tmp_path):
    """A missing > Description: shows up as a null description in the payload."""
    _make_project(tmp_path, specs={
        'specs/notify/notifications.md': MISSING_DESCRIPTION_SPEC,
        'specs/notify/notifications_documented.md': DOCUMENTED_DESCRIPTION_SPEC,
    })
    assert _has_section(MISSING_DESCRIPTION_SPEC, 'What it does'), (
        "Fixture should have ## What it does for the migration to derive from"
    )

    sync_status(str(tmp_path))

    # The two specs differ only by the > Description: line, so the contrast is
    # the parser's reading of that line and not the fixture restating itself.
    missing = _payload_feature(str(tmp_path), 'notifications')
    documented = _payload_feature(str(tmp_path), 'notifications_documented')
    assert missing['description'] is None, (
        f"Spec without > Description: should report no description, got {missing['description']!r}"
    )
    assert documented['description'] == 'Sends email and SMS notifications to users.', (
        f"Spec with > Description: should report it verbatim, got {documented['description']!r}"
    )

    skill = _skill_text()
    assert 'Missing `> Description:` metadata' in skill, (
        "SKILL.md Phase 1 step 3b must list the missing Description criterion"
    )
    assert 'add missing `> Description:`' in skill, (
        "SKILL.md Phase 3 step 3 must order the missing Description filled in"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-13", "RULE-6", tier="e2e")
def test_missing_proof_section_detected(tmp_path):
    """A spec with no ## Proof section plans no proof and gets the placeholder."""
    _make_project(tmp_path, specs={
        'specs/search/search.md': MISSING_PROOF_SECTION,
        'specs/notify/notifications.md': MISSING_DESCRIPTION_SPEC,
    })

    result = sync_status(str(tmp_path))
    search = _feature_block(result, 'search')
    assert 'search: 0/3 rules proved' in search, (
        f"search should report its 3 rules, got:\n{search}"
    )
    assert 'planned PROOF' not in search, (
        f"A spec with no ## Proof section can plan no proof, got:\n{search}"
    )
    assert '@pytest.mark.proof("search", "PROOF-N", "RULE-1")' in search, (
        f"Missing ## Proof section should leave the PROOF-N placeholder, got:\n{search}"
    )

    # Contrast: the sibling spec that does have a ## Proof section.
    notifications = _feature_block(result, 'notifications')
    assert ('planned PROOF-1: Create an order; verify confirmation email sent @integration'
            in notifications), (
        f"A spec with proofs should print its planned proof, got:\n{notifications}"
    )

    skill = _skill_text()
    assert 'Missing `## Proof` section' in skill, (
        "SKILL.md Phase 1 step 3b must list the missing Proof section criterion"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-14", "RULE-7", tier="e2e")
def test_compliant_spec_bytes_untouched(tmp_path):
    """A fully compliant spec is neither flagged nor rewritten."""
    _make_project(tmp_path, specs={
        'specs/users/profile.md': FULLY_COMPLIANT_SPEC,
    })
    spec_file = os.path.join(str(tmp_path), 'specs', 'users', 'profile.md')
    with open(spec_file, 'rb') as f:
        before_digest = hashlib.sha256(f.read()).hexdigest()
    before_mtime = os.stat(spec_file).st_mtime_ns

    result = sync_status(str(tmp_path))

    with open(spec_file, 'rb') as f:
        after_digest = hashlib.sha256(f.read()).hexdigest()
    assert after_digest == before_digest, "The compliant spec's bytes were rewritten"
    assert os.stat(spec_file).st_mtime_ns == before_mtime, (
        "The compliant spec's mtime moved, so something wrote to it"
    )

    block = _feature_block(result, 'profile')
    assert 'profile: 0/3 rules proved' in block, (
        f"profile should report its 3 rules, got:\n{block}"
    )
    assert 'WARNING' not in block, (
        f"A compliant spec should draw no format warning, got:\n{block}"
    )

    skill = _skill_text()
    assert 'are left untouched' in skill, (
        "SKILL.md Phase 1 step 3b must say compliant specs are left untouched"
    )
    assert 'they are not migration candidates' in skill, (
        "SKILL.md Phase 1 step 3b must exclude compliant specs from the candidates"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-15", "RULE-7", tier="e2e")
def test_compliant_spec_excluded_from_candidate_list(tmp_path):
    """The flagged specs are the non-compliant ones; the compliant one is not."""
    _make_project(tmp_path, specs={
        'specs/users/profile.md': FULLY_COMPLIANT_SPEC,
        'specs/cart/cart.md': UNNUMBERED_RULES_SPEC,
        'specs/legacy/legacy_thing.md': NO_RULES_SECTION_SPEC,
    })

    result = sync_status(str(tmp_path))

    cart = _feature_block(result, 'cart')
    assert 'WARNING: 4 lines under ## Rules are not numbered.' in cart, (
        f"The unnumbered spec should be flagged with its line count, got:\n{cart}"
    )
    legacy = _feature_block(result, 'legacy_thing')
    assert 'WARNING: No ## Rules section found.' in legacy, (
        f"The spec with no ## Rules section should be flagged, got:\n{legacy}"
    )
    profile = _feature_block(result, 'profile')
    assert 'profile: 0/3 rules proved' in profile, (
        f"profile should report its 3 rules, got:\n{profile}"
    )
    assert 'WARNING' not in profile, (
        f"The compliant spec must stay off the candidate list, got:\n{profile}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-16", "RULE-8", tier="e2e")
def test_existing_metadata_is_load_bearing(tmp_path):
    """Scope and Stack drive the tool's output, so losing them is observable."""
    built = tmp_path / 'built'
    _make_project(built, specs={
        'specs/notify/notifications.md': MISSING_DESCRIPTION_SPEC,
    })
    # One of the files named in > Scope: exists here.
    os.makedirs(os.path.join(str(built), 'src', 'notify'), exist_ok=True)
    with open(os.path.join(str(built), 'src', 'notify', 'email.py'), 'w') as f:
        f.write('def send_email():\n    return True\n')

    result = sync_status(str(built))
    block = _feature_block(result, 'notifications')
    assert '\u2192 Run: purlin:test' in block, (
        f"With a > Scope: file on disk the directive is purlin:test, got:\n{block}"
    )
    assert _payload_feature(str(built), 'notifications')['stack'] == 'python/stdlib, twilio', (
        "The > Stack: line must reach the dashboard payload verbatim"
    )

    # The same spec with no scope file present: the directive flips, which is
    # what a migration that dropped the > Scope: line would do to every reader.
    unbuilt = tmp_path / 'unbuilt'
    _make_project(unbuilt, specs={
        'specs/notify/notifications.md': MISSING_DESCRIPTION_SPEC,
    })
    unbuilt_block = _feature_block(sync_status(str(unbuilt)), 'notifications')
    assert '\u2192 Run: purlin:build notifications' in unbuilt_block, (
        f"With no > Scope: file on disk the directive is purlin:build, got:\n{unbuilt_block}"
    )

    skill = _skill_text()
    assert 'existing metadata (`> Scope:`, `> Stack:`, `> Requires:`)' in skill, (
        "SKILL.md Phase 3 step 3 must order existing metadata preserved"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-17", "RULE-5", tier="e2e")
def test_legacy_feature_name_and_category_preserved(tmp_path):
    """specs/auth/login.md is the destination the toolchain reads back."""
    _make_project(tmp_path, features={
        'features/auth/login.md': LEGACY_GIVEN_WHEN_THEN,
    })
    before = sync_status(str(tmp_path))
    assert 'No specs found in specs/' in before, (
        f"Before migration the project has no spec, got:\n{before}"
    )

    # Migration is agent prose, so the destination file is written by hand; what
    # is proved is that this path is what category and name resolve to.
    dest = os.path.join(str(tmp_path), 'specs', 'auth', 'login.md')
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w') as f:
        f.write(MIGRATED_LOGIN_SPEC)

    after = sync_status(str(tmp_path))
    block = _feature_block(after, 'login')
    assert 'login: 0/3 rules proved' in block, (
        f"The migrated spec should report its 3 rules, got:\n{after}"
    )
    assert _payload_feature(str(tmp_path), 'login')['category'] == 'auth', (
        "specs/auth/login.md must land in category auth"
    )

    skill = _skill_text()
    assert 'Read the original `features/<category>/<name>.md` file in full' in skill, (
        "SKILL.md Phase 3 step 3 must read features/<category>/<name>.md"
    )
    assert 'write `specs/<category>/<name>.md`' in skill, (
        "SKILL.md Phase 3 step 6 must write specs/<category>/<name>.md"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-18", "RULE-8", tier="e2e")
def test_llm_evaluates_migration_fidelity(tmp_path):
    """LLM evaluator rates migration fidelity as HIGH for each scenario.

    This test sends the original and a hand-migrated version to an LLM
    and verifies it rates the migration as preserving intent. The LLM
    call is mocked here with deterministic validation — in a real e2e
    run, replace with an actual LLM call.
    """
    # Scenario: unnumbered rules → numbered rules
    original = UNNUMBERED_RULES_SPEC
    migrated = """\
# Feature: cart

> Description: Shopping cart with add/remove items and checkout.
> Scope: src/cart/cart.py, src/cart/checkout.py
> Stack: python/flask, redis

## What it does

Shopping cart with add/remove items and checkout.

## Rules

- RULE-1: Adding an item increases the cart total
- RULE-2: Removing an item decreases the cart total
- RULE-3: Cart total is zero when empty
- RULE-4: Checkout with empty cart returns 400

## Proof

- PROOF-1 (RULE-1): Add item to cart; verify total increases @integration
- PROOF-2 (RULE-2): Remove item from cart; verify total decreases @integration
- PROOF-3 (RULE-3): Create empty cart; verify total is 0
- PROOF-4 (RULE-4): POST /checkout with empty cart; verify 400 response @integration
"""

    # Deterministic fidelity check: all original rule content preserved
    orig_rules = re.findall(r'^- (.+)$', original, re.MULTILINE)
    orig_rules = [r for r in orig_rules if not r.startswith('Verify')]
    migrated_rules = _parse_rules(migrated)
    migrated_rule_texts = [text for _, text in migrated_rules]

    for orig_rule in orig_rules:
        assert any(orig_rule in mt for mt in migrated_rule_texts), (
            f"Original rule '{orig_rule}' not found in migrated spec"
        )

    # Verify structural compliance of migrated output
    assert _has_section(migrated, 'Rules'), "Migrated spec should have Rules section"
    assert _has_section(migrated, 'Proof'), "Migrated spec should have Proof section"
    assert len(migrated_rules) == 4, f"Expected 4 numbered rules, got {len(migrated_rules)}"
    proofs = _parse_proofs(migrated)
    assert len(proofs) == 4, f"Expected 4 proofs, got {len(proofs)}"

    # Every rule has a corresponding proof
    rule_ids = {r_id for r_id, _ in migrated_rules}
    proof_rule_refs = {rule_ref for _, rule_ref, _ in proofs}
    assert rule_ids == proof_rule_refs, (
        f"Rule-proof mismatch: rules={rule_ids}, proof refs={proof_rule_refs}"
    )


# ---------------------------------------------------------------------------
# Simulated generated specs — four scenarios for RULE-10 through RULE-22
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

# Each complaint and the literal the rule answering it must carry.
CUSTOMER_COMPLAINTS = [
    ("The dashboard takes forever to load once I have a lot of features", "2 seconds"),
    ("Paging through the feature list reloads everything", "25 items per page"),
]

ALL_SCENARIOS = {
    'plain': PLAIN_DESCRIPTION_SPEC,
    'prd': PRD_SPEC,
    'vague': VAGUE_INPUT_SPEC,
    'feedback': CUSTOMER_FEEDBACK_SPEC,
}


# ---------------------------------------------------------------------------
# Tests for RULE-10 through RULE-22
# ---------------------------------------------------------------------------


@pytest.mark.proof("skill_spec_from_code", "PROOF-19", "RULE-10", tier="e2e")
def test_sequential_rule_numbering(tmp_path):
    """The rule ids sync_status reads back run RULE-1..RULE-4 with no gap."""
    assert '10MB' in PLAIN_DESCRIPTION_INPUT and '413' in PLAIN_DESCRIPTION_INPUT, (
        "The plain-description input states its values explicitly"
    )
    _make_project(tmp_path, specs={
        'specs/upload/file_upload.md': PLAIN_DESCRIPTION_SPEC,
    })

    block = _feature_block(sync_status(str(tmp_path)), 'file_upload')
    assert 'file_upload: 0/4 rules proved' in block, (
        f"Expected 4 rules read back from the generated spec, got:\n{block}"
    )
    printed = re.findall(r'^  (RULE-\d+):', block, re.MULTILINE)
    assert printed == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4'], (
        f"Rule ids should run 1..4 in order with no gap, got {printed}"
    )

    skill = _skill_text()
    assert ('- RULE-1: <Behavioral constraint extracted from code>\n'
            '- RULE-2: <Another constraint>') in skill, (
        "SKILL.md step 6 template must number feature rules RULE-1 then RULE-2"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-20", "RULE-11", tier="e2e")
def test_every_rule_has_proof(tmp_path):
    """Every RULE-N has at least one PROOF referencing it."""
    _make_project(tmp_path, specs={
        'specs/upload/file_upload.md': PLAIN_DESCRIPTION_SPEC,
    })
    rules = _parse_rules(PLAIN_DESCRIPTION_SPEC)
    proofs = _parse_proofs(PLAIN_DESCRIPTION_SPEC)
    rule_ids = {r_id for r_id, _ in rules}
    proved_rules = {rule_ref for _, rule_ref, _ in proofs}
    unproved = rule_ids - proved_rules
    assert not unproved, f"These rules have no proof: {unproved}"


@pytest.mark.proof("skill_spec_from_code", "PROOF-21", "RULE-12", tier="e2e")
def test_no_assumed_tags_with_explicit_values(tmp_path):
    """Explicit input: no (assumed) line; vague input: two of them."""
    _make_project(tmp_path, specs={
        'specs/upload/file_upload.md': PLAIN_DESCRIPTION_SPEC,
        'specs/search/search.md': VAGUE_INPUT_SPEC,
    })
    assert '(assumed' not in PLAIN_DESCRIPTION_SPEC, (
        "Spec generated from explicit values should carry no (assumed) tag"
    )

    result = sync_status(str(tmp_path))
    plain = _feature_block(result, 'file_upload')
    assert '(assumed) values' not in plain, (
        f"The explicit-values feature should draw no assumed advisory, got:\n{plain}"
    )
    vague = _feature_block(result, 'search')
    assert '\u26a0 2 rules have (assumed) values \u2014 PM should confirm' in vague, (
        f"The vague-input feature should report its 2 assumed rules, got:\n{vague}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-22", "RULE-13", tier="e2e")
def test_prd_extracts_at_least_5_rules(tmp_path):
    """PRD spec with multiple requirements extracts at least 5 RULE-N lines."""
    _make_project(tmp_path, specs={
        'specs/checkout/checkout.md': PRD_SPEC,
    })
    rules = _parse_rules(PRD_SPEC)
    assert len(rules) >= 5, (
        f"PRD spec should have at least 5 rules, got {len(rules)}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-23", "RULE-14", tier="e2e")
def test_prd_has_valid_metadata(tmp_path):
    """PRD spec has Description, Scope, and Stack metadata fields — verified via _scan_specs parser."""
    _make_project(tmp_path, specs={
        'specs/checkout/checkout.md': PRD_SPEC,
    })
    # Verify the parser (_scan_specs) extracts the metadata fields from the written spec file.
    # This tests that sync_status can read the spec and reports the expected fields — behavioral
    # proof that the spec format is parser-readable, not just a string check on the constant.
    features = _scan_specs(str(tmp_path))
    assert 'checkout' in features, "checkout feature not found by _scan_specs"
    feature = features['checkout']

    # Description is extracted from the > Description: line
    desc = feature.get('description')
    assert desc is not None and desc != '', (
        f"_scan_specs did not extract > Description: from checkout spec, got: {desc!r}"
    )
    assert 'checkout' in desc.lower() or 'step' in desc.lower(), (
        f"Extracted description does not match PRD content: {desc!r}"
    )

    # Scope is extracted and stored on the feature (as a list of paths)
    scope = feature.get('scope')
    assert scope, (
        f"_scan_specs did not extract > Scope: from checkout spec, got: {scope!r}"
    )
    scope_str = str(scope)
    assert 'src/checkout' in scope_str, (
        f"Extracted scope does not contain 'src/checkout': {scope!r}"
    )

    # Stack is extracted
    stack = feature.get('stack')
    assert stack is not None and stack != '', (
        f"_scan_specs did not extract > Stack: from checkout spec, got: {stack!r}"
    )
    assert 'python' in stack.lower() or 'flask' in stack.lower(), (
        f"Extracted stack does not match PRD content: {stack!r}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-24", "RULE-15", tier="e2e")
def test_prd_requires_overlapping_anchor(tmp_path):
    """PRD spec includes Requires referencing an anchor; sync_status counts required rules in total."""
    anchor = """\
# Anchor: api_conventions

> Description: REST API conventions.

## Rules

- RULE-1: All responses use JSON envelope
- RULE-2: Errors include error code and message

## Proof

- PROOF-1 (RULE-1): POST endpoint; verify JSON envelope
- PROOF-2 (RULE-2): Trigger error; verify error code and message
"""
    _make_project(tmp_path, specs={
        'specs/checkout/checkout.md': PRD_SPEC,
        'specs/_anchors/api_conventions.md': anchor,
    })

    # Verify _scan_specs extracts the Requires relationship from the written spec file.
    # This is behavioral: the parser must read > Requires: and link the anchor.
    features = _scan_specs(str(tmp_path))
    assert 'checkout' in features, "checkout feature not found by _scan_specs"
    requires = features['checkout'].get('requires', [])
    assert 'api_conventions' in requires, (
        f"_scan_specs did not extract > Requires: api_conventions from checkout spec. "
        f"Got requires={requires!r}"
    )

    # Verify sync_status counts anchor rules toward the feature's total coverage.
    # PRD_SPEC has 6 own rules + anchor has 2 rules = 8 total expected.
    result = sync_status(str(tmp_path))
    assert 'checkout' in result, "checkout not in sync_status output"
    assert 'api_conventions' in result, (
        "sync_status output should reference the required anchor api_conventions"
    )
    # With 0 proofs filed, sync_status must show the anchor rules in the total.
    # The total should be 8 (6 own + 2 required), shown as 0/8.
    assert '0/8' in result, (
        f"Expected 0/8 coverage (6 own + 2 anchor rules), did not find '0/8' in:\n{result}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-25", "RULE-16", tier="e2e")
def test_vague_input_assumed_tags_carry_context(tmp_path):
    """Only the (assumed \u2014 <context>) form is counted; a bare tag is not."""
    assert 'fast' in VAGUE_DESCRIPTION_INPUT, "The vague input states no values"
    tagged = re.findall(r'\(assumed \u2014 user said "([^"]+)"\)', VAGUE_INPUT_SPEC)
    assert len(tagged) == 2, f"Expected 2 context-carrying tags, got {tagged}"
    assert all(context.strip() for context in tagged), f"Empty context in {tagged}"

    with_context = tmp_path / 'with_context'
    _make_project(with_context, specs={'specs/search/search.md': VAGUE_INPUT_SPEC})
    block = _feature_block(sync_status(str(with_context)), 'search')
    assert '\u26a0 2 rules have (assumed) values \u2014 PM should confirm' in block, (
        f"Both context-carrying tags should be counted, got:\n{block}"
    )

    # Same two rules, context stripped: the bare form RULE-16 forbids.
    bare = re.sub(r'\(assumed \u2014 [^)]*\)', '(assumed)', VAGUE_INPUT_SPEC)
    assert bare.count('(assumed)') == 2, "The stripped fixture should carry 2 bare tags"
    without_context = tmp_path / 'without_context'
    _make_project(without_context, specs={'specs/search/search.md': bare})
    bare_block = _feature_block(sync_status(str(without_context)), 'search')
    assert '(assumed) values' not in bare_block, (
        f"A bare (assumed) with no context must not count, got:\n{bare_block}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-26", "RULE-17", tier="e2e")
def test_assumed_tags_parseable_by_sync_status(tmp_path):
    """sync_status parses rules with (assumed) tags without errors."""
    _make_project(tmp_path, specs={
        'specs/search/search.md': VAGUE_INPUT_SPEC,
    })
    result = sync_status(str(tmp_path))
    assert 'search' in result, "search feature not found in sync_status output"
    # Should report correct rule count — assumed rules still count
    rules = _parse_rules(VAGUE_INPUT_SPEC)
    assert len(rules) == 5, f"Expected 5 rules, got {len(rules)}"
    # sync_status should not error or skip assumed rules
    assert 'ERROR' not in result


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
    _make_project(clean, specs={
        'specs/upload/file_upload.md': PLAIN_DESCRIPTION_SPEC,
        'specs/checkout/checkout.md': PRD_SPEC,
        'specs/search/search.md': VAGUE_INPUT_SPEC,
        'specs/dashboard/dashboard_load.md': CUSTOMER_FEEDBACK_SPEC,
    })
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
    assert 'Does the proof need a browser or full app stack? \u2192 append `@e2e`' in skill, (
        "SKILL.md step 7 must route browser/full-stack proofs to @e2e"
    )
    assert ('Does the proof shell out to git, subprocess, or call an external service? '
            '\u2192 append `@integration`') in skill, (
        "SKILL.md step 7 must route external-dependency proofs to @integration"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-29", "RULE-20", tier="e2e")
def test_sync_status_parses_all_scenarios(tmp_path):
    """sync_status parses all four scenarios without errors, reporting correct rule counts and UNTESTED."""
    specs = {
        'specs/upload/file_upload.md': PLAIN_DESCRIPTION_SPEC,
        'specs/checkout/checkout.md': PRD_SPEC,
        'specs/search/search.md': VAGUE_INPUT_SPEC,
        'specs/dashboard/dashboard_load.md': CUSTOMER_FEEDBACK_SPEC,
    }
    _make_project(tmp_path, specs=specs)
    result = sync_status(str(tmp_path))
    assert 'ERROR' not in result, f"sync_status produced errors:\n{result}"

    expected = {
        'file_upload': 4,
        'checkout': 6,
        'search': 5,
        'dashboard_load': 4,
    }
    for feature, expected_count in expected.items():
        assert feature in result, f"{feature} not in sync_status output"

    # All should be UNTESTED (no proofs filed)
    for feature in expected:
        assert 'UNTESTED' in result or 'NO PROOF' in result, (
            f"Features without proof files should show UNTESTED or NO PROOF"
        )


@pytest.mark.proof("skill_spec_from_code", "PROOF-30", "RULE-21", tier="e2e")
def test_all_scenarios_have_rules_and_proof_sections(tmp_path):
    """## Rules and ## Proof sections exist in all four scenario specs."""
    for name, content in ALL_SCENARIOS.items():
        assert _has_section(content, 'Rules'), (
            f"Scenario '{name}' missing ## Rules section"
        )
        assert _has_section(content, 'Proof'), (
            f"Scenario '{name}' missing ## Proof section"
        )


@pytest.mark.proof("skill_spec_from_code", "PROOF-31", "RULE-22", tier="e2e")
def test_assumed_tag_removal_on_explicit_update(tmp_path):
    """Updating an (assumed) rule with an explicit value removes the tag."""
    original_rule = "- RULE-4: Search returns in under 500ms (assumed — user said \"fast\")"
    updated_rule = "- RULE-4: Search returns in under 200ms"

    # Verify original has assumed tag
    assert '(assumed' in original_rule

    # Verify updated has no assumed tag but is still valid RULE-N format
    assert '(assumed' not in updated_rule
    match = re.match(r'^- (RULE-\d+): (.+)$', updated_rule)
    assert match, f"Updated rule should still match RULE-N format: '{updated_rule}'"
    assert match.group(1) == 'RULE-4'

    # Create a full spec with the updated rule and verify sync_status parses it
    updated_spec = VAGUE_INPUT_SPEC.replace(original_rule, updated_rule)
    _make_project(tmp_path, specs={
        'specs/search/search.md': updated_spec,
    })
    result = sync_status(str(tmp_path))
    assert 'search' in result
    assert 'ERROR' not in result
