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
import subprocess
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Path setup -- resolve project root and config (Sections 2.11, 2.13)
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Check AGENTIC_PROJECT_ROOT env var (authoritative when set by launchers)
_env_root = os.environ.get('AGENTIC_PROJECT_ROOT', '')
if _env_root and os.path.isdir(_env_root):
    PROJECT_ROOT = _env_root
else:
    # 2. Climbing fallback: try FURTHER path first (submodule), then nearer (standalone)
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
    for depth in ('../../../', '../../'):
        candidate = os.path.abspath(os.path.join(SCRIPT_DIR, depth))
        if os.path.exists(os.path.join(candidate, '.agentic_devops')):
            PROJECT_ROOT = candidate
            break

# Config loading with resilience (Section 2.13)
CONFIG = {}
_cfg_path = os.path.join(PROJECT_ROOT, '.agentic_devops/config.json')
if os.path.exists(_cfg_path):
    try:
        with open(_cfg_path, 'r') as f:
            CONFIG = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        print("Warning: Failed to parse .agentic_devops/config.json; using defaults",
              file=sys.stderr)

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
    extract_test_entries,
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


def parse_discovery_entries(section_text):
    """Parse structured discovery entries from User Testing Discoveries text.

    Each entry starts with a ### heading containing [TYPE] and has a Status line.
    Also parses the optional "Action Required" field for routing.
    Returns list of dicts: {'type': str, 'title': str, 'status': str,
                            'heading': str, 'action_required': str}
    """
    entries = []
    current_type = None
    current_title = None
    current_status = None
    current_action = ''

    for line in section_text.split('\n'):
        heading_match = re.match(
            r'^###\s+\[(BUG|DISCOVERY|INTENT_DRIFT|SPEC_DISPUTE)\]\s+(.+)',
            line)
        if heading_match:
            if current_type is not None:
                entries.append({
                    'type': current_type,
                    'title': current_title,
                    'status': current_status or 'OPEN',
                    'heading': f'[{current_type}] {current_title}',
                    'action_required': current_action,
                })
            current_type = heading_match.group(1)
            current_title = heading_match.group(2).strip()
            current_status = None
            current_action = ''
            continue

        status_match = re.match(
            r'^-\s+\*\*Status:\*\*\s+(\S+)', line.strip())
        if status_match and current_type is not None:
            current_status = status_match.group(1)

        action_match = re.match(
            r'^-\s+\*\*Action Required:\*\*\s+(.+)', line.strip())
        if action_match and current_type is not None:
            current_action = action_match.group(1).strip()

    if current_type is not None:
        entries.append({
            'type': current_type,
            'title': current_title,
            'status': current_status or 'OPEN',
            'heading': f'[{current_type}] {current_title}',
            'action_required': current_action,
        })

    return entries


def is_policy_file(filename):
    """Check if a filename is an architectural policy file."""
    return os.path.basename(filename).startswith('arch_')


def get_feature_stem(filepath):
    """Get the feature stem from a filepath (filename without .md)."""
    return os.path.splitext(os.path.basename(filepath))[0]


# ===================================================================
# Spec Gate checks (Section 2.1)
# ===================================================================

def check_section_completeness(content, sections, policy_file=False):
    """Check that required sections exist.

    For policy files (arch_*.md), checks for Purpose and Invariants
    instead of Overview/Requirements/Scenarios.
    """
    if policy_file:
        has_purpose = any('purpose' in k for k in sections)
        has_invariants = any('invariants' in k for k in sections)

        if has_purpose and has_invariants:
            return {
                'status': 'PASS',
                'detail': 'Required policy sections present (Purpose, Invariants).',
            }

        missing = []
        if not has_purpose:
            missing.append('Purpose')
        if not has_invariants:
            missing.append('Invariants')

        return {
            'status': 'FAIL',
            'detail': f'Missing policy sections: {", ".join(missing)}.',
        }

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
        'status': 'WARN',
        'detail': 'No prerequisite link found.',
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

    Policy files (arch_*.md) receive reduced evaluation: only Purpose/Invariants
    section check; scenario_classification and gherkin_quality are skipped.
    """
    sections = parse_sections(content)
    scenarios = parse_scenarios(content)
    policy = is_policy_file(filename)

    if policy:
        checks = {
            'section_completeness': check_section_completeness(
                content, sections, policy_file=True),
            'scenario_classification': {
                'status': 'PASS', 'detail': 'N/A - policy file'},
            'policy_anchoring': check_policy_anchoring(content, filename),
            'prerequisite_integrity': check_prerequisite_integrity(
                content, features_dir),
            'gherkin_quality': {
                'status': 'PASS', 'detail': 'N/A - policy file'},
        }
    else:
        checks = {
            'section_completeness': check_section_completeness(content, sections),
            'scenario_classification': check_scenario_classification(scenarios),
            'policy_anchoring': check_policy_anchoring(content, filename),
            'prerequisite_integrity': check_prerequisite_integrity(
                content, features_dir),
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
        'INFEASIBLE': [],
    }

    pattern = re.compile(
        r'\[(CLARIFICATION|AUTONOMOUS|DEVIATION|DISCOVERY|INFEASIBLE)\]')
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

    has_infeasible = summary.get('INFEASIBLE', 0) > 0
    has_deviation = summary.get('DEVIATION', 0) > 0
    has_discovery = summary.get('DISCOVERY', 0) > 0
    has_autonomous = summary.get('AUTONOMOUS', 0) > 0

    if has_infeasible or has_deviation or has_discovery:
        return {
            'status': 'FAIL',
            'summary': summary,
            'detail': 'Has INFEASIBLE, DEVIATION, or unresolved DISCOVERY entries.',
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

    Returns dict with 'status', 'bugs', 'discoveries', 'intent_drifts',
    'spec_disputes'.
    """
    section_text = get_user_testing_section(content)

    if not section_text:
        return {
            'status': 'CLEAN',
            'bugs': 0,
            'discoveries': 0,
            'intent_drifts': 0,
            'spec_disputes': 0,
        }

    # Count by type
    bugs = len(re.findall(r'\[BUG\]', section_text))
    discoveries = len(re.findall(r'\[DISCOVERY\]', section_text))
    intent_drifts = len(re.findall(r'\[INTENT_DRIFT\]', section_text))
    spec_disputes = len(re.findall(r'\[SPEC_DISPUTE\]', section_text))

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
        'spec_disputes': spec_disputes,
    }


# ===================================================================
# Action Item Generation (Section 2.10)
# ===================================================================

def _read_cdd_feature_status():
    """Read CDD feature_status.json from disk.

    Returns dict or None if file doesn't exist or is malformed.
    """
    status_path = os.path.join(
        PROJECT_ROOT, '.agentic_devops', 'cache', 'feature_status.json')
    if not os.path.isfile(status_path):
        return None
    try:
        with open(status_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None


def generate_action_items(feature_result, cdd_status=None):
    """Generate role-specific action items from critic analysis results.

    Args:
        feature_result: per-feature critic.json data dict
        cdd_status: optional CDD feature_status.json data (for QA items)

    Returns:
        dict with 'architect', 'builder', 'qa' lists of action items.
    """
    feature_file = feature_result['feature_file']
    feature_name = os.path.splitext(os.path.basename(feature_file))[0]
    spec_gate = feature_result['spec_gate']
    impl_gate = feature_result['implementation_gate']
    user_testing = feature_result['user_testing']

    architect_items = []
    builder_items = []
    qa_items = []

    # --- Architect items ---
    # Spec Gate FAIL -> HIGH
    if spec_gate['status'] == 'FAIL':
        for check_name, check_result in spec_gate['checks'].items():
            if check_result['status'] == 'FAIL':
                architect_items.append({
                    'priority': 'HIGH',
                    'category': 'spec_gate',
                    'feature': feature_name,
                    'description': (
                        f'Fix spec gap: {check_name} -- '
                        f'{check_result.get("detail", "FAIL")}'
                    ),
                })

    # Spec Gate WARN -> LOW
    if spec_gate['status'] == 'WARN':
        for check_name, check_result in spec_gate['checks'].items():
            if check_result['status'] == 'WARN':
                architect_items.append({
                    'priority': 'LOW',
                    'category': 'spec_gate',
                    'feature': feature_name,
                    'description': (
                        f'Improve spec: {check_name} -- '
                        f'{check_result.get("detail", "WARN")}'
                    ),
                })

    # [INFEASIBLE] tag in Implementation Notes -> CRITICAL Architect
    bd = impl_gate['checks'].get('builder_decisions', {})
    bd_summary = bd.get('summary', {})
    if bd_summary.get('INFEASIBLE', 0) > 0:
        architect_items.append({
            'priority': 'CRITICAL',
            'category': 'infeasible',
            'feature': feature_name,
            'description': (
                f'Revise infeasible spec for {feature_name}: '
                f'Builder halted -- spec cannot be implemented as written'
            ),
        })

    # Unacknowledged DEVIATION/DISCOVERY -> HIGH Architect
    if bd_summary.get('DEVIATION', 0) > 0 or bd_summary.get('DISCOVERY', 0) > 0:
        architect_items.append({
            'priority': 'HIGH',
            'category': 'builder_decisions',
            'feature': feature_name,
            'description': (
                f'Acknowledge Builder decision in {feature_name}: '
                f'unresolved DEVIATION/DISCOVERY'
            ),
        })

    # Pre-parse User Testing discovery entries (block-level parsing)
    ut_entries = []
    if user_testing['status'] == 'HAS_OPEN_ITEMS':
        _ut_content = read_feature_file(
            os.path.join(FEATURES_DIR, os.path.basename(feature_file)))
        _ut_section = get_user_testing_section(_ut_content)
        ut_entries = parse_discovery_entries(_ut_section)

    # OPEN DISCOVERY/INTENT_DRIFT/SPEC_DISPUTE in User Testing -> HIGH Architect
    for entry in ut_entries:
        if entry['type'] in ('DISCOVERY', 'INTENT_DRIFT') \
                and entry['status'] == 'OPEN':
            architect_items.append({
                'priority': 'HIGH',
                'category': 'user_testing',
                'feature': feature_name,
                'description': f'Update spec for {feature_name}: {entry["heading"]}',
            })
        if entry['type'] == 'SPEC_DISPUTE' and entry['status'] == 'OPEN':
            architect_items.append({
                'priority': 'HIGH',
                'category': 'user_testing',
                'feature': feature_name,
                'description': (
                    f'Review disputed scenario in {feature_name}: '
                    f'{entry["heading"]}'
                ),
            })

    # --- Builder items ---
    # Feature in TODO lifecycle state -> HIGH (spec modified, needs review)
    if cdd_status is not None:
        lifecycle_state = _get_feature_lifecycle_state(feature_file, cdd_status)
        if lifecycle_state == 'todo':
            builder_items.append({
                'priority': 'HIGH',
                'category': 'lifecycle_reset',
                'feature': feature_name,
                'description': (
                    f'Review and implement spec changes for {feature_name}'
                ),
            })

    # Structural completeness FAIL -> HIGH
    struct = impl_gate['checks'].get('structural_completeness', {})
    if struct.get('status') == 'FAIL':
        builder_items.append({
            'priority': 'HIGH',
            'category': 'structural_completeness',
            'feature': feature_name,
            'description': (
                f'Fix failing tests for {feature_name}'
            ),
        })

    # Traceability gaps -> MEDIUM
    trace = impl_gate['checks'].get('traceability', {})
    if trace.get('status') in ('WARN', 'FAIL'):
        builder_items.append({
            'priority': 'MEDIUM',
            'category': 'traceability',
            'feature': feature_name,
            'description': (
                f'Write tests for {feature_name}: '
                f'{trace.get("detail", "coverage gap")}'
            ),
        })

    # OPEN BUGs in User Testing -> HIGH Builder
    for entry in ut_entries:
        if entry['type'] == 'BUG' and entry['status'] == 'OPEN':
            builder_items.append({
                'priority': 'HIGH',
                'category': 'user_testing',
                'feature': feature_name,
                'description': f'Fix bug in {feature_name}: {entry["heading"]}',
            })

    # SPEC_UPDATED discoveries with Builder action routing -> MEDIUM Builder
    for entry in ut_entries:
        if entry['status'] == 'SPEC_UPDATED' \
                and 'builder' in entry.get('action_required', '').lower():
            builder_items.append({
                'priority': 'MEDIUM',
                'category': 'user_testing',
                'feature': feature_name,
                'description': (
                    f'Implement fix for {feature_name}: {entry["heading"]}'
                ),
            })

    # --- QA items ---
    # Features in TESTING status (from CDD) -> MEDIUM
    if cdd_status is not None:
        testing_features = cdd_status.get('features', {}).get('testing', [])
        for tf in testing_features:
            tf_file = tf.get('file', '')
            tf_stem = os.path.splitext(os.path.basename(tf_file))[0]
            if tf_stem == feature_name:
                # Count manual scenarios
                content = read_feature_file(
                    os.path.join(FEATURES_DIR,
                                 os.path.basename(feature_file)))
                scenarios = parse_scenarios(content)
                manual_count = sum(
                    1 for s in scenarios if s.get('is_manual', False))
                if manual_count > 0:
                    qa_items.append({
                        'priority': 'MEDIUM',
                        'category': 'testing_status',
                        'feature': feature_name,
                        'description': (
                            f'Verify {feature_name}: '
                            f'{manual_count} manual scenario(s)'
                        ),
                    })
                break

    # SPEC_UPDATED discoveries -> MEDIUM QA
    for entry in ut_entries:
        if entry['status'] == 'SPEC_UPDATED':
            qa_items.append({
                'priority': 'MEDIUM',
                'category': 'user_testing',
                'feature': feature_name,
                'description': (
                    f'Re-verify {feature_name}: {entry["heading"]}'
                ),
            })

    return {
        'architect': architect_items,
        'builder': builder_items,
        'qa': qa_items,
    }


# ===================================================================
# Untracked File Audit (Section 2.12)
# ===================================================================

def audit_untracked_files(project_root=None):
    """Detect untracked files and generate Architect action items.

    Runs ``git status --porcelain`` and collects untracked entries (``??``).
    Excludes ``.agentic_devops/`` and ``.claude/`` directories.

    Returns:
        list of action item dicts with priority MEDIUM and category
        ``untracked_file``.
    """
    root = project_root or PROJECT_ROOT
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []

    items = []
    for line in result.stdout.strip().split('\n'):
        if not line.startswith('??'):
            continue
        path = line[3:].strip()
        if not path:
            continue
        # Exclude .agentic_devops/ and .claude/ directories
        if path.startswith('.agentic_devops/') or path == '.agentic_devops/':
            continue
        if path.startswith('.claude/') or path == '.claude/':
            continue
        items.append({
            'priority': 'MEDIUM',
            'category': 'untracked_file',
            'feature': 'project',
            'description': (
                f'Triage untracked file: {path} '
                f'(commit, gitignore, or delegate to Builder)'
            ),
        })

    return items


# ===================================================================
# Role Status Computation (Section 2.11)
# ===================================================================

def _get_feature_lifecycle_state(feature_file, cdd_status):
    """Determine lifecycle state (todo/testing/complete) from CDD status.

    Returns 'todo', 'testing', 'complete', or None if unknown.
    """
    if cdd_status is None:
        return None

    features_data = cdd_status.get('features', {})
    basename = os.path.basename(feature_file)

    for state in ('complete', 'testing', 'todo'):
        entries = features_data.get(state, [])
        for entry in entries:
            entry_file = entry.get('file', '')
            if os.path.basename(entry_file) == basename:
                return state

    return None


def compute_role_status(feature_result, cdd_status=None):
    """Compute role_status for a feature based on analysis results.

    Returns dict with 'architect', 'builder', 'qa' status strings.

    Architect: TODO | DONE
    Builder: DONE | TODO | FAIL | INFEASIBLE | BLOCKED
      Precedence: INFEASIBLE > BLOCKED > FAIL > TODO > DONE
    QA: CLEAN | TODO | FAIL | DISPUTED | N/A
      Precedence: FAIL > DISPUTED > TODO > CLEAN > N/A
    """
    spec_gate = feature_result['spec_gate']
    impl_gate = feature_result['implementation_gate']
    user_testing = feature_result['user_testing']
    action_items = feature_result.get('action_items', {})
    feature_file = feature_result['feature_file']

    # --- Architect status ---
    arch_items = action_items.get('architect', [])
    has_high_or_critical_arch = any(
        item['priority'] in ('HIGH', 'CRITICAL') for item in arch_items
    )
    architect_status = 'TODO' if has_high_or_critical_arch else 'DONE'

    # --- Builder status ---
    # Check for INFEASIBLE tag
    bd = impl_gate['checks'].get('builder_decisions', {})
    bd_summary = bd.get('summary', {})
    has_infeasible = bd_summary.get('INFEASIBLE', 0) > 0

    # Pre-parse User Testing discovery entries once (block-level parsing)
    try:
        _content = read_feature_file(
            os.path.join(FEATURES_DIR, os.path.basename(feature_file)))
    except (IOError, OSError):
        _content = ''
    _ut_section = get_user_testing_section(_content)
    _ut_entries = parse_discovery_entries(_ut_section)

    # Check for OPEN SPEC_DISPUTEs (Builder becomes BLOCKED)
    open_spec_disputes = any(
        e['type'] == 'SPEC_DISPUTE' and e['status'] == 'OPEN'
        for e in _ut_entries)

    # Check structural completeness
    struct = impl_gate['checks'].get('structural_completeness', {})
    struct_status = struct.get('status', 'FAIL')

    # Check for open BUGs
    has_open_bugs = any(
        e['type'] == 'BUG' and e['status'] == 'OPEN'
        for e in _ut_entries)

    # Check traceability
    trace = impl_gate['checks'].get('traceability', {})
    has_trace_fail = trace.get('status') == 'FAIL'

    # Lifecycle state (shared by Builder + QA status computation)
    lifecycle_state = _get_feature_lifecycle_state(feature_file, cdd_status)
    lifecycle_is_todo = lifecycle_state == 'todo'

    # Apply precedence: INFEASIBLE > BLOCKED > FAIL > TODO > DONE
    if has_infeasible:
        builder_status = 'INFEASIBLE'
    elif open_spec_disputes:
        builder_status = 'BLOCKED'
    elif struct_status == 'FAIL' or struct_status == 'WARN':
        # struct WARN = tests.json exists with status FAIL -> Builder FAIL (spec 2.11)
        # struct FAIL = tests.json missing/malformed -> Builder TODO (action item)
        if struct_status == 'WARN':
            builder_status = 'FAIL'
        else:
            builder_status = 'TODO'
    elif has_trace_fail:
        builder_status = 'TODO'
    elif lifecycle_is_todo:
        # Spec modified after last status commit -- implementation review needed
        builder_status = 'TODO'
    elif struct_status == 'PASS' and not has_open_bugs:
        # Check if there are any Builder action items
        builder_items = action_items.get('builder', [])
        builder_status = 'TODO' if builder_items else 'DONE'
    else:
        builder_status = 'TODO'

    # --- QA status ---
    # Lifecycle-independent checks using pre-parsed entries
    has_open_bugs_qa = any(
        e['type'] == 'BUG' and e['status'] == 'OPEN'
        for e in _ut_entries)
    has_open_disputes_qa = any(
        e['type'] == 'SPEC_DISPUTE' and e['status'] == 'OPEN'
        for e in _ut_entries)
    has_spec_updated_qa = any(
        e['status'] == 'SPEC_UPDATED' for e in _ut_entries)

    # Pre-compute: is this a TESTING feature with manual scenarios?
    testing_with_manual = False
    if lifecycle_state == 'testing':
        scenarios = parse_scenarios(_content)
        manual_count = sum(
            1 for s in scenarios if s.get('is_manual', False))
        testing_with_manual = manual_count > 0

    # Apply precedence: FAIL > DISPUTED > TODO > CLEAN > N/A
    if has_open_bugs_qa:
        qa_status = 'FAIL'
    elif has_open_disputes_qa:
        qa_status = 'DISPUTED'
    elif has_spec_updated_qa:
        # TODO condition (b): SPEC_UPDATED items -- lifecycle-independent
        qa_status = 'TODO'
    elif user_testing['status'] == 'HAS_OPEN_ITEMS':
        # TODO condition (c): other OPEN items -- lifecycle-independent
        qa_status = 'TODO'
    elif testing_with_manual:
        # TODO condition (a): TESTING with manual scenarios
        qa_status = 'TODO'
    elif user_testing['status'] == 'CLEAN' and struct_status == 'PASS':
        # CLEAN is lifecycle-independent: passing tests + no open items = CLEAN
        qa_status = 'CLEAN'
    else:
        qa_status = 'N/A'

    return {
        'architect': architect_status,
        'builder': builder_status,
        'qa': qa_status,
    }


# ===================================================================
# Output generation
# ===================================================================

def _policy_exempt_implementation_gate():
    """Return an Implementation Gate result for policy files (all PASS)."""
    exempt = 'N/A - policy file exempt'
    return {
        'status': 'PASS',
        'checks': {
            'traceability': {
                'status': 'PASS', 'coverage': 1.0, 'detail': exempt},
            'policy_adherence': {
                'status': 'PASS', 'violations': [], 'detail': exempt},
            'structural_completeness': {
                'status': 'PASS', 'detail': exempt},
            'builder_decisions': {
                'status': 'PASS',
                'summary': {'CLARIFICATION': 0, 'AUTONOMOUS': 0,
                            'DEVIATION': 0, 'DISCOVERY': 0},
                'detail': exempt},
            'logic_drift': {
                'status': 'PASS', 'pairs': [], 'detail': exempt},
        },
    }


def generate_critic_json(feature_path, cdd_status=None):
    """Analyze a single feature and return the critic.json data structure.

    Args:
        feature_path: absolute path to the feature file
        cdd_status: optional CDD feature_status.json data (for QA action items)
    """
    content = read_feature_file(feature_path)
    filename = os.path.basename(feature_path)
    feature_stem = get_feature_stem(feature_path)

    spec_gate = run_spec_gate(content, filename, FEATURES_DIR)

    if is_policy_file(filename):
        impl_gate = _policy_exempt_implementation_gate()
    else:
        impl_gate = run_implementation_gate(content, feature_stem, filename)

    user_testing = run_user_testing_audit(content)

    rel_path = os.path.relpath(feature_path, PROJECT_ROOT)

    result = {
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'feature_file': rel_path,
        'spec_gate': spec_gate,
        'implementation_gate': impl_gate,
        'user_testing': user_testing,
    }

    # Generate action items
    result['action_items'] = generate_action_items(result, cdd_status)

    # Compute role status (depends on action_items being populated)
    result['role_status'] = compute_role_status(result, cdd_status)

    return result


def write_critic_json(feature_path, cdd_status=None):
    """Analyze a feature and write critic.json to tests/<feature_stem>/."""
    feature_stem = get_feature_stem(feature_path)
    data = generate_critic_json(feature_path, cdd_status=cdd_status)

    output_dir = os.path.join(TESTS_DIR, feature_stem)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'critic.json')

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)
        f.write('\n')

    return data


def generate_critic_report(results, untracked_items=None):
    """Generate CRITIC_REPORT.md from a list of per-feature results.

    Args:
        results: list of critic.json data dicts
        untracked_items: optional list of untracked file action items

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

    # Action Items by Role
    lines.append('## Action Items by Role')
    lines.append('')
    priority_order = {'CRITICAL': -1, 'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    for role in ('Architect', 'Builder', 'QA'):
        role_key = role.lower()
        lines.append(f'### {role}')
        lines.append('')
        all_items = []
        for r in results:
            items = r.get('action_items', {}).get(role_key, [])
            all_items.extend(items)
        all_items.sort(key=lambda x: priority_order.get(x['priority'], 9))
        if all_items:
            for item in all_items:
                lines.append(
                    f'- **[{item["priority"]}]** ({item["feature"]}): '
                    f'{item["description"]}'
                )
        else:
            lines.append('No action items.')
        # Untracked Files subsection under Architect
        if role == 'Architect' and untracked_items:
            lines.append('')
            lines.append('#### Untracked Files')
            lines.append('')
            for item in untracked_items:
                lines.append(
                    f'- **[{item["priority"]}]**: '
                    f'{item["description"]}'
                )
        lines.append('')

    # Builder Decision Audit
    lines.append('## Builder Decision Audit')
    lines.append('')
    has_decisions = False
    for r in sorted(results, key=lambda x: x['feature_file']):
        bd = r['implementation_gate']['checks'].get('builder_decisions', {})
        summary = bd.get('summary', {})
        for tag in ('INFEASIBLE', 'AUTONOMOUS', 'DEVIATION', 'DISCOVERY'):
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
            if ut.get('spec_disputes', 0):
                parts.append(f'{ut["spec_disputes"]} SPEC_DISPUTE(s)')
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
    # Try to read CDD feature status for QA action items
    cdd_status = _read_cdd_feature_status()
    if cdd_status is None:
        print('Note: CDD feature_status.json not found; '
              'skipping status-dependent QA items.')

    if len(sys.argv) > 1:
        # Single feature mode
        feature_path = sys.argv[1]
        if not os.path.isabs(feature_path):
            feature_path = os.path.join(PROJECT_ROOT, feature_path)

        if not os.path.isfile(feature_path):
            print(f'Error: Feature file not found: {feature_path}',
                  file=sys.stderr)
            sys.exit(1)

        data = write_critic_json(feature_path, cdd_status=cdd_status)
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
            data = write_critic_json(fpath, cdd_status=cdd_status)
            results.append(data)
            stem = get_feature_stem(fpath)
            sg = data['spec_gate']['status']
            ig = data['implementation_gate']['status']
            print(f'  {fname}: Spec={sg} Impl={ig}')

        # Audit untracked files (project-level, not per-feature)
        untracked_items = audit_untracked_files()

        # Generate aggregate report
        report = generate_critic_report(results, untracked_items=untracked_items)
        report_path = os.path.join(PROJECT_ROOT, 'CRITIC_REPORT.md')
        with open(report_path, 'w') as f:
            f.write(report)

        print(f'\nCRITIC_REPORT.md generated at project root.')
        print(f'Analyzed {len(results)} feature(s).')


if __name__ == '__main__':
    main()
