#!/usr/bin/env python3
"""The model-cost trial: one Opus session from spec to audit, against the
orchestrator pattern, each run building the order system of
`requirement.md` in a new project.

    run_trial.py --plugin DIR --out DIR [--arms A,O] [--runs 3] [--parallel 6]

Arms:

A   one Opus session for every step, each step a turn of it: the PR #10
    trial's "off" arm.
O   the orchestrator: each part's spec in its own Opus session, each build
    in a new Sonnet session started with `claude -p --model`, each test
    run and the audit started as Purlin's own scripts with no session.

What is held equal: the requirement text and the answer to each spec, the
Purlin snapshot under `--plugin`, a project set up by `scaffold.py` with its
`tests` setting written before the first step, the planted bugs on
`claude-opus-5-5` through `ANTHROPIC_MODEL`, and the nudge a step gets when
it ends without its commit (at most two, the same words in both arms).

What is counted: the `total_cost_usd` of every `claude -p` the harness
starts, and of every `claude` the audit starts, which a wrapper first on
PATH logs. Each run's folder holds `calls.jsonl`, `nested.jsonl` and
`result.json`; `--out` holds `summary.json` over every run.

Quality, after the audit: the acceptance checks of `acceptance.py` run
against the build, the status's rule counts, and the audit's last line.

This reaches real models and spends money: about $5 to $9 a run, the
planted bugs about half of it.
"""

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
OPUS = 'claude-opus-5-5'
SONNET = 'claude-sonnet-5-5'
PARTS = ('inventory', 'orders', 'invoicing')
ANSWER = ('Keep the rules and proofs as they are. Save the spec and commit '
          'it.')
NUDGE = {'spec': 'Save the spec as drafted and commit it now. Ask nothing '
                 'more.',
         'build': 'Go ahead: finish the build, run the tests and commit it. '
                  'Ask nothing more.'}
CALL_TIMEOUT = 45 * 60
TESTS_SETTING = [{
    'name': 'pytest',
    'run': '/usr/bin/python3 -m pytest -q -p no:cacheprovider {files} '
           '--junitxml={report}',
    'report': '.purlin/runtime/reports/pytest.xml',
    'format': 'junit',
    'files': ['tests/test_*.py']}]

WRAPPER = '''#!/bin/sh
# Logs each call the audit makes to the real claude, then passes it on.
exec /usr/bin/python3 "%(here)s/run_trial.py" --wrap "%(real)s" "$@"
'''


def requirement_parts():
    """`{part: its text}` from `requirement.md`."""
    with open(os.path.join(HERE, 'requirement.md'), encoding='utf-8') as fh:
        text = fh.read()
    found = {}
    for part in PARTS:
        match = re.search(r'^## %s\n(.*?)(?=^## |\Z)' % part, text,
                          re.M | re.S)
        found[part] = match.group(1).strip()
    return found


def wrap(real, args):
    """Run the real claude with `args`, log its cost, print its output."""
    stdin = sys.stdin.read()
    started = time.time()
    done = subprocess.run([real] + args, input=stdin, capture_output=True,
                          text=True)
    record = {'args': [a for a in args if not a.startswith('You review')],
              'exit': done.returncode, 'seconds': round(time.time() - started)}
    try:
        body = json.loads(done.stdout)
        record.update(cost=body.get('total_cost_usd'),
                      models=sorted((body.get('modelUsage') or {}).keys()))
    except ValueError:
        record['cost'] = None
    log = os.environ.get('TRIAL_NESTED_LOG')
    if log:
        with open(log, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(record) + '\n')
    sys.stdout.write(done.stdout)
    sys.stderr.write(done.stderr)
    return done.returncode


class Run(object):

    def __init__(self, arm, number, out, plugin, real_claude, parts=PARTS):
        self.arm, self.number, self.parts = arm, number, parts
        self.folder = os.path.join(out, '%s-%d' % (arm, number))
        self.root = os.path.join(self.folder, 'project')
        self.plugin, self.real = plugin, real_claude
        self.calls = os.path.join(self.folder, 'calls.jsonl')
        self.nested = os.path.join(self.folder, 'nested.jsonl')
        shim = os.path.join(self.folder, 'shim')
        os.makedirs(shim)
        os.makedirs(self.root)
        with open(os.path.join(shim, 'claude'), 'w') as fh:
            fh.write(WRAPPER % {'here': HERE, 'real': real_claude})
        os.chmod(os.path.join(shim, 'claude'), 0o755)
        self.env = dict(os.environ,
                        PATH=shim + os.pathsep + '/usr/bin' + os.pathsep
                        + os.environ.get('PATH', ''),
                        TRIAL_NESTED_LOG=self.nested,
                        ANTHROPIC_MODEL=OPUS)
        self.env.pop('CLAUDECODE', None)

    # --- the project ------------------------------------------------------

    def git(self, *args):
        return subprocess.run(['git'] + list(args), cwd=self.root,
                              capture_output=True, text=True,
                              env=self.env).stdout

    def set_up(self):
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 'trial@example.com')
        self.git('config', 'user.name', 'trial')
        with open(os.path.join(self.root, 'README.md'), 'w') as fh:
            fh.write('# Order system\n')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'chore: start')
        self.script('init/scaffold.py', '--yes')
        path = os.path.join(self.root, '.purlin', 'config.json')
        with open(path, encoding='utf-8') as fh:
            settings = json.load(fh)
        settings['tests'] = TESTS_SETTING
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(settings, fh, indent=2)
            fh.write('\n')
        os.makedirs(os.path.join(self.root, 'tests'), exist_ok=True)
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'chore: tests setting')

    def script(self, path, *args, label=None):
        started = time.time()
        done = subprocess.run(
            ['/usr/bin/python3', os.path.join(self.plugin, 'scripts', path)]
            + list(args) + ['--project-root', self.root],
            cwd=self.root, capture_output=True, text=True, env=self.env,
            timeout=CALL_TIMEOUT)
        if label:
            self.log({'step': label, 'kind': 'script', 'cost': 0.0,
                      'exit': done.returncode,
                      'seconds': round(time.time() - started),
                      'last': done.stdout.strip().splitlines()[-1:]})
        return done

    # --- sessions ---------------------------------------------------------

    def log(self, record):
        with open(self.calls, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(record) + '\n')

    def claude(self, label, prompt, model, session=None, resume=None):
        argv = [self.real, '-p', '--model', model, '--plugin-dir',
                self.plugin, '--setting-sources', 'project,local',
                '--dangerously-skip-permissions', '--output-format', 'json',
                '--max-budget-usd', '6']
        argv += ['--session-id', session] if session else []
        argv += ['--resume', resume] if resume else []
        started = time.time()
        try:
            done = subprocess.run(argv, input=prompt, capture_output=True,
                                  text=True, cwd=self.root, env=self.env,
                                  timeout=CALL_TIMEOUT)
            out, code = done.stdout, done.returncode
        except subprocess.TimeoutExpired:
            out, code = '', 'timeout'
        record = {'step': label, 'kind': 'session', 'model': model,
                  'session': session or resume,
                  'exit': code, 'seconds': round(time.time() - started)}
        try:
            body = json.loads(out)
            record.update(cost=body.get('total_cost_usd'),
                          turns=body.get('num_turns'),
                          models={name: round(use.get('costUSD') or 0, 4)
                                  for name, use in
                                  (body.get('modelUsage') or {}).items()},
                          said=(body.get('result') or '')[-600:])
        except ValueError:
            record.update(cost=None, said=out[-600:])
        self.log(record)
        return record

    def committed(self, pattern):
        return re.search(pattern, self.git('log', '--format=%s'), re.M)

    def until_committed(self, label, kind, pattern, session_of, model):
        """Nudge a step that ended without its commit, twice at most."""
        for attempt in (1, 2):
            if self.committed(pattern):
                return True
            self.claude('%s nudge %d' % (label, attempt), NUDGE[kind], model,
                        resume=session_of())
        return bool(self.committed(pattern))

    # --- the arms ---------------------------------------------------------

    def arm_a(self, parts):
        session = str(uuid.uuid4())
        first = [True]

        def turn(label, prompt):
            if first[0]:
                first[0] = False
                return self.claude(label, prompt, OPUS, session=session)
            return self.claude(label, prompt, OPUS, resume=session)

        for part in self.parts:
            turn('%s spec' % part, '/purlin:spec %s\n\n%s' % (part,
                                                            parts[part]))
            turn('%s answer' % part, ANSWER)
            self.until_committed('%s spec' % part, 'spec',
                                 r'^spec\(%s\)' % part, lambda: session,
                                 OPUS)
            turn('%s build' % part, '/purlin:build %s' % part)
            self.until_committed('%s build' % part, 'build',
                                 r'^feat\(%s\)' % part, lambda: session,
                                 OPUS)
            turn('%s test' % part, '/purlin:test %s' % part)
        turn('audit', '/purlin:audit')

    def arm_o(self, parts):
        for part in self.parts:
            session = str(uuid.uuid4())
            self.claude('%s spec' % part, '/purlin:spec %s\n\n%s' % (
                part, parts[part]), OPUS, session=session)
            self.claude('%s answer' % part, ANSWER, OPUS, resume=session)
            self.until_committed('%s spec' % part, 'spec',
                                 r'^spec\(%s\)' % part, lambda: session,
                                 OPUS)
            build = str(uuid.uuid4())
            self.claude('%s build' % part, '/purlin:build %s' % part, SONNET,
                        session=build)
            self.until_committed('%s build' % part, 'build',
                                 r'^feat\(%s\)' % part, lambda: build,
                                 SONNET)
            self.script('run/purlin_run.py', '--test', '--feature', part,
                        label='%s test' % part)
        self.script('run/purlin_run.py', '--audit', label='audit')

    # --- quality ----------------------------------------------------------

    def quality(self):
        check = os.path.join(self.root, 'trial_acceptance.py')
        shutil.copy(os.path.join(HERE, 'acceptance.py'), check)
        done = subprocess.run(
            ['/usr/bin/python3', '-m', 'pytest', '-q', '-p',
             'no:cacheprovider', 'trial_acceptance.py'],
            cwd=self.root, capture_output=True, text=True, env=self.env)
        os.remove(check)
        passed = re.search(r'(\d+) passed', done.stdout)
        failed = re.findall(r'^FAILED \S+::(\S+)', done.stdout, re.M)
        status = self.script('run/purlin_status.py').stdout
        counts = re.search(r'^(\d+) rules\. (\d+) pass their tests', status,
                           re.M)
        audit = re.search(r'The audit found (\d+) of (\d+) rules strong',
                          status)
        return {'acceptance_passed': int(passed.group(1)) if passed else 0,
                'acceptance_failed': failed,
                'rules': int(counts.group(1)) if counts else None,
                'rules_passing': int(counts.group(2)) if counts else None,
                'audit_strong': int(audit.group(1)) if audit else None,
                'audit_of': int(audit.group(2)) if audit else None}

    def go(self, parts):
        started = time.time()
        self.set_up()
        try:
            (self.arm_a if self.arm == 'A' else self.arm_o)(parts)
        finally:
            result = dict(self.totals(), **self.quality())
            result.update(arm=self.arm, run=self.number,
                          minutes=round((time.time() - started) / 60, 1))
            with open(os.path.join(self.folder, 'result.json'), 'w') as fh:
                json.dump(result, fh, indent=2)
        return result

    def totals(self):
        # A resumed session's `total_cost_usd` counts the whole session so
        # far, so a step costs what its session's total grew by.
        steps, nested, so_far = {}, 0.0, {}
        for path, is_nested in ((self.calls, False), (self.nested, True)):
            if not os.path.isfile(path):
                continue
            with open(path, encoding='utf-8') as fh:
                for line in fh:
                    record = json.loads(line)
                    cost = record.get('cost') or 0.0
                    if is_nested:
                        nested += cost
                        continue
                    if record.get('session'):
                        total = cost
                        cost = max(total - so_far.get(record['session'], 0.0),
                                   0.0)
                        so_far[record['session']] = max(
                            total, so_far.get(record['session'], 0.0))
                    step = record['step'].split(' nudge')[0]
                    kind = step.split()[-1]
                    kind = 'spec' if kind == 'answer' else kind
                    steps[kind] = steps.get(kind, 0.0) + cost
        steps['planted bugs'] = nested
        return {'cost_by_step': {k: round(v, 4) for k, v in steps.items()},
                'cost_total': round(sum(steps.values()), 4)}


def main(argv):
    if argv[:1] == ['--wrap']:
        return wrap(argv[1], argv[2:])
    parser = argparse.ArgumentParser()
    parser.add_argument('--plugin', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--arms', default='A,O')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--parallel', type=int, default=6)
    parser.add_argument('--claude', default=shutil.which('claude'))
    parser.add_argument('--parts', default=','.join(PARTS))
    args = parser.parse_args(argv)
    parts = requirement_parts()
    chosen = tuple(args.parts.split(','))
    runs = [Run(arm, n, args.out, os.path.abspath(args.plugin), args.claude,
                chosen)
            for n in range(1, args.runs + 1) for arm in args.arms.split(',')]
    results = []
    with concurrent.futures.ThreadPoolExecutor(args.parallel) as pool:
        for result in pool.map(lambda run: run.go(parts), runs):
            results.append(result)
            print(json.dumps(result), flush=True)
    with open(os.path.join(args.out, 'summary.json'), 'w') as fh:
        json.dump(results, fh, indent=2)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
