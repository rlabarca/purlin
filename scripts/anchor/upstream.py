#!/usr/bin/env python3
"""Anchors that come from an anchor repo: add and sync.

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

Every command takes `--project-root DIR`; without it the root is the one
`config_engine` resolves from the working directory.

`add` fetches the file at the source's default branch head and writes the local
copy. The file is a spec in Purlin's format kept in a git repository: `add`
refuses a file on disk, a description in words or a file that holds no rule,
and writes nothing. It also refuses a `--name` that is not letters, digits,
`_` and `-`, a name an anchor in the project already holds, and a `--path` that is
absolute or holds `..`: only a file of the source is read.

`sync` names the rules that changed and advances the pin, fetching each distinct
source once per run. `--check` changes nothing and exits 1 when a pin is behind,
2 when a source could not be read or names no repository. `--json` prints the
same answer for the skill. A consumer never edits a remote anchor's rule in
place.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
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

# The three fields a local copy carries and the author's file does not. They
# are rewritten on every add and sync, so an incoming body is stripped of them
# before it is written.
_TRACKING_RE = re.compile(r'^>[ \t]*(?:Source|Path|Pinned):.*\n?', re.MULTILINE)
_HEADING_RE = re.compile(r'^#[ \t]+.*$', re.MULTILINE)

_CLONE_TIMEOUT = 120


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------

def _rmtree(path):
    """Remove a fetched checkout on every operating system.

    Git marks loose objects and packs read-only. A read-only file inside a
    writable directory still unlinks on POSIX; on Windows it does not, and the
    directory survives the removal, so the next clone into it fails on a
    destination that already exists. Clearing the bit and retrying once is the
    whole difference. A path that is not there at all is not an error.
    """
    def _retry(func, failed, _exc_info):
        try:
            os.chmod(failed, stat.S_IWRITE)
            func(failed)
        except OSError:
            pass

    shutil.rmtree(path, onerror=_retry)


def _git(args, cwd=None, timeout=30):
    """`(returncode, stdout, stderr)` for one git command."""
    try:
        result = subprocess.run(['git'] + args, capture_output=True,
                                encoding='utf-8', errors='replace',
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


def fetch_source(project_root, url, cache=None):
    """`(checkout_dir, head_sha, error)` for one source.

    The fetch is shallow: the head is all an add or a sync reads. A `cache`
    keyed on the url holds each answer for the rest of the run, so every
    anchor pinned to one source reads the one checkout.
    """
    if cache is not None:
        if url not in cache:
            cache[url] = fetch_source(project_root, url)
        return cache[url]
    safe, reason = drift_module.source_url_is_safe(url)
    if not safe:
        return None, None, 'source rejected: %s' % reason
    target = os.path.join(project_root, RUNTIME_DIR,
                          _checkout_name(url) + '.src')
    _rmtree(target)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    args = ['clone', '--quiet', '--depth', '1', '--end-of-options', url,
            target]
    code, _out, err = _git(args, cwd=project_root, timeout=_CLONE_TIMEOUT)
    if code != 0:
        return None, None, ' '.join(err.split())[:200] or 'clone failed'
    head = _git(['rev-parse', 'HEAD'], cwd=target)[1].strip()
    return target, head, ''


def leads_out(path):
    """True for a path into a source that is absolute or holds `..`."""
    path = (path or '').replace('\\', '/')
    return (path.startswith('/') or bool(re.match(r'[A-Za-z]:', path))
            or '..' in path.split('/'))


def read_source_file(checkout_dir, path):
    """`(text, error)` for one file in a fetched checkout, at its head."""
    if not path:
        return None, 'no path into the source; pass --path'
    # Only a file of the source is read: a path that leaves the checkout, by
    # `..`, by a leading `/` or by a link, names none.
    root = os.path.realpath(checkout_dir)
    full = os.path.realpath(os.path.join(root, path))
    if (leads_out(path) or not full.startswith(root + os.sep)
            or not os.path.isfile(full)):
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
    line to the copy.
    """
    return re.sub(r'\n{3,}', '\n\n', _TRACKING_RE.sub('', content or ''))


_NOTE_RE = re.compile(r'^>[ \t]*Note:[ \t]*(.*)$', re.MULTILINE)


def local_notes(project_root, name):
    """The `> Note:` lines the local copy carries, in order.

    A note is the consumer's own free text, so a sync keeps it beside the
    tracking fields it rewrites.
    """
    try:
        with open(anchor_path(project_root, name), 'r', encoding='utf-8') as handle:
            return [text.strip() for text in _NOTE_RE.findall(handle.read())
                    if text.strip()]
    except (IOError, OSError, UnicodeDecodeError):
        return []


def compose_copy(content, source_line, pinned, note=None):
    """The local copy: the author's body with the tracking fields after its title."""
    body = strip_tracking(content or '').lstrip('\n')
    fields = ['> Source: %s' % source_line, '> Pinned: %s' % pinned]
    for text in note or ():
        if text and '> Note: %s' % text not in body:
            fields.append('> Note: %s' % text)
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


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

# The refusal of a source that is not a spec in Purlin's format kept in a git
# repository: what was given, then the anchor's name.
NOT_A_SPEC = ("not added. %s is not a spec in Purlin's format kept in a git "
              "repository. Run purlin:anchor create %s to write its rules in "
              "this project.")

WORDS_GIVEN = 'The description given'

# The refusal of a name no spec may hold (`specs.NAME`): a name with a `/` or
# `..` in it would be written outside `specs/_anchors/`. The name the line
# ends on is the one given with every other character taken out.
NAME_REFUSED = ('not added. --name takes letters, digits, _ and - alone. Run '
                'purlin:anchor add <source> --path <path> --name %s.')
# The refusal of a name an anchor in the project already holds: the path of
# that anchor, then its name.
NAME_TAKEN = ('not added. %s already holds an anchor of that name. Run '
              'purlin:anchor sync %s to update it, or add it under another '
              '--name.')
# The refusal of a path that is absolute or holds `..`: it would be read from
# outside the fetched source. The anchor's name.
PATH_REFUSED = ('not added. --path takes a path inside the source, with no .. '
                'and no leading /. Run purlin:anchor add <source> --path '
                '<path> --name %s.')
_NAME_RE = re.compile(specs_module.NAME)


def _default_name(source, path):
    base = path or source
    base = re.split(r'[\\/]', base.rstrip('/\\'))[-1]
    for suffix in ('.git', '.md', '.txt'):
        if base.endswith(suffix):
            base = base[:-len(suffix)]
    return _slug(base).replace('-', '_') or 'anchor'


def add(project_root, source, path=None, name=None):
    """Fetch an anchor from a source and write the local copy. Returns a dict."""
    given = path
    path = path.replace('\\', '/') if path else path
    name = name or _default_name(source, path)
    result = {'command': 'add', 'anchor': name, 'source': source, 'path': path}
    # The name is checked before anything is fetched or written.
    if not _NAME_RE.fullmatch(name):
        result.update({'status': 'error',
                       'error': NAME_REFUSED % _default_name(name, None)})
        return result
    if os.path.lexists(anchor_path(project_root, name)):
        result.update({'status': 'error',
                       'error': NAME_TAKEN % ('specs/_anchors/%s.md' % name,
                                              name)})
        return result
    if leads_out(path):
        result.update({'status': 'error', 'error': PATH_REFUSED % name})
        return result
    safe, reason = drift_module.source_url_is_safe(source)
    if not safe:
        result.update({'status': 'error', 'error': 'source rejected: %s' % reason})
        return result
    if not drift_module.source_is_repository(project_root, source):
        what = source if _is_file(project_root, source) else WORDS_GIVEN
        result.update({'status': 'error', 'error': NOT_A_SPEC % (what, name)})
        return result

    checkout, head, error = fetch_source(project_root, source)
    if error:
        result.update({'status': 'error', 'error': error})
        return result
    # The download is read once and is not kept: every way out removes it,
    # the read-only files git writes on Windows included.
    try:
        content, error = read_source_file(checkout, path)
    finally:
        _rmtree(checkout)
    if error:
        result.update({'status': 'error', 'error': error})
        return result
    if not parse_rules(name, content):
        result.update({'status': 'error', 'error': NOT_A_SPEC % (given, name)})
        return result
    source_line = '%s %s' % (source, path)
    _write(anchor_path(project_root, name),
           compose_copy(content, source_line, head))
    result.update({'status': 'added', 'pinned': head,
                   'spec_path': 'specs/_anchors/%s.md' % name,
                   'rules': sorted(parse_rules(name, content))})
    return result


def _is_file(project_root, source):
    """True when a source refused as no repository names a file on disk."""
    return any(os.path.isfile(candidate)
               for candidate in (os.path.join(project_root, source), source))


def _write(path, text):
    """Write a copy Purlin composed: `\\n` line endings on every system.

    The text is written as it stands (`newline=''`), with every `\\r\\n` it
    held turned to `\\n` first, so the copy carries no carriage return
    whatever line endings its source had.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = (text or '').replace('\r\n', '\n')
    if text and not text.endswith('\n'):
        text += '\n'
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text)


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------

def remote_anchors(project_root):
    """`{name: info}` for every anchor carrying a `> Source:`."""
    features = specs_module.scan_specs(project_root)
    return {name: info for name, info in sorted(features.items())
            if info.get('is_anchor') and info.get('source')}


def sync(project_root, names=None, check=False):
    """Check, and unless `check`, advance every named pin. Returns a dict."""
    anchors = remote_anchors(project_root)
    wanted = list(names) if names else sorted(anchors)
    cache = {}
    fetched = {}
    rows = []
    for name in wanted:
        info = anchors.get(name)
        if info is None:
            rows.append({'anchor': name, 'status': 'error',
                         'error': 'no anchor named %s carries a git source' % name})
            continue
        rows.append(_sync_one(project_root, name, info, cache, fetched,
                              check))
    behind = [r for r in rows if r['status'] in ('behind', 'synced')]
    errors = [r for r in rows if r['status'] == 'error']
    return {'command': 'sync', 'checked': bool(check), 'anchors': rows,
            'behind': len(behind), 'errors': len(errors)}


def _sync_one(project_root, name, info, cache, fetched, check):
    row = {'anchor': name, 'source': info['source'],
           'path': info.get('source_path'), 'pinned': info.get('pinned')}
    if not drift_module.source_is_repository(project_root, info['source']):
        row.update({'status': 'error', 'not_a_spec': True,
                    'error': drift_module.not_a_spec_source(name,
                                                            info['source'])})
        return row
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

    checkout, _head, error = fetch_source(project_root, info['source'],
                                          fetched)
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
           compose_copy(content, source_line.strip(), head,
                        note=local_notes(project_root, name)))
    row.update({'status': 'synced', 'pinned': head, 'previous': pinned,
                'rule_changes': diff, 'summary': format_rule_diff(diff)})
    return row


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
        count = len(result['rules'])
        lines.append('  1 rule. Run purlin:status to see it.' if count == 1
                     else '  %d rules. Run purlin:status to see them.' % count)
        return lines
    for row in result['anchors']:
        name = row['anchor']
        status = row['status']
        if status == 'current':
            lines.append('%s: the pin is current. Run purlin:status %s to see '
                         'its rules.' % (name, name))
        elif status in ('behind', 'unpinned'):
            lines.append(drift_module.pin_line(row))
        elif status == 'synced':
            lines.append('%s: %s. Pin advanced from %s to %s. Commit it as '
                         'anchor(%s): sync (%s), then run purlin:test.'
                         % (name, row['summary'], (row.get('previous') or 'none')[:7],
                            row['pinned'][:7], name, row['pinned'][:7]))
        elif row.get('not_a_spec'):
            lines.append(drift_module.pin_line(row))
        elif 'source' not in row:
            # A name no anchor carries: nothing was read, so no source is named.
            lines.append('%s: %s. Run purlin:status to see the anchors this '
                         'project has.' % (name, row['error']))
        else:
            lines.append(drift_module.pin_line(row))
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
        description='Add and sync anchors held in an anchor repo.')
    parser.add_argument('--project-root', default=None,
                        help='the project root holding .purlin/ and specs/')
    sub = parser.add_subparsers(dest='command')

    add_parser = sub.add_parser('add', help='fetch an anchor and write the copy')
    add_parser.add_argument('source', help='a git url')
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
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.command:
        build_parser().print_help()
        return 2
    root = args.project_root or find_project_root()
    if not root or not os.path.isdir(root):
        sys.stderr.write('No Purlin project root found. Pass --project-root <dir>.\n')
        return 2

    if args.command == 'add':
        result = add(root, args.source, path=args.path, name=args.name)
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
