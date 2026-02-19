#!/usr/bin/env python3
"""Critic Quality Gate Tool -- Main Engine.

Performs dual-gate validation (Spec Gate + Implementation Gate) on feature
files. Produces per-feature critic.json and an aggregate CRITIC_REPORT.md.

Usage:
    python3 tools/critic/critic.py                       # All features
    python3 tools/critic/critic.py features/some.md      # Single feature
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Path setup -- resolve project root and config
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))

# Config climbing: try ../../.agentic_devops then ../../../.agentic_devops
CONFIG = {}
for depth in ('../../', '../../../'):
    cfg_path = os.path.abspath(
        os.path.join(SCRIPT_DIR, depth, '.agentic_devops/config.json')
    )
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r') as f:
            CONFIG = json.load(f)
        PROJECT_ROOT = os.path.abspath(os.path.join(cfg_path, '../../'))
        break

TOOLS_ROOT = CONFIG.get('tools_root', 'tools')
FEATURES_DIR = os.path.join(PROJECT_ROOT, 'features')
TESTS_DIR = os.path.join(PROJECT_ROOT, 'tests')
LLM_ENABLED = CONFIG.get('critic_llm_enabled', False)
LLM_MODEL = CONFIG.get('critic_llm_model', 'claude-sonnet-4-20250514')

# ---------------------------------------------------------------------------
# Import sibling modules
# ---------------------------------------------------------------------------
sys.path.insert(0, SCRIPT_DIR)
from traceability import (  # noqa: E402
    run_traceability,
    extract_keywords,
    discover_test_files,
    extract_test_functions,
)
from policy_check import (  # noqa: E402
    run_policy_check,
    get_feature_prerequisites,
)

# Stub for logic_drift (Phase 3 drop-in)
try:
    from logic_drift import run_logic_drift  # noqa: E402
except ImportError:
    run_logic_drift = None


# ===================================================================
# Feature file parsing helpers
# ===================================================================

def read_feature_file(filepath):
    """Read and return feature file content."""
    with open(filepath, 'r') as f:
        return f.read()


def parse_sections(content):
    """Parse markdown sections by heading.

    Returns dict mapping heading text (lowercase) to the section body.
    """
    sections = {}
    current_heading = None
    current_lines = []

    for line in content.split('\n'):
        heading_match = re.match(r'^(#{1,4})\s+(.+)', line)
        if heading_match:
            if current_heading is not None:
                sections[current_heading] = '\n'.join(current_lines)
            current_heading = heading_match.group(2).strip().lower()
            current_lines = []
        else:
            current_lines.append(line)

    if current_heading is not None:
        sections[current_heading] = '\n'.join(current_lines)

    return sections


def parse_scenarios(content):
    """Extract scenarios from the feature file.

    Returns list of dicts: [{"title": str, "is_manual": bool, "body": str}]
    """
    scenarios = []
    in_manual_section = False

    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]

        # Track manual vs automated section
        if re.match(r'^###\s+Manual\s+Scenarios', line, re.IGNORECASE):
            in_manual_section = True
        elif re.match(r'^###\s+Automated\s+Scenarios', line, re.IGNORECASE):
            in_manual_section = False

        # Match scenario headings (#### Scenario: Title)
        scenario_match = re.match(r'^####\s+Scenario:\s*(.+)', line)
        if scenario_match:
            title = scenario_match.group(1).strip()
            body_lines = []
            i += 1
            while i < len(lines):
                if re.match(r'^#{1,4}\s', lines[i]):
                    break
                body_lines.append(lines[i])
                i += 1
            scenarios.append({
                'title': title,
                'is_manual': in_manual_section,
                'body': '\n'.join(body_lines).strip(),
            })
            continue

        i += 1

    return scenarios


def get_implementation_notes(content):
    """Extract the Implementation Notes section text."""
    match = re.search(
        r'^##\s+\d*\.?\s*Implementation\s+Notes\s*$(.*?)(?=^##\s|\Z)',
        content, re.MULTILINE | re.DOTALL
    )
    if match:
        return match.group(1).strip()
    return ''


def get_user_testing_section(content):
    """Extract the User Testing Discoveries section text."""
    match = re.search(
        r'^##\s+User\s+Testing\s+Discoveries\s*$(.*?)(?=^##\s|\Z)',
        content, re.MULTILINE | re.DOTALL
    )
    if match:
        return match.group(1).strip()
    return ''


def is_policy_file(filename):
    """Check if a filename is an architectural policy file."""
    return os.path.basename(filename).startswith('arch_')


def get_feature_stem(filepath):
    """Get the feature stem from a filepath (filename without .md)."""
    return os.path.splitext(os.path.basename(filepath))[0]


# ===================================================================
# Spec Gate checks (Section 2.1)
# ===================================================================

def check_section_completeness(content, sections):
    """Check that required sections exist."""
    has_overview = any('overview' in k for k in sections)
    has_requirements = any('requirements' in k for k in sections)
    has_scenarios = any('scenarios' in k for k in sections)

    impl_notes = get_implementation_notes(content)
    has_impl_notes = bool(impl_notes.strip())

    if has_overview and has_requirements and has_scenarios:
        if not has_impl_notes:
            return {
                'status': 'WARN',
                'detail': 'All required sections present; Implementation Notes empty.',
            }
        return {
            'status': 'PASS',
            'detail': 'All required sections present.',
        }

    missing = []
    if not has_overview:
        missing.append('Overview')
    if not has_requirements:
        missing.append('Requirements')
    if not has_scenarios:
        missing.append('Scenarios')

    return {
        'status': 'FAIL',
        'detail': f'Missing sections: {", ".join(missing)}.',
    }


def check_scenario_classification(scenarios):
    """Check that both Automated and Manual subsections have scenarios."""
    has_automated = any(not s['is_manual'] for s in scenarios)
    has_manual = any(s['is_manual'] for s in scenarios)

    if not scenarios:
        return {'status': 'FAIL', 'detail': 'No scenarios at all.'}

    if has_automated and has_manual:
        return {'status': 'PASS', 'detail': 'Both Automated and Manual subsections present.'}

    if has_automated or has_manual:
        which = 'Automated' if has_automated else 'Manual'
        return {'status': 'WARN', 'detail': f'Only {which} subsection present.'}

    return {'status': 'FAIL', 'detail': 'No scenarios at all.'}


def check_policy_anchoring(content, filename):
    """Check that the feature has a Prerequisite link to arch_*.md."""
    if is_policy_file(filename):
        return {
            'status': 'PASS',
            'detail': 'Policy file is exempt from prerequisite requirement.',
        }

    prereqs = get_feature_prerequisites(content)
    if prereqs:
        return {
            'status': 'PASS',
            'detail': f'Anchored to: {", ".join(prereqs)}.',
        }

    # Check for any prerequisite line (even non-policy)
    has_any_prereq = bool(re.search(r'>\s*Prerequisite:', content))
    if has_any_prereq:
        return {
            'status': 'WARN',
            'detail': 'Has prerequisite but not linked to arch_*.md policy.',
        }

    return {
        'status': 'FAIL',
        'detail': 'No Prerequisite link defined.',
    }


def check_prerequisite_integrity(content, features_dir):
    """Check that all referenced prerequisite files exist on disk."""
    prereq_lines = []
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('> Prerequisite:'):
            prereq_lines.append(stripped)

    if not prereq_lines:
        return {'status': 'PASS', 'detail': 'No prerequisites to verify.'}

    # Extract all file references
    missing = []
    project_root = os.path.dirname(features_dir)
    for prereq_line in prereq_lines:
        text = prereq_line[len('> Prerequisite:'):].strip()
        # Look for .md file references
        file_refs = re.findall(r'[\w/.]+\.md', text)
        for ref in file_refs:
            found = False
            # Try multiple resolution strategies
            candidates = []
            if ref.startswith('features/'):
                # Strip prefix and look directly in features_dir
                bare = ref[len('features/'):]
                candidates.append(os.path.join(features_dir, bare))
            if '/' in ref:
                # Resolve relative to project root
                candidates.append(os.path.join(project_root, ref))
            # Try directly in features_dir
            candidates.append(os.path.join(features_dir, ref))
            # Try at project root level (HOW_WE_WORK.md etc.)
            candidates.append(os.path.join(project_root, ref))

            for candidate in candidates:
                if os.path.exists(candidate):
                    found = True
                    break

            if not found:
                missing.append(ref)

    if missing:
        return {
            'status': 'FAIL',
            'detail': f'Missing prerequisite files: {", ".join(missing)}.',
        }

    return {'status': 'PASS', 'detail': 'All prerequisite files exist.'}


def check_gherkin_quality(scenarios):
    """Check that scenarios have Given/When/Then steps."""
    if not scenarios:
        return {'status': 'WARN', 'detail': 'No scenarios to evaluate.'}

    total = len(scenarios)
    complete = 0

    for s in scenarios:
        body = s['body'].lower()
        has_given = 'given' in body
        has_when = 'when' in body
        has_then = 'then' in body
        if has_given and has_when and has_then:
            complete += 1

    if complete == total:
        return {
            'status': 'PASS',
            'detail': f'All {total} scenarios have Given/When/Then.',
        }

    return {
        'status': 'WARN',
        'detail': f'{complete}/{total} scenarios have complete Given/When/Then.',
    }


def run_spec_gate(content, filename, features_dir):
    """Run all Spec Gate checks.

    Returns dict with 'status' and 'checks'.
    """
    sections = parse_sections(content)
    scenarios = parse_scenarios(content)

    checks = {
        'section_completeness': check_section_completeness(content, sections),
        'scenario_classification': check_scenario_classification(scenarios),
        'policy_anchoring': check_policy_anchoring(content, filename),
        'prerequisite_integrity': check_prerequisite_integrity(content, features_dir),
        'gherkin_quality': check_gherkin_quality(scenarios),
    }

    # Overall status = worst of individual checks
    statuses = [c['status'] for c in checks.values()]
    if 'FAIL' in statuses:
        overall = 'FAIL'
    elif 'WARN' in statuses:
        overall = 'WARN'
    else:
        overall = 'PASS'

    return {'status': overall, 'checks': checks}


# ===================================================================
# Implementation Gate checks (Section 2.2)
# ===================================================================

def check_structural_completeness(feature_stem):
    """Check that tests/<feature>/tests.json exists with status."""
    tests_json = os.path.join(TESTS_DIR, feature_stem, 'tests.json')

    if not os.path.isfile(tests_json):
        return {
            'status': 'FAIL',
            'detail': f'Missing tests/{feature_stem}/tests.json.',
        }

    try:
        with open(tests_json, 'r') as f:
            data = json.load(f)
        status = data.get('status', 'UNKNOWN')
        if status == 'PASS':
            return {
                'status': 'PASS',
                'detail': f'tests/{feature_stem}/tests.json: PASS.',
            }
        return {
            'status': 'WARN',
            'detail': f'tests/{feature_stem}/tests.json: {status}.',
        }
    except (json.JSONDecodeError, IOError, OSError):
        return {
            'status': 'FAIL',
            'detail': f'tests/{feature_stem}/tests.json is malformed.',
        }


def parse_builder_decisions(impl_notes):
    """Parse builder decision tags from Implementation Notes.

    Returns dict: {tag: [entry_text, ...]}
    """
    decisions = {
        'CLARIFICATION': [],
        'AUTONOMOUS': [],
        'DEVIATION': [],
        'DISCOVERY': [],
    }

    pattern = re.compile(r'\[(CLARIFICATION|AUTONOMOUS|DEVIATION|DISCOVERY)\]')
    for line in impl_notes.split('\n'):
        match = pattern.search(line)
        if match:
            tag = match.group(1)
            decisions[tag].append(line.strip())

    return decisions


def check_builder_decisions(impl_notes):
    """Audit builder decision tags."""
    decisions = parse_builder_decisions(impl_notes)

    summary = {tag: len(entries) for tag, entries in decisions.items()}

    has_deviation = summary.get('DEVIATION', 0) > 0
    has_discovery = summary.get('DISCOVERY', 0) > 0
    has_autonomous = summary.get('AUTONOMOUS', 0) > 0

    if has_deviation or has_discovery:
        return {
            'status': 'FAIL',
            'summary': summary,
            'detail': 'Has DEVIATION or unresolved DISCOVERY entries.',
        }

    if has_autonomous:
        return {
            'status': 'WARN',
            'summary': summary,
            'detail': 'Has AUTONOMOUS entries.',
        }

    return {
        'status': 'PASS',
        'summary': summary,
        'detail': 'All entries are INFO/CLARIFICATION.',
    }


def check_logic_drift(scenarios=None, traceability_result=None,
                      feature_stem=None):
    """Run logic drift check (LLM-based, Phase 3).

    Returns WARN-skip when LLM is disabled (default).
    When enabled, assembles scenario-test pairs from traceability data
    and delegates to run_logic_drift for LLM analysis.
    """
    if not LLM_ENABLED or run_logic_drift is None:
        return {
            'status': 'WARN',
            'pairs': [],
            'detail': 'Logic drift check skipped (LLM disabled).',
        }

    # Build scenario title -> body lookup
    scenario_bodies = {}
    for s in (scenarios or []):
        scenario_bodies[s['title']] = s.get('body', '')

    # Discover test files and build function name -> body lookup
    test_files = discover_test_files(PROJECT_ROOT, feature_stem, TOOLS_ROOT)
    all_functions = []
    for tf in test_files:
        all_functions.extend(extract_test_functions(tf))
    func_lookup = {f['name']: f for f in all_functions}

    # Assemble pairs from traceability matched data
    matched = (traceability_result or {}).get('matched', [])
    pairs = []
    for m in matched:
        scenario_title = m['scenario']
        scenario_body = scenario_bodies.get(scenario_title, '')
        test_funcs = []
        for test_name in m.get('tests', []):
            func = func_lookup.get(test_name)
            if func:
                test_funcs.append({'name': test_name, 'body': func['body']})
        if test_funcs and scenario_body:
            pairs.append({
                'scenario_title': scenario_title,
                'scenario_body': scenario_body,
                'test_functions': test_funcs,
            })

    return run_logic_drift(
        pairs, PROJECT_ROOT, feature_stem, TOOLS_ROOT, LLM_MODEL,
    )


def run_implementation_gate(content, feature_stem, filename):
    """Run all Implementation Gate checks.

    Returns dict with 'status' and 'checks'.
    """
    impl_notes = get_implementation_notes(content)
    scenarios = parse_scenarios(content)

    # Traceability
    traceability_result = run_traceability(
        scenarios, PROJECT_ROOT, feature_stem,
        tools_root=TOOLS_ROOT, impl_notes=impl_notes,
    )

    # Policy adherence
    policy_result = run_policy_check(
        content, PROJECT_ROOT, feature_stem,
        features_dir=FEATURES_DIR, tools_root=TOOLS_ROOT,
    )

    checks = {
        'traceability': {
            'status': traceability_result['status'],
            'coverage': traceability_result['coverage'],
            'detail': traceability_result['detail'],
        },
        'policy_adherence': policy_result,
        'structural_completeness': check_structural_completeness(feature_stem),
        'builder_decisions': check_builder_decisions(impl_notes),
        'logic_drift': check_logic_drift(scenarios, traceability_result,
                                         feature_stem),
    }

    # Overall status = worst of individual checks
    # Logic drift WARN from disabled LLM should NOT worsen the overall status
    statuses = []
    for check_name, check_result in checks.items():
        if check_name == 'logic_drift' and not LLM_ENABLED:
            continue  # Skip logic drift from aggregation when LLM disabled
        statuses.append(check_result['status'])

    if 'FAIL' in statuses:
        overall = 'FAIL'
    elif 'WARN' in statuses:
        overall = 'WARN'
    elif statuses:
        overall = 'PASS'
    else:
        overall = 'PASS'

    return {'status': overall, 'checks': checks}


# ===================================================================
# User Testing Audit (Section 2.6)
# ===================================================================

def run_user_testing_audit(content):
    """Parse User Testing Discoveries section and count entries.

    Returns dict with 'status', 'bugs', 'discoveries', 'intent_drifts'.
    """
    section_text = get_user_testing_section(content)

    if not section_text:
        return {
            'status': 'CLEAN',
            'bugs': 0,
            'discoveries': 0,
            'intent_drifts': 0,
        }

    # Count by type
    bugs = len(re.findall(r'\[BUG\]', section_text))
    discoveries = len(re.findall(r'\[DISCOVERY\]', section_text))
    intent_drifts = len(re.findall(r'\[INTENT_DRIFT\]', section_text))

    # Check for OPEN or SPEC_UPDATED items
    open_count = len(re.findall(r'\bOPEN\b', section_text))
    spec_updated_count = len(re.findall(r'\bSPEC_UPDATED\b', section_text))

    if open_count > 0 or spec_updated_count > 0:
        status = 'HAS_OPEN_ITEMS'
    else:
        status = 'CLEAN'

    return {
        'status': status,
        'bugs': bugs,
        'discoveries': discoveries,
        'intent_drifts': intent_drifts,
    }


# ===================================================================
# Output generation
# ===================================================================

def generate_critic_json(feature_path):
    """Analyze a single feature and return the critic.json data structure."""
    content = read_feature_file(feature_path)
    filename = os.path.basename(feature_path)
    feature_stem = get_feature_stem(feature_path)

    spec_gate = run_spec_gate(content, filename, FEATURES_DIR)
    impl_gate = run_implementation_gate(content, feature_stem, filename)
    user_testing = run_user_testing_audit(content)

    rel_path = os.path.relpath(feature_path, PROJECT_ROOT)

    return {
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'feature_file': rel_path,
        'spec_gate': spec_gate,
        'implementation_gate': impl_gate,
        'user_testing': user_testing,
    }


def write_critic_json(feature_path):
    """Analyze a feature and write critic.json to tests/<feature_stem>/."""
    feature_stem = get_feature_stem(feature_path)
    data = generate_critic_json(feature_path)

    output_dir = os.path.join(TESTS_DIR, feature_stem)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'critic.json')

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)
        f.write('\n')

    return data


def generate_critic_report(results):
    """Generate CRITIC_REPORT.md from a list of per-feature results.

    Args:
        results: list of critic.json data dicts

    Returns:
        str: markdown report content
    """
    lines = [
        '# Critic Quality Gate Report',
        '',
        f'Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}',
        '',
        '## Summary',
        '',
        '| Feature | Spec Gate | Implementation Gate | User Testing |',
        '|---------|-----------|--------------------:|-------------|',
    ]

    for r in sorted(results, key=lambda x: x['feature_file']):
        feature = r['feature_file']
        sg = r['spec_gate']['status']
        ig = r['implementation_gate']['status']
        ut = r['user_testing']['status']
        lines.append(f'| {feature} | {sg} | {ig} | {ut} |')

    lines.append('')

    # Builder Decision Audit
    lines.append('## Builder Decision Audit')
    lines.append('')
    has_decisions = False
    for r in sorted(results, key=lambda x: x['feature_file']):
        bd = r['implementation_gate']['checks'].get('builder_decisions', {})
        summary = bd.get('summary', {})
        for tag in ('AUTONOMOUS', 'DEVIATION', 'DISCOVERY'):
            if summary.get(tag, 0) > 0:
                if not has_decisions:
                    has_decisions = True
                lines.append(
                    f'- **{r["feature_file"]}**: [{tag}] x{summary[tag]}'
                )
    if not has_decisions:
        lines.append('No AUTONOMOUS, DEVIATION, or DISCOVERY entries found.')
    lines.append('')

    # Policy Violations
    lines.append('## Policy Violations')
    lines.append('')
    has_violations = False
    for r in sorted(results, key=lambda x: x['feature_file']):
        pa = r['implementation_gate']['checks'].get('policy_adherence', {})
        violations = pa.get('violations', [])
        for v in violations:
            has_violations = True
            lines.append(
                f'- **{r["feature_file"]}**: `{v["pattern"]}` in '
                f'`{v["file"]}` line {v["line"]}'
            )
    if not has_violations:
        lines.append('No FORBIDDEN pattern violations detected.')
    lines.append('')

    # Traceability Gaps
    lines.append('## Traceability Gaps')
    lines.append('')
    has_gaps = False
    for r in sorted(results, key=lambda x: x['feature_file']):
        tr = r['implementation_gate']['checks'].get('traceability', {})
        if tr.get('status') in ('WARN', 'FAIL'):
            has_gaps = True
            lines.append(
                f'- **{r["feature_file"]}**: {tr.get("detail", "coverage gap")}'
            )
    if not has_gaps:
        lines.append('All automated scenarios have matching tests.')
    lines.append('')

    # Open User Testing Items
    lines.append('## Open User Testing Items')
    lines.append('')
    has_open = False
    for r in sorted(results, key=lambda x: x['feature_file']):
        ut = r['user_testing']
        if ut['status'] == 'HAS_OPEN_ITEMS':
            has_open = True
            parts = []
            if ut['bugs']:
                parts.append(f'{ut["bugs"]} BUG(s)')
            if ut['discoveries']:
                parts.append(f'{ut["discoveries"]} DISCOVERY(ies)')
            if ut['intent_drifts']:
                parts.append(f'{ut["intent_drifts"]} INTENT_DRIFT(s)')
            lines.append(
                f'- **{r["feature_file"]}**: {", ".join(parts)}'
            )
    if not has_open:
        lines.append('No open user testing items.')
    lines.append('')

    return '\n'.join(lines)


# ===================================================================
# CLI entry point
# ===================================================================

def main():
    """CLI entry point."""
    if len(sys.argv) > 1:
        # Single feature mode
        feature_path = sys.argv[1]
        if not os.path.isabs(feature_path):
            feature_path = os.path.join(PROJECT_ROOT, feature_path)

        if not os.path.isfile(feature_path):
            print(f'Error: Feature file not found: {feature_path}',
                  file=sys.stderr)
            sys.exit(1)

        data = write_critic_json(feature_path)
        stem = get_feature_stem(feature_path)
        print(f'Critic analysis complete for {os.path.basename(feature_path)}')
        print(f'  Spec Gate:           {data["spec_gate"]["status"]}')
        print(f'  Implementation Gate: {data["implementation_gate"]["status"]}')
        print(f'  User Testing:        {data["user_testing"]["status"]}')
        print(f'  Output: tests/{stem}/critic.json')
    else:
        # All features mode
        if not os.path.isdir(FEATURES_DIR):
            print(f'Error: Features directory not found: {FEATURES_DIR}',
                  file=sys.stderr)
            sys.exit(1)

        feature_files = sorted([
            f for f in os.listdir(FEATURES_DIR) if f.endswith('.md')
        ])

        if not feature_files:
            print('No feature files found.')
            sys.exit(0)

        results = []
        for fname in feature_files:
            fpath = os.path.join(FEATURES_DIR, fname)
            data = write_critic_json(fpath)
            results.append(data)
            stem = get_feature_stem(fpath)
            sg = data['spec_gate']['status']
            ig = data['implementation_gate']['status']
            print(f'  {fname}: Spec={sg} Impl={ig}')

        # Generate aggregate report
        report = generate_critic_report(results)
        report_path = os.path.join(PROJECT_ROOT, 'CRITIC_REPORT.md')
        with open(report_path, 'w') as f:
            f.write(report)

        print(f'\nCRITIC_REPORT.md generated at project root.')
        print(f'Analyzed {len(results)} feature(s).')


if __name__ == '__main__':
    main()
