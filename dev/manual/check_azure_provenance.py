#!/usr/bin/env python3
"""Check the Azure DevOps committer check against the real service, by hand.

For the machine with Azure DevOps access. This machine has none, so the tag
run's question, who pushed the commit that last changed a `ci/` file, is
proven here only against a fake opener (`dev/test_provenance.py`). The check
in `scripts/mcp/purlin/provenance.py` rests on two answers only the real
service can give, and this script asks for both with the same URLs and the
same reader, then prints each answer and a one-line ok or FAIL:

1. `commits/<sha>` returns `push.pushedBy` for a commit the Pushes API
   created, which is how a run branch's runner commits its evidence.
2. The build service's identity id is the same on the run branch run that
   pushed the commit and on the tag run that checks it. That depends on the
   job's authorization scope, project or collection. This is checked by
   comparing `authenticatedUser.id` from `connectionData`, read by the job
   this script runs in, with the `pushedBy.id` of the named commit.

Where to run it. Assumption 2 is answered only from inside a pipeline job
of the same pipeline, started by a `signed/*` tag, with the job's token:

    - bash: python3 "$PURLIN_ROOT/dev/manual/check_azure_provenance.py"
      env:
        SYSTEM_ACCESSTOKEN: $(System.AccessToken)

The job's own variables name the collection, the project and the
repository. Assumption 1 can also be answered from your own machine with a
personal access token that can read code, in a clean clone:

    AZURE_DEVOPS_PAT=... python3 /path/to/purlin/dev/manual/\\
        check_azure_provenance.py --pat-env AZURE_DEVOPS_PAT

With a personal access token the identity is yours, so the second check
reads FAIL by design and says so; only the first counts from there.

The commit is `--commit <sha>`, or else the last commit that changed a file
under `.purlin/evidence/ci/` in `--repo`. It has to be a commit a run branch
run pushed through the Pushes API, merged into the branch the tag is on
without being rewritten.

What it changes: nothing. It sends two GET requests, reads `git log`, and
prints. The token is read from the environment and never printed.

If assumption 1 fails (`push` or `push.pushedBy` is absent for a commit the
Pushes API created), the fallback to try is to look the push up by ref:
`GET {collection}{project}/_apis/git/repositories/{repo}/pushes?searchCriteria.refName=refs/heads/<run branch>&searchCriteria.includeRefUpdates=true&api-version=7.0`,
and find the push whose `refUpdates[].newObjectId` is the commit, then read
its `pushedBy`.

If assumption 2 fails (the ids differ between the two runs while the
unique names or descriptors match), the fallback to try is to compare
`push.pushedBy.uniqueName`, or `descriptor`, with the same field of
`authenticatedUser` instead of `id`. This script prints all three fields of
both identities so the one that matches can be read off the output.

These are the two fallbacks to try. Neither is built.

Exit codes: 0 both checks passed, 1 a check failed, 2 no token, no
collection or no commit to ask about.
"""

import argparse
import base64
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PLUGIN_ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(PLUGIN_ROOT, 'scripts', 'run'))

from purlin import provenance  # noqa: E402
import remote  # noqa: E402

CI_FOLDER = '.purlin/evidence/ci'
FIELDS = ('id', 'uniqueName', 'descriptor', 'displayName')

failures = []


def check(ok, text):
    print('%s %s' % ('ok  ' if ok else 'FAIL', text))
    print()
    if not ok:
        failures.append(text)
    return ok


def ask(url, authorization):
    """One GET through the reader the tag run uses. `(answer, error)`."""
    print('GET %s' % url)
    try:
        answer = provenance.get_json(url, authorization)
    except Exception as error:  # noqa: BLE001 - printed, never raised
        code = getattr(error, 'code', None)
        text = ('HTTP %d' % code) if code else type(error).__name__
        print('  error: %s' % text)
        return None, text
    print('  answer: %s' % json.dumps(answer, indent=2, sort_keys=True)
          .replace('\n', '\n  '))
    return answer, None


def where(args, root):
    """`(collection, project, repository)` from the job, or from `origin`."""
    collection = (os.environ.get(provenance.COLLECTION_VARIABLE) or '')
    project = os.environ.get(provenance.PROJECT_VARIABLE) or ''
    repository = os.environ.get(provenance.REPOSITORY_VARIABLE) or ''
    if collection and project and repository:
        return collection, project, repository
    try:
        url = subprocess.run(['git', 'remote', 'get-url', 'origin'],
                             cwd=root, capture_output=True, text=True,
                             timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        url = ''
    parsed = remote.parse_azure_remote(url)
    if parsed is None:
        return None
    organization, project, repository = parsed
    return 'https://dev.azure.com/%s/' % organization, project, repository


def last_ci_commit(root):
    try:
        done = subprocess.run(['git', 'log', '-1', '--format=%H', '--',
                               CI_FOLDER], cwd=root, capture_output=True,
                              text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return ''
    return done.stdout.strip()


def fields(who):
    return ', '.join('%s=%r' % (name, (who or {}).get(name))
                     for name in FIELDS)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--repo', default='.')
    parser.add_argument('--commit', default='')
    parser.add_argument('--pat-env', default='',
                        help='the variable holding a personal access token, '
                             'used in place of SYSTEM_ACCESSTOKEN')
    args = parser.parse_args(argv)
    root = os.path.abspath(args.repo)

    if args.pat_env:
        secret = os.environ.get(args.pat_env) or ''
        authorization = 'Basic %s' % base64.b64encode(
            (':' + secret).encode('utf-8')).decode('ascii')
        source = 'the personal access token in %s' % args.pat_env
    else:
        secret = os.environ.get(provenance.TOKEN_VARIABLE) or ''
        authorization = provenance.bearer(secret)
        source = 'the job token in %s' % provenance.TOKEN_VARIABLE
    if not check(bool(secret), 'a token is set: %s' % source):
        return 2

    found = where(args, root)
    if not check(found is not None,
                 'the collection, project and repository are %r' % (found,)):
        return 2
    collection, project, repository = found

    sha = args.commit or last_ci_commit(root)
    if not check(bool(sha), 'the commit to ask about is %r' % sha):
        return 2

    identity, error = ask(provenance.identity_url(collection), authorization)
    me = (identity or {}).get('authenticatedUser') or {}
    print('this job is: %s' % fields(me))
    check(bool(me.get('id')), 'connectionData names authenticatedUser.id%s'
          % (' (%s)' % error if error else ''))

    answer, error = ask(provenance.commit_url(collection, project,
                                              repository, sha),
                        authorization)
    push = (answer or {}).get('push') or {}
    who = push.get('pushedBy') or {}
    print('commit %s was pushed by: %s' % (sha[:7], fields(who)))
    check(bool(who.get('id')),
          'assumption 1: commits/%s returns push.pushedBy for a commit the '
          'Pushes API created%s' % (sha[:7], ' (%s)' % error if error else ''))

    same = bool(me.get('id')) and me.get('id') == who.get('id')
    note = ('' if not args.pat_env else
            '; with a personal access token the identity is yours, so this '
            'reads FAIL by design and only a pipeline job can answer it')
    check(same, 'assumption 2: the identity this job holds is the one that '
                'pushed the commit, by id%s' % note)
    for name in ('uniqueName', 'descriptor'):
        print('by %s: %s' % (name, 'same' if me.get(name)
                             and me.get(name) == who.get(name)
                             else 'different or absent'))
    print()
    if not args.pat_env and os.environ.get(provenance.COLLECTION_VARIABLE):
        folder = os.path.join(root, *CI_FOLDER.split('/'))
        names = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
        rels = ['%s/%s' % (CI_FOLDER, name) for name in names
                if name.endswith('.json')]
        problems, _unchecked, _notice = provenance.check_azure(root, rels)
        for rel, reason in problems:
            print('  %s: %s' % (rel, reason))
        check(not problems, 'provenance.check_azure passes all %d files under '
                            '%s in this checkout' % (len(rels), CI_FOLDER))

    print('%d checks failed.' % len(failures) if failures
          else 'Every check passed.')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
