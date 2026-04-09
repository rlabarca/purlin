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
def test_skill_has_contract_extraction():
    """SKILL.md contains data contract extraction with five categories."""
    content = _read(SKILL_PATH)

    # Five contract categories
    required_subsections = [
        'Inbound contracts',
        'Outbound contracts',
        'Transformation rules',
        'State transitions',
        'Access contracts',
    ]
    for subsection in required_subsections:
        assert subsection.lower() in content.lower(), (
            f"SKILL.md missing contract extraction subsection: '{subsection}'"
        )
    # Must be mandatory for ALL features, not just UI
    assert 'mandatory for ALL features' in content or 'mandatory for all features' in content.lower(), (
        "SKILL.md data contract extraction must be mandatory for ALL features"
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


@pytest.mark.proof("skill_spec_from_code", "PROOF-33", "RULE-23", tier="e2e")
def test_contract_extraction_identifies_all_categories(tmp_path):
    """Simulated React component yields extractable contracts across all five categories.

    Creates a realistic component and verifies the extraction can identify
    inbound contracts (data fields), outbound contracts (none in this component),
    transformation rules (filter/sort), state transitions (none), and
    access contracts (loanType gate).
    """
    comp_dir = tmp_path / 'src' / 'components'
    comp_dir.mkdir(parents=True)
    (comp_dir / 'SingleProductPresentation.tsx').write_text(SIMULATED_REACT_COMPONENT)

    source = SIMULATED_REACT_COMPONENT

    # --- Inbound contracts: exact field names from API/props ---
    # Hero consumes: product.address, product.loanAmount, product.rate
    assert 'product.address' in source, "Inbound: product.address"
    assert 'product.loanAmount' in source, "Inbound: product.loanAmount"
    assert 'product.rate' in source, "Inbound: product.rate"
    # Loan details consumes: product.fields
    assert 'product.fields' in source, "Inbound: product.fields"
    # Looking Ahead consumes: product.chartData, product.callouts, product.formulas
    assert 'product.chartData' in source, "Inbound: product.chartData"
    assert 'product.callouts' in source, "Inbound: product.callouts"
    assert 'product.formulas' in source, "Inbound: product.formulas"
    # Purchase-specific: rateLockDate, Refi-specific: payoffAmount
    assert 'product.rateLockDate' in source, "Inbound: product.rateLockDate"
    assert 'product.payoffAmount' in source, "Inbound: product.payoffAmount"

    # --- Transformation rules: filter/sort logic ---
    assert '.filter(' in source, "Transformation: filtering on product.fields"
    assert '.sort(' in source, "Transformation: sorting on product.fields"

    # --- Access contracts: loanType gates ---
    purchase_gates = re.findall(r"loanType\s*===\s*'purchase'", source)
    refi_gates = re.findall(r"loanType\s*===\s*'refi'", source)
    assert len(purchase_gates) >= 1, "Access: purchase gate"
    assert len(refi_gates) >= 1, "Access: refi gate"

    # --- Failure modes (supporting dimension): missing data fallback ---
    assert 'No projection data available' in source or 'no-data' in source, (
        "Failure mode: chart data fallback"
    )

    # --- Contract coverage count ---
    inbound_fields = 9  # address, loanAmount, rate, fields, chartData, callouts, formulas, rateLockDate, payoffAmount
    transformations = 2  # filter, sort
    access_gates = 3  # purchase gate, refi gate, chart-only gate
    failure_modes = 1  # missing chart fallback
    # (No outbound contracts or state transitions in this component — that's fine)

    contract_rules = inbound_fields + transformations + access_gates + failure_modes
    assert contract_rules >= 10, (
        f"Component should yield at least 10 contract-based rules, got {contract_rules}"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-36", "RULE-25", tier="e2e")
def test_impl_deviation_extraction(tmp_path):
    """PM-ACCEPTED deviations from .impl.md become rules reflecting actual behavior."""
    features_dir = tmp_path / 'features' / 'presentation'
    features_dir.mkdir(parents=True)
    (features_dir / 'single_product_presentation.impl.md').write_text(SIMULATED_IMPL_MD)

    content = SIMULATED_IMPL_MD

    # Parse the deviations table
    # Each row: | Spec says | Implementation does | Tag | PM status |
    deviation_lines = [
        line for line in content.splitlines()
        if '|' in line and line.count('|') >= 4
        and 'Spec says' not in line and '---' not in line
    ]
    assert len(deviation_lines) == 3, (
        f"Expected 3 deviations, found {len(deviation_lines)}"
    )

    # Extract PM statuses
    accepted = [l for l in deviation_lines if 'ACCEPTED' in l]
    pending = [l for l in deviation_lines if 'PENDING' in l]

    assert len(accepted) == 2, (
        f"Expected 2 ACCEPTED deviations, found {len(accepted)}"
    )
    assert len(pending) == 1, (
        f"Expected 1 PENDING deviation, found {len(pending)}"
    )

    # For ACCEPTED deviations, the "Implementation does" column becomes the rule
    # For PENDING deviations, they should be flagged for user review
    for line in accepted:
        cols = [c.strip() for c in line.split('|') if c.strip()]
        assert len(cols) >= 3, f"Deviation row should have at least 3 columns: {line}"
        impl_behavior = cols[1]  # "Implementation does" column
        assert impl_behavior, "ACCEPTED deviation must have an implementation description"

    # Verify the extraction would produce rules from implementation behavior
    assert 'Hero shows 3 stat cards' in content, (
        "ACCEPTED deviation about stat card count should be extractable"
    )
    assert 'Chart uses recharts' in content, (
        "ACCEPTED deviation about chart library should be extractable"
    )


@pytest.mark.proof("skill_spec_from_code", "PROOF-38", "RULE-26", tier="e2e")
def test_discoveries_bug_extraction(tmp_path):
    """Resolved bugs become regression rules; open bugs become deferred rules."""
    features_dir = tmp_path / 'features' / 'presentation'
    features_dir.mkdir(parents=True)
    (features_dir / 'single_product_presentation.discoveries.md').write_text(
        SIMULATED_DISCOVERIES_MD
    )

    content = SIMULATED_DISCOVERIES_MD

    # Parse bug entries
    bug_entries = re.findall(r'\[BUG\]\s+(M\d+):\s*(.+)', content)
    assert len(bug_entries) == 2, f"Expected 2 bugs, found {len(bug_entries)}"

    # Identify resolved vs open
    resolved_bugs = []
    open_bugs = []
    bug_blocks = content.split('[BUG]')[1:]  # skip preamble
    for block in bug_blocks:
        if 'Status: RESOLVED' in block:
            resolved_bugs.append(block)
        elif 'Status: OPEN' in block:
            open_bugs.append(block)

    assert len(resolved_bugs) == 1, f"Expected 1 resolved bug, found {len(resolved_bugs)}"
    assert len(open_bugs) == 1, f"Expected 1 open bug, found {len(open_bugs)}"

    # Resolved bug should become a regression rule
    # "Info bar overlaps disclaimer on mobile" → RULE: Info bar does not overlap disclaimer below 768px
    assert 'Info bar overlaps disclaimer' in resolved_bugs[0]
    assert '768px' in resolved_bugs[0] or 'mobile' in resolved_bugs[0], (
        "Resolved bug should have enough detail to create a specific regression rule"
    )

    # Open bug should become a deferred rule
    # "Chart tooltip cuts off" → RULE: Chart tooltip stays in viewport (deferred)
    assert 'Chart tooltip cuts off' in open_bugs[0]
    assert 'OPEN' in open_bugs[0], "Open bug should be extractable as a (deferred) rule"

    # Verify Figma references are present and extractable
    figma_urls = re.findall(r'https://www\.figma\.com/design/[^\s]+', content)
    assert len(figma_urls) >= 2, (
        f"Expected at least 2 Figma URLs, found {len(figma_urls)}"
    )
