#!/usr/bin/env python3
"""Purlin migration registry.

Ordered list of migration steps with preconditions, plan (dry-run),
and execute methods. Computes the migration path from a version
fingerprint to the target migration version.

Usage:
    python3 migration_registry.py --project-root <path> [--dry-run]
    Output: Computed migration path with step names and planned actions.
"""
import json
import os
import glob as glob_mod
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod

from version_detector import detect_version, _read_json


# Current migration version — the target for all migrations.
CURRENT_MIGRATION_VERSION = 3


class MigrationStep(ABC):
    """Base class for migration steps."""

    step_id: int  # The _migration_version this step stamps on completion.
    name: str
    from_era: str
    to_era: str

    @abstractmethod
    def preconditions(self, fingerprint, project_root):
        """Check if this step can run.

        Returns:
            (bool, str): (True, "") if ok, (False, "reason") if not.
        """

    @abstractmethod
    def plan(self, fingerprint, project_root):
        """Dry-run: return list of action description strings."""

    @abstractmethod
    def execute(self, fingerprint, project_root, auto_approve=False):
        """Run the migration. Returns True on success.

        Stamps _migration_version on completion.
        """

    def _stamp_version(self, project_root):
        """Write _migration_version to consumer config."""
        config_path = os.path.join(project_root, '.purlin', 'config.json')
        config = _read_json(config_path) or {}
        config['_migration_version'] = self.step_id
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
            f.write('\n')

    def _has_uncommitted_changes(self, project_root):
        """Check for uncommitted changes in the project."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, cwd=project_root, timeout=10
            )
            return bool(result.stdout.strip())
        except (subprocess.SubprocessError, OSError):
            return False


class Step1UnifiedAgentModel(MigrationStep):
    """Step 1: Pre-unified submodule -> Unified submodule."""

    step_id = 1
    name = 'Unified Agent Model'
    from_era = 'pre-unified'
    to_era = 'unified'

    def preconditions(self, fingerprint, project_root):
        if fingerprint.get('model') != 'submodule':
            return False, 'Not a submodule project.'
        mv = fingerprint.get('migration_version')
        if mv is not None and mv >= self.step_id:
            return False, f'Already at migration_version {mv}.'
        era = fingerprint.get('era', '')
        valid_eras = {
            'pre-unified-legacy', 'pre-unified-modern',
            'pre-unified-with-pm', 'unified-partial',
        }
        # Also allow unified with no migration_version (shouldn't happen, but safe)
        if era not in valid_eras and era != 'unified':
            return False, f'Unexpected era for step 1: {era}'
        return True, ''

    def plan(self, fingerprint, project_root):
        era = fingerprint.get('era', '')
        actions = []
        if era == 'unified-partial':
            actions.append('Repair partial migration: complete agents.purlin config.')
            actions.append('Remove stale agent entries (architect, builder, qa, pm).')
        else:
            actions.append('Advance submodule to v0.8.5+ with unified agent support.')
            actions.append('Consolidate 4-role config into agents.purlin.')
            actions.append('Merge override files into single PURLIN_OVERRIDES.md.')
            actions.append('Clean old role-specific launchers.')
        actions.append('Stamp _migration_version: 1.')
        return actions

    def execute(self, fingerprint, project_root, auto_approve=False):
        era = fingerprint.get('era', '')
        config_path = os.path.join(project_root, '.purlin', 'config.json')
        config = _read_json(config_path) or {}
        agents = config.get('agents', {})

        if era == 'unified-partial':
            # Repair: complete the purlin agent config
            purlin_agent = agents.get('purlin', {})
            purlin_agent.setdefault('find_work', True)
            purlin_agent.setdefault('auto_start', False)
            purlin_agent.setdefault('default_mode', None)
            purlin_agent.setdefault('bypass_permissions', True)
            agents['purlin'] = purlin_agent
        else:
            # Full consolidation: merge role configs into agents.purlin
            purlin_agent = agents.get('purlin', {})
            # Inherit model from architect if not set
            for role in ('architect', 'builder'):
                if role in agents and isinstance(agents[role], dict):
                    if 'model' not in purlin_agent and 'model' in agents[role]:
                        purlin_agent['model'] = agents[role]['model']
                    break
            purlin_agent.setdefault('effort', 'high')
            purlin_agent.setdefault('bypass_permissions', True)
            purlin_agent.setdefault('find_work', True)
            purlin_agent.setdefault('auto_start', False)
            purlin_agent.setdefault('default_mode', None)
            agents['purlin'] = purlin_agent

        # Remove deprecated agent entries
        for role in ('architect', 'builder', 'qa', 'pm'):
            agents.pop(role, None)

        config['agents'] = agents

        # Clean old role-specific launchers
        for pattern in ['pl-run-*.sh', 'run_*.sh', 'pl-cdd-*.sh']:
            for path in glob_mod.glob(os.path.join(project_root, pattern)):
                os.remove(path)

        # Write config and stamp
        config['_migration_version'] = self.step_id
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
            f.write('\n')

        return True


class Step2SubmoduleToPlugin(MigrationStep):
    """Step 2: Unified submodule -> Plugin."""

    step_id = 2
    name = 'Submodule to Plugin'
    from_era = 'unified'
    to_era = 'plugin'

    def preconditions(self, fingerprint, project_root):
        if fingerprint.get('model') != 'submodule':
            return False, 'Not a submodule project.'
        mv = fingerprint.get('migration_version')
        if mv is not None and mv >= self.step_id:
            return False, f'Already at migration_version {mv}.'
        if mv is None or mv < 1:
            return False, 'Step 1 (Unified Agent Model) must complete first.'
        if self._has_uncommitted_changes(project_root):
            return False, 'Commit or stash changes before updating.'
        return True, ''

    def plan(self, fingerprint, project_root):
        submodule_path = fingerprint.get('submodule_path', 'purlin')
        return [
            'Create pre-upgrade safety commit.',
            f'Remove submodule at {submodule_path}/.',
            'Delete stale artifacts: pl-run.sh, .claude/commands/pl-*.md, '
            '.claude/agents/*.md, .purlin/.upstream_sha.',
            'Declare plugin in .claude/settings.json.',
            'Migrate config: remove tools_root, models, deprecated agents.',
            'Update CLAUDE.md with plugin template.',
            'Update .gitignore with plugin patterns.',
            'Remove old hooks from settings.',
            'Stamp _migration_version: 2.',
        ]

    def execute(self, fingerprint, project_root, auto_approve=False):
        submodule_path = fingerprint.get('submodule_path', 'purlin')

        # Safety commit
        try:
            subprocess.run(
                ['git', 'add', '-A'], cwd=project_root,
                capture_output=True, timeout=10
            )
            subprocess.run(
                ['git', 'commit', '-m', 'chore(purlin): pre-upgrade snapshot',
                 '--allow-empty'],
                cwd=project_root, capture_output=True, timeout=10
            )
        except subprocess.SubprocessError:
            pass

        # Remove submodule
        sub_full = os.path.join(project_root, submodule_path)
        try:
            subprocess.run(
                ['git', 'submodule', 'deinit', '-f', submodule_path],
                cwd=project_root, capture_output=True, timeout=30
            )
            subprocess.run(
                ['git', 'rm', '-f', submodule_path],
                cwd=project_root, capture_output=True, timeout=30
            )
            git_modules = os.path.join(project_root, '.git', 'modules', submodule_path)
            if os.path.isdir(git_modules):
                shutil.rmtree(git_modules, ignore_errors=True)
            # Remove .gitmodules if empty
            gitmodules = os.path.join(project_root, '.gitmodules')
            if os.path.isfile(gitmodules):
                with open(gitmodules, encoding='utf-8') as f:
                    if not f.read().strip():
                        subprocess.run(
                            ['git', 'rm', '-f', '.gitmodules'],
                            cwd=project_root, capture_output=True, timeout=10
                        )
        except subprocess.SubprocessError as e:
            return False

        # Clean stale artifacts
        stale_files = [
            os.path.join(project_root, 'pl-run.sh'),
            os.path.join(project_root, 'pl-init.sh'),
            os.path.join(project_root, '.purlin', '.upstream_sha'),
        ]
        for f in stale_files:
            if os.path.exists(f):
                os.remove(f)
        for pattern in ['.claude/commands/pl-*.md', '.claude/agents/*.md']:
            for f in glob_mod.glob(os.path.join(project_root, pattern)):
                os.remove(f)

        # Declare plugin in settings
        settings_path = os.path.join(project_root, '.claude', 'settings.json')
        settings = _read_json(settings_path) or {}
        settings.setdefault('extraKnownMarketplaces', {})
        settings['extraKnownMarketplaces']['purlin'] = {
            'source': 'settings',
            'plugins': [{
                'name': 'purlin',
                'source': {'source': 'github', 'repo': 'rlabarca/purlin'}
            }]
        }
        settings.setdefault('enabledPlugins', {})
        settings['enabledPlugins']['purlin@purlin'] = True
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
            f.write('\n')

        # Migrate config
        config_path = os.path.join(project_root, '.purlin', 'config.json')
        config = _read_json(config_path) or {}
        config.pop('tools_root', None)
        config.pop('models', None)
        agents = config.get('agents', {})
        for role in ('architect', 'builder', 'qa', 'pm'):
            agents.pop(role, None)
        if agents:
            config['agents'] = agents
        config['_migration_version'] = self.step_id
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
            f.write('\n')

        # Commit
        try:
            subprocess.run(
                ['git', 'add', '-A'], cwd=project_root,
                capture_output=True, timeout=10
            )
            subprocess.run(
                ['git', 'commit', '-m',
                 'chore(purlin): migrate from submodule to plugin distribution'],
                cwd=project_root, capture_output=True, timeout=10
            )
        except subprocess.SubprocessError:
            pass

        return True


class Step3PluginRefresh(MigrationStep):
    """Step 3: Plugin -> Current."""

    step_id = 3
    name = 'Plugin Refresh'
    from_era = 'plugin'
    to_era = 'current'

    def preconditions(self, fingerprint, project_root):
        model = fingerprint.get('model')
        if model not in ('plugin', 'fresh'):
            return False, f'Expected plugin or fresh model, got {model}.'
        mv = fingerprint.get('migration_version')
        if mv is not None and mv >= self.step_id:
            return False, f'Already at migration_version {mv}.'
        return True, ''

    def plan(self, fingerprint, project_root):
        actions = [
            'Sync config: add missing keys from plugin template.',
            'Check for stale pre-plugin artifacts and clean up.',
            'Stamp _migration_version: 3.',
        ]
        return actions

    def execute(self, fingerprint, project_root, auto_approve=False):
        config_path = os.path.join(project_root, '.purlin', 'config.json')
        config = _read_json(config_path) or {}

        # Clean any leftover pre-plugin artifacts
        stale = [
            os.path.join(project_root, 'pl-run.sh'),
            os.path.join(project_root, 'pl-init.sh'),
            os.path.join(project_root, '.purlin', '.upstream_sha'),
        ]
        for f in stale:
            if os.path.exists(f):
                os.remove(f)

        # Stamp version
        self._stamp_version(project_root)
        return True


# Registry: ordered list of all migration steps.
STEPS = [
    Step1UnifiedAgentModel(),
    Step2SubmoduleToPlugin(),
    Step3PluginRefresh(),
]


def compute_path(fingerprint, target_migration_version=None):
    """Compute the ordered list of migration steps needed.

    Args:
        fingerprint: Version fingerprint from detect_version().
        target_migration_version: Target version (default: CURRENT_MIGRATION_VERSION).

    Returns:
        list[MigrationStep]: Steps to execute, in order.
    """
    if target_migration_version is None:
        target_migration_version = CURRENT_MIGRATION_VERSION

    current_mv = fingerprint.get('migration_version') or 0
    model = fingerprint.get('model')
    era = fingerprint.get('era')

    # Special cases
    if model == 'none':
        return []
    if model == 'fresh' and current_mv == 0:
        # Fresh project with no migration history — needs init, not update
        return []

    # Filter steps: those with step_id > current and <= target
    path = [
        step for step in STEPS
        if step.step_id > current_mv and step.step_id <= target_migration_version
    ]

    return path


def format_plan(steps, fingerprint, project_root):
    """Format a human-readable plan from computed steps."""
    if not steps:
        return 'Already up to date.'

    lines = []
    for step in steps:
        lines.append(f'Step {step.step_id}: {step.name}')
        for action in step.plan(fingerprint, project_root):
            lines.append(f'  - {action}')
    return '\n'.join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Compute and optionally execute the Purlin migration path.')
    parser.add_argument('--project-root', required=True,
                        help='Path to the consumer project root')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show migration plan without executing')
    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)
    fingerprint = detect_version(project_root)

    print(f'Detected: model={fingerprint["model"]}, '
          f'era={fingerprint["era"]}, '
          f'migration_version={fingerprint["migration_version"]}')
    print()

    model = fingerprint['model']
    if model == 'none':
        print('Not a Purlin project. Run purlin:init to set up.')
        sys.exit(1)
    if model == 'fresh' and not fingerprint.get('migration_version'):
        print('Fresh project detected. Run purlin:init first.')
        sys.exit(1)

    steps = compute_path(fingerprint)
    plan_text = format_plan(steps, fingerprint, project_root)
    print(plan_text)

    if args.dry_run or not steps:
        sys.exit(0)

    # Execute
    for step in steps:
        ok, reason = step.preconditions(fingerprint, project_root)
        if not ok:
            print(f'\nStep {step.step_id} ({step.name}) blocked: {reason}')
            sys.exit(1)
        print(f'\nExecuting step {step.step_id}: {step.name}...')
        success = step.execute(fingerprint, project_root)
        if not success:
            print(f'Step {step.step_id} failed.')
            sys.exit(1)
        print(f'Step {step.step_id} complete.')
        # Re-detect for next step
        fingerprint = detect_version(project_root)

    print('\nMigration complete.')


if __name__ == '__main__':
    main()
