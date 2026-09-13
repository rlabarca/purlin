"""E2E tests for spec-from-code UI component extraction and companion file migration.

Validates that:
1. UI component heuristics in SKILL.md cover visual sections, conditionals,
   responsive behavior, and theme/token usage
2. Coverage dimension check is mandatory for UI features
3. Legacy .impl.md deviations become rules
4. Legacy .discoveries.md bugs become rules (resolved) or deferred rules (open)
5. Figma references are preserved during migration
6. Quality guide uses coverage dimensions, not fixed rule counts

Run with: python3 -m pytest dev/test_e2e_ui_extraction.py -v
"""

import os
import re
import sys

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILL_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'skills', 'spec-from-code', 'SKILL.md'
)
QUALITY_GUIDE_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'references', 'spec_quality_guide.md'
)


def _read(path):
    with open(path) as f:
        return f.read()


# Phase 3 step 4 of SKILL.md is where the five contract categories live; a
# whole-file grep could pass on a label that had moved to another phase.
PHASE3_STEP4 = ('4. **Data contract extraction (mandatory for ALL features):**',
                '5. **Draft and evaluate rules (mandatory):**')
PHASE3_STEP3 = ('3. **Existing spec migration (per feature):**',
                '4. **Data contract extraction (mandatory for ALL features):**')

# The five category labels, in the a) to e) order step 4 lists them.
FIVE_CATEGORIES = [
    'Inbound contracts',
    'Outbound contracts',
    'Transformation rules',
    'State transitions',
    'Access contracts',
]


def _step(bounds, name):
    """The body of one numbered step of spec-from-code's SKILL.md."""
    content = _read(SKILL_PATH)
    start, end = bounds
    assert start in content, f"SKILL.md has no {name}: missing {start!r}"
    body = content.split(start, 1)[1]
    assert end in body, f"SKILL.md {name} is not followed by {end!r}"
    return body.split(end, 1)[0]


def _require(bounds, name, literal):
    step = _step(bounds, name)
    assert literal in step, \
        f"skills/spec-from-code/SKILL.md {name} must carry the literal {literal!r}"


def _extract_contracts(source):
    """Sort a component's contracts into the five categories step 4 names.

    Each detector is the trace step 4 orders for its category: inbound = the
    exact field names the component reads, outbound = emit/track/fetch calls,
    transformations = filters, sorts and aggregations over collections, state =
    state hooks and reducers, access = mode and permission gates.
    """
    return {
        'inbound': sorted({'product.' + m
                           for m in re.findall(r'\bproduct\.(\w+)', source)}),
        'outbound': sorted(set(re.findall(
            r'\b(track|logEvent|fetch|axios\.\w+)\s*\(', source))),
        'transformations': sorted(set(re.findall(
            r'\.(filter|sort|reduce)\(', source))),
        'state': sorted(set(re.findall(
            r'\b(useState|useReducer|setState)\s*\(', source))),
        'access': sorted({"%s === '%s'" % (name, value) for name, value
                          in re.findall(r"(\w+)\s*===\s*'([^']+)'", source)}),
    }


def _impl_rules(impl_text):
    """Apply step 3's Active Deviations selection to an `.impl.md` table.

    Returns (rules, flagged): a PM-ACCEPTED row becomes a rule carrying the
    "Implementation does" column, a PENDING or REJECTED row becomes no rule and
    is flagged for the review step instead.
    """
    rules, flagged = [], []
    for line in impl_text.splitlines():
        cols = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cols) != 4 or cols[0] == 'Spec says' or set(cols[0]) <= set('- '):
            continue
        _spec_says, impl_does, _tag, status = cols
        if status == 'ACCEPTED':
            rules.append('- RULE-%d: %s' % (len(rules) + 1, impl_does))
        else:
            flagged.append(impl_does)
    return rules, flagged


def _discovery_rules(discoveries_text):
    """Apply step 3's bug conversion to a `.discoveries.md` bug list.

    Each `[BUG]` block's `Expected:` line becomes a rule; a block whose
    `Status:` is not RESOLVED carries the `(deferred)` tag.
    """
    rules = []
    for block in discoveries_text.split('[BUG]')[1:]:
        expected = re.search(r'^- Expected: (.+)$', block, re.MULTILINE)
        status = re.search(r'^- Status: (\w+)$', block, re.MULTILINE)
        assert expected, f"bug block carries no Expected: line:\n{block}"
        assert status, f"bug block carries no Status: line:\n{block}"
        text = expected.group(1).rstrip('.')
        if status.group(1) != 'RESOLVED':
            text += ' (deferred)'
        rules.append('- RULE-%d: %s' % (len(rules) + 1, text))
    return rules


# ---------------------------------------------------------------------------
# Simulated UI component source — used in extraction heuristic tests
# ---------------------------------------------------------------------------

SIMULATED_REACT_COMPONENT = """\
import React from 'react';
import { useTheme } from '../hooks/useTheme';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { Chart } from '../components/Chart';

export function SingleProductPresentation({ product, loanType }) {
  const theme = useTheme();
  const isMobile = useMediaQuery('(max-width: 768px)');

  return (
    <div style={{ background: `var(--surface-primary)` }}>
      {/* Hero Section */}
      <section className="hero">
        <h1 style={{ color: `var(--text-heading)` }}>{product.address}</h1>
        <div className={isMobile ? 'stats-stack' : 'stats-grid'}>
          <StatCard label="Loan Amount" value={product.loanAmount} />
          <StatCard label="Rate" value={product.rate} />
          {loanType === 'purchase' && (
            <StatCard label="Rate Lock" value={product.rateLockDate} />
          )}
          {loanType === 'refi' && (
            <StatCard label="Payoff" value={product.payoffAmount} />
          )}
        </div>
      </section>

      {/* Loan Details Section */}
      <section className="loan-details">
        <h2>Loan Details</h2>
        <table>
          {product.fields
            .filter(f => !f.excluded)
            .sort((a, b) => a.order - b.order)
            .map(field => (
              <tr key={field.name}>
                <td>{field.label}</td>
                <td>{field.value}</td>
              </tr>
            ))}
        </table>
        {product.hasInfoBar && <InfoBar message={product.infoMessage} />}
        <Disclaimer text={product.disclaimer} />
      </section>

      {/* Looking Ahead Section */}
      <section className="looking-ahead">
        <h2>Looking Ahead</h2>
        {loanType === 'purchase' && product.chartData ? (
          <Chart data={product.chartData} />
        ) : (
          <p className="no-data">No projection data available</p>
        )}
        <div className={isMobile ? 'badges-stack' : 'badges-row'}>
          {product.callouts.map(c => (
            <CalloutBadge key={c.id} {...c} />
          ))}
        </div>
        <FormulaGrid formulas={product.formulas} />
      </section>
    </div>
  );
}
"""

SIMULATED_IMPL_MD = """\
# Implementation Notes — single_product_presentation

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| Hero shows 4 stat cards | Hero shows 3 stat cards (removed equity card) | DEVIATION-1 | ACCEPTED |
| Chart uses D3 library | Chart uses recharts for bundle size | DEVIATION-2 | ACCEPTED |
| Info bar shows below table | Info bar shows above disclaimer | DEVIATION-3 | PENDING |

## Architecture

- Design pattern: Container/Presenter split (file:42)
- Data flow: Product data flows through Redux selector (file:12)
"""

SIMULATED_DISCOVERIES_MD = """\
# Discoveries — single_product_presentation

## Bugs

[BUG] M12: Info bar overlaps disclaimer on mobile
- Observed: On viewports below 768px, the info bar text overflows into the disclaimer area
- Expected: Info bar and disclaimer should not overlap
- Action: Frontend fix needed
- Status: RESOLVED
- Resolution: Added margin-bottom to info-bar on mobile

[BUG] M15: Chart tooltip cuts off on right edge
- Observed: When hovering rightmost data point, tooltip extends beyond viewport
- Expected: Tooltip should reposition to stay within viewport
- Action: Chart component fix needed
- Status: OPEN

## Design References

- Hero section: https://www.figma.com/design/abc123/SPP?node-id=1234
- Loan details: https://www.figma.com/design/abc123/SPP?node-id=5678

## User Testing Observations

- Users expected rate lock date to be more prominent in purchase flow
- Accordion sections in Looking Ahead should operate independently
"""

# ---------------------------------------------------------------------------
# Tests — SKILL.md structural checks (frontmatter, usage, tier review)
# ---------------------------------------------------------------------------


@pytest.mark.proof("skill_spec_from_code", "PROOF-1", "RULE-1", tier="unit")
def test_skill_has_yaml_frontmatter():
    """SKILL.md has YAML frontmatter with name and description fields."""
    content = _read(SKILL_PATH)
    # Check for frontmatter delimiters
    assert content.startswith('---'), "SKILL.md must start with YAML frontmatter delimiter ---"
    parts = content.split('---', 2)
    assert len(parts) >= 3, "SKILL.md must have opening and closing --- delimiters"
    frontmatter = parts[1]
    assert 'name:' in frontmatter, "Frontmatter must contain 'name:' field"
    assert 'description:' in frontmatter, "Frontmatter must contain 'description:' field"


@pytest.mark.proof("skill_spec_from_code", "PROOF-2", "RULE-2", tier="unit")
def test_skill_has_usage_section():
    """SKILL.md contains a ## Usage section."""
    content = _read(SKILL_PATH)
    assert '## Usage' in content, "SKILL.md must contain '## Usage' section"


@pytest.mark.proof("skill_spec_from_code", "PROOF-3", "RULE-3", tier="unit")
def test_skill_name_matches_directory():
    """The name field in frontmatter equals 'spec-from-code'."""
    content = _read(SKILL_PATH)
    parts = content.split('---', 2)
    frontmatter = parts[1]
    match = re.search(r'^name:\s*(.+)$', frontmatter, re.MULTILINE)
    assert match, "Could not find 'name:' in frontmatter"
    assert match.group(1).strip() == 'spec-from-code', (
        f"Expected name 'spec-from-code', got '{match.group(1).strip()}'"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-4", "RULE-4", tier="unit")
def test_skill_has_tier_review_instructions():
    """SKILL.md contains tier review instructions with tier tag references."""
    content = _read(SKILL_PATH)
    assert 'Tier review pass' in content or 'tier review' in content.lower(), (
        "SKILL.md must contain tier review instructions"
    )
    assert '@integration' in content, "SKILL.md must reference @integration tier tag"
    assert '@e2e' in content, "SKILL.md must reference @e2e tier tag"
    assert '@manual' in content, "SKILL.md must reference @manual tier tag"


@pytest.mark.proof("skill_spec_from_code", "PROOF-9", "RULE-9", tier="unit")
def test_skill_has_migration_cleanup():
    """SKILL.md offers features/ cleanup and overwrites specs/ in place."""
    content = _read(SKILL_PATH)
    # Phase 4 offers to remove features/
    assert 'Remove old features/' in content or 'remove it manually' in content, (
        "SKILL.md must offer to remove features/ directory in Phase 4"
    )
    # Non-compliant specs are overwritten in place
    assert 'overwritten in place' in content, (
        "SKILL.md must state non-compliant specs are overwritten in place"
    )


# ---------------------------------------------------------------------------
# Tests — SKILL.md structural checks (UI extraction heuristics)
# ---------------------------------------------------------------------------


@pytest.mark.proof("skill_spec_from_code", "PROOF-32", "RULE-23", tier="unit")
def test_skill_names_the_categories_and_the_guide_carries_them():
    """Step 4 names the five categories and points at the guide; the guide
    carries the procedure.

    The two halves are asserted separately: a whole-file grep of SKILL.md
    survived the guide section being deleted, and the skill keeping the labels
    while the pointer rots is the other half of the same defect.
    """
    # The step's own heading carries the "mandatory" wording, so read it back
    # with the body rather than asserting on the body alone.
    step4 = PHASE3_STEP4[0] + _step(PHASE3_STEP4, 'Phase 3 step 4')
    for subsection in FIVE_CATEGORIES:
        assert subsection in step4, (
            f"SKILL.md step 4 missing contract category label: '{subsection}'"
        )
    # Must be mandatory for ALL features, not just UI
    assert 'mandatory for ALL features' in step4, (
        "SKILL.md data contract extraction must be mandatory for ALL features"
    )
    assert 'spec_quality_guide.md' in step4 and 'Data contract extraction' in step4, (
        "SKILL.md step 4 must point at spec_quality_guide.md "
        '("Data contract extraction") for the per-category procedure'
    )

    guide = _read(QUALITY_GUIDE_PATH)
    assert '### Data contract extraction' in guide, (
        "spec_quality_guide.md must carry the '### Data contract extraction' "
        "section the skill points at"
    )
    section = guide.split('### Data contract extraction', 1)[1].split('\n## ', 1)[0]
    for subsection in FIVE_CATEGORIES:
        assert subsection in section, (
            f"the guide's data contract section is missing '{subsection}'"
        )
    # The detail the skill no longer holds: it has to be here or nowhere.
    for literal in ('os.environ[', 'project_environment',
                    'Schema anchor missing field-level rules',
                    'do not stop at\nthe event name'):
        assert literal in section, (
            f"the guide's data contract section must carry {literal!r}, which "
            "left SKILL.md when the categories moved here"
        )


@pytest.mark.proof("skill_spec_from_code", "PROOF-34", "RULE-24", tier="unit")
def test_skill_has_draft_evaluate_and_contract_filter():
    """SKILL.md contains draft-and-evaluate step and contract coverage filter."""
    content = _read(SKILL_PATH)

    # Draft-and-evaluate step with three tests
    assert 'Draft and evaluate' in content or 'draft and evaluate' in content.lower(), (
        "SKILL.md missing 'Draft and evaluate' step"
    )
    for criterion in ['Rebuild test', 'Behavior test', 'Overlap test']:
        assert criterion in content, (
            f"Draft-and-evaluate step missing '{criterion}'"
        )

    # Rebuild-risk filter verifies contract coverage
    assert 'contract coverage' in content.lower() or 'Verify contract coverage' in content, (
        "Rebuild-risk filter must verify contract coverage"
    )
    # Filter references all five categories
    for category in ['Inbound contracts', 'Outbound contracts', 'Transformation rules',
                     'State transitions', 'Access contracts']:
        assert category.lower() in content.lower(), (
            f"Rebuild-risk filter missing contract category: '{category}'"
        )


@pytest.mark.proof("skill_spec_from_code", "PROOF-35", "RULE-25", tier="unit")
def test_skill_reads_impl_deviations():
    """SKILL.md instructs reading .impl.md and converting PM-accepted deviations to rules."""
    content = _read(SKILL_PATH)

    assert '.impl.md' in content, "SKILL.md must reference .impl.md companion files"
    assert 'Active Deviations' in content, (
        "SKILL.md must reference Active Deviations table from .impl.md"
    )
    assert 'PM-ACCEPTED' in content or 'PM-accepted' in content.lower(), (
        "SKILL.md must describe how PM-ACCEPTED deviations become rules"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-37", "RULE-26", tier="unit")
def test_skill_reads_discoveries_bugs():
    """SKILL.md instructs reading .discoveries.md and converting bugs to rules."""
    content = _read(SKILL_PATH)

    assert '.discoveries.md' in content, (
        "SKILL.md must reference .discoveries.md companion files"
    )
    assert 'Resolved bugs' in content or 'resolved bugs' in content.lower(), (
        "SKILL.md must describe how resolved bugs become regression rules"
    )
    assert '(deferred)' in content, (
        "SKILL.md must describe how open bugs become (deferred) rules"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-39", "RULE-27", tier="unit")
def test_skill_preserves_figma_references():
    """SKILL.md instructs preserving Figma references during migration."""
    content = _read(SKILL_PATH)

    # Check the .discoveries.md section specifically mentions Visual-Reference and Figma
    assert 'Visual-Reference' in content, (
        "SKILL.md must reference Visual-Reference metadata"
    )
    # Check that Figma references are mentioned in the discoveries migration context
    assert 'Figma' in content, (
        "SKILL.md must mention Figma reference preservation"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-40", "RULE-28", tier="unit")
def test_quality_guide_uses_coverage_dimensions():
    """Quality guide references coverage dimensions, not a fixed rule count."""
    content = _read(QUALITY_GUIDE_PATH)

    # Coverage dimensions section must exist
    assert '### Coverage dimensions' in content or '## Coverage dimensions' in content, (
        "Quality guide must have a 'Coverage dimensions' section"
    )

    # The old fixed target must be gone
    assert '5–10 rules per feature' not in content, (
        "Quality guide still contains the old '5–10 rules per feature' guidance"
    )
    assert '5-10 rules per feature' not in content, (
        "Quality guide still contains the old '5-10 rules per feature' guidance"
    )


# ---------------------------------------------------------------------------
# Tests — Simulated extraction (Level 3)
# ---------------------------------------------------------------------------


@pytest.mark.proof("skill_spec_from_code", "PROOF-33", "RULE-23", tier="unit")
def test_contract_extraction_sorts_the_component_into_five_categories(tmp_path):
    """The component's contracts sort into step 4's five categories.

    The categories are read out of SKILL.md step 4, the contracts out of a
    component written to disk and read back, so the assertion is on what the
    detection returns rather than on the fixture string.
    """
    comp_dir = tmp_path / 'src' / 'components'
    comp_dir.mkdir(parents=True)
    component = comp_dir / 'SingleProductPresentation.tsx'
    component.write_text(SIMULATED_REACT_COMPONENT)
    source = component.read_text()

    # Step 4 still names all five categories, as subsections a) to e).
    step4 = _step(PHASE3_STEP4, 'Phase 3 step 4')
    labels = re.findall('^\\s*\\*\\*([a-e])\\) (.+?)(?: \u2014|:)\\*\\*',
                        step4, re.MULTILINE)
    assert [letter for letter, _text in labels] == ['a', 'b', 'c', 'd', 'e'], (
        f"Phase 3 step 4 must carry subsections a) to e), got {labels}"
    )
    for (letter, text), expected in zip(labels, FIVE_CATEGORIES):
        assert text.startswith(expected), (
            f"Phase 3 step 4 subsection {letter}) should be '{expected}', got {text!r}"
        )

    found = _extract_contracts(source)

    # Inbound: every field the component reads, by exact name.
    assert found['inbound'] == [
        'product.address',
        'product.callouts',
        'product.chartData',
        'product.disclaimer',
        'product.fields',
        'product.formulas',
        'product.hasInfoBar',
        'product.infoMessage',
        'product.loanAmount',
        'product.payoffAmount',
        'product.rate',
        'product.rateLockDate',
    ], f"Inbound contracts should be the 12 product fields, got {found['inbound']}"

    # Transformations: the filter and sort applied to product.fields.
    assert found['transformations'] == ['filter', 'sort'], (
        f"Transformations should be filter and sort, got {found['transformations']}"
    )

    # Access: the two loanType mode gates.
    assert found['access'] == ["loanType === 'purchase'", "loanType === 'refi'"], (
        f"Access contracts should be the two loanType gates, got {found['access']}"
    )

    # This component emits nothing and holds no state: two of the five
    # categories come back empty, which is what step 4 allows for them.
    assert found['outbound'] == [], (
        f"The component emits nothing, got outbound {found['outbound']}"
    )
    assert found['state'] == [], (
        f"The component holds no state, got state {found['state']}"
    )

    # The same component with both mode gates deleted: the access category is
    # earned by the gates in the code, not by the category list in SKILL.md.
    gateless = (source
                .replace("loanType === 'purchase' && ", '')
                .replace("loanType === 'refi' && ", ''))
    assert gateless != source, "the gateless fixture did not apply"
    assert _extract_contracts(gateless)['access'] == [], (
        "With both loanType gates deleted there is no access contract, got "
        f"{_extract_contracts(gateless)['access']}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-36", "RULE-25", tier="unit")
def test_impl_accepted_deviations_become_rules(tmp_path):
    """PM-ACCEPTED deviations become rules; a PENDING row is flagged instead."""
    features_dir = tmp_path / 'features' / 'presentation'
    features_dir.mkdir(parents=True)
    impl = features_dir / 'single_product_presentation.impl.md'
    impl.write_text(SIMULATED_IMPL_MD)
    content = impl.read_text()

    # The instruction the conversion follows.
    _require(PHASE3_STEP3, 'Phase 3 step 3',
             "If the deviation was PM-ACCEPTED, use the implementation's "
             "behavior as the rule.")
    _require(PHASE3_STEP3, 'Phase 3 step 3',
             'If PENDING or REJECTED, flag it for the user in the review step '
             'as a discrepancy.')

    rules, flagged = _impl_rules(content)
    assert rules == [
        '- RULE-1: Hero shows 3 stat cards (removed equity card)',
        '- RULE-2: Chart uses recharts for bundle size',
    ], f"The 2 ACCEPTED rows should build these rules, got {rules}"
    assert flagged == ['Info bar shows above disclaimer'], (
        f"The PENDING row should be flagged, not turned into a rule, got {flagged}"
    )

    # PM status decides, not row order: accept nothing from the first row and
    # only the second ACCEPTED row survives as a rule.
    demoted = content.replace('| DEVIATION-1 | ACCEPTED |',
                              '| DEVIATION-1 | PENDING |')
    assert demoted != content, "the demoted-deviation fixture did not apply"
    demoted_rules, demoted_flagged = _impl_rules(demoted)
    assert demoted_rules == ['- RULE-1: Chart uses recharts for bundle size'], (
        f"With DEVIATION-1 demoted only 1 rule should be built, got {demoted_rules}"
    )
    assert len(demoted_flagged) == 2, (
        f"With DEVIATION-1 demoted 2 rows should be flagged, got {demoted_flagged}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-38", "RULE-26", tier="unit")
def test_discoveries_bugs_become_regression_and_deferred_rules(tmp_path):
    """A resolved bug becomes a regression rule; an open bug carries (deferred)."""
    features_dir = tmp_path / 'features' / 'presentation'
    features_dir.mkdir(parents=True)
    discoveries = features_dir / 'single_product_presentation.discoveries.md'
    discoveries.write_text(SIMULATED_DISCOVERIES_MD)
    content = discoveries.read_text()

    # The instruction the conversion follows.
    _require(PHASE3_STEP3, 'Phase 3 step 3',
             '(`[BUG]` entries with status RESOLVED) \u2014 each becomes a RULE-N '
             'protecting against regression')
    _require(PHASE3_STEP3, 'Phase 3 step 3',
             '**Open bugs** \u2014 each becomes a RULE-N tagged `(deferred)`')

    rules = _discovery_rules(content)
    assert rules == [
        '- RULE-1: Info bar and disclaimer should not overlap',
        '- RULE-2: Tooltip should reposition to stay within viewport (deferred)',
    ], f"The resolved and open bugs should build these rules, got {rules}"

    # The Status line decides the tag, not the entry order: resolve M15 too and
    # no rule carries (deferred).
    resolved = content.replace('- Status: OPEN', '- Status: RESOLVED')
    assert resolved != content, "the all-resolved fixture did not apply"
    resolved_rules = _discovery_rules(resolved)
    assert resolved_rules == [
        '- RULE-1: Info bar and disclaimer should not overlap',
        '- RULE-2: Tooltip should reposition to stay within viewport',
    ], f"With M15 resolved no rule should carry (deferred), got {resolved_rules}"
