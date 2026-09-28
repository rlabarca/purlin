"""Who committed a file under `.purlin/evidence/ci/`.

The folder is the source, and nothing on the git host guards it: a person can
write a file there. What keeps it honest is the tag run, which asks of each
`ci/` file who made the commit that last changed it, and fails when the
answer is not the runner's own identity. This module answers that question.

`git log -1 --format='%G? %cn %ce %an %H'` over the file's path names the
signature status, the committer name and email, the author name and the
commit of the last commit that touched it. No commit means the file is not
committed, which is `local`.

The identity decides and the signature confirms. A commit GitHub made
through its API carries `GitHub <noreply@github.com>` as the committer and
`github-actions[bot]` as the author, and it is signed with a key almost no
checkout holds, so requiring a checked signature would throw away every
file CI wrote. Azure DevOps signs nothing, so its commits are read on the
committer name alone, which is what its documentation offers.
"""

import shutil
import subprocess

# The Azure DevOps build identities, read on the committer name alone.
_AZURE_COMMITTERS = ('Project Collection Build Service', 'Azure DevOps')

# What a commit GitHub made through its API looks like. GitHub signs the
# commit with its own key and records its web identity as the committer, so
# the committer is `GitHub <noreply@github.com>` and the Actions token is the
# author. Reading the committer name alone misses it.
_GITHUB_COMMITTERS = ('github-actions[bot]', 'github-actions')
_GITHUB_COMMITTER_EMAIL = 'noreply@github.com'
_GITHUB_ACTIONS_AUTHOR = 'github-actions[bot]'


def signature_confirms(signature, signed=False):
    """True when `%G?` does not contradict a commit the git host claims.

    `G` and `U` are a checked signature and confirm it. `B` is a signature
    that does not match the commit, which is the one answer that says the
    commit was changed after it was made. Every other answer (`E`, `X`, `Y`,
    `R`) is a signature this machine holds no current key for, which is the
    ordinary case for the git host's own key and says nothing against the
    commit.

    `N` is the one answer that means two things. git prints it both for a
    commit that carries no signature at all and for a commit whose signature
    it could not even try to check, which is what an ssh signature read by a
    checkout with no allowed-signers file is. `signed` says which: with a
    signature on the commit, `N` is a machine that cannot check and the
    commit stands; with none, it is an unsigned commit, and then the only
    reason to let it stand is a machine with no gpg, where every commit reads
    as unsigned.
    """
    if signature == 'B':
        return False
    if signature == 'N':
        return signed or shutil.which('gpg') is None
    return True


def carries_a_signature(project_root, commit):
    """True when the commit object holds a signature header.

    `git cat-file commit` prints the commit's headers before a blank line and
    its message after, and a signed commit carries a `gpgsig` header among
    them whether or not this machine can check it. That is the one reading
    that tells `%G?` `N` for "no signature" apart from `N` for "no way to
    check this one".
    """
    try:
        result = subprocess.run(
            ['git', 'cat-file', 'commit', commit],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return False
    if result.returncode != 0:
        return False
    for line in result.stdout.split('\n'):
        if not line.strip():
            return False
        if line.startswith('gpgsig'):
            return True
    return False


def committed_by(project_root, rel_path):
    """`ci` when the git host's runner made the last commit to a file, else `local`."""
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%G?\t%cn\t%ce\t%an\t%H',
             '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return 'local'
    if result.returncode != 0 or not result.stdout.strip():
        return 'local'
    # `%G?` prints nothing at all when git neither found nor could look for a
    # signature, so the first field is empty and stripping the whole line
    # would move every field one place to the left.
    parts = result.stdout.split('\n', 1)[0].split('\t')
    parts += [''] * (5 - len(parts))
    signature, committer, committer_email, author, commit = parts[:5]
    if committer in _AZURE_COMMITTERS:
        return 'ci'
    made_by_github = (committer in _GITHUB_COMMITTERS
                      or (committer_email == _GITHUB_COMMITTER_EMAIL
                          and author == _GITHUB_ACTIONS_AUTHOR))
    if not made_by_github:
        return 'local'
    signed = (signature == 'N'
              and carries_a_signature(project_root, commit))
    if signature_confirms(signature, signed):
        return 'ci'
    return 'local'
