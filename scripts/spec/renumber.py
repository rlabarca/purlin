"""Renumber a spec's number written twice, and the test comments that name it.

    renumber.py <feature> [--dry-run] [--project-root DIR]

Run as `sh scripts/purlin_python.sh scripts/spec/renumber.py`. It reads this
checkout only, as drift does: it never fetches and it commits nothing. It
plans, and without `--dry-run` makes, these edits in the feature's spec and
in the test files of this checkout:

1. A number written twice. The line that moves is the one drift names: the
   line whose text is not on the default branch's copy; where neither is, or
   there is no default branch, the later line in the file. It takes the next
   free number of its kind. A rule that moves takes with it every proof line
   that names it and is not on the default branch's copy.
2. A test comment that names the moved id, where `git blame` says the
   comment was written when that id's text was the moving line's text. A
   comment not yet committed is named, not changed.
3. A test comment whose proof's wording changed, where the old wording is
   now another id of the same spec: the comment moves to that id.
4. `> Highest-Rule:` / `> Highest-Proof:` raised to the new number.
5. Comments on other branches that name the moved id are named, never
   touched: every local branch but the current one, and every branch of a
   remote but its `HEAD` and the default branch, as last fetched. A comment
   already in this checkout's history is left to step 2.

The agent runs the dry run, shows its lines, and asks `Do it? [y/N]`; on yes
it runs this without `--dry-run`. The steps live in `skills/spec/SKILL.md`,
under `Renumbering`.

Exit codes: 0 planned or done, or nothing to renumber; 1 the feature is no
spec of this checkout; 2 the command line was wrong.
"""

import argparse
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import (console as console_module,                 # noqa: E402
                    drift as drift_module,
                    markers as markers_module,
                    specs as specs_module)

MOVES = '%s: %s at line %d becomes %s: "%s".'
MOVES_NEITHER = ('%s: %s at line %d becomes %s: "%s". Neither line is on %s, '
                 'so the later one moves.')
MOVES_NO_DEFAULT = ('%s: %s at line %d becomes %s: "%s". This checkout has no '
                    'copy of a default branch, so the later one moves.')
PROOF_FOLLOWS = '%s: %s at line %d now names %s.'
COMMENT_MOVES = '%s:%d names %s %s and moves to %s.'
COMMENT_FOLLOWS = '%s:%d names %s %s and moves to %s, where its old wording is now.'
COMMENT_UNCOMMITTED = ('%s:%d names %s %s and is not committed, so it is not '
                       'changed: check which proof it means.')
HIGHEST = '%s: > Highest-%s: %d becomes %d.'
OTHER_BRANCH = ('%s names %s %s at %s:%d, which this checkout does not change. '
                'If it means the line that moves, move it to %s on that branch.')
DRY_RUN = 'Nothing is changed: this is a dry run.'
DONE = 'Renumbered in %s: %s and %s. Nothing is committed.'
NOTHING = '%s: nothing to renumber.'
NOT_A_SPEC = ('%s: no spec of this checkout has that name. Run purlin:status to '
              'see its specs.')

EXIT_OK = 0
EXIT_NOT_A_SPEC = 1

_HEADS = 'refs/heads/'
_REMOTES = 'refs/remotes/'


def _plural(count, word):
    return '%d %s' % (count, word if count == 1 else word + 's')


def _set_id(line, old, new):
    """The rule or proof line `line` with its own id `old` written `new`."""
    return re.sub(r'^(\s*-\s+)%s\b' % re.escape(old), r'\g<1>' + new, line,
                  count=1)


def _set_rule(line, old, new):
    """The proof line `line` naming the rule `new` where it named `old`."""
    return re.sub(r'\(([^)]*)\)',
                  lambda found: '(%s)' % re.sub(
                      r'\b%s\b' % re.escape(old), new, found.group(1)),
                  line, count=1)


def _set_comment(line, feature, old, new):
    """The marker line `line` naming `feature new` where it named `old`."""
    return re.sub(r'(purlin:\s+%s\s+)%s\b' % (re.escape(feature), re.escape(old)),
                  r'\g<1>' + new, line, count=1)


def _read(path):
    with open(path, 'r', encoding='utf-8', newline='') as handle:
        return handle.read().splitlines(True)


def _write(path, lines):
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        handle.write(''.join(lines))


def _highest(parsed, kind):
    return parsed.get('highest_rule' if kind == 'Rule' else 'highest_proof')


def _moves(project_root, info, ref):
    """Step 1: `(lines, spec edits, moved)`. `moved` maps each id that moves
    to `(new id, the moving line's text)`; a spec edit is
    `(line number, function of the line)`."""
    lines, edits, moved = [], [], {}
    spec_lines = _read(os.path.join(project_root, info['spec_path']))
    # The lines of the default branch's copy, as written; none without one.
    on_default = set()
    if ref:
        on_default = {line.strip() for line in drift_module._git(
            project_root, ['show', '--end-of-options',
                           '%s:%s' % (ref, info['spec_path'])]).splitlines()}
    follows = []
    for entry in drift_module.numbers_twice(project_root,
                                            {info['name']: info}, ref):
        item, to, moving = entry['id'], entry['to'], entry['moves']
        shape = {'neither': MOVES_NEITHER,
                 'no_default': MOVES_NO_DEFAULT}.get(entry['case'], MOVES)
        values = (info['name'], item, moving['line'], to, moving['text'])
        lines.append(shape % (values + ((ref,) if shape is MOVES_NEITHER
                                        else ())))
        edits.append((moving['line'],
                      lambda text, old=item, new=to: _set_id(text, old, new)))
        moved[item] = (to, moving['text'])
        if not item.startswith('RULE-') or not ref:
            continue
        for number, text in enumerate(spec_lines, 1):
            found = specs_module._PROOF_LINE_RE.match(text.strip())
            if (found and item in specs_module._split_list(found.group(2))
                    and text.strip() not in on_default):
                follows.append(PROOF_FOLLOWS % (info['name'], found.group(1),
                                                number, to))
                edits.append((number, lambda text, old=item, new=to:
                               _set_rule(text, old, new)))
    return lines + follows, edits, moved


def _comments(project_root, info, moved):
    """Steps 2 and 3: `(lines, file edits, the number of comments changed)`.
    A file edit is `(path, line number, function of the line)`."""
    name = info['name']
    features = {name: info}
    cache = {}
    moves, follows, uncommitted, edits = [], [], [], []
    doubled = set(info.get('doubled_lines') or {})
    scanned = markers_module.scan(project_root)
    for path in sorted(scanned):
        for marker in scanned[path].markers:
            if marker.feature != name:
                continue
            if marker.id in moved:
                to, text = moved[marker.id]
                sha = drift_module._blamed_commit(project_root, path,
                                                  marker.line)
                if sha is None:
                    uncommitted.append(COMMENT_UNCOMMITTED % (
                        path, marker.line, name, marker.id))
                    continue
                then = drift_module.text_of(drift_module.spec_at(
                    project_root, sha, name, info['spec_path'], cache),
                    marker.id)
                if then != text:
                    continue
                moves.append(COMMENT_MOVES % (path, marker.line, name,
                                              marker.id, to))
            elif marker.id not in doubled:
                entry = drift_module.comment_reworded(
                    project_root, path, marker, features, cache)
                if not entry or not entry['now_under']:
                    continue
                to = entry['now_under']
                follows.append(COMMENT_FOLLOWS % (path, marker.line, name,
                                                  marker.id, to))
            else:
                continue
            edits.append((path, marker.line,
                          lambda text, old=marker.id, new=to:
                          _set_comment(text, name, old, new)))
    return moves + follows + uncommitted, edits, len(edits)


def _highest_lines(info, moved):
    """Step 4: `(lines, spec edits)` for each Highest line the moves raise."""
    lines, edits = [], []
    for kind, prefix in (('Rule', 'RULE-'), ('Proof', 'PROOF-')):
        numbers = [int(to.split('-')[1]) for to, _ in moved.values()
                   if to.startswith(prefix)]
        old = _highest(info, kind)
        if not numbers or old is None or max(numbers) <= old:
            continue
        new = max(numbers)
        lines.append(HIGHEST % (info['name'], kind, old, new))
        pattern = re.compile(r'^(>[ \t]*Highest-%s:[ \t]*)%d\b' % (kind, old))
        edits.append((pattern, new))
    return lines, edits


def _other_refs(project_root, ref):
    """Every local branch but the current one, and every remote branch but a
    remote's `HEAD` and the default branch, as full ref names."""
    current = drift_module._git(project_root, ['symbolic-ref', '-q', 'HEAD'])
    out = drift_module._git(project_root, [
        'for-each-ref', '--format=%(refname)', _HEADS, _REMOTES])
    refs = []
    for name in out.splitlines():
        if name == current or name.endswith('/HEAD'):
            continue
        if ref and name == _REMOTES + ref:
            continue
        refs.append(name)
    return refs


def _short(name):
    for prefix in (_HEADS, _REMOTES):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def _other_branches(project_root, info, moved, ref):
    """Step 5: one line per comment on another branch naming a moved id."""
    lines = []
    name = info['name']
    for full in _other_refs(project_root, ref):
        for item in sorted(moved, key=drift_module._rule_number):
            out = drift_module._git(project_root, [
                'grep', '-n', '-I', '-z', '-E',
                r'purlin:[[:space:]]+%s[[:space:]]+%s([^0-9]|$)' % (name, item),
                full, '--'])
            for hit in out.split('\n'):
                parts = hit.split('\0')
                if len(parts) < 3 or not parts[1].isdigit():
                    continue
                path = parts[0][len(full) + 1:]
                number = int(parts[1])
                if markers_module.parse_comment(parts[2]) != (name, item):
                    continue
                sha = drift_module._blamed_commit(project_root, path, number,
                                                  rev=full)
                if sha and _in_history(project_root, sha):
                    continue
                lines.append(OTHER_BRANCH % (_short(full), name, item, path,
                                             number, moved[item][0]))
    return lines


def _in_history(project_root, sha):
    """True when the commit `sha` is in HEAD's history."""
    try:
        return subprocess.run(
            ['git', 'merge-base', '--is-ancestor', '--end-of-options', sha,
             'HEAD'], capture_output=True, cwd=project_root,
            timeout=15).returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def plan(project_root, feature):
    """The plan for `feature`, or None where it is no spec of this checkout.

    `{'lines', 'spec_edits', 'highest_edits', 'comment_edits', 'spec_lines',
    'comments'}`: `lines` are the plan's lines in order, without the closing
    line; the rest is what `apply` changes.
    """
    info = specs_module.scan_specs(project_root).get(feature)
    if info is None:
        return None
    ref = drift_module.default_branch(project_root)
    move_lines, spec_edits, moved = _moves(project_root, info, ref)
    comment_lines, comment_edits, comments = _comments(project_root, info,
                                                       moved)
    highest_lines, highest_edits = _highest_lines(info, moved)
    other = _other_branches(project_root, info, moved, ref)
    return {'info': info,
            'lines': move_lines + comment_lines + highest_lines + other,
            'spec_edits': spec_edits, 'highest_edits': highest_edits,
            'comment_edits': comment_edits, 'spec_lines': len(spec_edits),
            'comments': comments}


def apply(project_root, planned):
    """Make the edits `planned` holds. Nothing is staged or committed."""
    spec = os.path.join(project_root, planned['info']['spec_path'])
    lines = _read(spec)
    for number, edit in planned['spec_edits']:
        lines[number - 1] = edit(lines[number - 1])
    for pattern, new in planned['highest_edits']:
        lines = [pattern.sub(r'\g<1>%d' % new, line) for line in lines]
    _write(spec, lines)
    by_file = {}
    for path, number, edit in planned['comment_edits']:
        by_file.setdefault(path, []).append((number, edit))
    for path, changes in by_file.items():
        full = os.path.join(project_root, *path.split('/'))
        lines = _read(full)
        for number, edit in changes:
            lines[number - 1] = edit(lines[number - 1])
        _write(full, lines)


def run(project_root, feature, dry_run=False, out=None):
    """Print the plan, make it unless `dry_run`, and return the exit code."""
    out = out or sys.stdout
    planned = plan(project_root, feature)
    if planned is None:
        print(NOT_A_SPEC % feature, file=out)
        return EXIT_NOT_A_SPEC
    if not planned['spec_edits'] and not planned['comment_edits']:
        print(NOTHING % feature, file=out)
        return EXIT_OK
    for line in planned['lines']:
        print(line, file=out)
    if dry_run:
        print(DRY_RUN, file=out)
        return EXIT_OK
    apply(project_root, planned)
    print(DONE % (feature, _plural(planned['spec_lines'], 'spec line'),
                  _plural(planned['comments'], 'test comment')), file=out)
    return EXIT_OK


def main(argv=None):
    console_module.force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog='renumber.py',
        description='Renumber a number a spec writes twice, and the test '
                    'comments that name it.')
    parser.add_argument('feature')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--project-root', default='.')
    args = parser.parse_args(argv)
    return run(args.project_root, args.feature, dry_run=args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
