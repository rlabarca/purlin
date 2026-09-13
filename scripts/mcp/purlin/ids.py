"""Allocate, check and renumber rule and proof ids.

Two branches editing one spec will both reach for the next free number, so
`purlin:spec` allocates against a shared ref rather than the working tree:
`origin/main` when the checkout has it, else `HEAD`. Two branches then take
the same number only when neither has fetched, which is what
`duplicate_ids` finds after the merge and `renumber` fixes.

Ids are never reused. A retired rule leaves its number vacant and the rules
that remain keep the numbers they had: renumbering silently repoints every
test marker and every approval that already names the old id.
"""

import os
import re
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import specs as specs_module

_RULE_ID_RE = re.compile(r'\bRULE-(\d+)\b')
_PROOF_ID_RE = re.compile(r'\bPROOF-(\d+)\b')


def allocation_ref(project_root):
    """The ref ids are allocated against: `origin/main` when it exists.

    Falling back to `HEAD` is what lets a fresh checkout with no remote work
    at all; a project with a remote allocates against what everyone shares,
    so two branches cut from the same point do not both take RULE-9.
    """
    branch = _default_branch(project_root)
    for ref in ('refs/remotes/origin/%s' % branch, 'refs/remotes/origin/main'):
        if _ref_exists(project_root, ref):
            return ref
    return 'HEAD'


def _default_branch(project_root):
    try:
        result = subprocess.run(
            ['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return 'main'
    if result.returncode != 0:
        return 'main'
    return result.stdout.strip().rsplit('/', 1)[-1] or 'main'


def _ref_exists(project_root, ref):
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--verify', '--quiet', '--end-of-options', ref],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return False
    return result.returncode == 0


def _spec_text_at(project_root, spec_path, ref):
    """A spec's text at a ref, or '' when the ref does not carry it."""
    if ref == 'HEAD' and not _ref_exists(project_root, 'HEAD'):
        return ''
    try:
        result = subprocess.run(
            ['git', 'show', '--end-of-options', '%s:%s' % (ref, spec_path)],
            capture_output=True, text=True, cwd=project_root, timeout=15)
    except (subprocess.SubprocessError, OSError):
        return ''
    return result.stdout if result.returncode == 0 else ''


def next_ids(project_root, spec_path, ref=None):
    """`(next_rule, next_proof)` for a spec, allocated against a ref.

    The working tree and the ref are both read and the higher number wins, so
    an id already written locally is never handed out twice in one session.
    """
    ref = ref or allocation_ref(project_root)
    texts = [_spec_text_at(project_root, spec_path, ref)]
    full = os.path.join(project_root, spec_path)
    if os.path.isfile(full):
        try:
            with open(full, 'r', encoding='utf-8') as handle:
                texts.append(handle.read())
        except (IOError, OSError, UnicodeDecodeError):
            pass
    rule_max = 0
    proof_max = 0
    for text in texts:
        for m in _RULE_ID_RE.finditer(text or ''):
            rule_max = max(rule_max, int(m.group(1)))
        for m in _PROOF_ID_RE.finditer(text or ''):
            proof_max = max(proof_max, int(m.group(1)))
    return rule_max + 1, proof_max + 1


def duplicate_ids(project_root, spec_path):
    """`{'rules': {id: count}, 'proofs': {id: count}}` for ids written twice.

    A merge that took both sides of a spec leaves two RULE-9 lines. Nothing
    downstream can tell which test or which approval means which, so the
    duplicate is reported rather than guessed at.
    """
    full = os.path.join(project_root, spec_path)
    try:
        with open(full, 'r', encoding='utf-8') as handle:
            content = handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return {'rules': {}, 'proofs': {}}
    rules = _count_ids(specs_module.extract_section(content, '## Rules'),
                       r'^-\s+(RULE-\d+):')
    proofs = _count_ids(specs_module.extract_section(content, '## Proof'),
                        r'^-\s+(PROOF-\d+)\s*\(')
    return {
        'rules': {rid: count for rid, count in rules.items() if count > 1},
        'proofs': {pid: count for pid, count in proofs.items() if count > 1},
    }


def _count_ids(section, pattern):
    counts = {}
    if not section:
        return counts
    regex = re.compile(pattern)
    for line in section.splitlines():
        m = regex.match(line.strip())
        if m:
            counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return counts


def renumber(project_root, spec_path, mapping, extra_paths=()):
    """Rewrite ids across the spec, its test markers and its approvals.

    `mapping` is `{'RULE-9': 'RULE-14', 'PROOF-9': 'PROOF-14'}`. Every file
    that names an old id is rewritten in one pass, and an approval file whose
    name carries the old id is renamed with it: an approval that still points
    at a number the spec no longer uses binds nothing.

    Returns the list of project-relative paths that changed.
    """
    if not mapping:
        return []
    changed = []
    targets = [spec_path]
    targets.extend(extra_paths or ())
    targets.extend(_approval_paths(project_root, spec_path))

    for rel_path in targets:
        full = os.path.join(project_root, rel_path)
        if not os.path.isfile(full):
            continue
        try:
            with open(full, 'r', encoding='utf-8') as handle:
                text = handle.read()
        except (IOError, OSError, UnicodeDecodeError):
            continue
        rewritten = _apply(text, mapping)
        if rewritten == text:
            continue
        try:
            with open(full, 'w', encoding='utf-8') as handle:
                handle.write(rewritten)
        except (IOError, OSError):
            continue
        changed.append(rel_path)

    for rel_path in _approval_paths(project_root, spec_path):
        basename = os.path.basename(rel_path)
        old_id = basename.split('.')[0]
        new_id = mapping.get(old_id)
        if not new_id:
            continue
        full = os.path.join(project_root, rel_path)
        renamed = os.path.join(os.path.dirname(full),
                               new_id + basename[len(old_id):])
        if os.path.exists(full) and not os.path.exists(renamed):
            os.rename(full, renamed)
            changed.append(os.path.relpath(renamed, project_root)
                           .replace(os.sep, '/'))
    return changed


def _apply(text, mapping):
    """Replace whole ids only, longest first, so RULE-1 never eats RULE-12."""
    for old in sorted(mapping, key=len, reverse=True):
        text = re.sub(r'\b%s\b' % re.escape(old), mapping[old], text)
    return text


def _approval_paths(project_root, spec_path):
    directory = os.path.join(
        project_root, os.path.dirname(spec_path),
        os.path.basename(spec_path)[:-3] + '.approvals')
    if not os.path.isdir(directory):
        return []
    return [os.path.relpath(os.path.join(directory, name), project_root)
            .replace(os.sep, '/')
            for name in sorted(os.listdir(directory)) if name.endswith('.json')]
