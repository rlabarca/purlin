#!/usr/bin/env python3
"""Anchors that come from an anchor repo: add, sync, propose.

An anchor repo holds anchors for one or more projects. A project keeps a local
copy of each anchor it consumes under `specs/_anchors/`, with two tracking
fields the copy carries and the author's file does not:

    > Source: https://github.com/acme/policies.git specs/no_eval.md
    > Pinned: abc1234def5678

A pin is always a commit, never a branch. `references/formats/anchor_format.md`
is the contract for both fields. This module writes them and parses nothing
itself: `purlin.specs` reads every spec, and `purlin.drift` owns the one cached
`git ls-remote` per source per run.

    upstream.py add <source> [--path <file>] [--name <name>]
    upstream.py sync [<name>] [--all] [--check] [--json]
    upstream.py propose <name>

Every command takes `--project-root DIR`; without it the root is the one
`config_engine` resolves from the working directory.

`add` fetches the file at the source's default branch head and writes the local
copy. A source that is not a repository is free text: the copy carries the text
and a note saying the rules are still to be drafted, because drafting them is
the skill's job, not this module's.

`sync` names the rules that changed, copies the designs the source names into
`designs/<anchor>/`, and advances the pin. `--check` changes nothing and exits
1 when a pin is behind, 2 when a source could not be read. `--json` prints the
same answer for the skill and for the scheduled job.

`propose` writes the patch the anchor repo needs to
`.purlin/runtime/anchors/<name>.patch` and prints the commands a person runs to
open the pull request there. A consumer never edits a pinned rule in place.
"""

import argparse
import difflib
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MCP_DIR = os.path.join(_SCRIPTS_DIR, 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from config_engine import find_project_root  # noqa: E402
from purlin import drift as drift_module, specs as specs_module  # noqa: E402

ANCHOR_DIR = os.path.join('specs', '_anchors')
RUNTIME_DIR = os.path.join('.purlin', 'runtime', 'anchors')
DESIGNS_DIR = 'designs'

# The three fields a local copy carries and the author's file does not. They
# are rewritten on every add and sync, so an incoming body is stripped of them
# before it is written.
_TRACKING_RE = re.compile(r'^>[ \t]*(?:Source|Path|Pinned):.*\n?', re.MULTILINE)
_HEADING_RE = re.compile(r'^#[ \t]+.*$', re.MULTILINE)

# A design the source names: any path under `designs/` in the anchor's text,
# glob characters included. The files are copied out of the fetched checkout.
_DESIGN_REF_RE = re.compile(r'(designs/[A-Za-z0-9_./*?-]+)')
# Prose ends a sentence on the path it just named, so a trailing stop is
# part of the sentence and not of the file name.
_REF_PUNCTUATION = '.,;:)"\''

_CLONE_TIMEOUT = 120


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------

def _git(args, cwd=None, timeout=30):
    """`(returncode, stdout, stderr)` for one git command."""
    try:
        result = subprocess.run(['git'] + args, capture_output=True, text=True,
                                cwd=cwd or '.', timeout=timeout)
    except subprocess.TimeoutExpired:
        return 1, '', 'timed out'
    except (subprocess.SubprocessError, OSError) as exc:
        return 1, '', str(exc)[:200]
    return result.returncode, result.stdout, result.stderr


def remote_head(project_root, url, cache=None):
    """`(sha, error)` for a source's default branch head.

    `purlin.drift` owns the one `git ls-remote` in the codebase and the cache
    that keeps an anchor repo serving six anchors to a single call per run;
    this reuses both rather than opening a second connection of its own.
    """
    safe, reason = drift_module.source_url_is_safe(url)
    if not safe:
        return None, 'source rejected: %s' % reason
    cache = cache if cache is not None else {}
    if url not in cache:
        cache[url] = drift_module._ls_remote(project_root, url)
    remote = cache[url]
    if remote.get('error'):
        return None, remote['error']
    return remote.get('sha'), '' if remote.get('sha') else 'no HEAD ref returned'


def fetch_source(project_root, url, sha=None):
    """`(checkout_dir, head_sha, error)` for one source.

    Without a sha the fetch is shallow: the head is all an add or a sync
    reads. With one the clone carries history, because `propose` has to read
    the file as it stood at the pin.
    """
    safe, reason = drift_module.source_url_is_safe(url)
    if not safe:
        return None, None, 'source rejected: %s' % reason
    target = os.path.join(project_root, RUNTIME_DIR,
                          _checkout_name(url) + '.src')
    shutil.rmtree(target, ignore_errors=True)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    args = ['clone', '--quiet']
    if sha is None:
        args += ['--depth', '1']
    args += ['--end-of-options', url, target]
    code, _out, err = _git(args, cwd=project_root, timeout=_CLONE_TIMEOUT)
    if code != 0:
        return None, None, ' '.join(err.split())[:200] or 'clone failed'
    head = _git(['rev-parse', 'HEAD'], cwd=target)[1].strip()
    return target, head, ''


def read_source_file(checkout_dir, path, sha=None):
    """`(text, error)` for one file in a fetched checkout, at HEAD or at a sha."""
    if not path:
        return None, 'no path into the source; pass --path'
    if sha:
        code, out, err = _git(['show', '--end-of-options', '%s:%s' % (sha, path)],
                              cwd=checkout_dir)
        if code != 0:
            return None, ' '.join(err.split())[:200] or 'not found at the pin'
        return out, ''
    full = os.path.join(checkout_dir, path)
    if not os.path.isfile(full):
        return None, '%s is not in the source' % path
    with open(full, 'r', encoding='utf-8') as handle:
        return handle.read(), ''


# ---------------------------------------------------------------------------
# The local copy
# ---------------------------------------------------------------------------

def _slug(text):
    return re.sub(r'[^A-Za-z0-9]+', '-', text).strip('-').lower()[:60] or 'source'


def _checkout_name(url):
    """A directory name for one source: readable, and unique per url.

    Two anchor repos whose urls differ only past the sixtieth character would
    share a slug, and the second fetch would read the first one's files.
    """
    return '%s-%s' % (_slug(url)[:40],
                      hashlib.sha256(url.encode('utf-8')).hexdigest()[:8])


def anchor_path(project_root, name):
    return os.path.join(project_root, ANCHOR_DIR, name + '.md')


def strip_tracking(content):
    """An incoming body with the `> Source:`, `> Path:` and `> Pinned:` lines off.

    Removing a line leaves the blank line that followed it, so runs of blank
    lines collapse to one. Without that, every add and sync would add a blank
    line to the copy and the patch `propose` writes would carry it.
    """
    return re.sub(r'\n{3,}', '\n\n', _TRACKING_RE.sub('', content or ''))


def compose_copy(content, source_line, pinned, note=None):
    """The local copy: the author's body with the tracking fields after its title."""
    body = strip_tracking(content or '').lstrip('\n')
    fields = ['> Source: %s' % source_line, '> Pinned: %s' % pinned]
    if note:
        fields.append('> Note: %s' % note)
    heading = _HEADING_RE.search(body)
    if not heading:
        return '\n'.join(fields) + '\n\n' + body
    head = body[:heading.end()]
    rest = body[heading.end():].lstrip('\n')
    return head + '\n\n' + '\n'.join(fields) + '\n\n' + rest


def parse_rules(name, content):
    """`{RULE-N: text}` for an anchor's text, tags already off each line.

    `purlin.specs` owns the grammar; this hands it the text a fetch returned
    so an upstream file and a local copy are read exactly alike.
    """
    return specs_module._parse_spec(name, 'specs/_anchors/%s.md' % name,
                                    content or '')['rules']


def rule_diff(old_rules, new_rules):
    """`{'added', 'removed', 'changed'}`, each a sorted list of rule ids."""
    def order(ids):
        return sorted(ids, key=lambda r: int(r.split('-')[1]))
    added = order(set(new_rules) - set(old_rules))
    removed = order(set(old_rules) - set(new_rules))
    changed = order(r for r in set(old_rules) & set(new_rules)
                    if specs_module.rule_text_hash(old_rules[r])
                    != specs_module.rule_text_hash(new_rules[r]))
    return {'added': added, 'removed': removed, 'changed': changed}


def format_rule_diff(diff):
    """`RULE-3 changed, RULE-6 added`, or `no rule changes`."""
    parts = ['%s changed' % rule for rule in diff['changed']]
    parts += ['%s added' % rule for rule in diff['added']]
    parts += ['%s removed' % rule for rule in diff['removed']]
    return ', '.join(parts) or 'no rule changes'


def copy_designs(project_root, name, checkout_dir, content):
    """Copy every design the anchor's text names into `designs/<anchor>/`.

    A design reference is a path under `designs/` in the anchor's own text,
    glob characters allowed. Files that the source does not hold are skipped:
    a stale reference is the anchor author's to fix, not a reason to refuse
    the sync.
    """
    copied = []
    if not checkout_dir:
        return copied
    target_dir = os.path.join(project_root, DESIGNS_DIR, name)
    references = {reference.rstrip(_REF_PUNCTUATION)
                  for reference in _DESIGN_REF_RE.findall(content or '')}
    for reference in sorted(references):
        if '..' in reference or not reference:
            continue
        for found in sorted(glob.glob(os.path.join(checkout_dir, reference))):
            if not os.path.isfile(found):
                continue
            os.makedirs(target_dir, exist_ok=True)
            destination = os.path.join(target_dir, os.path.basename(found))
            shutil.copyfile(found, destination)
            copied.append(os.path.relpath(destination, project_root)
                          .replace(os.sep, '/'))
    return sorted(set(copied))


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

FREE_TEXT_NOTE = ('the source is free text, so the rules below are still to be '
                  'drafted from it. Run purlin:anchor create to draft them.')


def _default_name(source, path):
    base = path or source
    base = base.rstrip('/').split('/')[-1]
    for suffix in ('.git', '.md', '.txt'):
        if base.endswith(suffix):
            base = base[:-len(suffix)]
    return _slug(base).replace('-', '_') or 'anchor'


def add(project_root, source, path=None, name=None):
    """Fetch an anchor from a source and write the local copy. Returns a dict."""
    name = name or _default_name(source, path)
    result = {'command': 'add', 'anchor': name, 'source': source, 'path': path}
    safe, reason = drift_module.source_url_is_safe(source)
    if not safe:
        result.update({'status': 'error', 'error': 'source rejected: %s' % reason})
        return result
    is_free_text, text = _free_text(project_root, source)
    if is_free_text:
        pinned = hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]
        body = text if text.lstrip().startswith('#') else (
            '# Anchor: %s\n\n%s' % (name, text))
        if '## Rules' not in body:
            body = body.rstrip('\n') + '\n\n## Rules\n\n## Proof\n'
        copy = compose_copy(body, source, pinned, note=FREE_TEXT_NOTE)
        _write(anchor_path(project_root, name), copy)
        result.update({'status': 'drafted', 'pinned': pinned,
                       'spec_path': 'specs/_anchors/%s.md' % name,
                       'note': FREE_TEXT_NOTE})
        return result

    checkout, head, error = fetch_source(project_root, source)
    if error:
        result.update({'status': 'error', 'error': error})
        return result
    content, error = read_source_file(checkout, path)
    if error:
        result.update({'status': 'error', 'error': error})
        return result
    source_line = '%s %s' % (source, path)
    _write(anchor_path(project_root, name),
           compose_copy(content, source_line, head))
    result.update({'status': 'added', 'pinned': head,
                   'spec_path': 'specs/_anchors/%s.md' % name,
                   'designs': copy_designs(project_root, name, checkout, content),
                   'rules': sorted(parse_rules(name, content))})
    return result


def is_repository(project_root, source):
    """True when a `> Source:` names a repository rather than free text.

    A path to a readable file satisfies the git-url test as well, because
    `/home/me/policy.txt` begins with a slash; the file wins, since a text
    file is not a repository. Anything that is neither a file nor a git url
    is free text too, and the person writes the rules from it.
    """
    for candidate in (os.path.join(project_root, source), source):
        if os.path.isfile(candidate):
            return False
    return drift_module._looks_like_git(source)


def _free_text(project_root, source):
    """`(is_free_text, text)` for a source, the text empty unless it is a file."""
    if is_repository(project_root, source):
        return False, ''
    for candidate in (os.path.join(project_root, source), source):
        if os.path.isfile(candidate):
            with open(candidate, 'r', encoding='utf-8') as handle:
                return True, handle.read()
    return True, ''


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if text and not text.endswith('\n'):
        text += '\n'
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------

def pinned_anchors(project_root):
    """`{name: info}` for every anchor whose `> Source:` names a repository."""
    features = specs_module.scan_specs(project_root)
    return {name: info for name, info in sorted(features.items())
            if info.get('is_anchor') and info.get('source')
            and is_repository(project_root, info['source'])}


def sync(project_root, names=None, check=False):
    """Check, and unless `check`, advance every named pin. Returns a dict."""
    anchors = pinned_anchors(project_root)
    wanted = list(names) if names else sorted(anchors)
    cache = {}
    rows = []
    for name in wanted:
        info = anchors.get(name)
        if info is None:
            rows.append({'anchor': name, 'status': 'error',
                         'error': 'no anchor named %s carries a git source' % name})
            continue
        rows.append(_sync_one(project_root, name, info, cache, check))
    behind = [r for r in rows if r['status'] in ('behind', 'synced')]
    errors = [r for r in rows if r['status'] == 'error']
    return {'command': 'sync', 'checked': bool(check), 'anchors': rows,
            'behind': len(behind), 'errors': len(errors)}


def _sync_one(project_root, name, info, cache, check):
    row = {'anchor': name, 'source': info['source'],
           'path': info.get('source_path'), 'pinned': info.get('pinned')}
    head, error = remote_head(project_root, info['source'], cache)
    if error:
        row.update({'status': 'error', 'error': error})
        return row
    row['remote_sha'] = head
    pinned = info.get('pinned') or ''
    if pinned and (head.startswith(pinned) or pinned.startswith(head)):
        row['status'] = 'current'
        return row
    if check:
        row['status'] = 'behind' if pinned else 'unpinned'
        return row

    checkout, _head, error = fetch_source(project_root, info['source'])
    if error:
        row.update({'status': 'error', 'error': error})
        return row
    content, error = read_source_file(checkout, info.get('source_path'))
    if error:
        row.update({'status': 'error', 'error': error})
        return row

    diff = rule_diff(info['rules'], parse_rules(name, content))
    source_line = '%s %s' % (info['source'], info.get('source_path') or '')
    _write(anchor_path(project_root, name),
           compose_copy(content, source_line.strip(), head))
    row.update({'status': 'synced', 'pinned': head, 'previous': pinned,
                'rule_changes': diff, 'summary': format_rule_diff(diff),
                'designs': copy_designs(project_root, name, checkout, content)})
    return row


# ---------------------------------------------------------------------------
# propose
# ---------------------------------------------------------------------------

_GH_HOSTS = ('github.com',)
_ADO_HOSTS = ('dev.azure.com', 'visualstudio.com')


def propose(project_root, name):
    """Write the patch the anchor repo needs, and the commands to open the PR."""
    anchors = pinned_anchors(project_root)
    info = anchors.get(name)
    result = {'command': 'propose', 'anchor': name}
    if info is None:
        result.update({'status': 'error',
                       'error': 'no anchor named %s carries a git source' % name})
        return result
    pinned = info.get('pinned')
    if not pinned:
        result.update({'status': 'error',
                       'error': '%s has no pin; run sync first' % name})
        return result

    checkout, _head, error = fetch_source(project_root, info['source'], sha=pinned)
    if error:
        result.update({'status': 'error', 'error': error})
        return result
    path = info.get('source_path')
    published, error = read_source_file(checkout, path, sha=pinned)
    if error:
        result.update({'status': 'error', 'error': error})
        return result

    with open(anchor_path(project_root, name), 'r', encoding='utf-8') as handle:
        local = strip_tracking(handle.read())
    patch = ''.join(difflib.unified_diff(
        published.splitlines(True), local.splitlines(True),
        fromfile='a/%s' % path, tofile='b/%s' % path))
    patch_path = os.path.join(project_root, RUNTIME_DIR, name + '.patch')
    _write(patch_path, patch)
    result.update({'status': 'empty' if not patch else 'written',
                   'patch': os.path.relpath(patch_path, project_root)
                            .replace(os.sep, '/'),
                   'source': info['source'], 'path': path, 'pinned': pinned,
                   'commands': _propose_commands(info['source'], name, patch_path)})
    return result


def _propose_commands(url, name, patch_path):
    lines = ['git checkout -b purlin/%s' % name,
             'git apply %s' % patch_path,
             'git commit -am "anchor(%s): proposed change"' % name]
    host = url.lower()
    if any(h in host for h in _GH_HOSTS):
        lines.append('gh pr create --fill')
    elif any(h in host for h in _ADO_HOSTS):
        lines.append('az repos pr create --source-branch purlin/%s' % name)
    else:
        lines.append('gh pr create --fill    # on Azure DevOps: '
                     'az repos pr create --source-branch purlin/%s' % name)
    return lines


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

def _render(result):
    """The text a person reads: one line per anchor, sentence case, no glyphs."""
    lines = []
    if result['command'] == 'add':
        if result['status'] == 'error':
            return ['%s: %s' % (result['anchor'], result['error'])]
        lines.append('%s: written to %s, pinned %s'
                     % (result['anchor'], result['spec_path'],
                        result['pinned'][:7]))
        if result['status'] == 'drafted':
            lines.append('  the source is free text: the rules are still to be '
                         'drafted. Run purlin:anchor create %s.' % result['anchor'])
        else:
            lines.append('  %d rules. Run purlin:status to see them.'
                         % len(result['rules']))
            for design in result.get('designs', []):
                lines.append('  design copied: %s' % design)
        return lines
    if result['command'] == 'propose':
        if result['status'] == 'error':
            return ['%s: %s' % (result['anchor'], result['error'])]
        if result['status'] == 'empty':
            return ['%s: the local copy matches the source at the pin, so there '
                    'is nothing to propose.' % result['anchor']]
        lines.append('%s: patch written to %s. In a checkout of %s run:'
                     % (result['anchor'], result['patch'], result['source']))
        lines.extend('  ' + command for command in result['commands'])
        return lines

    for row in result['anchors']:
        name = row['anchor']
        status = row['status']
        if status == 'current':
            lines.append('%s: the pin is current.' % name)
        elif status == 'behind':
            lines.append('%s: the pin %s is behind its source, now %s. Run '
                         'purlin:anchor sync %s.'
                         % (name, (row.get('pinned') or '')[:7],
                            (row.get('remote_sha') or '')[:7], name))
        elif status == 'unpinned':
            lines.append('%s: names a source and no pin. Run purlin:anchor sync '
                         '%s.' % (name, name))
        elif status == 'synced':
            lines.append('%s: %s. Pin advanced from %s to %s.'
                         % (name, row['summary'], (row.get('previous') or 'none')[:7],
                            row['pinned'][:7]))
            for design in row.get('designs', []):
                lines.append('  design copied: %s' % design)
        else:
            lines.append('%s: the source could not be read (%s).'
                         % (name, row.get('error', 'unknown')))
    if not lines:
        lines.append('No anchors name a git source.')
    return lines


def _exit_code(result):
    """0 when nothing is outstanding, 1 when a pin is behind, 2 on any error."""
    if result['command'] != 'sync':
        return 2 if result['status'] == 'error' else 0
    if result['errors']:
        return 2
    return 1 if result['checked'] and result['behind'] else 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog='upstream.py',
        description='Add, sync and propose anchors held in an anchor repo.')
    parser.add_argument('--project-root', default=None,
                        help='the workspace holding .purlin/ and specs/')
    sub = parser.add_subparsers(dest='command')

    add_parser = sub.add_parser('add', help='fetch an anchor and write the copy')
    add_parser.add_argument('source', help='a git url, or a file of free text')
    add_parser.add_argument('--path', default=None,
                            help='the path to the anchor inside the source')
    add_parser.add_argument('--name', default=None,
                            help='the local anchor name (default: from the path)')
    add_parser.add_argument('--json', action='store_true',
                            help='print the answer as JSON')

    sync_parser = sub.add_parser('sync', help='compare and advance pins')
    sync_parser.add_argument('name', nargs='?', default=None)
    sync_parser.add_argument('--all', action='store_true',
                             help='every anchor with a git source')
    sync_parser.add_argument('--check', action='store_true',
                             help='report only; exit 1 when a pin is behind')
    sync_parser.add_argument('--json', action='store_true',
                             help='print the answer as JSON')

    propose_parser = sub.add_parser(
        'propose', help='write the patch the anchor repo needs')
    propose_parser.add_argument('name')
    propose_parser.add_argument('--json', action='store_true',
                                help='print the answer as JSON')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.command:
        build_parser().print_help()
        return 2
    root = args.project_root or find_project_root()
    if not root or not os.path.isdir(root):
        sys.stderr.write('No Purlin workspace found. Pass --project-root DIR.\n')
        return 2

    if args.command == 'add':
        result = add(root, args.source, path=args.path, name=args.name)
    elif args.command == 'propose':
        result = propose(root, args.name)
    else:
        names = [args.name] if args.name else None
        if args.all:
            names = None
        result = sync(root, names=names, check=args.check)

    if getattr(args, 'json', False):
        print(json.dumps(result, separators=(',', ':'), sort_keys=True))
    else:
        print('\n'.join(_render(result)))
    return _exit_code(result)


if __name__ == '__main__':
    sys.exit(main())
