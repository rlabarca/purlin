#!/usr/bin/env python3
"""Purlin migration module.

Detects old 4-role config (architect/builder/pm/qa) and migrates to the
unified Purlin agent model. Steps: config schema update, override file
consolidation, spec file role renames, companion file restructuring,
and launcher generation.

All spec modifications use the [Migration] exemption tag to prevent
lifecycle resets.
"""

import argparse
import copy
import json
import os
import re
import subprocess
import sys


# ---------------------------------------------------------------------------
# Project root detection (shared pattern with resolve_config.py)
# ---------------------------------------------------------------------------

def find_project_root(start_dir=None):
    """Detect project root using PURLIN_PROJECT_ROOT or climbing fallback."""
    env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if env_root and os.path.isdir(env_root):
        return env_root

    if start_dir is None:
        start_dir = os.path.dirname(os.path.abspath(__file__))

    for depth in ('../../../', '../../'):
        candidate = os.path.abspath(os.path.join(start_dir, depth))
        if os.path.exists(os.path.join(candidate, '.purlin')):
            return candidate

    return os.path.abspath(os.path.join(start_dir, '../../'))


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _read_json(path):
    """Read a JSON file, return dict. Returns None on error."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None


def _write_json(path, data):
    """Atomically write a JSON file."""
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w') as f:
            json.dump(data, f, indent=4)
            f.write('\n')
        os.replace(tmp, path)
    except (IOError, OSError):
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ---------------------------------------------------------------------------
# Step 1: Detection
# ---------------------------------------------------------------------------

def detect_migration_needed(project_root):
    """Check if migration from old 4-role config to Purlin is needed.

    Returns:
        'needed'   - old config exists, no purlin config
        'partial'  - agents.purlin exists but migration incomplete (v0.8.4 gap)
        'complete' - fully migrated (marker present or heuristic confirms)
        'fresh'    - neither old nor new config exists (fresh install)
    """
    purlin_dir = os.path.join(project_root, '.purlin')

    # Check both config files (local first — it's the authority)
    for config_name in ('config.local.json', 'config.json'):
        config_path = os.path.join(purlin_dir, config_name)
        config = _read_json(config_path)
        if config is None:
            continue

        # Fast path: migration marker is the authoritative signal
        if '_migration_version' in config:
            return 'complete'

        agents = config.get('agents', {})
        has_purlin = 'purlin' in agents
        has_old = 'architect' in agents or 'builder' in agents

        if has_purlin:
            # agents.purlin exists but no marker — check if migration is
            # truly complete or just a partial entry from the launcher's
            # first-run flow (v0.8.4 upgrade gap)
            purlin_cfg = agents['purlin']
            required_fields = ('find_work', 'auto_start', 'default_mode')
            missing_fields = [f for f in required_fields if f not in purlin_cfg]

            # Old agents not deprecated = migration didn't run
            old_not_deprecated = has_old and any(
                not agents.get(role, {}).get('_deprecated', False)
                for role in ('architect', 'builder')
                if role in agents
            )

            if missing_fields or old_not_deprecated:
                return 'partial'
            return 'complete'

        if has_old:
            return 'needed'

    return 'fresh'


# ---------------------------------------------------------------------------
# Step 2: Config Migration
# ---------------------------------------------------------------------------

def migrate_config(project_root, dry_run=False):
    """Create or enrich agents.purlin; remove old agent entries.

    Handles both full migration (no agents.purlin) and enrichment
    (partial agents.purlin from launcher first-run).

    Returns list of changes made (strings).
    """
    changes = []
    purlin_dir = os.path.join(project_root, '.purlin')

    _DEFAULTS = {
        'bypass_permissions': False,
        'find_work': True,
        'auto_start': False,
        'default_mode': None,
    }
    _OLD_ROLES = ('architect', 'builder', 'qa', 'pm')

    for config_name in ('config.json', 'config.local.json'):
        config_path = os.path.join(purlin_dir, config_name)
        config = _read_json(config_path)
        if config is None:
            continue

        agents = config.get('agents', {})

        if 'purlin' in agents:
            # Enrichment path: backfill missing keys (read from builder BEFORE removing)
            purlin_cfg = agents['purlin']
            builder = agents.get('builder', {})
            backfilled = []
            for key, default in _DEFAULTS.items():
                if key not in purlin_cfg:
                    purlin_cfg[key] = builder.get(key, default)
                    backfilled.append(key)

            old_present = [r for r in _OLD_ROLES if r in agents]
            if backfilled or old_present:
                if not dry_run:
                    for role in old_present:
                        del agents[role]
                    _write_json(config_path, config)

                if backfilled:
                    changes.append(
                        f"Enriched partial agents.purlin in {config_name} "
                        f"(backfilled {len(backfilled)} missing keys: {', '.join(backfilled)})"
                    )
                for role in old_present:
                    changes.append(f"Removed agents.{role} from {config_name}")
            continue

        if 'builder' not in agents:
            continue

        # Full migration: create agents.purlin from builder (read BEFORE removing)
        builder = agents['builder']
        purlin_agent = {
            'model': builder.get('model', ''),
            'effort': builder.get('effort', ''),
            'bypass_permissions': builder.get('bypass_permissions', False),
            'find_work': True,
            'auto_start': False,
            'default_mode': None,
        }

        old_present = [r for r in _OLD_ROLES if r in agents]
        if not dry_run:
            agents['purlin'] = purlin_agent
            for role in old_present:
                del agents[role]
            config['agents'] = agents
            _write_json(config_path, config)

        changes.append(f"Created agents.purlin in {config_name} (cloned from builder)")
        for role in old_present:
            changes.append(f"Removed agents.{role} from {config_name}")

    return changes


# ---------------------------------------------------------------------------
# Step 3: Override File Consolidation
# ---------------------------------------------------------------------------

def _read_file_content(path):
    """Read file content, return empty string if absent."""
    if not os.path.exists(path):
        return ''
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except (IOError, OSError):
        return ''


def consolidate_overrides(project_root, dry_run=False):
    """Merge old role-specific override files into PURLIN_OVERRIDES.md.

    Returns list of changes made.
    """
    changes = []
    purlin_dir = os.path.join(project_root, '.purlin')
    output_path = os.path.join(purlin_dir, 'PURLIN_OVERRIDES.md')

    if os.path.exists(output_path):
        changes.append("PURLIN_OVERRIDES.md already exists, skipping consolidation")
        return changes

    sections = []

    # General (all modes) from HOW_WE_WORK_OVERRIDES.md
    hww = _read_file_content(os.path.join(purlin_dir, 'HOW_WE_WORK_OVERRIDES.md'))
    if hww:
        sections.append(f"## General (all modes)\n\n{hww}")
        changes.append("Merged HOW_WE_WORK_OVERRIDES.md into General section")

    # Engineer Mode from BUILDER_OVERRIDES.md + technical content from ARCHITECT_OVERRIDES.md
    builder_content = _read_file_content(os.path.join(purlin_dir, 'BUILDER_OVERRIDES.md'))
    architect_content = _read_file_content(os.path.join(purlin_dir, 'ARCHITECT_OVERRIDES.md'))

    engineer_parts = []
    if builder_content:
        engineer_parts.append(builder_content)
        changes.append("Merged BUILDER_OVERRIDES.md into Engineer Mode section")
    if architect_content:
        # Architect content that is technical goes to Engineer, spec/design to PM.
        # Heuristic: content with technical keywords goes to Engineer.
        tech_lines, spec_lines = _split_architect_content(architect_content)
        if tech_lines:
            engineer_parts.append(tech_lines)
            changes.append("Merged technical ARCHITECT_OVERRIDES.md content into Engineer Mode")
        if spec_lines:
            # Will be handled in PM section below
            pass

    if engineer_parts:
        sections.append("## Engineer Mode\n\n" + "\n\n".join(engineer_parts))

    # PM Mode from PM_OVERRIDES.md + spec/design content from ARCHITECT_OVERRIDES.md
    pm_content = _read_file_content(os.path.join(purlin_dir, 'PM_OVERRIDES.md'))
    pm_parts = []
    if pm_content:
        pm_parts.append(pm_content)
        changes.append("Merged PM_OVERRIDES.md into PM Mode section")
    if architect_content:
        _, spec_lines = _split_architect_content(architect_content)
        if spec_lines:
            pm_parts.append(spec_lines)
            changes.append("Merged spec/design ARCHITECT_OVERRIDES.md content into PM Mode")
    if pm_parts:
        sections.append("## PM Mode\n\n" + "\n\n".join(pm_parts))

    # QA Mode from QA_OVERRIDES.md
    qa_content = _read_file_content(os.path.join(purlin_dir, 'QA_OVERRIDES.md'))
    if qa_content:
        sections.append(f"## QA Mode\n\n{qa_content}")
        changes.append("Merged QA_OVERRIDES.md into QA Mode section")

    if not sections:
        changes.append("No override files found to consolidate")
        return changes

    output = "# Purlin Overrides\n\n" + "\n\n".join(sections) + "\n"

    if not dry_run:
        with open(output_path, 'w') as f:
            f.write(output)

    changes.append(f"Created PURLIN_OVERRIDES.md with {len(sections)} section(s)")

    # Delete old override files after successful consolidation
    if not dry_run:
        _OLD_OVERRIDES = [
            'ARCHITECT_OVERRIDES.md', 'BUILDER_OVERRIDES.md',
            'QA_OVERRIDES.md', 'PM_OVERRIDES.md',
            'HOW_WE_WORK_OVERRIDES.md',
        ]
        for name in _OLD_OVERRIDES:
            old_path = os.path.join(purlin_dir, name)
            if os.path.exists(old_path):
                os.remove(old_path)
                changes.append(f"Deleted {name}")

    return changes


def _split_architect_content(content):
    """Split architect override content into technical vs spec/design parts.

    Heuristic: sections with headers containing technical keywords go to
    Engineer; sections about spec/design authority go to PM.
    If no clear split is possible, all content goes to Engineer.
    """
    tech_keywords = re.compile(
        r'(arch|technical|code|implementation|testing|infrastructure|'
        r'performance|script|tool|build|deploy)', re.IGNORECASE
    )
    spec_keywords = re.compile(
        r'(spec|design|requirement|visual|UX|UI|stakeholder|'
        r'product|feature\s+definition)', re.IGNORECASE
    )

    # Split into sections by ## headers
    parts = re.split(r'(?=^## )', content, flags=re.MULTILINE)
    tech_parts = []
    spec_parts = []

    for part in parts:
        part = part.strip()
        if not part:
            continue
        header_match = re.match(r'^## (.+)', part)
        if header_match:
            header = header_match.group(1)
            if spec_keywords.search(header):
                spec_parts.append(part)
            elif tech_keywords.search(header):
                tech_parts.append(part)
            else:
                # Default: technical (Engineer)
                tech_parts.append(part)
        else:
            # No header — default to technical
            tech_parts.append(part)

    return '\n\n'.join(tech_parts), '\n\n'.join(spec_parts)


# ---------------------------------------------------------------------------
# Step 4: Spec File Role Renames
# ---------------------------------------------------------------------------

# Ordered from most specific to least specific to avoid double-replacement
_ROLE_REPLACEMENTS = [
    # Exact phrases first (case-sensitive)
    ('the Architect', 'PM mode'),
    ('the Builder', 'Engineer mode'),
    ('The Architect', 'PM mode'),
    ('The Builder', 'Engineer mode'),
    # Standalone role names (word-boundary aware)
    # These are applied via regex in rename_roles_in_text
]

# Regex patterns for word-boundary role renames
_ROLE_REGEX_REPLACEMENTS = [
    # "Architect" as a role reference (not in "ARCHITECT_OVERRIDES" etc.)
    (re.compile(r'\bArchitect\b(?!_)'), 'PM'),
    (re.compile(r'\bBuilder\b(?!_)'), 'Engineer'),
]

# Discovery sidecar specific replacements
_DISCOVERY_REPLACEMENTS = [
    ('Action Required: Architect', 'Action Required: PM'),
    ('Action Required: Builder', 'Action Required: Engineer'),
]


def rename_roles_in_text(text, is_discovery=False):
    """Apply role renames to text content.

    Returns the modified text.
    """
    result = text

    if is_discovery:
        for old, new in _DISCOVERY_REPLACEMENTS:
            result = result.replace(old, new)

    # Apply exact phrase replacements first
    for old, new in _ROLE_REPLACEMENTS:
        result = result.replace(old, new)

    # Apply regex replacements
    for pattern, replacement in _ROLE_REGEX_REPLACEMENTS:
        result = pattern.sub(replacement, result)

    return result


def rename_spec_roles(project_root, dry_run=False):
    """Rename role references in feature spec files.

    Returns list of changes made.
    """
    changes = []
    features_dir = os.path.join(project_root, 'features')
    if not os.path.isdir(features_dir):
        return changes

    for filename in sorted(os.listdir(features_dir)):
        filepath = os.path.join(features_dir, filename)
        if not os.path.isfile(filepath):
            continue

        is_discovery = filename.endswith('.discoveries.md')
        is_impl = filename.endswith('.impl.md')
        is_spec = filename.endswith('.md') and not is_discovery and not is_impl

        if not (is_spec or is_discovery or is_impl):
            continue

        try:
            with open(filepath, 'r') as f:
                original = f.read()
        except (IOError, OSError):
            continue

        modified = rename_roles_in_text(original, is_discovery=is_discovery)

        if modified != original:
            if not dry_run:
                with open(filepath, 'w') as f:
                    f.write(modified)
            changes.append(f"Renamed roles in {filename}")

    return changes


# ---------------------------------------------------------------------------
# Step 5: Companion File Restructuring
# ---------------------------------------------------------------------------

_ACTIVE_DEVIATIONS_HEADER = """## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|"""

_TAG_PATTERN = re.compile(
    r'\*?\*?\[(\w+)\]\*?\*?\s+(.+?)(?:\s*\(Severity:\s*\w+\))?$',
    re.MULTILINE
)

# Tags that get promoted to Active Deviations table rows
_PROMOTABLE_TAGS = {'DEVIATION', 'DISCOVERY', 'INFEASIBLE', 'SPEC_PROPOSAL'}


def restructure_companion(filepath, dry_run=False):
    """Add Active Deviations table to a companion file if absent.

    Returns list of changes made.
    """
    changes = []

    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except (IOError, OSError):
        return changes

    # Check if table already exists
    if '## Active Deviations' in content:
        return changes

    # Parse existing tags from prose
    rows = []
    for match in _TAG_PATTERN.finditer(content):
        tag = match.group(1).upper()
        description = match.group(2).strip()
        if tag in _PROMOTABLE_TAGS:
            rows.append(f"| (see prose) | {description} | {tag} | PENDING |")

    # Build the table
    table = _ACTIVE_DEVIATIONS_HEADER
    if rows:
        table += '\n' + '\n'.join(rows)
    else:
        table += '\n'

    # Insert table after the first heading (# Implementation Notes: ...)
    heading_match = re.match(r'^(#[^\n]+\n+)', content)
    if heading_match:
        insert_pos = heading_match.end()
        new_content = content[:insert_pos] + table + '\n\n' + content[insert_pos:]
    else:
        # No heading — prepend table
        new_content = table + '\n\n' + content

    if not dry_run:
        with open(filepath, 'w') as f:
            f.write(new_content)

    filename = os.path.basename(filepath)
    changes.append(f"Added Active Deviations table to {filename}")
    if rows:
        changes.append(f"  Promoted {len(rows)} tag(s) to table rows")

    return changes


def restructure_companions(project_root, dry_run=False):
    """Restructure all companion files to include Active Deviations tables.

    Returns list of changes made.
    """
    changes = []
    features_dir = os.path.join(project_root, 'features')
    if not os.path.isdir(features_dir):
        return changes

    for filename in sorted(os.listdir(features_dir)):
        if not filename.endswith('.impl.md'):
            continue
        filepath = os.path.join(features_dir, filename)
        changes.extend(restructure_companion(filepath, dry_run=dry_run))

    return changes


# ---------------------------------------------------------------------------
# Step 6: Launcher Generation
# ---------------------------------------------------------------------------

def generate_launcher(project_root, dry_run=False):
    """Generate pl-run.sh by invoking init.sh --quiet.

    Returns list of changes made.
    """
    changes = []

    # Find tools_root from config
    config_path = os.path.join(project_root, '.purlin', 'config.json')
    config = _read_json(config_path) or {}
    tools_root = config.get('tools_root', 'tools')
    init_sh = os.path.join(project_root, tools_root, 'init.sh')

    if not os.path.exists(init_sh):
        changes.append("init.sh not found, skipping launcher generation")
        return changes

    if dry_run:
        changes.append("Would run init.sh --quiet to regenerate pl-run.sh")
        return changes

    try:
        result = subprocess.run(
            ['bash', init_sh, '--quiet'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, 'PURLIN_PROJECT_ROOT': project_root}
        )
        if result.returncode == 0:
            changes.append("Ran init.sh --quiet to regenerate launcher")
        else:
            changes.append(f"init.sh failed (exit {result.returncode}): {result.stderr.strip()}")
    except (subprocess.TimeoutExpired, OSError) as e:
        changes.append(f"init.sh error: {e}")

    return changes


# ---------------------------------------------------------------------------
# Step 7: Complete Transition
# ---------------------------------------------------------------------------

def complete_transition(project_root, dry_run=False):
    """Remove old launchers, deprecated config entries, and old override files.

    Returns list of changes made.
    """
    changes = []
    purlin_dir = os.path.join(project_root, '.purlin')

    # Remove old launchers
    old_launchers = [
        'pl-run-architect.sh', 'pl-run-builder.sh',
        'pl-run-qa.sh', 'pl-run-pm.sh',
    ]
    for launcher in old_launchers:
        launcher_path = os.path.join(project_root, launcher)
        if os.path.exists(launcher_path):
            if not dry_run:
                os.remove(launcher_path)
            changes.append(f"Removed {launcher}")

    # Remove deprecated agent entries from config
    for config_name in ('config.json', 'config.local.json'):
        config_path = os.path.join(purlin_dir, config_name)
        config = _read_json(config_path)
        if config is None:
            continue

        agents = config.get('agents', {})
        removed = []
        for role in ('architect', 'builder', 'qa', 'pm'):
            if role in agents:
                del agents[role]
                removed.append(role)

        if removed:
            if not dry_run:
                config['agents'] = agents
                _write_json(config_path, config)
            changes.append(f"Removed agents.{{{','.join(removed)}}} from {config_name}")

    # Remove old override files
    old_overrides = [
        'ARCHITECT_OVERRIDES.md', 'BUILDER_OVERRIDES.md',
        'QA_OVERRIDES.md', 'PM_OVERRIDES.md',
        'HOW_WE_WORK_OVERRIDES.md',
    ]
    for override in old_overrides:
        override_path = os.path.join(purlin_dir, override)
        if os.path.exists(override_path):
            if not dry_run:
                os.remove(override_path)
            changes.append(f"Removed {override}")

    return changes


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def _stamp_migration_version(project_root, dry_run=False):
    """Write _migration_version: 1 to the active config file."""
    purlin_dir = os.path.join(project_root, '.purlin')
    for config_name in ('config.local.json', 'config.json'):
        config_path = os.path.join(purlin_dir, config_name)
        config = _read_json(config_path)
        if config is None:
            continue
        if '_migration_version' not in config:
            if not dry_run:
                config['_migration_version'] = 1
                _write_json(config_path, config)
            return f"Stamped _migration_version: 1 in {config_name}"
    return None


def run_migration(project_root, dry_run=False, skip_overrides=False,
                  skip_companions=False, skip_specs=False,
                  auto_approve=False, purlin_only=False,
                  do_complete_transition=False):
    """Run the full migration pipeline.

    Returns dict with 'status' and 'changes' keys.
    """
    all_changes = []

    # Detection
    status = detect_migration_needed(project_root)
    if status == 'fresh':
        return {'status': 'fresh', 'changes': ['Fresh install detected, skipping migration']}

    if do_complete_transition:
        changes = complete_transition(project_root, dry_run=dry_run)
        all_changes.extend(changes)
        return {'status': 'transition_complete', 'changes': all_changes}

    if status == 'complete' and not purlin_only:
        # Stamp marker for future fast-path if missing (backfill for
        # users who migrated before the marker was introduced)
        stamp = _stamp_migration_version(project_root, dry_run=dry_run)
        changes = ['Migration already complete']
        if stamp:
            changes.append(stamp)
        return {'status': 'complete', 'changes': changes}

    if status == 'partial':
        all_changes.append('Partial migration detected — running repair pass')

    # Step 1: Config migration / enrichment (always runs)
    changes = migrate_config(project_root, dry_run=dry_run)
    all_changes.extend(changes)

    if purlin_only:
        stamp = _stamp_migration_version(project_root, dry_run=dry_run)
        if stamp:
            all_changes.append(stamp)
        return {'status': 'purlin_only', 'changes': all_changes}

    # Step 2: Override consolidation
    if not skip_overrides:
        changes = consolidate_overrides(project_root, dry_run=dry_run)
        all_changes.extend(changes)

    # Step 3: Spec role renames
    if not skip_specs:
        changes = rename_spec_roles(project_root, dry_run=dry_run)
        all_changes.extend(changes)

    # Step 4: Companion restructuring
    if not skip_companions:
        changes = restructure_companions(project_root, dry_run=dry_run)
        all_changes.extend(changes)

    # Step 5: Launcher generation + old launcher cleanup
    changes = generate_launcher(project_root, dry_run=dry_run)
    all_changes.extend(changes)

    # Delete old launchers
    _OLD_LAUNCHERS = [
        'pl-run-architect.sh', 'pl-run-builder.sh',
        'pl-run-qa.sh', 'pl-run-pm.sh',
        'pl-cdd-start.sh', 'pl-cdd-stop.sh',
    ]
    for name in _OLD_LAUNCHERS:
        old_path = os.path.join(project_root, name)
        if os.path.exists(old_path):
            if not dry_run:
                os.remove(old_path)
            all_changes.append(f"Deleted old launcher {name}")

    # Step 6: Write migration marker
    stamp = _stamp_migration_version(project_root, dry_run=dry_run)
    if stamp:
        all_changes.append(stamp)

    return {'status': 'migrated', 'changes': all_changes}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Migrate Purlin project from 4-role to unified agent model'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would change without modifying files')
    parser.add_argument('--skip-overrides', action='store_true',
                        help="Don't merge override files")
    parser.add_argument('--skip-companions', action='store_true',
                        help="Don't restructure companion files")
    parser.add_argument('--skip-specs', action='store_true',
                        help="Don't rename roles in spec files")
    parser.add_argument('--auto-approve', action='store_true',
                        help='Skip confirmation prompts')
    parser.add_argument('--purlin-only', action='store_true',
                        help='Only add purlin config section')
    parser.add_argument('--complete-transition', action='store_true',
                        help='Remove old launchers, config, and override files')
    parser.add_argument('--project-root', default=None,
                        help='Override project root (default: auto-detect)')
    parser.add_argument('--detect-only', action='store_true',
                        help='Only check if migration is needed (for scripting)')

    args = parser.parse_args()

    project_root = args.project_root or find_project_root()

    if args.detect_only:
        status = detect_migration_needed(project_root)
        print(status)
        sys.exit(0 if status == 'needed' else 1)

    if not args.auto_approve and not args.dry_run:
        status = detect_migration_needed(project_root)
        if status == 'needed':
            print("Migration will modify config, override files, specs, and companions.")
            print("Use --dry-run to preview changes, or --auto-approve to skip this prompt.")
            try:
                answer = input("Proceed? [y/N] ")
                if answer.lower() not in ('y', 'yes'):
                    print("Aborted.")
                    sys.exit(0)
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                sys.exit(0)

    result = run_migration(
        project_root,
        dry_run=args.dry_run,
        skip_overrides=args.skip_overrides,
        skip_companions=args.skip_companions,
        skip_specs=args.skip_specs,
        auto_approve=args.auto_approve,
        purlin_only=args.purlin_only,
        do_complete_transition=args.complete_transition,
    )

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{prefix}Migration status: {result['status']}")
    for change in result['changes']:
        print(f"  {prefix}{change}")

    if args.dry_run:
        print(f"\n{prefix}No files were modified.")


if __name__ == '__main__':
    main()
