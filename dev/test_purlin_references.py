"""Tests for purlin_references — 11 rules.

Grep-based structural verification of the 8 reference documents
that define Purlin's formats, conventions, and quality standards.
"""

import json
import os
import re
import subprocess

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
REFS = os.path.join(PROJECT_ROOT, 'references')
FORMATS = os.path.join(REFS, 'formats')


def _read(path):
    with open(path) as f:
        return f.read()


def _markdown_under(*roots):
    """Every .md file under the given directories, sorted."""
    found = []
    for root in roots:
        for dirpath, _dirnames, filenames in os.walk(root):
            found.extend(os.path.join(dirpath, fn)
                         for fn in sorted(filenames) if fn.endswith('.md'))
    return sorted(found)


def _yaml_blocks(text):
    """The bodies of every fenced ```yaml block, in order."""
    return [m.group(1) for m in re.finditer(r'```ya?ml\n(.*?)```', text, re.S)]


def _tables(text):
    """[(header cells, [row cells])] for every pipe table in a markdown file."""
    tables = []
    header = None
    rows = None
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            if header is None:
                header, rows = cells, []
            elif set(''.join(cells)) <= set('-: '):
                continue
            else:
                rows.append(cells)
        else:
            if header is not None and rows:
                tables.append((header, rows))
            header, rows = None, None
    if header is not None and rows:
        tables.append((header, rows))
    return tables


class TestPurlinReferences:

    @pytest.mark.proof("purlin_references", "PROOF-1", "RULE-1")
    def test_spec_format_required_sections(self):
        content = _read(os.path.join(FORMATS, 'spec_format.md'))
        # Scope to the Required Sections block
        m = re.search(r'## Required Sections(.*?)(?=^## |\Z)', content,
                       re.MULTILINE | re.DOTALL)
        assert m, "Missing '## Required Sections' heading in spec_format.md"
        section = m.group(1)
        assert '## Rules' in section
        assert '## Proof' in section
        # Description is now a metadata field, not a required section
        assert '> Description:' in content
        assert re.search(r'RULE-\d+', content)

    @pytest.mark.proof("purlin_references", "PROOF-2", "RULE-2")
    def test_proofs_format_fields_and_merge(self):
        content = _read(os.path.join(FORMATS, 'proofs_format.md'))
        for field in ('feature', 'id', 'rule', 'test_file', 'test_name', 'status', 'tier'):
            assert field in content, f"Missing field: {field}"
        assert re.search(r'[Ww]rite.[Ss]coped [Oo]verwrite', content), \
            "proofs_format.md must name the merge behaviour"
        assert '(feature, tier, test_file)' in content, \
            "proofs_format.md must state the merge key, not just the pattern's name"

    @pytest.mark.proof("purlin_references", "PROOF-3", "RULE-3")
    def test_proofs_format_three_frameworks(self):
        content = _read(os.path.join(FORMATS, 'proofs_format.md'))
        for fw in ('pytest', 'Jest', 'Shell'):
            assert re.search(rf'###\s+{fw}', content, re.IGNORECASE), \
                f"Missing framework section: {fw}"

    @pytest.mark.proof("purlin_references", "PROOF-4", "RULE-4")
    def test_anchor_format_metadata(self):
        content = _read(os.path.join(FORMATS, 'anchor_format.md'))
        assert '_anchors/' in content
        assert '> Source:' in content
        assert '> Pinned:' in content
        assert re.search(r'[Ss]ync|purlin:anchor', content), \
            "Missing sync protocol documentation"

    @pytest.mark.proof("purlin_references", "PROOF-5", "RULE-5")
    def test_anchor_format_eight_type_values(self):
        content = _read(os.path.join(FORMATS, 'anchor_format.md'))
        type_values = ['design', 'api', 'security', 'brand',
                       'platform', 'schema', 'legal', 'prodbrief']
        for tv in type_values:
            assert tv in content, f"Missing type value: {tv}"

    @pytest.mark.proof("purlin_references", "PROOF-6", "RULE-6")
    def test_hard_gates_exactly_one(self):
        content = _read(os.path.join(REFS, 'hard_gates.md'))
        assert 'Proof Coverage' in content, \
            "Missing 'Proof Coverage' gate name"
        gate_headers = re.findall(r'^## Gate \d+', content, re.MULTILINE)
        assert len(gate_headers) == 1

    @pytest.mark.proof("purlin_references", "PROOF-7", "RULE-7")
    def test_commit_conventions_prefixes_and_the_verify_vocabulary(self):
        content = _read(os.path.join(REFS, 'commit_conventions.md'))
        # Extract table/list rows to avoid matching prefixes in prose
        rows = [l for l in content.splitlines()
                if l.strip().startswith('|') or l.strip().startswith('- `')]
        row_text = '\n'.join(rows)
        for prefix in ('spec', 'feat', 'fix', 'test',
                        'verify', 'anchor', 'chore', 'docs'):
            assert prefix in row_text, \
                f"Missing commit prefix '{prefix}' in table/list rows"
        assert 'chore(update):' in row_text, (
            "the `chore(update):` migration prefix has no table row")

        # The verify-commit vocabulary, stated here and copied by three other
        # files. Features and anchors are two counts, never one.
        section = content[content.index('## Verification Receipt Commit'):
                          content.index('## Manual Stamp Commit')]
        assert ('verify: [Complete:all] features=N/T anchors=A/B '
                'vhash=<combined-hash>') in section, section
        assert 'separately' in section, (
            "the section must say the two counts are never summed: " + section)
        assert re.search(r'verify: \[Complete:all\] features=\d+/\d+ '
                         r'anchors=\d+/\d+ vhash=', content), (
            "the worked example must carry both counts")

        skill = _read(os.path.join(PROJECT_ROOT, 'skills', 'verify',
                                   'SKILL.md'))
        assert 'features=N/T anchors=A/B' in skill, (
            "skills/verify/SKILL.md states a different verify-commit format "
            "from the reference that owns it")

        issuer = _read(os.path.join(PROJECT_ROOT, 'dev', 'issue_receipts.py'))
        assert "features={features_issued}/{features_total} " in issuer, (
            "the issuer's summary line must print the features count the "
            "commit message copies")
        assert "anchors={anchors_issued}/{anchors_total}" in issuer, (
            "the issuer's summary line must print the anchors count "
            "separately from the features count")

    @pytest.mark.proof("purlin_references", "PROOF-8", "RULE-8")
    def test_purlin_commands_categories_and_skills(self):
        content = _read(os.path.join(REFS, 'purlin_commands.md'))
        for category in ('Authoring', 'Building', 'Quality', 'Reporting', 'Project'):
            assert category in content, f"Missing category: {category}"
        expected_skills = {
            'purlin:spec', 'purlin:spec-from-code', 'purlin:build',
            'purlin:test', 'purlin:verify', 'purlin:audit',
            'purlin:status', 'purlin:find', 'purlin:drift',
            'purlin:init', 'purlin:anchor',
            'purlin:rename',
        }
        skills = re.findall(r'`(purlin:[\w-]+)`', content)
        found = set(skills)
        assert found == expected_skills, \
            f"Skill mismatch: missing={expected_skills - found}, extra={found - expected_skills}"

    @pytest.mark.proof("purlin_references", "PROOF-9", "RULE-9")
    def test_spec_quality_guide_coverage(self):
        content = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert 'rebuild test' in content.lower(), "Missing rebuild test guidance"
        assert 'contract boundar' in content.lower(), "Missing contract boundaries guidance"
        assert 'Coverage dimensions' in content, "Missing coverage dimensions guidance"
        assert 'FORBIDDEN' in content
        # Verify tier assignment is documented as a dedicated section/topic
        assert re.search(r'(?i)##.*tier|tier\s+assign', content), \
            "Missing tier assignment section heading or guidance"
        assert '@integration' in content, "Missing @integration tier tag documentation"
        assert '@e2e' in content, "Missing @e2e tier tag documentation"

    @pytest.mark.proof("purlin_references", "PROOF-10", "RULE-10")
    def test_quality_guide_test_failure_diagnosis(self):
        content = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert 'Code bug' in content, "Missing 'Code bug' diagnosis category"
        assert 'Test bug' in content, "Missing 'Test bug' diagnosis category"
        assert 'Spec drift' in content, "Missing 'Spec drift' diagnosis category"
        assert 'Assertion Integrity' in content, "Missing Assertion Integrity section"

    @pytest.mark.proof("purlin_references", "PROOF-12", "RULE-12")
    def test_drift_criteria_sections(self):
        content = _read(os.path.join(REFS, 'drift_criteria.md'))
        assert 'File Classification' in content, \
            "Missing 'File Classification' section"
        assert 'NO_IMPACT Patterns' in content, \
            "Missing 'NO_IMPACT Patterns' section"
        assert 'Behavioral Directory Exclusions' in content, \
            "Missing 'Behavioral Directory Exclusions' section"
        assert 'Significance Classification' in content, \
            "Missing 'Significance Classification' section"
        assert re.search(r'Behavioral Gap Drift', content), \
            "Missing 'Behavioral Gap Drift Detection' section"
        assert 'drift_flags' in content, \
            "Missing 'drift_flags' documentation"

    @pytest.mark.proof("purlin_references", "PROOF-11", "RULE-11")
    def test_quality_guide_audience_language(self):
        content = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert 'Audience-Appropriate Language' in content, \
            "Missing Audience-Appropriate Language section"
        # Verify section contains at least one artifact-to-audience mapping
        m = re.search(
            r'Audience-Appropriate Language(.*?)(?=^## |\Z)', content,
            re.MULTILINE | re.DOTALL
        )
        assert m, "Could not extract Audience-Appropriate Language section"
        section_body = m.group(1)
        # Must contain a table or mapping where an artifact and audience appear on the same line
        lines = section_body.splitlines()
        paired = [l for l in lines
                  if re.search(r'(?i)(rules?|specs?|proofs?|drift)', l)
                  and re.search(r'(?i)(engineer|PM|QA|agent|developer)', l)]
        assert len(paired) >= 3, \
            f"Expected at least 3 artifact-to-audience mapping rows, found {len(paired)}"

    @pytest.mark.proof("purlin_references", "PROOF-13", "RULE-13")
    def test_quality_guide_e2e_proof_section(self):
        content = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert 'E2E proof descriptions' in content, \
            "Missing 'E2E proof descriptions' section"
        m = re.search(
            r'E2E proof descriptions(.*?)(?=^### |^## |\Z)', content,
            re.MULTILINE | re.DOTALL
        )
        assert m, "Could not extract E2E proof descriptions section"
        section = m.group(1)
        assert 'arrange → act → observe' in section, \
            "E2E section missing arrange → act → observe flow language"
        assert re.search(r'(?i)must not name source files or internal functions', section), \
            "E2E section missing the ban on naming source files/internal functions"
        assert re.search(r'(?i)tool-agnostic', section), \
            "E2E section missing tool-agnostic requirement"
        assert re.search(r'(?i)tier/description match|inverse check', section), \
            "E2E section missing the tier/description match (inverse) check"

    @pytest.mark.proof("purlin_references", "PROOF-14", "RULE-14")
    def test_audit_criteria_e2e_tier_integrity(self):
        content = _read(os.path.join(REFS, 'audit_criteria.md'))
        assert 'E2E Proof Tier Integrity' in content, \
            "Missing 'E2E Proof Tier Integrity' section"
        m = re.search(
            r'## E2E Proof Tier Integrity(.*?)(?=^## )', content,
            re.MULTILINE | re.DOTALL
        )
        assert m, "Could not extract E2E Proof Tier Integrity section"
        section = m.group(1)
        assert re.search(r'(?i)tier mismatch', section), \
            "E2E Proof Tier Integrity missing 'tier mismatch' criterion"
        assert re.search(r'(?i)source-constant', section), \
            "E2E Proof Tier Integrity missing 'source-constant assertion' criterion"
        # Section must apply to ALL @e2e proofs, not only design anchors
        assert re.search(r'(?i)ALL proofs tagged `?@e2e`?', section), \
            "E2E Proof Tier Integrity must state it applies to ALL @e2e proofs"
        assert re.search(r'(?i)not just `?design_', section), \
            "E2E Proof Tier Integrity must state it is not limited to design anchors"

    @pytest.mark.proof("purlin_references", "PROOF-15", "RULE-15")
    def test_supported_frameworks_e2e_section(self):
        content = _read(os.path.join(REFS, 'supported_frameworks.md'))
        assert 'End-to-end (browser) proofs' in content, \
            "Missing 'End-to-end (browser) proofs' section"
        m = re.search(
            r'## End-to-end \(browser\) proofs(.*?)(?=^## )', content,
            re.MULTILINE | re.DOTALL
        )
        assert m, "Could not extract End-to-end (browser) proofs section"
        section = m.group(1)
        assert re.search(r'(?i)no dedicated e2e proof reporter', section), \
            "e2e section must state no dedicated reporter ships"
        assert re.search(r'(?i)tool-agnostic', section), \
            "e2e section must describe @e2e proofs as tool-agnostic"
        # Wiring through existing plugins: Vitest/Jest markers and shell purlin_proof
        assert re.search(r'\[proof:[^:\]]+:PROOF-\d+:RULE-\d+:e2e\]', section), \
            "e2e section must document the Vitest/Jest e2e marker wiring"
        assert 'purlin_proof' in section, \
            "e2e section must document the shell purlin_proof wiring"

    @pytest.mark.proof("purlin_references", "PROOF-16", "RULE-16")
    def test_audit_criteria_defines_both_gauges(self):
        """audit_criteria.md must define Proof Design and Proof Integrity separately,
        score each, and mark the Integrity criteria a vague description disables."""
        crit = _read(os.path.join(REFS, 'audit_criteria.md'))

        assert '## Pass D' in crit, "audit_criteria.md missing the Pass D (Proof Design) section"
        for level in ('PROVABLE', 'LOOSE', 'UNPROVABLE', 'STRUCTURAL'):
            assert level in crit, f"audit_criteria.md missing Design level {level}"
        for level in ('STRONG', 'WEAK', 'HOLLOW', 'EXCLUDED', 'MANUAL'):
            assert level in crit, f"audit_criteria.md missing Integrity level {level}"

        # Both scoring formulas, with the Integrity one kept verbatim for sync_status RULE-33
        assert '(STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL)' in crit, \
            "audit_criteria.md must keep the Integrity formula verbatim"
        assert 'PROVABLE / (PROVABLE + LOOSE + UNPROVABLE)' in crit, \
            "audit_criteria.md must state the Design formula"

        # The criteria that only fire against a specific description
        assert crit.count('[relative]') >= 5, \
            "audit_criteria.md must mark the description-relative Integrity criteria"

        guide = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert '## Test Quality Rules (Proof Integrity)' in guide, \
            "spec_quality_guide.md must name the gauge its test-quality rules belong to"
        assert guide.count('*Graded as:') >= 4, \
            "spec_quality_guide.md proof-description sections must carry Design-level labels"
        assert 'UNPROVABLE' in guide, \
            "spec_quality_guide.md must use the Design vocabulary for Level 1 descriptions"


class TestHardGatesAccuracy:
    """RULE-17 — hard_gates.md contradicted the verify skill and, read literally,
    described a state no feature could ever reach."""

    @pytest.mark.proof("purlin_references", "PROOF-17", "RULE-17")
    def test_receipt_condition_is_passing_not_verified(self):
        gates = _read(os.path.join(REFS, 'hard_gates.md'))
        assert 'PASSING' in gates, \
            "hard_gates.md must name PASSING as the receipt condition"
        assert re.search(r'(?i)VERIFIED\s+is\s+the\s+state\s+\*?after\*?\s+a\s+receipt', gates, re.S) or \
               re.search(r'(?i)requiring\s+VERIFIED', gates, re.S), \
            "hard_gates.md must explain that VERIFIED is the post-receipt state"
        assert re.search(r'(?i)(deadlock|no\s+feature\s+could\s+ever)', gates, re.S), \
            "hard_gates.md must record why requiring VERIFIED would deadlock"

        # Still exactly one gate, and both gauges are explicitly not gates.
        assert re.search(r'(?i)exactly 1 hard gate', gates), \
            "the single-gate promise must survive"
        not_gate = gates.split('What Is NOT a Gate', 1)
        assert len(not_gate) == 2, "hard_gates.md missing the 'What Is NOT a Gate' list"
        assert 'Proof Design' in not_gate[1] and 'Proof Integrity' in not_gate[1], \
            "both gauges must be listed as non-gates"


class TestRemoteVerificationReference:
    """purlin_references RULE-18/19/20."""

    RV = os.path.join(REFS, 'remote_verification.md')

    @pytest.mark.proof("purlin_references", "PROOF-18", "RULE-18")
    def test_documents_the_loop_and_a_complete_workflow_template(self):
        rv = _read(self.RV)

        assert 'purlin:test' in rv, "the reference must name the owning skill"
        assert re.search(r'(?i)read-only', rv), (
            "it must give verify's read-only contract as the reason the loop "
            "lives in purlin:test")

        for label, pattern in (('push', r'(?i)push(es)? the (current )?branch'),
                               ('dispatch', r'(?i)dispatch'),
                               ('await', r'(?i)await'),
                               ('pull', r'(?i)pull')):
            assert re.search(pattern, rv), f"the loop is missing {label}"

        assert re.search(r'bounded at \*\*3 rounds\*\*|at \*\*3 rounds\*\*|3 rounds',
                         rv), "the 3-round bound must be stated as a literal"

        # The template is what gets copied, so every load-bearing part must be
        # in the template block itself, not only in the prose around it.
        template = _yaml_blocks(rv)
        assert template, "no YAML workflow template block"
        template = template[0]

        required = [
            ('workflow name', r'name:\s*purlin-<platform-id>-proofs'),
            ('paths-ignore', r"paths-ignore:"),
            ('scoped paths-ignore entry',
             r"'\*\*/\*\.proofs-\*@<platform-id>\.json'"),
            ('workflow_dispatch', r'workflow_dispatch'),
            ('write permission', r'permissions:\s*\n\s*contents:\s*write'),
            ('PURLIN_PLATFORM in the job env',
             r'PURLIN_PLATFORM:\s*<platform-id>'),
            # Set in a step, never in the job env: `runner` is not one of the
            # contexts `jobs.<id>.env` admits, and a job env that reads it is
            # rejected at startup with no job created (RULE-29).
            ('PURLIN_PLUGIN_ROOT published from a step',
             r'run: echo "PURLIN_PLUGIN_ROOT=\$RUNNER_TEMP/purlin" '
             r'>> "\$GITHUB_ENV"'),
            ('persist-credentials', r'persist-credentials:\s*true'),
            ('pinned tooling clone',
             r'git clone --depth 1 --branch v<VERSION>'),
            ('clone target is the plugin root', r'"\$PURLIN_PLUGIN_ROOT"'),
            ('migrate preflight',
             r'"\$PURLIN_PLUGIN_ROOT/scripts/update/migrate\.py" --check'),
            ('per-framework setup block', r'(?i)per-framework setup block'),
            ('narrowed git add',
             r"git add '\*\*/\*\.proofs-\*@<platform-id>\.json'"),
            ('idempotency guard', r'git diff --cached --quiet'),
            ('skip ci', r'\[skip ci\]'),
            # One -m carrying both: git reads trailers from the last
            # paragraph only, and each -m is a paragraph of its own.
            ('both trailers in one -m',
             r'-m "[^"]*Purlin-Runner: github-actions/<runs-on>'
             r'(?:\\n|\n)\s*Purlin-Platform: <platform-id>[^"]*"'),
            ('rebase retry loop', r'git pull --rebase origin "\$GITHUB_REF_NAME"'),
            ('three attempts', r'for attempt in 1 2 3; do'),
            ('failure after the attempts', r'exit 1'),
        ]
        for label, pattern in required:
            assert re.search(pattern, template), (
                f"the workflow template is missing {label}: a copy of it "
                f"without that element does not work ({pattern!r})")

        # Every `run:` step is bash. PowerShell reads a leading `@` in a path
        # as a splat, which silently mangles every scoped proof path.
        run_steps = len(re.findall(r'^\s*run:', template, re.M))
        bash_steps = len(re.findall(r'^\s*shell:\s*bash\s*$', template, re.M))
        assert run_steps >= 5, (
            f"the template should carry the install, preflight, setup, test "
            f"and commit-back steps; found {run_steps} run: steps")
        assert bash_steps >= run_steps, (
            f"{run_steps} `run:` steps but only {bash_steps} `shell: bash`; "
            "PowerShell is the default on windows runners and parses a "
            "leading @ in a path as a splat")

        # The reason each of the new elements is load-bearing is stated.
        for phrase in ('splat', 'agnostic', 'at once'):
            assert phrase in rv, (
                f"the reference must say why the template needs {phrase!r}")


    @pytest.mark.proof("purlin_references", "PROOF-19", "RULE-19")
    def test_states_the_declaration_enforcement_split_and_the_gauge_gap(self):
        rv = _read(self.RV)

        assert 'branch protection' in rv, (
            "the enforcement must be named")
        assert re.search(r'(?i)declares? the mode', rv), (
            "the field must be described as declaring, not enforcing")
        assert re.search(r'(?i)agent can edit', rv), (
            "the reason must be given: the field is editable in the tree")

        assert re.search(r'(?i)gitignored', rv), (
            "both gauge caches must be recorded as gitignored")
        assert 'audit_cache.json' in rv and 'design_cache.json' in rv, (
            "both caches must be named")
        assert re.search(r'(?i)per-machine|do not\b.*travel|not travelling', rv), (
            "the reference must say the gauges do not travel with a branch")
        assert 'audit_llm' in rv, (
            "the Integrity recommendation must name the config that makes it "
            "possible")
        assert re.search(r'(?i)deterministic', rv), (
            "the Design recommendation rests on it being deterministic")

    @pytest.mark.proof("purlin_references", "PROOF-20", "RULE-20")
    def test_every_config_template_field_has_an_ownership_row(self):
        """A field stamped into new projects with no row here has no recorded
        owner and no recorded default, which is how `digest` went unlisted."""
        with open(os.path.join(PROJECT_ROOT, 'templates', 'config.json')) as f:
            template_keys = set(json.load(f).keys())
        assert template_keys, "templates/config.json is empty"

        drift = _read(os.path.join(REFS, 'drift_criteria.md'))
        section = drift.split('Config Field Ownership', 1)
        assert len(section) == 2, "drift_criteria.md has no ownership section"
        body = section[1].split('\n## ', 1)[0]

        listed = set(re.findall(r'^\|\s*`([^`]+)`\s*\|', body, re.M))
        assert listed, "the ownership table has no rows"

        missing = sorted(template_keys - listed)
        assert not missing, (
            f"templates/config.json stamps {missing} into every new project "
            f"with no row in drift_criteria.md's Config Field Ownership table")

        # Optional fields init never writes still need an owner and a default:
        # a skill reads them, so somebody has to say who sets them.
        optional = {'audit_llm', 'audit_llm_name', 'audit_criteria',
                    'audit_criteria_pinned', 'platforms'}
        missing_optional = sorted(optional - listed)
        assert not missing_optional, (
            f"optional config fields {missing_optional} are read by a skill but "
            f"have no row in drift_criteria.md's Config Field Ownership table")

    @pytest.mark.proof("purlin_references", "PROOF-21", "RULE-21")
    def test_receipt_format_is_the_receipt_contract(self):
        """RULE-21: the receipt contract lives in one file and states the
        version, every v2 field, what the vhash does and does not bind, and
        that a receipt issued without a run marker records no run."""
        path = os.path.join(FORMATS, 'receipt_format.md')
        assert os.path.isfile(path), \
            "references/formats/receipt_format.md is the receipt contract"
        content = _read(path)

        m = re.match(r'>\s*Format-Version:\s*(\d+)', content)
        assert m, "receipt_format.md must open with a > Format-Version: line"
        assert int(m.group(1)) >= 2, \
            f"receipt v2 needs Format-Version 2 or later, got {m.group(1)}"

        fields = ['feature', 'vhash', 'vhash_version', 'commit', 'timestamp',
                  'rules', 'rule_hashes', 'proofs', 'manual', 'evidence',
                  'test_run', 'proof_files', 'awaiting_runner']
        missing = [f for f in fields if f'`{f}`' not in content]
        assert not missing, \
            f"receipt_format.md documents no {missing} field"

        row_keys = ['file', 'tier', 'platform', 'committed_at', 'runner',
                    'executed_in_test_run']
        missing_rows = [k for k in row_keys if f'`{k}`' not in content]
        assert not missing_rows, (
            f"the proof_files row keys {missing_rows} are undocumented, so a "
            f"consumer cannot read the evidence block")

        assert 'What the vhash binds' in content, \
            "receipt_format.md must say what the vhash binds"
        assert 'It does not bind' in content, (
            "receipt_format.md must say what the vhash does NOT bind: a hash "
            "read as binding the source code is read as a signature")

        assert re.search(r'^## Version 1', content, re.M), \
            "receipt_format.md must document the version 1 shape as historical"

        null_marker = re.search(
            r'`evidence\.test_run` is null for a receipt issued without a '
            r'run marker', content)
        assert null_marker, (
            "receipt_format.md must state that evidence.test_run is null for a "
            "receipt issued without a run marker")

        # RULE-21: the `evidence` section must also say WHO writes the marker.
        # A consumer project has no `dev/run_tests.sh`; told only about the
        # sweep, it concludes no run can ever be recorded and reaches for
        # `--no-run-check`, the one flag that makes the receipt claim nothing.
        evidence = content.split('### `evidence`')[1].split('### What the vhash')[0]
        assert '.purlin/runtime/test_run.json' in evidence, \
            "the evidence section must name the run marker's path"
        assert 'proof plugins' in evidence, (
            "the evidence section must name the proof plugins as the writers "
            "of the marker in a consumer project")
        assert 'dev/run_tests.sh' in evidence, \
            "the evidence section must name this repository's writer too"
        assert 'RULE-19' in evidence, \
            "the evidence section must point at proof_common RULE-19"
        for key in ('sweep', 'runs'):
            assert f'| `{key}` |' in evidence, (
                f"`{key}` must be documented as a key of evidence.test_run")
        assert 'per run that contributed' in evidence, \
            "`runs` must be documented as one object per contributing run"


class TestCITemplatesGoThroughThePluginRoot:
    """purlin_references RULE-22/23."""

    RV = os.path.join(REFS, 'remote_verification.md')

    @pytest.mark.proof("purlin_references", "PROOF-22", "RULE-22")
    def test_no_template_invokes_a_bare_scripts_path(self):
        """A consumer checkout holds specs, proofs, receipts and `.purlin/`,
        and no Purlin `scripts/`. A template with a bare `scripts/` path runs
        nowhere but in this repository."""
        hits = 0
        clones = 0
        for path in _markdown_under(REFS, os.path.join(PROJECT_ROOT, 'docs')):
            for block in _yaml_blocks(_read(path)):
                rel = os.path.relpath(path, PROJECT_ROOT)
                # Comments explain the rule; the rule is about what runs.
                block = '\n'.join(
                    '' if line.lstrip().startswith('#') else line
                    for line in block.split('\n'))
                for m in re.finditer(r'scripts/', block):
                    before = block[max(0, m.start() - 40):m.start()]
                    assert re.search(r'\$\{?PURLIN_PLUGIN_ROOT\}?/$', before), (
                        f"{rel}: a workflow template invokes a bare "
                        f"`scripts/` path: {block[max(0, m.start() - 60):m.start() + 40]!r}")
                    hits += 1
                # Join backslash continuations so a clone split over two
                # lines is read as the one command it is.
                joined = re.sub(r'\\\n\s*', ' ', block)
                for m in re.finditer(r'git clone[^\n]*', joined):
                    line = m.group(0)
                    if 'purlin' not in line:
                        continue
                    assert '--branch v<VERSION>' in line or \
                           re.search(r'--branch v\d', line), (
                        f"{rel}: the tooling clone does not pin a tag: {line!r}")
                    clones += 1
        assert hits, (
            "no template invokes a Purlin scripts/ path at all; this proof "
            "must not pass by matching nothing")
        assert clones, (
            "no template installs the tooling; the pinned-tag half of the "
            "rule would be unchecked")

        rv = _read(self.RV)
        assert re.search(r'PURLIN_PLUGIN_ROOT[`:\s]*(to\s*)?`?\.`?', rv) and \
            re.search(r"(?i)this repos?itor(y|ies)['’]?s own workflows", rv), (
            "the reference must record this repository's own workflows as the "
            "PURLIN_PLUGIN_ROOT: . exception")

    @pytest.mark.proof("purlin_references", "PROOF-23", "RULE-23")
    def test_every_listed_framework_carries_a_runner_setup_cell(self):
        content = _read(os.path.join(REFS, 'supported_frameworks.md'))
        tables = 0
        setups = {}
        for header, rows in _tables(content):
            if 'Runner setup' not in header:
                continue
            tables += 1
            col = header.index('Runner setup')
            for cells in rows:
                name = cells[0].strip('* ').strip()
                assert col < len(cells), (
                    f"row {name!r} has no Runner setup cell at all")
                assert cells[col].strip(), (
                    f"{name} has an empty Runner setup cell; a scaffolded "
                    "workflow would install nothing for it")
                setups[name.lower()] = cells[col].strip()
        assert tables == 2, (
            f"both the built-in and the additional-plugin tables must carry "
            f"the column; found {tables}")
        assert len(setups) >= 7, (
            f"only {len(setups)} frameworks carry a runner-setup cell: "
            f"{sorted(setups)}")

        # The column covers the frameworks the plugin column names, so a
        # framework cannot pass by being dropped from the table.
        plugins = set()
        for header, rows in _tables(content):
            if 'Plugin file' not in header:
                continue
            col = header.index('Plugin file')
            for cells in rows:
                if col < len(cells) and 'scripts/proof/' in cells[col]:
                    plugins.add(cells[0].strip('* ').strip().lower())
        assert plugins <= set(setups), (
            f"frameworks with a plugin file but no runner setup: "
            f"{sorted(plugins - set(setups))}")

        assert re.search(r'(?i)runner setup.{0,200}scaffold', content, re.S), (
            "the file must name the column as what purlin:test reads when it "
            "scaffolds a runner workflow")


class TestSharedSectionsSkillsPointAt:
    """RULE-24 and RULE-25: the two sections every skill links rather than
    restates. Each proof reads the section's own content, so deleting the
    section or hollowing it out fails here rather than at the twelve call
    sites."""

    @pytest.mark.proof("purlin_references", "PROOF-24", "RULE-24")
    def test_pending_migrations_section_exists_and_names_the_directive(self):
        content = _read(os.path.join(REFS, 'purlin_commands.md'))
        m = re.search(r'(?m)^## Pending migrations\s*$', content)
        assert m, "purlin_commands.md has no '## Pending migrations' heading"
        nxt = re.search(r'(?m)^## ', content[m.end():])
        section = content[m.end():m.end() + (nxt.start() if nxt else len(content))]
        flat = ' '.join(section.split())
        assert 'purlin:init --update' in section, section
        assert 'stop before doing the skill' in flat, section
        assert re.search(r'purlin:status.*purlin:drift', section, re.S), (
            "the section must name the skills that see the advisory by "
            "construction")
        assert ('`purlin:verify` does not issue receipts while a '
                '`legacy-*` migration is pending') in flat, section
        assert 'refusal to claim' in section and 'not a gate' in section, section

    @pytest.mark.proof("purlin_references", "PROOF-25", "RULE-25")
    def test_mutation_check_section_carries_steps_examples_and_value(self):
        content = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        m = re.search(r'(?m)^## Mutation check\s*$', content)
        assert m, "spec_quality_guide.md has no '## Mutation check' heading"
        nxt = re.search(r'(?m)^## ', content[m.end():])
        section = content[m.end():m.end() + (nxt.start() if nxt else len(content))]

        steps = re.findall(r'(?m)^(\d)\. (.+)$', section)
        assert [s[0] for s in steps] == ['1', '2', '3'], steps
        assert 'Break' in steps[0][1] or 'break' in steps[0][1], steps[0]
        assert 'Run' in steps[1][1] or 'run' in steps[1][1], steps[1]
        assert 'Restore' in steps[2][1] or 'restore' in steps[2][1], steps[2]

        flat = ' '.join(section.split())
        assert 'cannot tell the correct behaviour from the broken one' in flat, \
            "the surviving-mutation clause is missing"
        examples = re.findall(r'\*\*Worked example: ', section)
        assert len(examples) == 2, f"expected 2 worked examples, found {len(examples)}"
        assert flat.count('discriminating case') >= 3, section

        value = flat[flat.index('**What it is worth.**'):]
        assert 'passes against broken code' in value, value
        assert 'twice the tokens' in value, value
        assert 'regulated' in value and 'prototypes' in value, value

        skill = _read(os.path.join(PROJECT_ROOT, 'skills', 'init', 'SKILL.md'))
        assert 'spec_quality_guide.md' in skill and 'Mutation check' in skill, \
            "the init skill must quote the value statement by reference"
        assert 'twice the tokens' not in skill, \
            "the init skill restates the value statement instead of quoting it"


class TestRepoHygiene:
    """RULE-26 and RULE-27: two facts about this repository that a reference
    document asserts in prose. Each proof reads the fact itself, so the prose
    fails the day the fact changes rather than quietly going stale."""

    @pytest.mark.proof("purlin_references", "PROOF-26", "RULE-26")
    def test_no_hook_gates_anything_and_hard_gates_says_so(self):
        with open(os.path.join(PROJECT_ROOT, 'hooks', 'hooks.json')) as f:
            hooks = json.load(f)

        registered = hooks.get('hooks') or {}
        for event in ('PreToolUse', 'PermissionRequest', 'UserPromptSubmit'):
            assert event not in registered, (
                f"hooks/hooks.json registers a {event} hook: that is the event "
                f"through which a hook can gate or steer a turn, and "
                f"references/hard_gates.md promises none does")
        entries = [h for groups in registered.values() for g in groups
                   for h in (g.get('hooks') or [])]
        assert entries, "the digest refresh hook is expected to be registered"
        for entry in entries:
            assert entry.get('async') is True, (
                f"a registered hook must run async so it can never hold a "
                f"turn: {entry}")
            command = entry.get('command', '')
            m = re.search(r'scripts/hooks/([A-Za-z0-9_.-]+)', command)
            assert m, f"a hook command must name a script under scripts/hooks/: {command!r}"
            source = _read(os.path.join(PROJECT_ROOT, 'scripts', 'hooks', m.group(1)))
            assert not re.search(r'sys\.exit\(\s*[1-9]', source), (
                f"{m.group(1)} can exit non-zero, so it can block")
            assert '"decision"' not in source and '"continue": false' not in source, (
                f"{m.group(1)} emits hook output that can steer a turn")

        gates = _read(os.path.join(REFS, 'hard_gates.md'))
        assert 'hooks/hooks.json' in gates, (
            "hard_gates.md must name the file it is making a claim about")
        assert 'no Claude Code hook gates anything' in gates.lower() or \
            'No Claude Code Hook Gates Anything' in gates, gates[-1500:]
        assert 'agents/purlin.md' in gates and 'instruction' in gates, (
            "hard_gates.md must say the NEVERs are instructions, not "
            "mechanisms")
        for layer in ('purlin:verify', 'pre-push', 'CI', 'Branch protection'):
            assert layer in gates, (
                f"hard_gates.md names no enforcement layer {layer!r}; without "
                f"the list a reader has nothing to fall back on")

    @pytest.mark.proof("purlin_references", "PROOF-27", "RULE-27")
    def test_nothing_under_purlin_cache_is_tracked(self):
        root = os.path.abspath(PROJECT_ROOT)
        tracked = subprocess.run(
            ['git', 'ls-files', '--', '.purlin/cache'],
            cwd=root, capture_output=True, text=True, check=True)
        listed = [l for l in tracked.stdout.splitlines() if l.strip()]
        assert listed == [], (
            f"tracked files under .purlin/cache: {listed}. The gauges are per "
            f"machine; a tracked cache file is a stale number that travels "
            f"into every clone")

        # A positive control: `git ls-files` really does see this repository,
        # so the empty result above is a fact and not a broken invocation.
        everything = subprocess.run(
            ['git', 'ls-files'], cwd=root,
            capture_output=True, text=True, check=True)
        assert len(everything.stdout.splitlines()) > 100, (
            "git ls-files returned almost nothing; the emptiness above proves "
            "nothing")

        ignore = _read(os.path.join(PROJECT_ROOT, '.gitignore'))
        assert '.purlin/cache/' in ignore, (
            ".gitignore must exclude the directory, so a cache file cannot be "
            "added back without -f")


MEMBERSHIP_QUESTIONS = {
    'platform': (
        'Would the same test passing on a different OS be evidence for this '
        'claim?'),
    'environment': (
        "Does the outcome depend on an external system's real answers, an "
        'account, a model, or money, so that installing a package cannot '
        'reproduce it?'),
    'prerequisite': (
        'Would any host with the tool installed produce the same evidence?'),
}

PROVIDER_SENTENCE = (
    'is transport to reach a platform and is never itself a platform')

TAXONOMY_HEADING = 'Platforms, environments and prerequisites'


def _collapse(text):
    """One space for every run of whitespace, so a wrapped sentence matches."""
    return re.sub(r'\s+', ' ', text)


def _sections(text):
    """{heading: body} for every `## ` section of a markdown file."""
    parts = re.split(r'^## ', text, flags=re.M)[1:]
    return {p.split('\n', 1)[0].strip(): p.split('\n', 1)[1] if '\n' in p
            else '' for p in parts}


def _tracked_markdown(*dirs):
    """Every git-tracked .md path under the given repository directories."""
    out = subprocess.run(
        ['git', 'ls-files', '--', *dirs],
        cwd=os.path.abspath(PROJECT_ROOT),
        capture_output=True, text=True, check=True)
    return sorted(p for p in out.stdout.splitlines() if p.endswith('.md'))


class TestPlatformTaxonomyHasOneHome:
    """RULE-28: platforms, environments and prerequisites are three things with
    three mechanisms, and the rule set that tells them apart lives in exactly
    one section. A second copy is a second answer the day one is edited."""

    RV_REL = 'references/remote_verification.md'
    RV = os.path.join(REFS, 'remote_verification.md')

    @pytest.mark.proof("purlin_references", "PROOF-28", "RULE-28")
    def test_the_rule_set_has_one_home_and_the_questions_appear_only_there(self):
        sections = _sections(_read(self.RV))
        assert TAXONOMY_HEADING in sections, (
            f"references/remote_verification.md has no `## {TAXONOMY_HEADING}` "
            f"section; its headings are {sorted(sections)}")
        body = _collapse(sections[TAXONOMY_HEADING])

        for label in ('**Platform**', '**Environment**', '**Prerequisite**'):
            assert label in body, (
                f"the section names no category {label}; all three category "
                f"names belong in the one home of the rule set")

        for category, question in MEMBERSHIP_QUESTIONS.items():
            assert f'**{question}**' in body, (
                f"the {category} membership question is missing from the "
                f"section, or is not in bold: {question!r}")

        assert PROVIDER_SENTENCE in body, (
            f"the section must carry the sentence {PROVIDER_SENTENCE!r}: a "
            f"`runner.provider` is transport, and a reader who takes github "
            f"for a platform will look for a proof that depends on GitHub")

        for platform_id in ('`windows-2022`', '`figma-mcp`', '`gemini-cli`',
                            '`claude-cli`'):
            assert platform_id in body, (
                f"the classification of the current ids omits {platform_id}")
        for tool in ('php', 'dotnet', 'node', 'gcc', 'tsc', 'sqlite3'):
            assert re.search(rf'\b{re.escape(tool)}\b', body), (
                f"the classification omits the prerequisite {tool}")

        # One home means one copy. Every other file links the section.
        tracked = _tracked_markdown('docs', 'references', 'skills')
        assert len(tracked) > 10, (
            f"git ls-files found only {tracked}; the uniqueness scan below "
            f"would pass by matching nothing")
        for category, question in MEMBERSHIP_QUESTIONS.items():
            hits = {}
            for rel in tracked:
                text = _collapse(_read(os.path.join(PROJECT_ROOT, rel)))
                count = text.count(question)
                if count:
                    hits[rel] = count
            assert hits == {self.RV_REL: 1}, (
                f"the {category} membership question must appear exactly once "
                f"in {self.RV_REL} and nowhere else under docs/, references/ "
                f"or skills/; found {hits}")

        guide = _collapse(_read(os.path.join(
            PROJECT_ROOT, 'docs', 'testing-workflow-guide.md')))
        assert 'references/remote_verification.md' in guide, (
            "docs/testing-workflow-guide.md must link the reference that owns "
            "the rule set")
        assert TAXONOMY_HEADING in guide, (
            "docs/testing-workflow-guide.md must name the section it points "
            "at, not just the file")


class TestNoJobEnvReadsTheRunnerContext:
    """purlin_references RULE-29."""

    RV = os.path.join(REFS, 'remote_verification.md')

    @staticmethod
    def _job_env_lines(block):
        """[(job id, line)] for every line inside a `jobs.<id>.env:` mapping.

        The blocks are workflow templates carrying placeholders, so they are
        read by indentation rather than through a YAML parser: `<runs-on>`
        and `${{ ... }}` are not values a strict loader accepts.
        """
        found = []
        lines = block.split('\n')
        in_jobs = False
        job = None
        job_indent = None
        env_indent = None
        for line in lines:
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            indent = len(line) - len(line.lstrip())
            if re.match(r'^jobs:\s*$', line):
                in_jobs = True
                job = None
                env_indent = None
                continue
            if not in_jobs:
                continue
            if indent == 0:
                in_jobs = False
                job = None
                env_indent = None
                continue
            m = re.match(r'^(\s+)([A-Za-z0-9_.<>-]+):\s*$', line)
            if m and (job_indent is None or len(m.group(1)) == job_indent) \
                    and m.group(2) != 'env':
                # A new job id: the first mapping key under `jobs:`.
                if job_indent is None:
                    job_indent = len(m.group(1))
                if len(m.group(1)) == job_indent:
                    job = m.group(2)
                    env_indent = None
                    continue
            if job is None:
                continue
            if env_indent is not None:
                if indent > env_indent:
                    found.append((job, line))
                    continue
                env_indent = None
            if re.match(r'^\s+env:\s*$', line) and indent == job_indent + 2:
                env_indent = indent
        return found

    @pytest.mark.proof("purlin_references", "PROOF-29", "RULE-29")
    def test_no_documented_job_env_reads_the_runner_context(self):
        """`jobs.<id>.env` is evaluated before a runner exists.

        GitHub admits only `github`, `needs`, `strategy`, `matrix`, `vars`,
        `secrets` and `inputs` there. A job env carrying `${{ runner.temp }}`
        is refused at startup: "This run likely failed because of a workflow
        file issue", no job created, no log to read.
        """
        env_blocks = 0
        for path in _markdown_under(REFS, os.path.join(PROJECT_ROOT, 'docs')):
            rel = os.path.relpath(path, PROJECT_ROOT)
            for block in _yaml_blocks(_read(path)):
                for job, line in self._job_env_lines(block):
                    env_blocks += 1
                    assert not re.search(r'\$\{\{\s*runner\.', line), (
                        f"{rel}: job `{job}` sets a job-level env entry from "
                        f"the `runner` context, which GitHub refuses before "
                        f"any job starts: {line.strip()!r}")
        assert env_blocks, (
            "no job-level `env:` entry was found under references/ or docs/; "
            "this proof must not pass by parsing nothing")

        # The template's replacement: the per-runner path is published from a
        # step, where `$RUNNER_TEMP` is an ordinary environment variable.
        rv = _read(self.RV)
        assert 'run: echo "PURLIN_PLUGIN_ROOT=$RUNNER_TEMP/purlin" ' \
               '>> "$GITHUB_ENV"' in rv, (
            "the workflow template must publish PURLIN_PLUGIN_ROOT from the "
            "`Locate Purlin tooling` step through $GITHUB_ENV")
        assert '- name: Locate Purlin tooling' in rv, (
            "the template must carry the `Locate Purlin tooling` step")
