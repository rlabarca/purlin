"""Resolve the conflict a merge left in a spec, renumber a number written
twice, and move the test comments that name it.

    renumber.py <feature> [--dry-run | --yes] [--project-root DIR]

Run as `sh scripts/purlin_python.sh scripts/spec/renumber.py`. It reads this
checkout only, as drift does: it never fetches, it stages nothing and it
commits nothing. It plans these edits in the feature's spec and in the test
files of this checkout, prints the plan, and asks `Do it? [y/N] ` on its
input. `y`, `yes` or `--yes` makes them; any other answer, an empty one or
the end of input changes nothing. `--dry-run` prints the plan and asks
nothing.

0. A conflict git left in the spec. Where both sides only added rule lines
   or proof lines, both sides' lines are kept, the first side's first and a
   line both hold once. Where each side holds `> Highest-` lines, the higher
   of each kind stays. Any other conflict is left as it is and named with
   why: a side changed or removed a line of the version both sides started
   from, the conflict holds another kind of line, or git no longer holds
   that version, as after `git add`. A number written twice on a line of a
   conflict that is left waits for the next run. The renumbering is planned
   over the spec as it reads once those conflicts are resolved, and every
   line number printed is the line's number in the file on disk.
1. A number written twice. The line that moves is the one drift names: the
   line whose text is not on the default branch's copy; where neither is, or
   there is no default branch, the later line in the file. It takes the next
   free number of its kind. A rule that moves takes with it every proof line
   that names it and is not on the default branch's copy.
2. A test comment that names the moved id, where `git blame` says the
   comment was written when that id's text was the moving line's text. A
   comment not yet committed is named, not changed.
3. A test comment whose proof's wording changed after its test was last
   changed, where the wording it had then is now another id of the same
   spec: the comment moves to that id, the one `wording.py` names.
4. `> Highest-Rule:` / `> Highest-Proof:` raised to the new number.
5. Comments on other branches that name the moved id are named, never
   touched: every local branch but the current one, and every branch of a
   remote but its `HEAD` and the default branch, as last fetched. A comment
   already in this checkout's history is left to step 2.

The steps an agent follows live in `skills/spec/SKILL.md`, under
`Renumbering`.

Exit codes: 0 planned or done, nothing to do, or the answer was not yes; 1
the feature is no spec of this checkout; 2 the command line was wrong.
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
                    specs as specs_module,
                    wording as wording_module)

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
ASK = 'Do it? [y/N] '
NOT_DONE = 'Nothing is changed.'
KEEPS_BOTH = ('%s: the conflict at line %d keeps both sides: %s from %s and '
              '%s from %s.')
TAKES_HIGHER = ('%s: the conflict at line %d takes > Highest-%s: %d, the '
                'higher of %d and %d.')
LEFT = ('%s: the conflict at line %d is left: %s. Resolve it by hand, then '
        'run purlin:spec %s again.')
LEFT_BOTH_CHANGED = 'both sides changed %s'
LEFT_CHANGED = 'a side changed %s'
LEFT_REMOVED = 'a side removes %s'
LEFT_OTHER_LINE = ('it holds a line that is not a rule, a proof or a '
                   '> Highest- line')
LEFT_NO_BASE = 'git holds no version both sides started from'
RESOLVED = 'Resolved %s in %s.'
RESOLVED_ALONE = 'Resolved %s in %s. Nothing is committed.'
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


# ---------------------------------------------------------------------------
# A conflict git left in the spec
# ---------------------------------------------------------------------------

_OURS_RE = re.compile(r'^<{7}(?:[ \t]+(.*))?$')
_BASE_RE = re.compile(r'^\|{7}(?:[ \t].*)?$')
_SPLIT_RE = re.compile(r'^={7}[ \t]*$')
_THEIRS_RE = re.compile(r'^>{7}(?:[ \t]+(.*))?$')
_ID_RE = re.compile(r'^-\s+((?:RULE|PROOF)-\d+)\b')
_HIGHEST_LINE_RE = re.compile(r'^>[ \t]*Highest-(Rule|Proof):[ \t]*(\d+)[ \t]*$')
_KINDS = ('Rule', 'Proof')


def _bare(line):
    return line.rstrip('\r\n')


def _line_id(text):
    """The id a rule line or a proof line opens on, or None for any other."""
    text = text.strip()
    if (specs_module._RULE_RE.match(text)
            or specs_module._PROOF_LINE_RE.match(text)):
        return _ID_RE.match(text).group(1)
    return None


def _blocks(lines):
    """Each whole conflict of `lines`, in order: `{start, end, ours, theirs,
    labels}`. `start` and `end` are the 1-based numbers of git's opening and
    closing lines, and a side is `[(number, line)]`. The lines git shows of
    the starting version, under `|||||||`, belong to neither side."""
    found, block, part = [], None, None
    for number, line in enumerate(lines, 1):
        text = _bare(line)
        opened = _OURS_RE.match(text)
        if opened:
            block = {'start': number, 'ours': [], 'theirs': [],
                     'labels': [(opened.group(1) or '').strip(), '']}
            part = 'ours'
        elif block is None:
            continue
        elif _BASE_RE.match(text) and part == 'ours':
            part = 'base'
        elif _SPLIT_RE.match(text) and part in ('ours', 'base'):
            part = 'theirs'
        elif _THEIRS_RE.match(text) and part == 'theirs':
            block['end'] = number
            block['labels'][1] = (_THEIRS_RE.match(text).group(1) or '').strip()
            found.append(block)
            block, part = None, None
        elif part in ('ours', 'theirs'):
            block[part].append((number, line))
    return found


def _left_why(sides, base):
    """Why a conflict of rule lines and proof lines is left, or None where
    both sides only added lines. `base` is the starting version's text."""
    base_lines = {line.strip() for line in base.splitlines()}
    base_ids = {_line_id(line) for line in base.splitlines()} - {None}
    held = []   # per side, {id: True where a line of it is the base's own}
    for side in sides:
        ids = {}
        for text in side:
            item = _line_id(text)
            ids[item] = ids.get(item, False) or text.strip() in base_lines
        held.append(ids)
    seen = []
    for ids in held:
        seen += [item for item in ids if item not in seen]
    for item in seen:
        if item not in base_ids:
            continue
        if not all(item in ids for ids in held):
            return LEFT_REMOVED % item
        changed = [not ids[item] for ids in held]
        if all(changed):
            return LEFT_BOTH_CHANGED % item
        if any(changed):
            return LEFT_CHANGED % item
    return None


def _highest_values(side):
    """`{kind: (value, number, line)}` for a side, `[(number, line)]`, of
    `> Highest-` lines: the higher where the side writes a kind twice."""
    found = {}
    for number, line in side:
        if not line.strip():
            continue
        kind, value = _HIGHEST_LINE_RE.match(_bare(line).strip()).groups()
        if kind not in found or int(value) > found[kind][0]:
            found[kind] = (int(value), number, line)
    return found


def conflicts(lines, base):
    """Each conflict git left in `lines`, a spec's lines, in order:
    `{start, ours, theirs, labels, kind, why}`.

    `start` is the 1-based line of git's `<<<<<<<`; `ours` and `theirs` are
    the two sides, each `[(number, line)]`; `labels` is the text after git's
    `<<<<<<< ` and `>>>>>>> `. `base` is the version both sides started
    from, `git show :1:<spec>`, or None where git holds none.

    `kind` is `both` where every line of each side is blank, or a rule or
    proof line whose id `base` does not hold, or holds with the same text on
    both sides; `highest` where each side holds only `> Highest-` lines and
    neither drops one `base` holds; else `left`, with `why` saying so in
    words.
    """
    found = []
    for block in _blocks(lines):
        sides = [[line for _number, line in block[key] if line.strip()]
                 for key in ('ours', 'theirs')]
        texts = [line for side in sides for line in side]
        kind, why = 'both', ''
        if base is None:
            kind, why = 'left', LEFT_NO_BASE
        elif texts and all(_HIGHEST_LINE_RE.match(_bare(line).strip())
                           for line in texts):
            values = [_highest_values(block[key])
                      for key in ('ours', 'theirs')]
            # A kind one side alone holds was added by it, unless the
            # starting version held that line: then the other side removed it.
            missing = [name for name in _KINDS
                       if (name in values[0]) != (name in values[1])
                       and re.search(r'^>[ \t]*Highest-%s:' % name, base,
                                     re.MULTILINE)]
            if missing:
                kind, why = 'left', LEFT_REMOVED % ('the > Highest-%s: line'
                                                    % missing[0])
            else:
                kind = 'highest'
        elif not all(_line_id(line) for line in texts):
            kind, why = 'left', LEFT_OTHER_LINE
        else:
            why = _left_why(sides, base)
            kind, why = ('left', why) if why else ('both', '')
        found.append({'start': block['start'], 'end': block['end'],
                      'ours': block['ours'], 'theirs': block['theirs'],
                      'labels': block['labels'], 'kind': kind, 'why': why})
    return found


def _kept(conflict):
    """The lines a `both` or `highest` conflict leaves, `[(number, line)]`.

    `both`: the first side's lines, then the second's that the first does
    not hold. `highest`: of each kind, the line naming the higher number,
    the first side's where both name one number."""
    ours, theirs = conflict['ours'], conflict['theirs']
    if conflict['kind'] == 'both':
        held = {line.strip() for _number, line in ours}
        return ours + [(number, line) for number, line in theirs
                       if line.strip() not in held]
    values = [_highest_values(side) for side in (ours, theirs)]
    best = {}
    for side in values:
        for kind, entry in side.items():
            if kind not in best or entry[0] > best[kind][0]:
                best[kind] = entry
    order = [kind for side in values
             for kind in sorted(side, key=lambda name: side[name][1])]
    return [best[kind][1:] for kind in dict.fromkeys(order)]


def resolve(lines, found):
    """`lines` with each `both` and `highest` conflict of `found` resolved,
    as `[(number, line)]`: each kept line with the number it has on disk. A
    conflict that is `left` stays whole, git's own lines included."""
    by_start = {conflict['start']: conflict for conflict in found
                if conflict['kind'] != 'left'}
    resolved, number = [], 1
    while number <= len(lines):
        conflict = by_start.get(number)
        if conflict is None:
            resolved.append((number, lines[number - 1]))
            number += 1
            continue
        resolved.extend(_kept(conflict))
        number = conflict['end'] + 1
    return resolved


def _count(side):
    return len([line for _number, line in side if line.strip()])


def _second(first, second):
    """The second side's count: with its noun only where the noun differs
    from the first side's, as `1 line from HEAD and 1 from qa/login`."""
    if (first == 1) == (second == 1):
        return '%d' % second
    return _plural(second, 'line')


def _keeps_both(name, conflict):
    first, second = _count(conflict['ours']), _count(conflict['theirs'])
    return KEEPS_BOTH % (name, conflict['start'], _plural(first, 'line'),
                         conflict['labels'][0], _second(first, second),
                         conflict['labels'][1])


def _conflict_lines(name, found):
    """The plan's lines for the conflicts, one per conflict; a conflict
    holding both kinds of `> Highest-` line has one per kind that differs."""
    lines = []
    for conflict in found:
        start = conflict['start']
        if conflict['kind'] == 'left':
            lines.append(LEFT % (name, start, conflict['why'], name))
        elif conflict['kind'] == 'both':
            lines.append(_keeps_both(name, conflict))
        else:
            values = [_highest_values(conflict[key])
                      for key in ('ours', 'theirs')]
            # One line per kind the two sides wrote differently; where
            # none differs, the first kind both wrote.
            kinds = [kind for kind in sorted(
                values[0], key=lambda name: values[0][name][1])
                if kind in values[1]]
            differ = [kind for kind in kinds
                      if values[0][kind][0] != values[1][kind][0]]
            for kind in differ or kinds[:1]:
                ours, theirs = values[0][kind][0], values[1][kind][0]
                lines.append(TAKES_HIGHER % (name, start, kind,
                                             max(ours, theirs), ours, theirs))
            if not kinds:
                lines.append(_keeps_both(name, conflict))
    return lines


def _outside(info, found, kept):
    """`info` without the numbers written twice that a conflict left as it
    is holds a line of: such a number waits for the person's choice, and the
    next run sees what they chose."""
    left = [(conflict['start'], conflict['end']) for conflict in found
            if conflict['kind'] == 'left']
    inside = {index for index, (number, _line) in enumerate(kept, 1)
              if any(start <= number <= end for start, end in left)}
    waits = {item for item, written in (info.get('doubled_lines') or {}).items()
             if any(line['line'] in inside for line in written)}
    if not waits:
        return info
    return dict(
        info,
        doubled_lines={item: written for item, written
                       in info['doubled_lines'].items() if item not in waits},
        doubled_rules=[item for item in info['doubled_rules']
                       if item not in waits],
        doubled_proofs=[item for item in info['doubled_proofs']
                        if item not in waits])


def _base(project_root, spec_path):
    """The version of the spec both sides of a merge started from, as git
    holds it while the file is not yet marked resolved, or None."""
    return drift_module._git(project_root, [
        'show', '--end-of-options', ':1:%s' % spec_path]) or None


# ---------------------------------------------------------------------------
# The renumbering
# ---------------------------------------------------------------------------

def _moves(project_root, info, ref, spec_lines, disk):
    """Step 1: `(lines, spec edits, moved)`. `spec_lines` are the spec's
    lines as `info` was read from them, and `disk` maps a line's number
    there to its number in the file on disk, the one printed. `moved` maps
    each id that moves to `(new id, the moving line's text)`; a spec edit is
    `(line number in spec_lines, function of the line)`."""
    lines, edits, moved = [], [], {}
    follows = []
    for entry in drift_module.numbers_twice(
            project_root, {info['name']: info}, ref,
            spec_lines={info['name']: spec_lines}):
        item, to, moving = entry['id'], entry['to'], entry['moves']
        shape = {'neither': MOVES_NEITHER,
                 'no_default': MOVES_NO_DEFAULT}.get(entry['case'], MOVES)
        values = (info['name'], item, disk(moving['line']), to, moving['text'])
        lines.append(shape % (values + ((ref,) if shape is MOVES_NEITHER
                                        else ())))
        edits.append((moving['line'],
                      lambda text, old=item, new=to: _set_id(text, old, new)))
        moved[item] = (to, moving['text'])
        for follow in entry.get('follows') or ():
            follows.append(PROOF_FOLLOWS % (info['name'], follow['proof'],
                                            disk(follow['line']), to))
            edits.append((follow['line'], lambda text, old=item, new=to:
                           _set_rule(text, old, new)))
    return lines + follows, edits, moved


def _comments(project_root, info, moved):
    """Steps 2 and 3: `(lines, file edits, the number of comments changed)`.
    A file edit is `(path, line number, function of the line)`."""
    name = info['name']
    cache = {}
    moves, follows, uncommitted, edits = [], [], [], []
    doubled = set(info.get('doubled_lines') or {})
    scanned = markers_module.scan(project_root)
    # Step 3's comments, each read where its test was last changed.
    stale = {(entry['file'], entry['line'], entry['id']): entry['now_under']
             for entry in wording_module.stale_comments(
                 project_root, {name: info}, scanned=scanned)}
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
                to = stale.get((path, marker.line, marker.id))
                if not to:
                    continue
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

    `{'lines', 'resolved', 'conflicts', 'spec_edits', 'highest_edits',
    'comment_edits', 'spec_lines', 'comments'}`: `lines` are the plan's lines
    in order, the conflicts' first, without the closing line; `resolved` is
    the spec's text, line by line, once its conflicts are resolved, which
    the edits are made over; `conflicts` counts the conflicts resolved.
    """
    on_disk = specs_module.scan_specs(project_root).get(feature)
    if on_disk is None:
        return None
    path = on_disk['spec_path']
    spec_lines = _read(os.path.join(project_root, *path.split('/')))
    found = conflicts(spec_lines, _base(project_root, path))
    kept = resolve(spec_lines, found)
    resolved = [line for _number, line in kept]
    info = specs_module._parse_spec(feature, path, ''.join(resolved))
    disk = lambda number: kept[number - 1][0]

    ref = drift_module.default_branch(project_root)
    move_lines, spec_edits, moved = _moves(
        project_root, _outside(info, found, kept), ref, resolved, disk)
    comment_lines, comment_edits, comments = _comments(project_root, info,
                                                       moved)
    highest_lines, highest_edits = _highest_lines(info, moved)
    other = _other_branches(project_root, info, moved, ref)
    return {'info': info,
            'lines': (_conflict_lines(feature, found) + move_lines
                      + comment_lines + highest_lines + other),
            'resolved': resolved,
            'conflicts': len([conflict for conflict in found
                              if conflict['kind'] != 'left']),
            'spec_edits': spec_edits, 'highest_edits': highest_edits,
            'comment_edits': comment_edits, 'spec_lines': len(spec_edits),
            'comments': comments}


def apply(project_root, planned):
    """Write the spec with its conflicts resolved, then make the edits
    `planned` holds. Nothing is staged or committed."""
    spec = os.path.join(project_root,
                        *planned['info']['spec_path'].split('/'))
    lines = list(planned['resolved'])
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


def _answered_yes(out, source):
    """Ask `ASK` on `out` and read one line of `source`. Reading the input
    rather than testing for a terminal lets a script pipe its answer in, and
    the end of input is no, so a run with nobody there changes nothing."""
    out.write(ASK)
    out.flush()
    answer = source.readline()
    if not source.isatty():
        # No terminal echoed the answer's line end, so the next line starts
        # on a line of its own.
        out.write('\n')
    return answer.strip().lower() in ('y', 'yes')


def run(project_root, feature, dry_run=False, yes=False, out=None,
        source=None):
    """Print the plan; make it on `yes` or a yes read from `source`, never
    on `dry_run`; return the exit code."""
    out = out or sys.stdout
    planned = plan(project_root, feature)
    if planned is None:
        print(NOT_A_SPEC % feature, file=out)
        return EXIT_NOT_A_SPEC
    for line in planned['lines']:
        print(line, file=out)
    renumbers = bool(planned['spec_edits'] or planned['comment_edits'])
    if not renumbers and not planned['conflicts']:
        print(NOTHING % feature, file=out)
        return EXIT_OK
    if dry_run:
        print(DRY_RUN, file=out)
        return EXIT_OK
    if not yes and not _answered_yes(out, source or sys.stdin):
        print(NOT_DONE, file=out)
        return EXIT_OK
    apply(project_root, planned)
    resolved = _plural(planned['conflicts'], 'conflict')
    if not renumbers:
        print(RESOLVED_ALONE % (resolved, feature), file=out)
        return EXIT_OK
    if planned['conflicts']:
        print(RESOLVED % (resolved, feature), file=out)
    print(DONE % (feature, _plural(planned['spec_lines'], 'spec line'),
                  _plural(planned['comments'], 'test comment')), file=out)
    return EXIT_OK


def main(argv=None):
    console_module.force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog='renumber.py',
        description='Resolve the conflict a merge left in a spec, renumber a '
                    'number it writes twice, and move the test comments that '
                    'name it. It asks before it changes a file.')
    parser.add_argument('feature')
    how = parser.add_mutually_exclusive_group()
    how.add_argument('--dry-run', action='store_true',
                     help='print the plan and change nothing')
    how.add_argument('--yes', action='store_true',
                     help='make the edits without asking')
    parser.add_argument('--project-root', default='.')
    args = parser.parse_args(argv)
    return run(args.project_root, args.feature, dry_run=args.dry_run,
               yes=args.yes)


if __name__ == '__main__':
    sys.exit(main())
