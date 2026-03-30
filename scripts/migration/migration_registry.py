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
import re
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from version_detector import detect_version, _read_json


# Current migration version — the target for all migrations.
CURRENT_MIGRATION_VERSION = 5


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
        """Write _migration_version to consumer config.

        Stamps BOTH config.json and config.local.json (if it exists).
        The version detector reads config.local.json first, so if we
        only stamp config.json, re-detection between steps sees a stale
        version and steps 4/5 think step 3 hasn't completed yet.
        """
        for filename in ('config.json', 'config.local.json'):
            config_path = os.path.join(project_root, '.purlin', filename)
            if filename == 'config.local.json' and not os.path.isfile(config_path):
                continue  # Only stamp config.local.json if it already exists
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


def _remove_stale_submodule(project_root):
    """Remove a lingering purlin submodule if present. Returns True if cleaned."""
    from version_detector import _gitmodules_has_purlin

    submodule_path = _gitmodules_has_purlin(project_root)
    if not submodule_path:
        return False

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
    except subprocess.SubprocessError:
        return False

    return True


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
        if not _remove_stale_submodule(project_root):
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
        from version_detector import _gitmodules_has_purlin

        actions = []
        if _gitmodules_has_purlin(project_root):
            actions.append('Remove stale purlin submodule.')
        actions.extend([
            'Sync config: add missing keys from plugin template.',
            'Check for stale pre-plugin artifacts and clean up.',
            'Stamp _migration_version: 3.',
        ])
        return actions

    def execute(self, fingerprint, project_root, auto_approve=False):
        # Remove stale submodule if plugin was installed while submodule still exists
        _remove_stale_submodule(project_root)

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


def _find_features_with_figma(project_root):
    """Find ANY feature files that reference Figma (design_*.md OR regular specs).

    Old Purlin versions (<=0.8.5) put Figma references directly in feature
    specs instead of design anchors. This function scans ALL .md files in
    features/ so the migration can extract Figma references into i_design_*
    invariants regardless of where they were placed.

    Returns list of (filepath, figma_ref, invariant_stem) tuples.
    The invariant_stem is used for the output filename: i_design_{stem}.md.
    For design_*.md files, stem is the part after 'design_'.
    For regular feature files, stem is the feature name.
    """
    features_dir = os.path.join(project_root, 'features')
    if not os.path.isdir(features_dir):
        return []

    # Full Figma URL patterns
    metadata_url_re = re.compile(
        r'>\s*Figma-URL:\s*(https?://(?:www\.)?figma\.com/[^\s>]+)'
    )
    link_re = re.compile(
        r'\[(?:[^\]]*)\]\((https?://(?:www\.)?figma\.com/[^)]+)\)'
    )
    # Figma file key patterns (no full URL, just the key)
    figma_key_re = re.compile(
        r'>\s*\*{0,2}Figma[- ](?:File|Node):?\*{0,2}\s*([A-Za-z0-9_:-]{5,})'
    )
    results = []

    for dirpath, _dirnames, filenames in os.walk(features_dir):
        # Skip _invariants (already converted), _tombstones, system folders
        rel_dir = os.path.relpath(dirpath, features_dir)
        if rel_dir.startswith('_'):
            continue

        for fname in filenames:
            if not fname.endswith('.md'):
                continue
            if fname.endswith('.impl.md') or fname.endswith('.discoveries.md'):
                continue
            # Skip existing invariants
            if fname.startswith('i_'):
                continue

            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, encoding='utf-8') as f:
                    content = f.read()
            except OSError:
                continue

            figma_ref = None

            # Try full URL first
            match = metadata_url_re.search(content)
            if not match:
                match = link_re.search(content)
            if match:
                figma_ref = match.group(1).rstrip('.,;:"\'>)')

            # Try file key in metadata
            if not figma_ref:
                match = figma_key_re.search(content)
                if match:
                    figma_ref = f'figma:file:{match.group(1)}'

            # Check for companion brief.json with figma_file_key
            if not figma_ref:
                stem_for_brief = fname[:-len('.md')]
                if stem_for_brief.startswith('design_'):
                    stem_for_brief = stem_for_brief[len('design_'):]
                brief_path = os.path.join(
                    features_dir, 'design', stem_for_brief, 'brief.json'
                )
                if os.path.isfile(brief_path):
                    try:
                        with open(brief_path, encoding='utf-8') as bf:
                            brief = json.loads(bf.read())
                        fkey = brief.get('figma_file_key')
                        if fkey:
                            figma_ref = f'figma:file:{fkey}'
                    except (OSError, json.JSONDecodeError):
                        pass

            if figma_ref:
                # Derive invariant stem
                if fname.startswith('design_'):
                    stem = fname[len('design_'):-len('.md')]
                else:
                    stem = fname[:-len('.md')]
                results.append((fpath, figma_ref, stem))

    return results


def _count_prerequisite_refs(project_root, anchor_filepath):
    """Count how many OTHER feature files reference this anchor in Prerequisite metadata."""
    features_dir = os.path.join(project_root, 'features')
    anchor_filename = os.path.basename(anchor_filepath)
    prereq_re = re.compile(
        r'>\s*Prerequisite:.*' + re.escape(anchor_filename)
    )
    count = 0
    for dirpath, _dirnames, filenames in os.walk(features_dir):
        for fname in filenames:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(dirpath, fname)
            if os.path.abspath(fpath) == os.path.abspath(anchor_filepath):
                continue
            try:
                with open(fpath, encoding='utf-8') as f:
                    for line in f:
                        if prereq_re.search(line):
                            count += 1
                            break
            except OSError:
                continue
    return count


class Step4DesignToInvariant(MigrationStep):
    """Step 4: Extract Figma references from any feature file into i_design_* invariants.

    Old Purlin versions (<=0.8.5) put Figma references directly in feature
    specs. This step scans ALL feature .md files, creates i_design_* invariants
    for each Figma reference found, and updates the source file:
    - design_*.md files: converted to invariant, original deleted.
    - Regular feature files: Figma metadata removed, prerequisite reference
      to the new invariant added. The feature file is preserved.
    """

    step_id = 4
    name = 'Figma to Design Invariant'
    from_era = 'current'
    to_era = 'current'

    def preconditions(self, fingerprint, project_root):
        mv = fingerprint.get('migration_version')
        if mv is not None and mv >= self.step_id:
            return False, f'Already at migration_version {mv}.'
        if mv is None or mv < 3:
            return False, 'Step 3 (Plugin Refresh) must complete first.'
        return True, ''

    def plan(self, fingerprint, project_root):
        anchors = _find_features_with_figma(project_root)
        if not anchors:
            return [
                'No feature files with Figma references found.',
                'Stamp _migration_version: 4.',
            ]

        actions = []
        for fpath, figma_ref, stem in anchors:
            rel = os.path.relpath(fpath, project_root)
            fname = os.path.basename(fpath)
            is_design = fname.startswith('design_')
            if is_design:
                actions.append(
                    f'Convert {rel} → features/_invariants/i_design_{stem}.md '
                    f'(delete original)'
                )
            else:
                actions.append(
                    f'Extract Figma from {rel} → features/_invariants/i_design_{stem}.md '
                    f'(add prerequisite to feature, keep feature file)'
                )
        actions.append('Update prerequisite references in dependent features.')
        actions.append('Stamp _migration_version: 4.')
        return actions

    def execute(self, fingerprint, project_root, auto_approve=False):
        anchors = _find_features_with_figma(project_root)

        if not anchors:
            self._stamp_version(project_root)
            return True

        features_dir = os.path.join(project_root, 'features')
        invariants_dir = os.path.join(features_dir, '_invariants')
        os.makedirs(invariants_dir, exist_ok=True)

        now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        converted = []

        # Regex to strip Figma metadata lines from feature files
        figma_line_re = re.compile(
            r'^\s*>\s*\*{0,2}(?:Figma[- ](?:File|Node|URL)|Figma-URL):?\*{0,2}\s*.*$'
        )
        ref_line_re = re.compile(
            r'^(>\s*(?:Prerequisite|[*]*Design Anchor[*]*):\s*)'
        )

        for fpath, figma_ref, stem in anchors:
            old_filename = os.path.basename(fpath)
            is_design = old_filename.startswith('design_')

            ref_count = _count_prerequisite_refs(project_root, fpath)
            scope = 'global' if ref_count >= 3 else 'scoped'

            category = 'Design'
            try:
                with open(fpath, encoding='utf-8') as f:
                    for line in f:
                        cat_match = re.match(r'>\s*Category:\s*"?([^"\n]+)"?', line)
                        if cat_match:
                            category = cat_match.group(1).strip()
                            break
            except OSError:
                pass

            display_name = stem.replace('_', ' ').title()

            invariant_content = (
                f'# Design: {display_name}\n'
                f'\n'
                f'> Label: "Design: {display_name}"\n'
                f'> Category: "{category}"\n'
                f'> Format-Version: 1.0\n'
                f'> Invariant: true\n'
                f'> Version: pending-sync\n'
                f'> Source: figma\n'
                f'> Figma-URL: {figma_ref}\n'
                f'> Synced-At: {now_iso}\n'
                f'> Scope: {scope}\n'
                f'\n'
                f'## Purpose\n'
                f'\n'
                f'Migrated from `{old_filename}`. Run `purlin:invariant sync` '
                f'to fetch Figma metadata and update this section.\n'
                f'\n'
                f'## Figma Source\n'
                f'\n'
                f'This invariant is governed by the Figma document linked above.\n'
                f'Design tokens, constraints, and visual standards are defined in Figma\n'
                f'and cached locally in per-feature `brief.json` files during spec authoring.\n'
                f'\n'
                f'## Annotations\n'
                f'\n'
                f'- *(Run `purlin:invariant sync` to extract annotations from Figma)*\n'
            )

            invariant_path = os.path.join(invariants_dir, f'i_design_{stem}.md')
            with open(invariant_path, 'w', encoding='utf-8') as f:
                f.write(invariant_content)

            new_filename = f'i_design_{stem}.md'

            if is_design:
                # design_*.md: update references in other files, then delete
                old_rel = os.path.relpath(fpath, features_dir)
                new_rel = os.path.relpath(invariant_path, features_dir)
                old_forms = [old_filename, old_rel, f'features/{old_rel}']
                new_forms = [new_filename, new_rel, f'features/{new_rel}']

                for dp, _dn, fns in os.walk(features_dir):
                    for fn in fns:
                        if not fn.endswith('.md'):
                            continue
                        rp = os.path.join(dp, fn)
                        if os.path.abspath(rp) in (
                            os.path.abspath(fpath),
                            os.path.abspath(invariant_path),
                        ):
                            continue
                        try:
                            with open(rp, encoding='utf-8') as f:
                                content = f.read()
                        except OSError:
                            continue
                        if old_filename not in content:
                            continue
                        lines = content.split('\n')
                        changed = False
                        for i, line in enumerate(lines):
                            if not ref_line_re.match(line):
                                continue
                            new_line = line
                            for of, nf in zip(old_forms, new_forms):
                                if of in new_line:
                                    new_line = new_line.replace(of, nf)
                            if new_line != line:
                                lines[i] = new_line
                                changed = True
                        if changed:
                            with open(rp, 'w', encoding='utf-8') as f:
                                f.write('\n'.join(lines))

                os.remove(fpath)
            else:
                # Regular feature file: strip Figma metadata lines, add
                # prerequisite reference to the new invariant. Keep the file.
                try:
                    with open(fpath, encoding='utf-8') as f:
                        lines = f.read().split('\n')
                except OSError:
                    continue

                # Remove Figma metadata lines
                cleaned = [l for l in lines if not figma_line_re.match(l)]

                # Add prerequisite to invariant if not already present
                invariant_ref = f'_invariants/{new_filename}'
                if invariant_ref not in '\n'.join(cleaned):
                    # Insert after existing metadata block (lines starting with >)
                    insert_idx = 0
                    for i, line in enumerate(cleaned):
                        if line.startswith('>'):
                            insert_idx = i + 1
                    cleaned.insert(insert_idx,
                                   f'> Prerequisite: {invariant_ref}')

                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(cleaned))

            converted.append(f'i_design_{stem}.md')

        try:
            subprocess.run(
                ['git', 'add', '-A'], cwd=project_root,
                capture_output=True, timeout=10
            )
            names = ', '.join(converted)
            subprocess.run(
                ['git', 'commit', '-m',
                 f'chore(purlin): extract Figma references to design invariants ({names})'],
                cwd=project_root, capture_output=True, timeout=10
            )
        except subprocess.SubprocessError:
            pass

        self._stamp_version(project_root)
        return True


_TIER_ROW_RE = re.compile(r'^\|\s*(\S+)\s*\|\s*(\S+)\s*\|$')

# Template boilerplate section headers to strip
_TEMPLATE_SECTIONS = {
    '## General (all modes)',
    '## Engineer Mode',
    '## PM Mode',
    '## QA Mode',
    '# Purlin Agent Overrides',
}


class Step5RemoveOverrides(MigrationStep):
    """Step 5: Remove PURLIN_OVERRIDES.md system, migrate tiers to config.json."""

    step_id = 5
    name = 'Remove Override System'
    from_era = 'current'
    to_era = 'current'

    def preconditions(self, fingerprint, project_root):
        mv = fingerprint.get('migration_version')
        if mv is not None and mv >= self.step_id:
            return False, f'Already at migration_version {mv}.'
        if mv is None or mv < 4:
            return False, 'Step 4 (Design Anchor to Invariant) must complete first.'
        return True, ''

    def plan(self, fingerprint, project_root):
        purlin_dir = os.path.join(project_root, '.purlin')
        actions = []

        for filename in ('PURLIN_OVERRIDES.md', 'QA_OVERRIDES.md'):
            if os.path.exists(os.path.join(purlin_dir, filename)):
                actions.append(f'Parse Test Priority Tiers from {filename} → config.json.')
                actions.append(f'Migrate meaningful content from {filename} → CLAUDE.md.')
                actions.append(f'Delete {filename}.')

        if not actions:
            actions.append('No override files found.')

        actions.append('Stamp _migration_version: 5.')
        return actions

    def _parse_tiers(self, content):
        """Extract tier table from markdown content."""
        tiers = {}
        in_table = False
        for line in content.splitlines():
            if '## Test Priority Tiers' in line:
                in_table = True
                continue
            if in_table:
                if line.startswith('## ') and 'Test Priority Tiers' not in line:
                    break
                m = _TIER_ROW_RE.match(line.strip())
                if m:
                    feature, tier = m.group(1), m.group(2)
                    if feature.lower() not in ('feature', '---', '---------'):
                        tiers[feature] = tier
        return tiers

    # Submodule-era boilerplate patterns to strip entirely
    _OBSOLETE_KEYWORDS = [
        'submodule', 'read-only', 'Read-Only', 'READ-ONLY',
        'HARD PROHIBITION', 'hard prohibition',
        'pl-run.sh', 'pl-init.sh', 'purlin/',
        'Do not modify anything inside purlin/',
        'Do not write to purlin/',
        'never modify the purlin directory',
    ]

    def _strip_boilerplate(self, content):
        """Strip tier table, template boilerplate, HTML comments, and
        submodule-era content that is no longer relevant.

        Returns remaining meaningful content or empty string.
        """
        lines = content.splitlines()
        result = []
        in_tier_table = False
        in_skip_section = False
        skip_next_blank = False

        for line in lines:
            stripped = line.strip()

            # Skip tier table section
            if '## Test Priority Tiers' in line:
                in_tier_table = True
                skip_next_blank = True
                continue
            if in_tier_table:
                if stripped.startswith('## ') and 'Test Priority Tiers' not in stripped:
                    in_tier_table = False
                else:
                    continue

            # Skip sections with obsolete submodule-era headings
            if stripped.startswith('#') and any(kw in stripped for kw in
                    ['Read-Only', 'READ-ONLY', 'Submodule', 'PROHIBITION']):
                in_skip_section = True
                skip_next_blank = True
                continue
            if in_skip_section:
                if stripped.startswith('#') and not any(kw in stripped for kw in
                        ['Read-Only', 'READ-ONLY', 'Submodule', 'PROHIBITION']):
                    in_skip_section = False
                else:
                    continue

            # Skip HTML comments
            if stripped.startswith('<!--') and stripped.endswith('-->'):
                continue

            # Skip template section headers
            if stripped in _TEMPLATE_SECTIONS:
                skip_next_blank = True
                continue

            # Skip blockquote boilerplate (template instructions)
            if stripped.startswith('>') and any(kw in stripped for kw in
                    ['Project-specific rules', 'Project-wide context',
                     'Build commands', 'Domain context', 'Test tiers']):
                continue

            # Skip individual lines with submodule-era keywords
            if any(kw in line for kw in self._OBSOLETE_KEYWORDS):
                continue

            if skip_next_blank and not stripped:
                skip_next_blank = False
                continue
            skip_next_blank = False

            result.append(line)

        # Trim leading/trailing blank lines
        while result and not result[0].strip():
            result.pop(0)
        while result and not result[-1].strip():
            result.pop()

        return '\n'.join(result)

    def execute(self, fingerprint, project_root, auto_approve=False):
        purlin_dir = os.path.join(project_root, '.purlin')
        config_path = os.path.join(purlin_dir, 'config.json')
        config = _read_json(config_path) or {}
        all_tiers = config.get('test_priority_tiers', {})
        migrated_content = []

        for filename in ('PURLIN_OVERRIDES.md', 'QA_OVERRIDES.md'):
            filepath = os.path.join(purlin_dir, filename)
            if not os.path.exists(filepath):
                continue

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (IOError, OSError):
                continue

            # Parse tiers
            tiers = self._parse_tiers(content)
            all_tiers.update(tiers)

            # Strip boilerplate and check for meaningful content
            remaining = self._strip_boilerplate(content)
            if remaining.strip():
                migrated_content.append(remaining)

            # Delete the override file
            os.remove(filepath)

        # Write tiers to config
        if all_tiers:
            config['test_priority_tiers'] = all_tiers
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
                f.write('\n')

        # Append meaningful content to CLAUDE.md
        if migrated_content:
            claude_md = os.path.join(project_root, 'CLAUDE.md')
            existing = ''
            if os.path.exists(claude_md):
                with open(claude_md, 'r', encoding='utf-8') as f:
                    existing = f.read()

            section = '\n\n## Project Rules (migrated from Purlin overrides)\n\n'
            section += '\n\n'.join(migrated_content) + '\n'

            with open(claude_md, 'w', encoding='utf-8') as f:
                f.write(existing.rstrip() + section)

        self._stamp_version(project_root)
        return True


# Registry: ordered list of all migration steps.
STEPS = [
    Step1UnifiedAgentModel(),
    Step2SubmoduleToPlugin(),
    Step3PluginRefresh(),
    Step4DesignToInvariant(),
    Step5RemoveOverrides(),
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

    # Execute — skip steps whose preconditions fail (e.g. submodule steps
    # on a plugin project), re-detect fingerprint after each successful step
    # so later steps see updated state (e.g. Step 4 sees migration_version: 3
    # after Step 3 completes).
    executed = 0
    for step in steps:
        ok, reason = step.preconditions(fingerprint, project_root)
        if not ok:
            print(f'\nStep {step.step_id} ({step.name}) skipped: {reason}')
            continue
        print(f'\nExecuting step {step.step_id}: {step.name}...')
        success = step.execute(fingerprint, project_root)
        if not success:
            print(f'Step {step.step_id} failed.')
            sys.exit(1)
        print(f'Step {step.step_id} complete.')
        executed += 1
        # Re-detect for next step
        fingerprint = detect_version(project_root)

    if executed == 0:
        print('\nAlready up to date.')
    else:
        print(f'\nMigration complete. ({executed} step(s) executed)')

    print('\nMigration complete.')


if __name__ == '__main__':
    main()
