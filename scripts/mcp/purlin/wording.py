#!/usr/bin/env python3
"""The test comments to correct: a comment naming a proof whose wording changed.

    python3 scripts/mcp/purlin/wording.py [--project-root DIR] [--file PATH ...]

Prints each entry's `text`, one per line, then `<n> test comments to correct.`,
`1 test comment to correct.` or `No test comment to correct.`, and exits 0.

A test shows the proof its comment names as the proof read when the test was
last changed. Where the proof's wording has changed since, the test may no
longer show it, so the comment is named until the test itself changes. A
test is last changed at the newest commit `git blame` names for the lines
below its comment down to the test's last line, or for any line of its file
when the file is run whole. A test with a line not yet committed is never
named: the person changing it is the one who reads the new wording.

The payload carries each line in its warnings and counts it under
`to_correct`; a test run prints them after its `Markers:` line; drift reads
them for the range it covers; the renumber helper moves a comment to
`now_under`; the evidence package reads `test_last_change` for who last
changed each test.
"""

import argparse
import os
import re
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import notices                                     # noqa: E402

# What follows what changed in the proof's wording, in the sentence that says
# what is wrong (`notices.change_sentence`): the test's file and line, the
# sha7 of the commit that last changed the test.
STALE_AFTER = ' after %s:%d last changed (%s)'
# What to do where the old wording is now another proof's: that proof.
STALE_MOVE = 'Move the comment to %s, which holds the old wording.'

NONE_TO_CORRECT = 'No test comment to correct.'
ONE_TO_CORRECT = '1 test comment to correct.'
MANY_TO_CORRECT = '%d test comments to correct.'

# A proof line, read the same way at any commit: its id and its words after
# the rule it proves, tags included, `@slow` apart: it says when the test
# runs and nothing the test must show.
_PROOF_RE = re.compile(r'^-\s+(PROOF-\d+)\s*\([^)]*\)[^:\n]*:[ \t]*(.*)$', re.M)
_UNCOMMITTED = '0' * 40


def stale_comments(project_root, features, scanned=None):
    """One entry per test comment naming a proof whose wording, at the commit that last
    changed the test, differs from its wording now. A test is last changed at the newest
    commit git blame names for the lines below its comment down to the test's last line,
    or for any line of its file when the file is run whole. A test with an uncommitted
    line is never named. By file, then line.
    Each: {'file','line','feature','id','commit' (sha7),'old','new','now_under','text'}."""
    from purlin import markers as markers_module
    if scanned is None:
        scanned = markers_module.scan(project_root)
    reader = _Reader(project_root)
    reader.prefetch(sorted(scanned))
    now = {name: proof_words(_read_file(project_root, info.get('spec_path')))
           for name, info in (features or {}).items() if info.get('spec_path')}
    candidates = []
    for path in sorted(scanned):
        listing = scanned[path]
        for marker, first, last in _marked_spans(project_root, path, listing):
            words = now.get(marker.feature) or {}
            if not marker.id.startswith('PROOF-') or marker.id not in words:
                continue
            blamed = reader.last_change(path, first, last)
            if blamed is not None:
                candidates.append((path, marker, blamed[0]))
    reader.fetch_specs({(sha, features[marker.feature]['spec_path'])
                        for _path, marker, sha in candidates})
    found = []
    for path, marker, sha in candidates:
        words = now[marker.feature]
        old = reader.words_at(sha, features[marker.feature]['spec_path']).get(
            marker.id)
        new = words[marker.id]
        if old is None or old == new:
            continue
        now_under = next((other for other in sorted(words, key=_number)
                          if other != marker.id and words[other] == old), None)
        text = stale_line(features[marker.feature], path, marker, sha[:7],
                          old, new, now_under)
        found.append({'file': path, 'line': marker.line,
                      'feature': marker.feature, 'id': marker.id,
                      'commit': sha[:7], 'old': old, 'new': new,
                      'now_under': now_under, 'text': text})
    found.sort(key=lambda entry: (entry['file'], entry['line'], entry['id']))
    return found


def stale_line(info, path, marker, commit, old, new, now_under):
    """One test comment to correct, as every surface prints it:
    `package PROOF-3 (RULE-3): test comment to correct. "sixteen" became
    "seventeen" after tests/test_export.py:336 last changed (82c91f6). Run
    purlin:build package.` on one line. Neither wording is printed whole."""
    about, rule = notices.about_proof(info, marker.feature, marker.id)
    wrong = notices.change_sentence(
        old, new, STALE_AFTER % (path, marker.line, commit))
    do = (STALE_MOVE % now_under if now_under
          else notices.run('purlin:build %s' % marker.feature))
    return notices.line('to_correct', about, wrong, do, feature=marker.feature,
                        rule=rule, proof=marker.id)


def test_last_change(project_root, path, marker_line, end_line, reader=None):
    """`(sha, author email)` of that commit, or None. `reader`, from
    `reader()`, is handed in by a caller that asks about many tests, so each
    file is blamed once."""
    reader = reader or _Reader(project_root)
    return reader.last_change(path, marker_line + 1, end_line)


def reader(project_root, paths=()):
    """What `test_last_change` reads git through, with `paths` blamed already."""
    made = _Reader(project_root)
    made.prefetch(sorted(set(paths)))
    return made


def proof_words(text):
    """`{PROOF-N: its words}` of a spec's text, whitespace folded, `@slow` left out."""
    return {proof_id: _without_slow(' '.join(words.split()))
            for proof_id, words in _PROOF_RE.findall(text or '')}


def _without_slow(words):
    """A proof's words with its `@slow` tag taken out, every other tag kept."""
    from purlin import specs as specs_module
    text, _manual, _env, _unknown, slow = specs_module.split_proof_tags(words)
    if not slow:
        return words
    return text + re.sub(r'\s+@slow\b', '', words[len(text):], count=1)


def test_source(path, text, test):
    """`(first line, last line, source)` of one test declaration, or None.

    A Python test is bounded by its lines, decorators included; a test of
    another language by the offsets its reader gives. Line ends read as `\\n`.
    """
    if test is None or test.start is None or test.end is None:
        return None
    text = text.replace('\r\n', '\n')
    if path.endswith('.py'):
        lines = text.split('\n')
        return test.start, test.end, '\n'.join(lines[test.start - 1:test.end])
    first = text.count('\n', 0, test.start) + 1
    last = text.count('\n', 0, test.end) + 1
    return first, last, text[test.start:test.end]


def _marked_spans(project_root, path, listing):
    """`(marker, first line, last line)` for each marker tied to a test.

    The span runs from the line below the marker to the test's last line; a
    file run whole spans every line, `last` None.
    """
    if listing.whole:
        return [(marker, 1, None) for marker in listing.markers]
    text = _read_file(project_root, path) or ''
    spans = []
    for test in listing.tests:
        bounds = test_source(path, text, test)
        for marker in test.markers:
            last = bounds[1] if bounds else None
            spans.append((marker, marker.line + 1, last))
    return spans


def _number(proof_id):
    digits = proof_id.split('-')[-1]
    return int(digits) if digits.isdigit() else 0


def _read_file(project_root, rel_path):
    if not rel_path:
        return None
    try:
        full = os.path.join(project_root, *rel_path.split('/'))
        with open(full, 'r', encoding='utf-8') as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return None


class _Reader(object):
    """Git's answers, each asked once: one blame per test file, one show per spec."""

    def __init__(self, project_root):
        self.root = project_root
        self.blames = {}
        self.specs = {}

    def _git(self, *args):
        try:
            result = subprocess.run(['git'] + list(args), capture_output=True,
                                    cwd=self.root, timeout=60)
        except (subprocess.SubprocessError, OSError):
            return None
        if result.returncode != 0:
            return None
        return result.stdout.decode('utf-8', 'replace')

    def prefetch(self, paths):
        """Blame every file at once, a few processes side by side."""
        from concurrent.futures import ThreadPoolExecutor
        wanted = [path for path in paths if path not in self.blames]
        with ThreadPoolExecutor(max_workers=8) as pool:
            for path, text in zip(wanted, pool.map(
                    lambda path: self._git('blame', '--porcelain', '--', path),
                    wanted)):
                self.blames[path] = _parse_blame(text)

    def blame(self, path):
        """`[(sha, time, email)]` per line of the file as it stands, or None."""
        if path not in self.blames:
            self.blames[path] = _parse_blame(
                self._git('blame', '--porcelain', '--', path))
        return self.blames[path]

    def last_change(self, path, first, last):
        lines = self.blame(path)
        if not lines:
            return None
        last = len(lines) if last is None else min(last, len(lines))
        span = lines[max(first, 1) - 1:last]
        if not span or any(sha == _UNCOMMITTED for sha, _when, _who in span):
            return None
        newest = max(when for _sha, when, _who in span)
        tied = sorted({sha for sha, when, _who in span if when == newest})
        sha = tied[0]
        if len(tied) > 1:
            # Commits made in the same second: the one the others lead to.
            sha = (self._git('rev-list', '--topo-order', '--max-count=1',
                             '--end-of-options', *tied) or sha).strip() or sha
        email = next(who for line_sha, _when, who in span if line_sha == sha)
        return sha, email

    def fetch_specs(self, keys):
        """Read every `(sha, spec path)` asked for through one `git cat-file`."""
        wanted = sorted(key for key in keys if key not in self.specs)
        if not wanted:
            return
        request = ''.join('%s:%s\n' % key for key in wanted).encode('utf-8')
        try:
            result = subprocess.run(['git', 'cat-file', '--batch'], input=request,
                                    capture_output=True, cwd=self.root, timeout=60)
        except (subprocess.SubprocessError, OSError):
            return
        out, at = result.stdout, 0
        for key in wanted:
            end = out.find(b'\n', at)
            if end < 0:
                break
            header = out[at:end].split()
            at = end + 1
            if len(header) == 3 and header[1] == b'blob':
                size = int(header[2])
                self.specs[key] = proof_words(
                    out[at:at + size].decode('utf-8', 'replace'))
                at += size + 1

    def words_at(self, sha, spec_path):
        key = (sha, spec_path)
        if key not in self.specs:
            text = self._git('show', '--end-of-options', '%s:%s' % (sha, spec_path))
            if text is None:
                text = self._moved(sha, spec_path)
            self.specs[key] = proof_words(text)
        return self.specs[key]

    def _moved(self, sha, spec_path):
        """The spec's text at `sha` where it then sat in another folder."""
        listed = self._git('ls-tree', '-r', '--name-only', sha, '--', 'specs')
        name = spec_path.rsplit('/', 1)[-1]
        for path in (listed or '').splitlines():
            if path.rsplit('/', 1)[-1] == name:
                return self._git('show', '--end-of-options', '%s:%s' % (sha, path))
        return None


_HEADER_RE = re.compile(r'^([0-9a-f]{40}) \d+ \d+')


def _parse_blame(text):
    """`git blame --porcelain` read into one `(sha, committer time, author email)` per line."""
    if text is None:
        return None
    commits = {}
    lines = []
    current = None
    for line in text.split('\n'):
        if line.startswith('\t'):
            lines.append(current)
        elif line.startswith('committer-time '):
            commits[current]['time'] = int(line[15:])
        elif line.startswith('author-mail '):
            commits[current]['email'] = line[12:].strip().strip('<>')
        elif len(line) > 41 and line[40] == ' ':
            header = _HEADER_RE.match(line)
            if header:
                current = header.group(1)
                commits.setdefault(current, {'time': 0, 'email': ''})
    return [(sha, commits[sha]['time'], commits[sha]['email']) for sha in lines]


def count_line(count):
    """The command line's last line."""
    if count == 0:
        return NONE_TO_CORRECT
    return ONE_TO_CORRECT if count == 1 else MANY_TO_CORRECT % count


def main(argv=None):
    parser = argparse.ArgumentParser(prog='wording.py')
    parser.add_argument('--project-root', default=None)
    parser.add_argument('--file', nargs='+', action='extend', default=[])
    args = parser.parse_args(argv)
    from config_engine import find_project_root
    from purlin import markers as markers_module, specs as specs_module
    root = os.path.abspath(args.project_root or find_project_root())
    scanned = markers_module.scan(root)
    if args.file:
        wanted = {os.path.relpath(os.path.abspath(path), root).replace(os.sep, '/')
                  if os.path.isabs(path) else path.replace(os.sep, '/')
                  for path in args.file}
        scanned = {path: found for path, found in scanned.items() if path in wanted}
    entries = stale_comments(root, specs_module.scan_specs(root), scanned)
    for entry in entries:
        print(entry['text'])
    print(count_line(len(entries)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
