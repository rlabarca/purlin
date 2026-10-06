"""The two facts: whether the tests are met, and whether this code is signed.

Every surface states both in these words: the status opens on them, the
dashboard's first two boxes read them from the payload, and a test run ends on the
status. `Tests: met` where no work left is of a blocking kind;
`Sign-off: signed 0.1.0 at a1b2c3d` where the newest version whose sign-off
counts sits on code nothing has changed since, else
`signed 0.1.0, 4 commits since`, or `not signed` where there is none. A
version is read from its `signed/*` tag on HEAD or an ancestor of it, where
`signatures.standing` decides whether the tag's sign-off counts and a tag
written by hand is passed over, with one warning. Where this checkout holds
no tag for a version whose sign-off files HEAD holds, as after a pull that
fetched no tag, `signatures.standing_by_files` reads the sign-off from those
files, with one line naming `git fetch --tags`.

`results_to_retake` answers a third question for the status's last line:
whether `purlin:sign` would refuse the committed results as they stand,
because some are recorded on an earlier version of the code or were taken
while files were changed and not committed.
"""

import os
import re
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXPORT_DIR = os.path.join(os.path.dirname(_MCP_DIR), 'export')

TESTS_MET = 'met'
TESTS_NOT_MET = 'not met'
SIGNED_AT = 'signed %s at %s'                 # version, sha7 of the tagged commit
SIGNED_SINCE = 'signed %s, %d commits since'  # 'signed 0.1.0, 1 commit since' for one
NOT_SIGNED = 'not signed'

# How far HEAD is from a signed commit, as a hand check's note says it.
AT_THIS_COMMIT = 'at this commit'
COMMITS_SINCE = '%d commits since'
ONE_COMMIT_SINCE = '1 commit since'

TAG_PREFIX = 'signed/'

# A sign-off read from its files: the tag, the version, the sha7 of the commit
# that added the sign-off.
TAG_NOT_HERE = 'The sign-off of %s at %s is read from its files.'
TAG_NOT_HERE_DO = 'Run git fetch --tags, or purlin:sign if no one wrote the tag.'


def tests_fact(payload):
    """`met` when no entry of `left` is of a kind in summary.BLOCKING, else `not met`."""
    from purlin import summary
    blocking = [item for item in payload.get('left') or ()
                if item.get('kind') in summary.BLOCKING]
    return TESTS_NOT_MET if blocking else TESTS_MET


def signoff_fact(project_root):
    """{'word','version','commit','since','warnings'} for the newest version whose
    sign-off counts, numbered versions compared as numbers. The versions read are
    those of the signed/* tags on HEAD or an ancestor of it, where
    `signatures.standing` answers, and those of the `.signoffs` folders HEAD holds
    with no tag of that name in this checkout, where `signatures.standing_by_files`
    answers with the commit that added the sign-off. SIGNED_AT where
    package.only_records_between(that commit, HEAD), else SIGNED_SINCE with the
    count of commits from it to HEAD; word NOT_SIGNED and the rest None where there
    is none. `warnings` holds one line per tag passed over on the way, newest
    first, the tag and why it is no sign-off, and TAG_NOT_HERE where the sign-off
    is read from its files."""
    from purlin import signatures
    warnings = []
    none = {'word': NOT_SIGNED, 'version': None, 'commit': None, 'since': None,
            'warnings': warnings}
    tags = git_line(project_root, 'tag', '--merged', 'HEAD', '--list', TAG_PREFIX + '*')
    tagged = {name[len(TAG_PREFIX):] for name in tags.split()}
    versions = tagged | set(signatures.signed_versions(project_root))
    for version in sorted(versions, key=version_order, reverse=True):
        name = TAG_PREFIX + version
        if version in tagged:
            stands, why = signatures.standing(project_root, version)
            if not stands:
                warnings.append(why)
                continue
            commit = git_line(project_root, 'rev-list', '-n', '1', name)
        else:
            # No tag on HEAD: the files answer where the checkout holds no
            # tag of that name at all. A tag on another branch, or files no
            # sign-off of which counts, leave the version not signed.
            commit, _why = signatures.standing_by_files(project_root, version)
            if not commit:
                continue
            from purlin import notices
            warnings.append(notices.line(
                'tag_not_here', name, TAG_NOT_HERE % (version, commit[:7]),
                TAG_NOT_HERE_DO))
        since = commits_since(project_root, commit)
        if records_only_since(project_root, commit):
            word = SIGNED_AT % (version, commit[:7])
        else:
            word = since_word(version, since)
        return {'word': word, 'version': version, 'commit': commit, 'since': since,
                'warnings': warnings}
    return none


def is_signed_here(signoff):
    """True where the sign-off reads `signed <version> at <sha7>`."""
    signoff = signoff or {}
    if not signoff.get('version') or not signoff.get('commit'):
        return False
    return signoff.get('word') == SIGNED_AT % (signoff['version'],
                                               signoff['commit'][:7])


def since_word(version, count):
    """`signed 0.1.0, 4 commits since`, singular for one."""
    if count == 1:
        return (SIGNED_SINCE % (version, count)).replace('commits', 'commit')
    return SIGNED_SINCE % (version, count)


def distance(project_root, commit):
    """`at this commit`, `1 commit since` or `<n> commits since` from `commit` to HEAD."""
    if records_only_since(project_root, commit):
        return AT_THIS_COMMIT
    count = commits_since(project_root, commit)
    return ONE_COMMIT_SINCE if count == 1 else COMMITS_SINCE % count


def records_only_since(project_root, commit):
    """True where `commit` is HEAD, or every commit since changes only `.purlin/`."""
    head = git_line(project_root, 'rev-parse', 'HEAD')
    if not commit or not head:
        return False
    if commit == head:
        return True
    if _EXPORT_DIR not in sys.path:
        sys.path.insert(0, _EXPORT_DIR)
    import package
    return bool(package.only_records_between(project_root, commit, head))


def _speaks(section, rule_id, ids):
    """True where the section holds a result for the rule, under its own id
    or one of its proofs'."""
    return rule_id in (section.get('rules') or {}) or any(
        isinstance(entry, dict) and entry.get('id') in ids
        for entry in section.get('proofs') or ())


def results_to_retake(project_root, features):
    """Why `purlin:sign` would refuse the results as they stand, or None:
    `(why, [(source, system)])`, each source and system once, in the order
    the sections are read.

    `why` is `code` where a section that holds a result for a rule names
    another version of the code than HEAD's, one from which a commit since
    changes a path outside `.purlin/` or the `tests` setting; else `dirty`
    where such a section was taken while files were changed and not
    committed. A result a run carried forward is recorded in a section that
    names the run's own commit, and counts there. `features` is the payload's
    feature entries; each rule is read under the spec that owns it. This is
    what `scripts/export/package.py` records for the sign-off, `off_code`
    then `taken_dirty`, read here from the working tree.
    """
    from purlin import evidence
    same = {}
    off, dirty = [], []
    for feature in features or ():
        name = feature.get('name')
        own = [rule for rule in feature.get('rules') or ()
               if rule.get('feature') == name]
        if not own:
            continue
        for entry in evidence.sections(evidence.load(project_root, name)):
            section = entry['section']
            if not any(_speaks(section, rule.get('id'),
                               {proof.get('id') for proof
                                in rule.get('proofs') or ()}
                               or {rule.get('id')})
                       for rule in own):
                continue
            key = (entry['source'], entry['os'])
            commit = section.get('commit') or ''
            if commit not in same:
                same[commit] = records_only_since(project_root, commit)
            if not same[commit] and key not in off:
                off.append(key)
            if section.get('dirty') is True and key not in dirty:
                dirty.append(key)
    if off:
        return 'code', off
    if dirty:
        return 'dirty', dirty
    return None


def commits_since(project_root, commit):
    """How many commits HEAD holds that `commit` does not."""
    counted = git_line(project_root, 'rev-list', '--count', '%s..HEAD' % commit)
    return int(counted) if counted.isdigit() else 0


def version_order(name):
    """A sort key for a tag name or a version: numbered versions as numbers, after
    any other name."""
    version = str(name)[len(TAG_PREFIX):] if str(name).startswith(TAG_PREFIX) else str(name)
    parts = re.split(r'[.\-+]', version)
    numbers = []
    for part in parts:
        if not part.isdigit():
            break
        numbers.append(int(part))
    return (bool(numbers), numbers, version)


def git_line(project_root, *args):
    try:
        result = subprocess.run(['git'] + list(args), capture_output=True, text=True,
                                cwd=project_root, timeout=15)
    except (subprocess.SubprocessError, OSError):
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''
