#!/usr/bin/env python3
"""Mechanical migrations for a project initialized by an older Purlin plugin.

    python3 scripts/update/migrate.py --check [--project-root DIR]
    python3 scripts/update/migrate.py --apply <id> [<id> ...] [--project-root DIR]
                                      [--platform-id ID] [--mutation-checks on|off]

`purlin:init --update` is the user-facing command; this script is the part of it
that must be deterministic and provable, so the skill asks and this script edits.
Detection lives in the MCP server (`_pending_migrations`), so the advisory
`sync_status` prints and the list this script acts on cannot disagree.

WHAT --check DOES
    Prints the pending list as JSON on stdout and writes nothing, ever.

EXIT CODES  (aligned with scripts/ci/verify_gate.py and dev/bump_version.sh)
    0  nothing blocking is pending
    1  a blocking migration is pending
    2  bad invocation: unreadable project, unknown id, no action given

    Blocking means a migration whose presence makes the evidence a test run is
    about to write unreliable: every `legacy-*` id, because the legacy alias
    makes coverage a guess, and `plugin-copies-stale`, because plugin copies
    that predate platform scoping write agnostic proof files from a platform
    runner, which satisfies nothing while the job goes green. The other two are
    reported in the JSON and do not fail the check: a config field is filled
    without touching evidence, and a version 1 receipt is a claim that
    `purlin:verify` re-issues from a fresh run. A preflight that failed on those
    would block the CI of every project that has not verified since the vhash
    formula changed, which is a different problem than the one it guards.

WHAT --apply DOES, AND WHAT IT REFUSES TO DO
    It performs the five mechanical rewrites: the spec tag, the proof-file
    rename, the proof markers, the plugin copies and the config fields. It never
    writes a proof entry and never writes a receipt. A proof entry is a claim
    that a test ran and a receipt is a claim that a suite passed; renaming a file
    through `git mv` moves an existing record and keeps its history, which is not
    the same act. `receipt-v1` and `legacy-mcp` print a directive and change
    nothing: `purlin:verify` re-issues receipts from a fresh run, and
    `purlin:init --mcp` owns the MCP entry.

    `mutation_checks` is the one config field that is asked rather than
    backfilled (`references/spec_quality_guide.md`, "Mutation check"): it costs
    the project roughly twice the tokens and minutes per proof, so writing a
    default on the user's behalf is deciding for them. Without
    `--mutation-checks on|off` the field is left absent and the flag is named.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

EXIT_OK = 0
EXIT_PENDING = 1
EXIT_BAD_INVOCATION = 2

# Reported by --check, not a reason to fail it. See the module docstring.
_NON_BLOCKING = ('config-fields-missing', 'receipt-v1')


def _server():
    """The MCP server module, imported by path like scripts/ci/verify_gate.py.

    CI checks the repository out; it does not pip-install it.
    """
    server_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mcp')
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)
    import purlin_server
    return purlin_server


def _plugin_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git(root, *args):
    """Run a git command in `root`; returns (ok, output)."""
    try:
        result = subprocess.run(['git'] + list(args), cwd=root,
                                capture_output=True, text=True)
    except (FileNotFoundError, OSError) as exc:
        return False, str(exc)
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _write(path, text):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


# ── The five mechanical rewrites ──────────────────────────────────────

_LEGACY_TAG_RE = re.compile(
    r'(?m)^(-[ \t]+PROOF-\d+[ \t]*\(RULE-\d+(?:,[ \t]*RULE-\d+)*\):.*?)'
    r'[ \t]+@windows[ \t]*$')


def _apply_legacy_tier_windows(ps, root, platform_id, actions):
    """`@windows` on a proof line becomes `@unit @on(<platform-id>)`."""
    for entry in _pending_by_id(ps, root, 'legacy-tier-windows'):
        for rel in entry['files']:
            path = os.path.join(root, rel)
            text = _read(path)
            new_text, count = _LEGACY_TAG_RE.subn(
                lambda m: f'{m.group(1)} @unit @on({platform_id})', text)
            if count:
                _write(path, new_text)
                actions.append(f'rewrote {count} proof tag'
                               f'{"s" if count != 1 else ""} in {rel} '
                               f'to @unit @on({platform_id})')


def _apply_legacy_proof_file(ps, root, platform_id, actions):
    """`<f>.proofs-windows.json` becomes `<f>.proofs-unit@<id>.json`.

    `git mv` rather than write-and-delete: the file's entries are an existing
    record of a run that happened, and its history is the only provenance the
    report has for it.
    """
    for entry in _pending_by_id(ps, root, 'legacy-proof-file'):
        for rel in entry['files']:
            old_path = os.path.join(root, rel)
            base = os.path.basename(rel)
            parts = ps._proof_file_parts(base)
            if parts is None:
                continue
            stem, tier = parts[0], parts[1]
            new_rel = os.path.join(os.path.dirname(rel),
                                   f'{stem}.proofs-{tier}@{platform_id}.json')
            new_rel = new_rel.replace(os.sep, '/')
            new_path = os.path.join(root, new_rel)
            moved, output = _git(root, 'mv', rel, new_rel)
            if not moved:
                os.rename(old_path, new_path)
                actions.append(f'renamed {rel} to {new_rel} without git '
                               f'(git mv said: {output or "unavailable"})')
            else:
                actions.append(f'git mv {rel} {new_rel}')
            try:
                data = json.loads(_read(new_path))
            except json.JSONDecodeError:
                continue
            payload = {'tier': tier, 'platform': platform_id}
            proofs = []
            for proof in data.get('proofs', []):
                proof['tier'] = tier
                proof['platform'] = platform_id
                proofs.append(proof)
            payload['proofs'] = proofs
            _write(new_path, json.dumps(payload, indent=2) + '\n')
            actions.append(f'stamped platform "{platform_id}" on {new_rel} '
                           f'and its {len(proofs)} entr'
                           f'{"ies" if len(proofs) != 1 else "y"}')


def _marker_replacement(label, platform_id):
    """The per-syntax rewrite for one legacy `windows`-tier proof marker."""
    if label == 'pytest':
        return lambda m: (f'{m.group(1)}{m.group(2)}unit{m.group(2)}, '
                          f'platforms=({m.group(2)}{platform_id}{m.group(2)},)')
    if label == 'jest/vitest':
        return lambda m: f'{m.group(1)}:unit:on({platform_id})]'
    if label == 'shell':
        return lambda m: (f'PURLIN_PROOF_TIER={m.group(1)}unit{m.group(1)} '
                          f'PURLIN_PROOF_PLATFORMS={m.group(1)}{platform_id}'
                          f'{m.group(1)}')
    if label == 'c':
        return lambda m: (f'purlin_proof_on({m.group(1)}"unit", '
                          f'"{platform_id}")')
    if label in ('phpunit', 'sql'):
        return lambda m: f'{m.group(1)} unit on({platform_id})'
    if label == 'xunit':
        return lambda m: f'{m.group(1)}:unit:on({platform_id})"'
    raise KeyError(label)


def _apply_legacy_marker(ps, root, platform_id, actions):
    """Every plugin's `windows`-tier marker becomes tier `unit` plus `on(<id>)`."""
    by_file = {}
    for rel, label, count in ps._legacy_marker_hits(root):
        by_file.setdefault(rel, []).append((label, count))
    for rel in sorted(by_file):
        path = os.path.join(root, rel)
        text = _read(path)
        total = 0
        for label, _count in by_file[rel]:
            pattern = dict((lbl, pat) for lbl, _ext, pat
                           in ps._LEGACY_MARKER_SYNTAXES)[label]
            text, count = pattern.subn(_marker_replacement(label, platform_id),
                                       text)
            total += count
        if total:
            _write(path, text)
            actions.append(f'rewrote {total} marker{"s" if total != 1 else ""} '
                           f'in {rel} to tier unit with on({platform_id})')


def _apply_plugin_copies_stale(ps, root, _platform_id, actions):
    """Each `.purlin/plugins/` copy is replaced by the installed plugin's file."""
    source_dir = ps._plugin_source_dir()
    for rel in ps._stale_plugin_copies(root):
        name = os.path.basename(rel)
        shutil.copyfile(os.path.join(source_dir, name), os.path.join(root, rel))
        actions.append(f'copied scripts/proof/{name} over {rel}')


def _apply_config_fields_missing(ps, root, _platform_id, actions,
                                 mutation_checks=None):
    """Missing template fields are filled; `version` is stamped from VERSION."""
    path = os.path.join(root, '.purlin', 'config.json')
    try:
        config = json.loads(_read(path))
    except (json.JSONDecodeError, IOError, OSError):
        actions.append('.purlin/config.json is not readable JSON; left alone')
        return
    template = ps._template_config()
    filled = []
    for key in sorted(template):
        if key in config:
            continue
        if key in ps._ASKED_CONFIG_FIELDS:
            continue
        config[key] = template[key]
        filled.append(f'{key}={json.dumps(template[key])}')
    installed = ps._read_version()
    if config.get('version') != installed:
        config['version'] = installed
        filled.append(f'version={installed}')
    for key in ps._ASKED_CONFIG_FIELDS:
        if key in config:
            continue
        if mutation_checks is None:
            actions.append(f'{key} left absent: it is asked, not backfilled '
                           f'(re-run with --mutation-checks on|off)')
        else:
            config[key] = (mutation_checks == 'on')
            filled.append(f'{key}={json.dumps(config[key])}')
    if filled:
        _write(path, json.dumps(config, indent=2) + '\n')
        actions.append(f'filled .purlin/config.json: {", ".join(filled)}')


_APPLIERS = {
    'legacy-tier-windows': _apply_legacy_tier_windows,
    'legacy-proof-file': _apply_legacy_proof_file,
    'legacy-marker': _apply_legacy_marker,
    'plugin-copies-stale': _apply_plugin_copies_stale,
    'config-fields-missing': _apply_config_fields_missing,
}

_DIRECTIVES = {
    'receipt-v1': ('→ Run: purlin:verify  (a receipt is a claim that tests '
                   'ran; this script never writes one)'),
    'legacy-mcp': '→ Run: purlin:init --mcp (then /reload-plugins)',
}


def _pending_by_id(ps, root, migration_id):
    return [entry for entry in ps._pending_migrations(root)
            if entry['id'] == migration_id]


def _blocking(pending):
    return [entry for entry in pending if entry['id'] not in _NON_BLOCKING]


def check(ps, root):
    pending = ps._pending_migrations(root)
    print(json.dumps({'project_root': os.path.abspath(root),
                      'pending': pending}, indent=2))
    blocking = _blocking(pending)
    if blocking:
        ids = ', '.join(entry['id'] for entry in blocking)
        print(f'Blocking migrations pending: {ids}', file=sys.stderr)
        print('→ Run: purlin:init --update and commit', file=sys.stderr)
        return EXIT_PENDING
    return EXIT_OK


def apply(ps, root, ids, platform_id, mutation_checks):
    actions = []
    for migration_id in _MIGRATION_APPLY_ORDER:
        if migration_id not in ids:
            continue
        applier = _APPLIERS[migration_id]
        if migration_id == 'config-fields-missing':
            applier(ps, root, platform_id, actions,
                    mutation_checks=mutation_checks)
        else:
            applier(ps, root, platform_id, actions)
    for migration_id in ids:
        if migration_id in _DIRECTIVES:
            actions.append(_DIRECTIVES[migration_id])
    for line in actions:
        print(line)
    if not actions:
        print('nothing to do')
    return EXIT_OK


# Order matters: the spec tag is rewritten before the proof file is renamed, so
# a reader that runs between the two steps sees a declared platform with a file
# still to move rather than a file naming a platform no spec declares.
_MIGRATION_APPLY_ORDER = ('legacy-tier-windows', 'legacy-proof-file',
                          'legacy-marker', 'plugin-copies-stale',
                          'config-fields-missing')


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='migrate.py', add_help=True,
        description='Mechanical migrations for purlin:init --update')
    parser.add_argument('--check', action='store_true',
                        help='print the pending list as JSON; write nothing')
    parser.add_argument('--apply', nargs='+', metavar='ID',
                        help='apply the named migrations')
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--platform-id', default='windows',
                        help='what a legacy @windows tag becomes (default: windows)')
    parser.add_argument('--mutation-checks', choices=('on', 'off'), default=None,
                        help='answer the mutation_checks question during '
                             'config-fields-missing')
    args = parser.parse_args(argv)

    if bool(args.check) == bool(args.apply):
        print('give exactly one of --check or --apply <id> ...', file=sys.stderr)
        return EXIT_BAD_INVOCATION

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(os.path.join(root, '.purlin')):
        print(f'not a Purlin project (no .purlin/): {root}', file=sys.stderr)
        return EXIT_BAD_INVOCATION
    try:
        ps = _server()
    except ImportError as exc:
        print(f'cannot import the Purlin server: {exc}', file=sys.stderr)
        return EXIT_BAD_INVOCATION

    if args.check:
        return check(ps, root)

    unknown = [i for i in args.apply if i not in ps._MIGRATION_ORDER]
    if unknown:
        print(f'unknown migration id: {", ".join(unknown)}', file=sys.stderr)
        print(f'known ids: {", ".join(ps._MIGRATION_ORDER)}', file=sys.stderr)
        return EXIT_BAD_INVOCATION
    if not ps._PLATFORM_ID_RE.match(args.platform_id):
        print(f'platform id {args.platform_id!r} is not [a-z0-9][a-z0-9-]*',
              file=sys.stderr)
        return EXIT_BAD_INVOCATION
    return apply(ps, root, list(args.apply), args.platform_id,
                 args.mutation_checks)


if __name__ == '__main__':
    sys.exit(main())
