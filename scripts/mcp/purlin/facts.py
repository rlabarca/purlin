"""The two facts: whether the tests are met, and whether this code is signed.

Every surface states both in these words: the status opens on them, the
dashboard's two boxes read them from the payload, and a test run ends on the
status. `Tests: met` where no work left is of a blocking kind;
`Sign-off: signed 0.1.0 at a1b2c3d` where the newest `signed/*` tag on HEAD
or an ancestor of it sits on code nothing has changed since, else
`signed 0.1.0, 4 commits since`, or `not signed` where there is no such tag.
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


def tests_fact(payload):
    """`met` when no entry of `left` is of a kind in summary.BLOCKING, else `not met`."""
    from purlin import summary
    blocking = [item for item in payload.get('left') or ()
                if item.get('kind') in summary.BLOCKING]
    return TESTS_NOT_MET if blocking else TESTS_MET


def signoff_fact(project_root):
    """{'word','version','commit','since'} for the newest signed/* tag on HEAD or an
    ancestor of it, numbered versions compared as numbers: SIGNED_AT where
    package.only_records_between(tag commit, HEAD), else SIGNED_SINCE with the count of
    commits from the tag to HEAD; word NOT_SIGNED and the rest None where there is none."""
    none = {'word': NOT_SIGNED, 'version': None, 'commit': None, 'since': None}
    tags = git_line(project_root, 'tag', '--merged', 'HEAD', '--list', TAG_PREFIX + '*')
    if not tags:
        return none
    name = sorted(tags.split(), key=version_order)[-1]
    commit = git_line(project_root, 'rev-list', '-n', '1', name)
    if not commit:
        return none
    version = name[len(TAG_PREFIX):]
    since = commits_since(project_root, commit)
    if records_only_since(project_root, commit):
        word = SIGNED_AT % (version, commit[:7])
    else:
        word = since_word(version, since)
    return {'word': word, 'version': version, 'commit': commit, 'since': since}


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


def commits_since(project_root, commit):
    """How many commits HEAD holds that `commit` does not."""
    counted = git_line(project_root, 'rev-list', '--count', '%s..HEAD' % commit)
    return int(counted) if counted.isdigit() else 0


def version_order(name):
    """A sort key for a tag name: numbered versions as numbers, after any other name."""
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
        result = subprocess.run(('git',) + args, capture_output=True, text=True,
                                cwd=project_root, timeout=15)
    except (subprocess.SubprocessError, OSError):
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''
