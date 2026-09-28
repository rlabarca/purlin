#!/usr/bin/env python3
"""Check the Azure DevOps remote run against the real service, by hand.

For the machine with Azure DevOps access. This machine has none, so the part
of `purlin:test --remote` that talks to Azure DevOps is proven here only
against a stand-in `az` (`dev/test_remote.py`). This check asks the real
service the same questions, with the same commands `scripts/run/remote.py`
builds, and prints each command, its raw output and a one-line verdict.

What it confirms:

- `origin` parses into the organisation, project and repository the commands
  name;
- `az` is on PATH with its azure-devops extension and is signed in;
- a push to a `run/` branch starts a pipeline run, and how many seconds that
  run takes to appear in `az pipelines runs list --branch refs/heads/<branch>`;
- `az pipelines runs show --query "[status,result]" --output tsv` answers in
  the shape `remote.py` reads, while the run is going and once it completes;
- `remote.find_azure_run` and `remote.wait_azure_run` read the same id and
  result from the live answers.

What it changes: one branch on `origin`, `run/purlin-azure-check-<sha7>`,
which it creates from HEAD and deletes before it exits, whatever happened.
The pipeline run that branch starts stays in the pipeline's history, and the
runner may commit onto the branch before it is deleted. Nothing local is
created, pulled or committed.

Run it from a clean clone of a real Azure DevOps repository whose pipeline
is `purlin.azure-pipelines.yml`, signed in with `az login`:

    python3 /path/to/purlin/dev/manual/check_azure_remote.py [--repo .]
        [--poll-minutes 90]

Exit codes: 0 every verdict passed, 1 a verdict failed, 2 `origin` is not an
Azure DevOps URL or `az` is not on PATH.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PLUGIN_ROOT, 'scripts', 'run'))

import remote  # noqa: E402

BRANCH_PREFIX = 'run/purlin-azure-check-'
STATUSES = ('notStarted', 'inProgress', 'canceling', 'completed', 'postponed')
RESULTS = ('succeeded', 'failed', 'canceled', 'partiallySucceeded')

failures = []


def show(argv, root, timeout=remote.COMMAND_SECONDS):
    """Run `argv` as `remote.py` would, print it and its raw output."""
    print('$ %s' % ' '.join(_quoted(part) for part in argv))
    try:
        done = subprocess.run(argv, cwd=root, stdin=subprocess.DEVNULL,
                              env=remote._environment(), capture_output=True,
                              text=True, timeout=timeout)
    except (subprocess.SubprocessError, OSError) as error:
        print('  error: %s' % error)
        return 1, ''
    print('  exit %d' % done.returncode)
    print('  stdout %r' % done.stdout)
    if done.stderr.strip():
        print('  stderr %r' % done.stderr)
    return done.returncode, done.stdout


def verdict(ok, text):
    print('%s %s' % ('ok  ' if ok else 'FAIL', text))
    print()
    if not ok:
        failures.append(text)
    return ok


def _quoted(part):
    return "'%s'" % part if (' ' in part or '[' in part) else part


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--repo', default='.')
    parser.add_argument('--poll-minutes', type=int,
                        default=remote.POLL_SECONDS // 60)
    args = parser.parse_args(argv)
    root = os.path.abspath(args.repo)

    code, url = show(['git', 'remote', 'get-url', remote.REMOTE], root)
    where = remote.parse_azure_remote(url.strip())
    if not verdict(where is not None,
                   'origin parses as (organisation, project, repository) = %r'
                   % (where,)):
        return 2
    organization, project, _repository = where

    az = shutil.which('az')
    if not verdict(bool(az), '`az` is on PATH at %s' % az):
        return 2
    code, _out = show([az, 'extension', 'show', '--name', 'azure-devops',
                       '--query', 'version', '--output', 'tsv'], root)
    verdict(code == 0, 'the azure-devops extension is installed')
    code, _out = show([az, 'account', 'show', '--query', 'user.name',
                       '--output', 'tsv'], root)
    verdict(code == 0, '`az` is signed in')

    code, sha = show(['git', 'rev-parse', 'HEAD'], root)
    branch = BRANCH_PREFIX + sha.strip()[:7]
    code, _out = show(['git', 'push', remote.REMOTE,
                       'HEAD:refs/heads/%s' % branch], root)
    if not verdict(code == 0, 'pushed HEAD as %s' % branch):
        return 1
    try:
        _find_and_wait(root, az, organization, project, branch,
                       args.poll_minutes * 60)
    finally:
        code, _out = show(['git', 'push', remote.REMOTE, '--delete', branch],
                          root)
        verdict(code == 0, 'deleted %s from %s' % (branch, remote.REMOTE))
    print('%d verdicts failed.' % len(failures) if failures
          else 'Every verdict passed.')
    return 1 if failures else 0


def _find_and_wait(root, az, organization, project, branch, poll_seconds):
    started = time.time()
    run_id = ''
    command = remote.azure_list_command(az, organization, project, branch)
    while time.time() - started <= remote.FIND_SECONDS:
        code, out = show(command, root)
        if code == 0 and out.strip() and out.strip() != 'None':
            run_id = out.strip()
            break
        time.sleep(remote.FIND_EVERY)
    if not verdict(bool(run_id),
                   'the run registered after %d seconds, id %r (limit %d)'
                   % (time.time() - started, run_id, remote.FIND_SECONDS)):
        return
    found = remote.find_azure_run(root, az, organization, project, branch,
                                  seconds=0)
    verdict(found == run_id.split()[0],
            'remote.find_azure_run reads the same id: %r' % found)

    started = time.time()
    command = remote.azure_show_command(az, organization, project, run_id)
    words = []
    while True:
        code, out = show(command, root)
        words = out.split()
        verdict(code == 0 and bool(words) and words[0] in STATUSES,
                'the answer opens with a status `remote.py` knows: %r'
                % (words[:1],))
        if words and words[0] == 'completed':
            break
        if time.time() - started >= poll_seconds:
            verdict(False, 'the run did not complete within %d seconds'
                    % poll_seconds)
            return
        time.sleep(remote.POLL_EVERY)
    verdict(len(words) > 1 and words[1] in RESULTS,
            'the completed run names a result `remote.py` knows: %r'
            % (words[1:],))
    result = remote.wait_azure_run(root, az, organization, project, run_id)
    verdict(result == words[1] if len(words) > 1 else False,
            'remote.wait_azure_run reads the same result: %r' % result)
    print('The run took %d seconds after it registered.'
          % (time.time() - started))


if __name__ == '__main__':
    sys.exit(main())
