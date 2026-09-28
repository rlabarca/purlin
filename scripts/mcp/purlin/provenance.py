"""Who committed a file under `.purlin/evidence/ci/`.

The folder is the source, and nothing on the git host guards it: a person can
write a file there. What keeps it honest is the tag run, which asks of each
`ci/` file who made the commit that last changed it, and fails when the
answer is not the runner's own identity. This module answers that question,
once per git host, and neither answer rests on a name a person can set.

**GitHub.** `git log -1 --format='%G? %cn %ce %an %H'` over the file's path
names the signature status, the committer name and email, the author name
and the commit of the last commit that touched it. No commit means the file
is not committed, which is `local`. The identity decides and the signature
confirms. A commit GitHub made through its API carries
`GitHub <noreply@github.com>` as the committer and `github-actions[bot]` as
the author, and it is signed with a key almost no checkout holds, so
requiring a checked signature would throw away every file CI wrote.

**Azure DevOps.** A commit there carries no signature, and its committer is a
name anyone can type, so git alone cannot answer. The host can. The tag run
asks it two things with the build service's own token, `SYSTEM_ACCESSTOKEN`:
its own identity, `authenticatedUser.id` from `_apis/connectionData`, and for
the commit that last changed each file, who pushed it, `push.pushedBy.id`
from `_apis/git/repositories/<repo>/commits/<sha>`. The file counts only when
the two ids are the same. A different id, a commit record with no push, a
refusal, or no answer within `TIMEOUT_SECONDS` fails the file. A machine that
is not a runner holds no token, so it cannot ask: it says so, and the files
are counted as not checked, neither passed nor failed.

On either host a squash merge or a rebase that rewrites a `ci/` commit makes
a person's commit the last one to change the file, and the file fails.
"""

import json
import os
import shutil
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request

# What a commit GitHub made through its API looks like. GitHub signs the
# commit with its own key and records its web identity as the committer, so
# the committer is `GitHub <noreply@github.com>` and the Actions token is the
# author. Reading the committer name alone misses it.
_GITHUB_COMMITTERS = ('github-actions[bot]', 'github-actions')
_GITHUB_COMMITTER_EMAIL = 'noreply@github.com'
_GITHUB_ACTIONS_AUTHOR = 'github-actions[bot]'

# How long one request to Azure DevOps may take before the file it was for
# fails. The tag run asks once for its identity and once per commit.
TIMEOUT_SECONDS = 30
API_VERSION = '7.0'

# The Azure DevOps variables the tag run reads: the token, and where the
# repository is.
TOKEN_VARIABLE = 'SYSTEM_ACCESSTOKEN'
COLLECTION_VARIABLE = 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI'
PROJECT_VARIABLE = 'SYSTEM_TEAMPROJECT'
REPOSITORY_VARIABLE = 'BUILD_REPOSITORY_ID'

NO_TOKEN = ('ci/ provenance is checked by the tag run; this machine has no '
            'token.')
NOT_THE_RUNNERS = "the commit that added it is not the runner's"


class Refused(Exception):
    """A question the git host did not answer, as the sentence that says why."""


# ---------------------------------------------------------------------------
# The commit that last changed a file
# ---------------------------------------------------------------------------

def last_commit(project_root, rel_path):
    """The sha of the last commit that changed `rel_path`, or '' for none."""
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%H', '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return ''
    if result.returncode != 0:
        return ''
    return result.stdout.strip()


def check(project_root, rel_paths, host, environ=None):
    """`(problems, not_checked, notice)` for the `ci/` files at `rel_paths`.

    `problems` is `[(path, reason)]`, one plain sentence per file that fails.
    `not_checked` lists the files this machine could not ask about, and
    `notice` is the one line that says why, or None. `host` is `azure` for
    Azure DevOps and anything else for GitHub.
    """
    rel_paths = list(rel_paths)
    if host == 'azure':
        return check_azure(project_root, rel_paths, environ)
    problems = [(rel, NOT_THE_RUNNERS) for rel in rel_paths
                if committed_by(project_root, rel) != 'ci']
    return problems, [], None


# ---------------------------------------------------------------------------
# GitHub: the identity git reads, confirmed by the signature
# ---------------------------------------------------------------------------

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
    """`ci` when GitHub's runner made the last commit to a file, else `local`."""
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


# ---------------------------------------------------------------------------
# Azure DevOps: who pushed the commit, as the host records it
# ---------------------------------------------------------------------------

def check_azure(project_root, rel_paths, environ=None):
    """`(problems, not_checked, notice)` for Azure DevOps.

    With no collection URL this is not a runner, and nothing is asked: every
    file is not checked and `notice` is `NO_TOKEN`. On a runner, a missing
    token or repository variable fails every file, because a tag run that
    cannot ask has not checked anything.
    """
    env = os.environ if environ is None else environ
    rel_paths = list(rel_paths)
    if not rel_paths:
        return [], [], None
    token = env.get(TOKEN_VARIABLE) or ''
    collection = env.get(COLLECTION_VARIABLE) or ''
    project = env.get(PROJECT_VARIABLE) or ''
    repository = env.get(REPOSITORY_VARIABLE) or ''
    if not collection:
        return [], rel_paths, NO_TOKEN
    missing = [name for name, value in ((TOKEN_VARIABLE, token),
                                        (PROJECT_VARIABLE, project),
                                        (REPOSITORY_VARIABLE, repository))
               if not value]
    if missing:
        reason = ('the run has no %s, so who pushed it cannot be read'
                  % ' and no '.join(missing))
        return [(rel, reason) for rel in rel_paths], [], None

    authorization = bearer(token)
    try:
        mine = identity(collection, authorization)
    except Refused as refused:
        return [(rel, str(refused)) for rel in rel_paths], [], None

    problems = []
    answers = {}
    for rel in rel_paths:
        sha = last_commit(project_root, rel)
        if not sha:
            problems.append((rel, 'no commit has changed it'))
            continue
        if sha not in answers:
            try:
                answers[sha] = pushed_by(collection, project, repository, sha,
                                         authorization)
            except Refused as refused:
                answers[sha] = refused
        answer = answers[sha]
        if isinstance(answer, Refused):
            problems.append((rel, str(answer)))
            continue
        if answer.get('id') != mine:
            who = (answer.get('uniqueName') or answer.get('displayName')
                   or answer.get('id'))
            problems.append((rel, 'commit %s was pushed by %s, not by the '
                                  "identity this run holds"
                             % (sha[:7], who)))
    return problems, [], None


def identity(collection, authorization):
    """The id of the identity the token speaks for. Raises `Refused`."""
    answer = _ask(identity_url(collection), authorization,
                  'the identity of this run')
    found = (answer.get('authenticatedUser') or {}).get('id') or ''
    if not found:
        raise Refused('Azure DevOps named no identity for the token this run '
                      'holds')
    return found


def pushed_by(collection, project, repository, sha, authorization):
    """`push.pushedBy` of one commit, as a dict with an `id`. Raises `Refused`."""
    answer = _ask(commit_url(collection, project, repository, sha),
                  authorization, 'commit %s' % sha[:7])
    push = answer.get('push')
    if not isinstance(push, dict) or not push:
        raise Refused('Azure DevOps names no push for commit %s' % sha[:7])
    who = push.get('pushedBy')
    if not isinstance(who, dict) or not who.get('id'):
        raise Refused('Azure DevOps names nobody who pushed commit %s'
                      % sha[:7])
    return who


def identity_url(collection):
    return '%s/_apis/connectionData?api-version=%s' % (
        collection.rstrip('/'), API_VERSION)


def commit_url(collection, project, repository, sha):
    return '%s/%s/_apis/git/repositories/%s/commits/%s?api-version=%s' % (
        collection.rstrip('/'), urllib.parse.quote(project, safe=''),
        urllib.parse.quote(repository, safe=''), sha, API_VERSION)


def bearer(token):
    return 'Bearer %s' % token


def _ask(url, authorization, what):
    """One GET, its JSON, or `Refused` with the sentence that says why.

    No sentence carries the error's own text: a message from the network
    layer can quote a header, and one of the headers is the token.
    """
    try:
        return get_json(url, authorization)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise Refused('Azure DevOps refused the token with HTTP %d when '
                          'asked for %s' % (error.code, what))
        raise Refused('Azure DevOps answered HTTP %d when asked for %s'
                      % (error.code, what))
    except urllib.error.URLError as error:
        if isinstance(error.reason, socket.timeout):
            raise Refused(_no_answer(what))
        raise Refused('Azure DevOps could not be reached when asked for %s'
                      % what)
    except socket.timeout:
        raise Refused(_no_answer(what))
    except OSError:
        raise Refused('Azure DevOps could not be reached when asked for %s'
                      % what)
    except ValueError:
        raise Refused('Azure DevOps answered %s with something that is not '
                      'JSON' % what)


def _no_answer(what):
    return ('Azure DevOps did not answer within %d seconds when asked for %s'
            % (TIMEOUT_SECONDS, what))


def get_json(url, authorization):
    """One GET with the token in the Authorization header, as parsed JSON."""
    request = urllib.request.Request(
        url, headers={'Accept': 'application/json',
                      'Authorization': authorization,
                      'User-Agent': 'purlin'}, method='GET')
    response = _open(request, TIMEOUT_SECONDS)
    try:
        text = response.read().decode('utf-8')
    finally:
        response.close()
    answer = json.loads(text) if text.strip() else {}
    if not isinstance(answer, dict):
        raise ValueError('not an object')
    return answer


def _open(request, timeout):
    """The one place a request leaves this machine. A test replaces it."""
    return urllib.request.urlopen(request, timeout=timeout)
