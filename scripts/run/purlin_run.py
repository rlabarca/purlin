"""Run a project's marked tests, write the evidence, and audit it on request.

    purlin_run.py [--feature NAME ... | --all] (--test | --ci) [--commit]
                  [--arm-timeout SECONDS] [--project-root DIR]
    purlin_run.py [--feature NAME ... | --all] --audit [--commit]
                  [--arm-timeout SECONDS] [--project-root DIR]
    purlin_run.py --help | -h

**Before anything runs.** With no `.purlin/config.json` the run says so,
names `purlin:init`, writes nothing and exits 1. A settings file that cannot
be read is named with its cause the same way (`config_problem`). In a
project Purlin 0.9.5 set up and nobody upgraded (`set_up_by_095`) it names
`purlin:init --update` the same way. With the `tests` setting empty it
writes nothing and exits 1: where it detects test tools it knows, it prints
each tool's command and the whole `tests` setting to add
(`frameworks.suggest`), and otherwise it says that the agent reads the
project and proposes a command.

**Which features run.** `--feature` names them and `--all` runs every one.
With neither, `--test` and `--audit` run the features the change touched:
`fingerprint.selection` selects a feature with no section for this
operating system, one whose newest such section was taken over another
spec, code or tests, one with an untracked file under its scope or beside
its tests, and one whose spec names no files. Before anything runs the run
prints what it selected and why, what it skipped, and each untracked file
that selected a feature; with nothing selected it says so and runs no test.
`--ci` with no feature named runs every feature that has a proof tagged
`@env` for this machine's system.

**Slow proofs.** `--test` and `--audit` without `--all` never start a test
whose every marker names a proof tagged `@slow` (`slow_plan`): the test is
left out through its own tool's option (`frameworks.leave_out`), the run
says which proofs it left out, lists each as `not run`, and keeps the
result the section it replaces holds for it where that section was taken
over the same spec, code and tests (`keep_slow_results`). `--all` and `--ci`
start every test. A slow test a suite's command cannot leave out is started,
and the run says so.

**How the tests run.** The settings file names the project's own suites
under `tests`, each with its command, where its report lands, the report's
format and the globs its test files live under. The run runs each suite's
own command, reads the report it wrote, and ties every result to the marker
comments above its test (`scripts/run/reports.py`,
`references/formats/marker_format.md`). A run over every feature runs every
suite whole; a narrower run gives `{files}` the test files that carry a
marker of a feature it runs, and starts no suite that has none.

`--test` is what `purlin:test` runs: the suites run, and the run writes this
operating system's section of `.purlin/evidence/local/<feature>.json` for
every feature it covered. After the `Markers:` line it prints each test
comment whose proof's wording changed after the test was last changed
(`wording.stale_comments`). It names each rule that fails or has no test,
with the command that fixes it, and ends on the status table, the summary
sentence and `Left to do`, which count every rule under `specs/`. It writes
and does not commit. `--commit` makes two commits under the person's own
identity: the specs of the features run, the test files carrying their
markers and the settings file, then the evidence, which names the first;
nothing here ever pushes. A section's `commit` is the first of those
commits where `--commit` made one, else `HEAD` when the run started.

`--audit` is what `purlin:audit` runs: the tests, as `--test` runs them, then
the audit (`scripts/review/audit_run.py`): the spot tests, the planted bugs
and the model's reading, written into the same evidence file under `audit`,
which `--commit` commits the same way. With features named it reads their
rules; otherwise every feature's, and `--all` reads every passing rule again.

`--ci` is what a project's own run on another system runs. It answers only
for the proofs tagged `@env` for this machine's own system: a feature with
none is not run, `{files}` is the test files carrying those proofs' markers,
a suite with no such file is not started, and only those markers count for
missing evidence and for the exit code. A file holding other tests beside
them is started whole, and the results of the others are neither written nor
counted. It writes this system's section of
`.purlin/evidence/ci/<feature>.json`, listing those proofs and the rules they
prove, on whatever branch it runs. `--commit` makes one commit of the files
under `.purlin/evidence/ci/`, under the git identity set in that checkout;
nothing here pushes. The audit is not called there.

Under `--test` and `--audit` a proof the spec tags `@env` for another
operating system reads `not run`, whatever its test did here. The run counts
those proofs in one line per system and names `purlin:test` on that system.

No suite ever reads this process's stdin, and none may ask git for a
password: a pipeline is nobody's terminal, and a command that stops for an
answer holds the whole run until the job limit cancels it. Every suite also
gets `--arm-timeout` seconds, 3600 by default; past it the suite is killed,
what it printed is kept, the run reports the timeout as missing evidence and
carries on.

Exit codes for `--test`: 0 everything asked happened; 1 a tied test failed
or did not run, evidence is missing, a marker names nothing a spec has, a
spec writes a number twice or holds a merge-conflict line, there is no
settings file or it cannot be read, an older Purlin set the project up and
it was not upgraded, or no test command is set; 2 the command line was
wrong. A test comment to correct sets no code. `--audit` exits as its tests
do, whatever the audit found, or 1 where the audit stopped because the
project changed while a planted bug ran. `--help` and `-h` print the usage
to stdout and exit 0. `--ci` exits 1 only when a test tied to a proof
tagged for its system failed or could not run.

The flow is one pass. Resolve the configuration and the suites, scan the
specs and the markers, run each suite, then check two things no test
framework reports on its own:

  loud failure A  a suite ran and left no report to read
  loud failure B  a marker of a feature this run covers has no passing or
                  failing result: its test was skipped, no case in the report
                  is its test, or no test follows the marker. An anchor's
                  test skipped with a reason starting `nothing to check:` has
                  its result.

Both are silent in every test framework there is. A marker that names a
feature, a proof or a rule no spec has, or names a rule that has proofs, is
printed by file and line and fails the run.
`references/formats/evidence_format.md` is the shape of what the run then
writes.
"""

import json
import os
import platform
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
_REVIEW_DIR = os.path.join(os.path.dirname(_HERE), 'review')
for _path in (_MCP_DIR, _REVIEW_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from config_engine import config_problem, resolve_config      # noqa: E402
from purlin import (console as console_module,                # noqa: E402
                    evidence as evidence_reader,
                    fingerprint as fingerprint_module,
                    frameworks as frameworks_module,
                    markers as markers_module,
                    payload as payload_module,
                    specs as specs_module,
                    status as status_module,
                    wording as wording_module)
import evidence as evidence_writer                             # noqa: E402
import reports as reports_module                               # noqa: E402

LOG_PATH = os.path.join('.purlin', 'runtime', 'run.log')

USAGE = (
    'Usage: purlin_run.py [--feature NAME ... | --all] (--test | --ci) '
    '[--commit] [--arm-timeout SECONDS] [--project-root DIR]\n'
    '       purlin_run.py [--feature NAME ... | --all] --audit [--commit] '
    '[--arm-timeout SECONDS] [--project-root DIR]')

# What the run says about the proofs tagged for an operating system it is
# not on, one line per system, each in the words a person reads. A proof
# with no test tied to it is not counted: it has its rule's no-test line.
NEEDS_ONE = '1 proof needs %s; this machine is %s. Run purlin:test on %s.'
NEEDS_MANY = '%d proofs need %s; this machine is %s. Run purlin:test on %s.'

# How long one arm may take before it is killed. An hour is longer than any
# shipped suite and far shorter than a hosted pipeline's six-hour job limit, so
# a stuck arm ends as a named piece of missing evidence rather than as a
# cancelled job with an empty log.
ARM_TIMEOUT_DEFAULT = 3600

# What `_run` returns when it killed the command.
TIMED_OUT = 124

# How many lines of a failing suite's own output the run prints. Everything a
# suite prints is captured into the run log, which a job log never shows, so a
# suite that exits non-zero or is killed would otherwise leave a reader with a
# failure and no reason. Sixty lines carry the summary and the first failing
# assertion of every framework init writes a command for.
ARM_TAIL_LINES = 60

# What the run says, and does not run, before any test.
SETTINGS_PATH = os.path.join('.purlin', 'config.json')
NO_SETTINGS = ('No .purlin/config.json here, so nothing ran. Run purlin:init '
               'to write it.')
SET_UP_BY_AN_OLDER_PURLIN = (
    'This project was set up by an older Purlin and not upgraded, so nothing '
    'ran. Run purlin:init --update.')
NO_TEST_COMMAND = ('No test command is set in .purlin/config.json, so nothing '
                   'ran.')
SUGGESTED_FOR = 'Suggested for %s: %s'
SUGGESTED_SETTING = 'Suggested tests setting: %s'
NO_TEST_TOOL = ('No test command is set and no test tool Purlin knows was '
                'found, so nothing ran. The agent reads the project and '
                'proposes a command for you to confirm.')

# A spec named on the command line that the project does not have.
NO_SUCH_SPEC = ('purlin: no spec named %s under specs/. Run purlin:status to '
                'see the specs this project has.')

# A problem in the `tests` setting, then the step that puts it right.
SUITE_PROBLEM = ('purlin: %s. Fix the tests setting in .purlin/config.json, '
                 'then run purlin:test.')

# What the run says of each piece of evidence it could not take, after
# `Evidence is missing: `, each with the step that puts it right. The
# timeouts name the command the run was started by, `test` or `audit`.
TIMED_OUT_ON = ('the %s suite timed out after %d s on %s. Run purlin:%s '
                '--arm-timeout <seconds> to give it longer.')
TIMED_OUT_AFTER = ('the %s suite timed out after %d s. Run purlin:%s '
                   '--arm-timeout <seconds> to give it longer.')
NO_REPORT = ('the %s suite %s. Check its command and report in the tests '
             'setting of .purlin/config.json, then run purlin:test.')
ONE_MARKER_MISSING = ('1 marker has no passing or failing result: %s. Check '
                      'that its test ran and was not skipped, then run '
                      'purlin:test.')
MARKERS_MISSING = ('%d markers have no passing or failing result: %s. Check '
                   'that their tests ran and were not skipped, then run '
                   'purlin:test.')

# What the run says about each rule of the features it ran that fails or
# has no test, before the status.
RULE_FAILS = '%s %s fails: %s. Run purlin:build %s.'
RULE_HAS_NO_TEST = '%s %s has no test. Run purlin:build %s.'
RULE_HAS_NO_TEST_FOR = '%s %s has no test for %s. Run purlin:build %s.'

# What a run that left slow proofs' tests out says before it starts, and
# what it says of each suite whose command could not leave them out.
LEFT_OUT_ONE = 'Left out 1 slow proof: %s. purlin:test --all runs it too.'
LEFT_OUT_MANY = ('Left out %d slow proofs: %s. purlin:test --all runs them '
                 'too.')
STARTED_SLOW = ('Started %s in the %s suite: its command gives Purlin no way '
                'to leave one test out.')

# The start of the reason an anchor's test skips with where the project has
# nothing it checks (`reports RULE-32`).
NOTHING_TO_CHECK = 'nothing to check:'

# What the run says about the markers it read, once per run.
TIED_LINE = 'Markers: %d tied to a test, %d not tied.'



# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class Args(object):
    """One parsed invocation, or the reason it could not be parsed."""

    def __init__(self):
        self.features = []
        self.all = False
        self.action = None          # 'test', 'audit' or 'ci'
        self.commit = False
        self.arm_timeout = ARM_TIMEOUT_DEFAULT
        self.project_root = '.'
        self.help = False
        self.error = None


def parse_args(argv):
    args = Args()
    actions = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in ('--help', '-h'):
            args.help = True
            return args
        if token == '--feature':
            index += 1
            if index >= len(argv):
                args.error = '--feature needs a name'
                return args
            args.features.append(argv[index])
        elif token == '--all':
            args.all = True
        elif token in ('--test', '--audit', '--ci'):
            actions.append(token[2:])
        elif token == '--commit':
            args.commit = True
        elif token == '--arm-timeout':
            index += 1
            value = argv[index] if index < len(argv) else ''
            if not value.isdigit() or int(value) < 1:
                args.error = '--arm-timeout needs a whole number of seconds'
                return args
            args.arm_timeout = int(value)
        elif token == '--project-root':
            index += 1
            if index >= len(argv):
                args.error = '--project-root needs a directory'
                return args
            if not argv[index].strip():
                # An empty value would become the working directory, because
                # that is what `os.path.abspath('')` answers, so a caller whose
                # variable did not get set would run against whatever tree the
                # run was started in. Naming the flag is the only safe answer.
                args.error = '--project-root needs a directory, not an empty '\
                             'value'
                return args
            args.project_root = argv[index]
        else:
            args.error = 'unknown argument %s' % token
            return args
        index += 1

    if len(actions) != 1:
        args.error = 'name exactly one of --test, --audit and --ci'
        return args
    args.action = actions[0]
    if args.all and args.features:
        args.error = 'name features or --all, not both'
        return args
    return args


# ---------------------------------------------------------------------------
# The operating system, and the proofs another one owns
# ---------------------------------------------------------------------------

def host_os():
    """`windows`, `macos` or `linux` for the machine this run is on.

    The reader package answers it, so the platform a run writes into its
    evidence and the platform a cell reads back out are the same string.
    """
    return evidence_reader.host_os()


def foreign_env_proofs(features, selected, os_name):
    """`[(feature, proof_id, env)]` for proofs another operating system owns."""
    out = []
    for name in selected:
        info = features.get(name) or {}
        for proof_id in sorted(info.get('proofs', {})):
            env = info['proofs'][proof_id].get('env')
            if env and env != os_name:
                out.append((name, proof_id, env))
    return out


def needs_lines(foreign, index, os_name):
    """One line per other system that proofs with a tied test wait on.

    `foreign` is `foreign_env_proofs`' answer and `index` the markers this
    run tied to tests. The systems come in the reader's order.
    """
    counts = {}
    for feature, proof_id, env in foreign:
        if index.get((feature, proof_id)):
            counts[env] = counts.get(env, 0) + 1
    here = evidence_reader.os_word(os_name)
    lines = []
    for env in evidence_reader.PLATFORMS:
        count = counts.get(env)
        there = evidence_reader.os_word(env)
        if count == 1:
            lines.append(NEEDS_ONE % (there, here, there))
        elif count:
            lines.append(NEEDS_MANY % (count, there, here, there))
    return lines


def tagged_here(features, selected, os_name):
    """`{(feature, proof_id)}` for the proofs tagged `@env` for `os_name`.

    What a `--ci` run answers for: it runs only the tests tied to these
    proofs, and a feature with none of them is not run.
    """
    return {(name, proof_id) for name in selected
            for proof_id, proof in ((features.get(name) or {})
                                    .get('proofs') or {}).items()
            if proof.get('env') == os_name}


# ---------------------------------------------------------------------------
# The suites
# ---------------------------------------------------------------------------

def arm_environment(extra=None):
    """The environment every suite and every engine is given.

    `GIT_TERMINAL_PROMPT=0` makes git fail instead of asking for a password.
    A hosted pipeline is nobody's terminal, so the question would never be
    answered and the run would sit there until the job limit cancelled it.
    """
    environment = dict(os.environ)
    environment['GIT_TERMINAL_PROMPT'] = '0'
    environment.update(extra or {})
    return environment


def bash_command():
    """The bash that runs a suite's command, found rather than taken from PATH.

    Everywhere but Windows the answer is `bash` on PATH. On Windows PATH
    normally finds `C:\\Windows\\System32\\bash.exe` first, and that is not a
    shell at all: it is the launcher for the Windows Subsystem for Linux,
    which on a machine with no distribution installed prints "Windows
    Subsystem for Linux has no installed distributions" and exits 1 before it
    has read the command. Every hosted Windows machine is such a machine.

    Git for Windows ships a real bash beside its own git, so the answer there
    is found from git: `<install>/bin/bash.exe`, next to `<install>/cmd/git.exe`
    or `<install>/bin/git.exe`. The usual install directories are tried after
    that, and `bash` is the last resort, because a machine that has a working
    bash on PATH and no Git for Windows is better served by trying it than by
    refusing to run.
    """
    if os.name != 'nt':
        return 'bash'
    candidates = []
    git = shutil.which('git')
    if git:
        install = os.path.dirname(os.path.dirname(git))
        candidates.append(os.path.join(install, 'bin', 'bash.exe'))
    for variable in ('ProgramFiles', 'ProgramW6432', 'ProgramFiles(x86)',
                     'LOCALAPPDATA'):
        base = os.environ.get(variable)
        if base:
            candidates.append(os.path.join(base, 'Git', 'bin', 'bash.exe'))
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return 'bash'


def command_line(command):
    """The line the run log names a command by, before its output."""
    return '$ %s' % ' '.join(command)


def _run(command, project_root, log, timeout, environment=None,
         keep_stdout=False):
    """Run one command in the project root, echoing it and its output.

    The command gets no stdin: a pipeline is nobody's terminal, and a prompt
    nobody answers is a run that never ends. It gets `timeout` seconds; past
    them it is killed, whatever it printed is kept, and `TIMED_OUT` comes
    back so the caller names the timeout as missing evidence. With
    `keep_stdout` the answer is `(code, stdout)`, for a suite whose report
    is its standard output.
    """
    log.append(command_line(command))
    stdout = ''
    try:
        result = subprocess.run([*command], cwd=project_root,
                                stdin=subprocess.DEVNULL,
                                capture_output=True, text=True,
                                encoding='utf-8', errors='replace',
                                timeout=timeout,
                                env=environment or arm_environment())
    except subprocess.TimeoutExpired as expired:
        for stream in (expired.stdout, expired.stderr):
            if stream:
                log.append(stream.decode('utf-8', 'replace')
                           if isinstance(stream, bytes) else stream)
        log.append('timed out after %d s' % timeout)
        return (TIMED_OUT, stdout) if keep_stdout else TIMED_OUT
    except (OSError, subprocess.SubprocessError) as error:
        log.append(str(error))
        return (127, stdout) if keep_stdout else 127
    for stream in (result.stdout, result.stderr):
        if stream:
            log.append(stream.rstrip('\n'))
    if keep_stdout:
        return result.returncode, result.stdout or ''
    return result.returncode


def print_arm_output(name, text):
    """Print the tail of one suite's captured output, as soon as it failed.

    The suites write into the run log, which is a file on the machine and
    never reaches a job log, so a suite that exits non-zero or is killed
    reads there as a bare exit code. This puts the last `ARM_TAIL_LINES`
    lines of that suite's own output on stdout, flushed, before the
    missing-evidence lines, so the reason is in the job log every time.
    """
    lines = text.splitlines()
    print('--- %s output (last %d lines) ---' % (name, ARM_TAIL_LINES))
    if lines:
        for line in lines[-ARM_TAIL_LINES:]:
            print(line)
    else:
        print('The %s suite printed nothing.' % name)
    print('--- end of %s output ---' % name)
    sys.stdout.flush()


class SuiteRun(object):
    """What running one suite left: its outcomes, its failures, its log."""

    def __init__(self, suite):
        self.suite = suite
        self.outcomes = {}        # (path, test line) -> [outcome]
        self.reasons = {}         # (path, test line) -> [skip reason]
        self.file_results = {}    # path -> pass | fail, for an exit suite
        self.failures = []
        self.failed_tests = False  # it ran, and at least one test failed
        self.problems = []
        self.log = ''
        self.output = ''

    def keep_log(self, entries, commands):
        """Keep what the suite's commands logged: `log` whole, and `output`
        without the line naming each of `commands`, so the tail a failing
        suite prints is what the suite itself printed."""
        named = {command_line(command) for command in commands}
        self.log = '\n'.join(entries)
        self.output = '\n'.join(entry for entry in entries
                                if entry not in named)


def run_suite(project_root, suite, files, log, timeout=ARM_TIMEOUT_DEFAULT,
              marked=None, action='test', option='', held=()):
    """Run one suite and read what it saw. A `SuiteRun`.

    `files` is the test files to hand `{files}`, or empty for the whole
    suite. An `exit` suite runs its command once per file, `{files}` being
    that one file, and every file it matches when `files` is empty; each
    file passes when the command exits 0. Any other suite runs once and its
    report is read and tied to the markers in `marked`. `action` is the
    command the run was started by, `test` or `audit`, which a timeout
    names as the one to run again with a longer limit. `option` is the
    tool's own option that leaves the slow tests out, and `held` the files
    of an `exit` suite that are not run.
    """
    done = SuiteRun(suite)
    mark = len(log)
    if suite.format == 'exit':
        paths = [path for path in list(files) or sorted(
            markers_module.test_files(project_root, [suite]))
            if path not in held]
        failed = []
        ran = []
        for path in paths:
            command = [bash_command(), '-c',
                       reports_module.command_for(suite, [path])]
            ran.append(command)
            code = _run(command, project_root, log, timeout)
            if code == TIMED_OUT:
                done.failures.append(TIMED_OUT_ON % (suite.name, timeout, path,
                                                     action))
                continue
            done.file_results[path] = (reports_module.PASS if code == 0
                                       else reports_module.FAIL)
            if code != 0:
                failed.append(path)
        done.failed_tests = bool(failed)
        done.keep_log(log[mark:], ran)
        return done

    report = suite.report_path()
    reports_module.clear_report(project_root, report)
    command = [bash_command(), '-c',
               reports_module.command_for(suite, files, report, option)]
    code, stdout = _run(command, project_root, log, timeout, keep_stdout=True)
    done.keep_log(log[mark:], [command])
    if code == TIMED_OUT:
        done.failures.append(TIMED_OUT_AFTER % (suite.name, timeout, action))
    done.failed_tests = code not in (0, TIMED_OUT)
    if option and code == frameworks_module.PYTEST_NOTHING_COLLECTED \
            and frameworks_module.tool_of(suite) == 'pytest':
        # Every test it was given was a slow one left out: nothing failed.
        done.failed_tests = False
    cases, problem = reports_module.read_report(suite.format, project_root,
                                                report, stdout)
    if problem:
        # Loud failure A: the suite ran and there is no report to read. A
        # suite that exits non-zero over a report it wrote has only failing
        # tests, which the report itself says.
        done.failures.append(NO_REPORT % (suite.name, problem))
        return done
    here = {path: found for path, found in (marked or {}).items()
            if markers_module.suite_of(path, [suite]) is suite}
    done.outcomes, done.problems = reports_module.tie(project_root, suite,
                                                      cases, here)
    done.reasons = skip_reasons(project_root, suite, cases, here)
    return done


def skip_reasons(project_root, suite, cases, marked):
    """`{(path, test line): [reason, ...]}` for each marked test a case
    with a skip reason was tied to, the case tied as `reports.tie` ties it."""
    reasons = {}
    cache = {}
    for case in cases:
        reason = getattr(case, 'reason', None)
        if not reason:
            continue
        found = reports_module.locate(project_root, suite, case, marked, cache)
        if len(found) == 1:
            path, test = found[0]
            reasons.setdefault((path, test.line), []).append(reason)
    return reasons


def reason_of(status, reasons):
    """The reason a test that did not run gives, or None.

    Only a test whose every case skipped gives one, and only where each of
    them gave the same: one result reads one reason.
    """
    if status != reports_module.NOT_RUN or not reasons:
        return None
    return reasons[0] if len(set(reasons)) == 1 else None


def marker_results(scan, suites, runs, held=()):
    """`{(feature, id): [entry, ...]}` for every marker whose suite ran.

    Each entry is `{status, test_file, test_name, line, reason, held}`,
    `status` being `pass`, `fail` or `not run`, and `reason` the text a test
    that was skipped gave, or None. A marker no test follows gets no entry:
    the run reports it by file and line instead. `held` is the `(path, test
    line)` pairs of the slow tests the run left out, the line None for a
    file that is one test: each has its entry whether its suite started or
    not, `held` true unless the test ran all the same.
    """
    by_name = {run.suite.name: run for run in runs}
    index = {}
    for path in sorted(scan):
        found = scan[path]
        suite = markers_module.suite_of(path, suites)
        done = by_name.get(suite.name) if suite else None
        if suite is None:
            continue
        if found.whole:
            left_out = (path, None) in held
            if done is None and not left_out:
                continue
            status = (done.file_results.get(path, reports_module.NOT_RUN)
                      if done else reports_module.NOT_RUN)
            for marker in found.markers:
                index.setdefault(marker.key(), []).append({
                    'status': status, 'test_file': path,
                    'test_name': reports_module.test_name(path, None, 'exit'),
                    'line': marker.line, 'reason': None,
                    'held': left_out and status == reports_module.NOT_RUN})
            continue
        for test in found.tests:
            if not test.markers:
                continue
            left_out = (path, test.line) in held
            if done is None and not left_out:
                continue
            status = reports_module.result_of(
                done.outcomes.get((path, test.line), [])
                if done else [])
            left_out = left_out and status == reports_module.NOT_RUN
            reason = None if left_out or done is None else reason_of(
                status, done.reasons.get((path, test.line)))
            for marker in test.markers:
                index.setdefault(marker.key(), []).append({
                    'status': status, 'test_file': path,
                    'test_name': reports_module.test_name(path, test,
                                                          suite.format),
                    'line': marker.line, 'reason': reason,
                    'held': left_out})
    return index


# ---------------------------------------------------------------------------
# Slow proofs
# ---------------------------------------------------------------------------

class SlowPlan(object):
    """What a run does about the tests of the proofs tagged `@slow`.

    `held` is the `(path, test line)` pairs it leaves out, the line None for
    a file that is one test; `options` gives each suite's command the tool's
    own option that leaves them out; `started` is `{suite name: [path]}`
    for the slow tests a suite's command cannot leave out, one path per
    test; `proofs` is the `(feature, proof id)` pairs the held tests carry.
    """

    def __init__(self):
        self.held = set()
        self.options = {}
        self.started = {}
        self.proofs = set()

    def all_held(self, path, found):
        """True for a file every test of which is left out."""
        if found.whole:
            return (path, None) in self.held
        return bool(found.tests) and all((path, test.line) in self.held
                                         for test in found.tests)


def slow_plan(features, scan, suites):
    """The `SlowPlan` of a run that starts no slow proof's test.

    A test is a slow proof's when it carries a marker and every marker it
    carries names a proof tagged `@slow`; a test that also carries another
    proof's marker is that proof's too, and runs.
    """
    slow_ids = {(name, proof_id) for name, info in features.items()
                for proof_id, proof in (info.get('proofs') or {}).items()
                if proof.get('slow')}
    plan = SlowPlan()
    if not slow_ids:
        return plan

    def is_slow(markers):
        return bool(markers) and all(marker.key() in slow_ids
                                     for marker in markers)
    for suite in suites:
        slow, others = [], []
        for path in sorted(scan):
            found = scan[path]
            if markers_module.suite_of(path, suites) is not suite:
                continue
            if found.whole:
                (slow if is_slow(found.markers) else others).append(
                    (path, None))
                continue
            for test in found.tests:
                (slow if is_slow(test.markers) else others).append(
                    (path, test))
        option, held, started = frameworks_module.leave_out(suite, slow,
                                                            others)
        if option:
            plan.options[suite.name] = option
        if started:
            plan.started[suite.name] = [path for path, _test in started]
        for path, test in held:
            plan.held.add((path, test.line if test is not None else None))
            markers = scan[path].markers if test is None else test.markers
            plan.proofs.update(marker.key() for marker in markers)
    return plan


def slow_lines(plan, selected, given):
    """What a run says of the slow proofs before it starts a suite.

    One line naming the proofs of the features it runs whose tests it left
    out, then one per suite it starts that holds a slow test its command
    cannot leave out. `given` is `{suite name: files}` for the suites the
    run starts, the files empty for a suite run whole.
    """
    lines = []
    named = ['%s %s' % key for key in sorted(plan.proofs)
             if key[0] in selected]
    if len(named) == 1:
        lines.append(LEFT_OUT_ONE % named[0])
    elif named:
        lines.append(LEFT_OUT_MANY % (len(named), ', '.join(named)))
    for name in sorted(plan.started):
        if name not in given:
            continue
        count = len([path for path in plan.started[name]
                     if not given[name] or path in given[name]])
        if count:
            lines.append(STARTED_SLOW % (
                '1 slow test' if count == 1 else '%d slow tests' % count,
                name))
    return lines


def keep_slow_results(project_root, name, os_name, fingerprint, entries):
    """`entries` with each held test given the result the feature's local
    section for this system already holds for it, where that section was
    taken over the same fingerprint.

    A slow proof's result counts until the feature's spec, code or tests
    change, and a run that left its test out is no reason to drop it.
    """
    if not any(entry.get('held') for found in entries.values()
               for entry in found):
        return entries
    data = evidence_writer.read_file(project_root, 'local', name) or {}
    kept = (data.get('platforms') or {}).get(os_name)
    if not isinstance(kept, dict) \
            or kept.get('fingerprint') != dict(fingerprint):
        return entries
    known = {}
    for listed in kept.get('proofs') or ():
        if isinstance(listed, dict) and listed.get('result') in (
                reports_module.PASS, reports_module.FAIL,
                evidence_reader.NOTHING_TO_CHECK):
            known[(listed.get('id'), listed.get('test'))] = listed
    out = {}
    for marker_id, found in entries.items():
        out[marker_id] = []
        for entry in found:
            listed = known.get((marker_id, '%s::%s' % (
                entry.get('test_file', ''), entry.get('test_name', ''))))
            if not entry.get('held') or listed is None:
                out[marker_id].append(entry)
            elif listed['result'] == evidence_reader.NOTHING_TO_CHECK:
                out[marker_id].append(dict(
                    entry, held=False, reason='%s %s' % (
                        evidence_reader.NOTHING_TO_CHECK_PREFIX,
                        listed.get('reason') or '')))
            else:
                out[marker_id].append(dict(entry, held=False,
                                           status=listed['result']))
    return out


def marked_files(scan, suite, selected, proofs=None):
    """The `/` relative paths, sorted, of one suite's files a run gives `{files}`.

    A file is given when it carries a marker of a feature in `selected`, or,
    where `proofs` names the `(feature, proof_id)` pairs a `--ci` run
    answers for, a marker of one of them. The files are read from the disk,
    tracked or not, so a new test is run before anyone has added it.
    """
    wanted = set(selected)

    def carries(found):
        if proofs is None:
            return bool(found.features() & wanted)
        return any(marker.key() in proofs for marker in found.markers)
    return sorted(path for path, found in scan.items()
                  if markers_module.suite_of(path, [suite]) is suite
                  and carries(found))


# ---------------------------------------------------------------------------
# Who ran, and on what
# ---------------------------------------------------------------------------

def runner_name(project_root):
    """The slug of the git email set in this checkout, under every action."""
    return evidence_writer.runner_slug(_git_email(project_root))


def _git_email(project_root):
    try:
        result = subprocess.run(['git', 'config', 'user.email'],
                                capture_output=True, text=True,
                                cwd=project_root, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ''
    return result.stdout.strip()


def head_commit(project_root):
    return payload_module.head_sha(project_root) or ''


def working_tree_dirty(project_root):
    """True when the tree carries a change no commit holds, outside `.purlin/`.

    What Purlin writes about a project is not a change to the project, so
    the evidence a run has just written does not make the next run's tree
    read as dirty.
    """
    try:
        result = subprocess.run(['git', 'status', '--porcelain'],
                                capture_output=True, text=True,
                                cwd=project_root, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    for line in result.stdout.splitlines():
        if len(line) > 3 and not line[3:].strip('"').startswith('.purlin/'):
            return True
    return False


# ---------------------------------------------------------------------------
# The evidence
# ---------------------------------------------------------------------------

def machine_name():
    """What a section names the machine it ran on, under every action: the
    host's name, `unknown` where it has none."""
    return platform.node() or 'unknown'


def build_sections(project_root, args, features, selected, index, os_name,
                   commit, proofs=None):
    """`{feature: section}`, one section per feature this run covered.

    `commit` is the code the sections describe: the run's own commit of the
    specs, tests and settings where `--commit` made one, else `HEAD` when
    the run started. `proofs`, under `--ci`, is the `(feature, proof_id)`
    pairs tagged for this machine's system: each section lists those proofs
    alone.
    """
    dirty = working_tree_dirty(project_root)
    runner = runner_name(project_root)
    markers = fingerprint_module.marker_index(project_root)
    machine = machine_name()
    sections = {}
    for name in selected:
        info = features.get(name) or {}
        entries = {}
        by_rule = info.get('proofs_by_rule') or {}
        # A rule with no proof may be marked by its own id instead.
        ids = sorted(info.get('proofs') or {}) + [
            rule_id for rule_id in info.get('rule_order') or ()
            if not by_rule.get(rule_id)]
        for marker_id in ids:
            found = index.get((name, marker_id), [])
            if found:
                entries[marker_id] = found
        fingerprint = fingerprint_module.fingerprint(project_root, name,
                                                     features, markers)
        if args.action != 'ci':
            entries = keep_slow_results(project_root, name, os_name,
                                        fingerprint, entries)
        sections[name] = evidence_writer.build_section(
            info, entries, os_name, commit, dirty, runner,
            fingerprint,
            machine=machine,
            only=(None if proofs is None else
                  {pid for feature, pid in proofs if feature == name}))
    return sections


def write_sections(project_root, features, sections, os_name, source):
    """Merge each section into its feature's file. The paths.

    Each file is read from disk and only this operating system's section is
    replaced, so a `--feature` run, and a run on another machine, leave
    every other section as it was.

    A file a merge left conflicted is written afresh, then keeps from both
    of its sides each audit entry whose rule, proof and test are the rule's
    current ones.
    """
    conflicted = {}
    for name in sections:
        sides = evidence_writer.read_conflicted(project_root, source, name)
        if sides:
            conflicted[name] = sides
    paths = [evidence_writer.write_section(
        project_root, source, name, features.get(name) or {}, os_name,
        section) for name, section in sections.items()]
    if conflicted:
        # The current hashes are read after the new sections are written:
        # a rule's test hash is taken over the tests its results name.
        payload = payload_module.build_payload(project_root, generated_by='run')
        for feature in payload.get('features') or ():
            name = feature.get('name')
            if name not in conflicted:
                continue
            current = {rule['id']: (rule.get('rule_hash'),
                                    rule.get('proof_hash'),
                                    rule.get('test_hash'))
                       for rule in feature.get('rules') or ()
                       if rule.get('feature') == name}
            entries = evidence_writer.kept_audits(conflicted[name], current)
            if entries:
                evidence_writer.write_audit(
                    project_root, source, name, features.get(name) or {},
                    entries)
    return paths


def rule_problems(features, sections, index):
    """One line per rule of the features run that fails or has no test.

    Read from the words this run's sections give each rule, so the lines,
    the evidence and the exit code say the same. A failing rule names each
    of its tests that failed here. A rule that has no test names each of
    its proofs no test is tied to; only a rule with no proof, and no test
    marked with its own id, reads `has no test.` alone.
    """
    lines = []
    for name, section in sections.items():
        info = features.get(name) or {}
        by_rule = info.get('proofs_by_rule') or {}
        for rule_id in info.get('rule_order') or ():
            word = (section.get('rules') or {}).get(rule_id)
            if word == 'failed':
                failing = []
                for marker_id in (by_rule.get(rule_id) or [rule_id]):
                    for entry in index.get((name, marker_id)) or ():
                        test = '%s::%s' % (entry['test_file'],
                                           entry['test_name'])
                        if entry['status'] == reports_module.FAIL \
                                and test not in failing:
                            failing.append(test)
                lines.append(RULE_FAILS % (name, rule_id, ', '.join(failing),
                                           name))
            elif word == 'no test':
                listed = [entry for entry in section.get('proofs') or ()
                          if entry.get('rule') == rule_id
                          and entry.get('id') != rule_id
                          and not entry.get('manual')]
                untested = []
                for entry in listed:
                    if not entry.get('test') and entry['id'] not in untested:
                        untested.append(entry['id'])
                if untested:
                    lines.append(RULE_HAS_NO_TEST_FOR % (
                        name, rule_id, ', '.join(untested), name))
                else:
                    lines.append(RULE_HAS_NO_TEST % (name, rule_id, name))
    return lines


def work_paths(scan, features, selected):
    """What the first commit of `--commit` holds, sorted.

    The spec of each feature run, the test files carrying a marker of one,
    and the settings file.
    """
    wanted = set(selected)
    paths = {(features.get(name) or {}).get('spec_path') for name in selected}
    paths.update(path for path, found in scan.items()
                 if found.features() & wanted)
    paths.add('.purlin/config.json')
    return sorted(path for path in paths if path)


def commit_the_work(project_root, paths):
    """The first of the two commits: the sha the evidence names, or None."""
    return evidence_writer.commit_work(project_root, paths)


# The first commit's subject where the work names no feature.
WORK_SUBJECT_NO_FEATURE = 'purlin: specs, tests and settings'


def commit_all_work(project_root, features, suites):
    """The first commit of a `--commit` run that selected nothing, or None.

    Every spec, every test file carrying a marker and the settings file,
    where any changed, go into one commit, so nothing of Purlin's is left
    uncommitted. Its subject names each feature whose spec or marked tests
    it holds, or no feature where it holds only the settings. Returns the
    new commit's sha, or None where nothing changed.
    """
    scan = markers_module.scan(project_root, suites)
    changed = changed_paths(project_root,
                            work_paths(scan, features, sorted(features)))
    if not changed:
        return None
    named = {name for name in features
             if (features[name] or {}).get('spec_path') in changed}
    for path in changed:
        if path in scan:
            named.update(scan[path].features() & set(features))
    if named:
        specs = [features[name].get('spec_path') for name in named]
        return commit_the_work(project_root,
                               sorted(set(changed) | set(filter(None, specs))))
    if evidence_writer.commit_paths(project_root, changed,
                                    WORK_SUBJECT_NO_FEATURE) \
            != evidence_writer.COMMITTED:
        return None
    sha = head_commit(project_root)
    print(evidence_writer.WORK_COMMITTED % sha[:7])
    for path in changed:
        print('  %s' % path)
    return sha


def changed_paths(project_root, paths):
    """Those of `paths` git sees a change in, sorted; none outside git."""
    if not paths:
        return []
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain', '-z', '--no-renames',
             '--untracked-files=all', '--'] + list(paths),
            capture_output=True, text=True, cwd=project_root, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return sorted({entry[3:] for entry in result.stdout.split('\0')
                   if len(entry) > 3})


def commit_the_evidence(project_root, work, removed=()):
    """The second commit, naming the first, or HEAD where nothing was."""
    evidence_writer.commit_local(
        project_root, work or head_commit(project_root), removed)


def _prune(project_root, features):
    """Delete the evidence of every feature no spec defines, one line each."""
    removed = evidence_writer.prune(project_root, features)
    for path in removed:
        print(evidence_writer.REMOVED
              % (path, path.rsplit('/', 1)[-1][:-len('.json')]))
    return removed


def failed_rules(project_root):
    """How many rules under specs/ read `failed` in the evidence they stand on.

    Each rule is counted once, under the feature that owns it, and the
    project is counted rather than the run: this is what a run that ran no
    test answers with.
    """
    payload = payload_module.build_payload(project_root, generated_by='run')
    return sum(1 for feature in payload.get('features') or ()
               for rule in feature.get('rules') or ()
               if rule.get('feature') == feature.get('name')
               and ((rule.get('cells') or {}).get('passed') or {}).get('word')
               == 'failed')


def broken_specs(features):
    """The features whose spec writes a number twice or holds a line left
    from a merge conflict: every rule of such a spec reads `failed`, so the
    run exits 1 on it and the audit reads none of its rules.

    The reasons are the spec reader's `broken_reasons`.
    """
    return {name for name, info in features.items()
            if specs_module.broken_reasons(info)}


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

def main(argv=None):
    # UTF-8 so the table's glyphs survive a cp1252 console, line buffering
    # so a pipeline's log shows where a long run got to.
    console_module.force_utf8_stdio(line_buffering=True)
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.help:
        print(USAGE)
        return 0
    if args.error:
        # Each refusal is one `purlin:` line, ending on a full stop unless
        # it ends on the command to run.
        print(args.error if args.error.startswith('purlin: ')
              else 'purlin: %s.' % args.error, file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2

    project_root = os.path.abspath(args.project_root)
    if not os.path.isdir(project_root):
        print('purlin: %s is not a directory.' % args.project_root,
              file=sys.stderr)
        return 2

    stopped = settings_stop(project_root)
    if stopped:
        print(stopped)
        return 1

    config = resolve_config(project_root)

    features = specs_module.scan_specs(project_root)
    if not features:
        for line in status_module.no_spec_lines(project_root):
            print(line)
        return 1
    suites, suite_problems = markers_module.read_suites(project_root, config)
    for problem in suite_problems:
        print(SUITE_PROBLEM % problem)
    if not suites:
        for line in no_test_command_lines(project_root):
            print(line)
        return 1

    os_name = host_os()
    if args.all or (not args.features and args.action == 'ci'):
        selected = sorted(features)
    elif args.features:
        selected = [name for name in args.features if name in features]
        unknown = [name for name in args.features if name not in features]
        for name in unknown:
            print(NO_SUCH_SPEC % name, file=sys.stderr)
        if unknown:
            return 2
    else:
        selected = print_selection(
            fingerprint_module.selection(project_root, features, os_name),
            'purlin:%s' % args.action)
        if not selected:
            return _nothing_to_run(project_root, args, features, suites)

    # A `--ci` run answers only for the proofs tagged for this machine's
    # system: a feature with none of them is not run, and only their markers
    # count for missing evidence and for the exit code.
    remote_proofs = None
    if args.action == 'ci':
        remote_proofs = tagged_here(features, selected, os_name)
        selected = [name for name in selected
                    if any(feature == name for feature, _p in remote_proofs)]
    foreign = foreign_env_proofs(features, selected, os_name)
    foreign_ids = {(feature, proof_id) for feature, proof_id, _env in foreign}
    # A run over every feature runs every suite whole. A narrower run gives
    # each suite the files that carry a marker of a feature it runs, and a
    # suite with none of those is not started. A `--ci` run gives each
    # suite the files that carry a marker of a proof it answers for.
    narrow = remote_proofs is not None or len(selected) < len(features)
    scan = markers_module.scan(project_root, suites)
    # `--all` and `--ci` start every test; any other run leaves
    # out the tests of the proofs tagged `@slow`.
    plan = (SlowPlan() if args.all or args.action == 'ci'
            else slow_plan(features, scan, suites))
    # The code the sections describe where `--commit` makes no commit.
    started = head_commit(project_root)

    log = []
    failures = []
    runs = []
    given = {}
    for suite in suites:
        files = []
        if narrow:
            # A file every test of which is left out is not handed over.
            files = [path for path in marked_files(scan, suite, selected,
                                                   remote_proofs)
                     if not plan.all_held(path, scan[path])]
            if not files:
                continue
        given[suite.name] = files
    said = slow_lines(plan, selected, given)
    for line in said:
        print(line)
    if said:
        print('')
    held_files = {path for path, line in plan.held if line is None}
    for suite in suites:
        if suite.name not in given:
            continue
        files = given[suite.name]
        # One line per suite before it starts, so a job log says where a run
        # is while it is still running.
        print('Running the %s suite.' % suite.name)
        done = run_suite(project_root, suite, files, log, args.arm_timeout,
                         scan, 'audit' if args.action == 'audit' else 'test',
                         plan.options.get(suite.name, ''), held_files)
        runs.append(done)
        failures.extend(done.failures)
        if done.failures or done.failed_tests:
            print_arm_output(suite.name, done.output)
        for problem in done.problems:
            print(problem)

    index = marker_results(scan, suites, runs, plan.held)
    ran_suites = {done.suite.name for done in runs}
    missing = []
    for (feature, marker_id), entries in sorted(index.items()):
        if feature not in selected or (feature, marker_id) in foreign_ids:
            continue
        if remote_proofs is not None \
                and (feature, marker_id) not in remote_proofs:
            continue
        anchor = (features.get(feature) or {}).get('is_anchor')
        for entry in entries:
            if entry['status'] in (reports_module.PASS, reports_module.FAIL):
                continue
            if entry.get('held'):
                # A slow proof's test this run left out: `purlin:test --all`
                # runs it, and the status says so.
                continue
            if anchor and nothing_to_check(entry):
                continue
            missing.append('%s %s at %s:%d' % (feature, marker_id,
                                               entry['test_file'],
                                               entry['line']))
    untied = 0
    tied = 0
    for path, found in sorted(scan.items()):
        suite = markers_module.suite_of(path, suites)
        tied += len(found.markers) - len(found.untied)
        untied += len(found.untied)
        if suite is None or suite.name not in ran_suites:
            continue
        for marker in found.untied:
            if marker.feature in selected and (
                    remote_proofs is None or marker.key() in remote_proofs):
                missing.append('%s %s at %s:%d' % (marker.feature, marker.id,
                                                   path, marker.line))
    # A marker naming nothing a spec has fails the run, whatever the tests did.
    wrong = reports_module.marker_problems(scan, features)
    if scan:
        print('')
        print(TIED_LINE % (tied, untied))
        for line in reports_module.untied_lines(scan) + wrong:
            print(line)
        if args.action != 'ci':
            # A test comment to correct changes no exit code: it is work
            # left, which the status counts.
            for entry in wording_module.stale_comments(project_root, features,
                                                       scanned=scan):
                print(entry['text'])
    if missing:
        # Loud failure B: a marker of a feature this run covers has no result.
        # Five are named and the rest counted: a reader acts on the first few
        # either way.
        shown = ', '.join(missing[:5])
        more = ('' if len(missing) <= 5
                else ', and %d more' % (len(missing) - 5))
        failures.append(ONE_MARKER_MISSING % (shown + more)
                        if len(missing) == 1
                        else MARKERS_MISSING % (len(missing), shown + more))
    ran = [done.suite.name for done in runs]

    print('Ran %s on %s.'
          % (', '.join(ran) or 'nothing',
             '1 feature' if len(selected) == 1
             else '%d features' % len(selected)))
    needs = [] if remote_proofs is not None else needs_lines(foreign, index,
                                                             os_name)
    if needs:
        print('')
        for line in needs:
            print(line)

    # A failing test is a result the evidence records, so it fails the run
    # without being called missing; only a suite that left nothing to read,
    # or a marker with no result, is missing evidence. A `--ci` run
    # starts a file of mixed tests whole, and only the tests tied to the
    # proofs it answers for can fail it.
    if remote_proofs is None:
        tests_failed = bool(failures
                            or any(done.failed_tests for done in runs))
    else:
        tests_failed = bool(failures or any(
            entry['status'] == reports_module.FAIL
            for key in remote_proofs for entry in index.get(key) or ()))
    # A broken spec fails the run whichever features it ran, once every test
    # has run and printed.
    exit_code = 1 if (tests_failed or wrong or broken_specs(features)) else 0
    if failures:
        print('')
        for failure in failures:
            print('Evidence is missing: %s' % failure)

    # A `--ci` run commits its `ci/` files alone: the specs, tests and
    # settings it ran are the commit it was started on.
    work = None
    if args.commit and args.action != 'ci':
        print('')
        work = commit_the_work(project_root,
                               work_paths(scan, features, selected))
    sections = build_sections(project_root, args, features, selected, index,
                              os_name, work or started, remote_proofs)
    problems = rule_problems(features, sections, index)
    if problems:
        print('')
        for line in problems:
            print(line)

    if args.action == 'ci':
        # Called whatever the suites found: a run that reports missing
        # evidence still writes what it saw, which is where a reader finds
        # out what went missing. Only the tests decide the exit code.
        _ci(project_root, args, features, sections, log, os_name, started)
        print('')
        print(status_module.sync_status(project_root))
        return 1 if tests_failed else 0

    print('')
    paths = write_sections(project_root, features, sections, os_name, 'local')
    removed = _prune(project_root, features)
    print(evidence_writer.written_line(paths))
    if args.action == 'audit':
        # The tests ran on the selection; the audit reads every feature's
        # rules unless features were named.
        _write_log(project_root, log)
        exit_code = _audit(project_root, args, features,
                           selected if args.features else sorted(features),
                           exit_code)
    if args.commit:
        commit_the_evidence(project_root, work, removed)

    print('')
    print(status_module.sync_status(project_root))
    return exit_code


def nothing_to_check(entry):
    """True for a result whose test skipped with a reason starting
    `nothing to check:`, which an anchor's rule reads as its answer."""
    return (entry.get('status') == reports_module.NOT_RUN
            and (entry.get('reason') or '').startswith(NOTHING_TO_CHECK))


def settings_stop(project_root):
    """The line a run stops on before anything runs, or None.

    No settings file, a settings file that cannot be read, or a project an
    older Purlin set up that was not upgraded: each names what puts it
    right. A file that cannot be read is named before the older Purlin is
    looked for, since that look reads the file.
    """
    if not os.path.isfile(os.path.join(project_root, SETTINGS_PATH)):
        return NO_SETTINGS
    problem = config_problem(project_root)
    if problem:
        return problem
    if set_up_by_095(project_root):
        return SET_UP_BY_AN_OLDER_PURLIN
    return None


def set_up_by_095(project_root):
    """True when Purlin 0.9.5 set this project up and it was not upgraded.

    This is the one piece of 0.9.5 the run keeps: 0.9.5 wrote no `tests`
    setting, and every setup and upgrade since writes one, so a settings
    file without it is a project that release set up. A project with no
    settings file is not one: that is a missing settings file, named on its
    own. The version stamp is not read, so a plugin update alone never
    makes this true.
    """
    path = os.path.join(os.path.abspath(project_root), SETTINGS_PATH)
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            config = json.load(handle)
    except (IOError, OSError, ValueError):
        return False
    return isinstance(config, dict) and 'tests' not in config


def no_test_command_lines(project_root):
    """What a run with no suite prints: the setting to add, or where to get one.

    Where test tools Purlin knows are detected, each tool's command, then
    what that tool needs added before it can write its report where it
    needs something, then every entry as one JSON array on one line, the
    `tests` setting to write; otherwise the line saying that the agent reads
    the project and proposes one.
    """
    entries = frameworks_module.suggest(project_root)
    if not entries:
        return [NO_TEST_TOOL]
    lines = [NO_TEST_COMMAND]
    for entry in entries:
        lines.append(SUGGESTED_FOR % (entry['name'], entry['run']))
        needs = frameworks_module.needs(project_root, entry['name'])
        if needs:
            lines.append(needs)
    lines.append(SUGGESTED_SETTING % json.dumps(entries))
    return lines


# ---------------------------------------------------------------------------
# The selection a run with no feature named makes
# ---------------------------------------------------------------------------

SELECTED = 'Selected %d of %d %s: %s.'
SKIPPED_FEATURES = ('Skipped %d %s whose spec, code and tests match %s '
                    'evidence: %s. %s --all runs them too.')
NOTHING_TO_RUN = ("Nothing to run: every feature's spec, code and tests match "
                  'its evidence. %s --all runs them anyway.')
NOT_TRACKED_LINE = ('%s is %s and is not tracked, so its content is not part '
                    'of the evidence until you git add it.')

# How many skipped features the line names before it counts the rest.
SKIPPED_SHOWN = 10


def print_selection(rows, command):
    """Print what a run with no feature named selected and why. The names.

    `rows` is `fingerprint.selection`'s answer and `command` the command
    the person ran, which the lines name as the way to run everything.
    Nothing is printed when nothing was selected: `_nothing_to_run` says so.
    """
    chosen = [row for row in rows if row['selected']]
    skipped = [row['feature'] for row in rows if not row['selected']]
    if not chosen:
        return []
    print(SELECTED % (len(chosen), len(rows),
                      _plural(len(rows), 'feature', 'features'),
                      ', '.join('%s (%s)' % (row['feature'],
                                             '; '.join(row['reasons']))
                                for row in chosen)))
    if skipped:
        shown = ', '.join(skipped[:SKIPPED_SHOWN])
        if len(skipped) > SKIPPED_SHOWN:
            shown += ', and %d more' % (len(skipped) - SKIPPED_SHOWN)
        print(SKIPPED_FEATURES % (len(skipped),
                                  _plural(len(skipped), 'feature', 'features'),
                                  _plural(len(skipped), 'its', 'their'),
                                  shown, command))
    for line in untracked_lines(chosen):
        print(line)
    print('')
    return [row['feature'] for row in chosen]


def untracked_lines(rows):
    """One line per untracked file that selected a feature, sorted by path."""
    by_path = {}
    for row in rows:
        loose = row.get('untracked') or {}
        for kind in ('scope', 'tests'):
            for path in loose.get(kind) or ():
                by_path.setdefault(path, []).append((row['feature'], kind))
    lines = []
    for path in sorted(by_path):
        names = sorted({name for name, _kind in by_path[path]})
        kind = ('scope' if any(k == 'scope' for _n, k in by_path[path])
                else 'tests')
        if len(names) == 1:
            where = ("under %s's scope" % names[0] if kind == 'scope'
                     else "beside %s's tests" % names[0])
        else:
            listed = '%s and %s' % (', '.join(names[:-1]), names[-1])
            where = ('under the scope of %s' % listed if kind == 'scope'
                     else 'beside the tests of %s' % listed)
        lines.append(NOT_TRACKED_LINE % (path, where))
    return lines


def _nothing_to_run(project_root, args, features, suites):
    """A run with no feature named that selected nothing. The exit code.

    No test runs. `--commit` still commits every changed spec, marked test
    and the settings in one commit, then the evidence an earlier run wrote,
    so the hand-off to a sign-off is one command. `--audit` goes on to the
    audit of every feature's rules. The tests this run answers with are the
    ones the evidence already holds: a rule whose tests fail there exits 1.
    """
    print(NOTHING_TO_RUN % ('purlin:%s' % args.action))
    exit_code = 1 if (failed_rules(project_root)
                      or broken_specs(features)) else 0
    work = None
    if args.commit:
        print('')
        work = commit_all_work(project_root, features, suites)
    if args.action == 'audit':
        exit_code = _audit(project_root, args, features, sorted(features),
                           exit_code)
    if args.commit:
        commit_the_evidence(project_root, work)
    print('')
    print(status_module.sync_status(project_root))
    return exit_code


def _write_log(project_root, log):
    """The run's console log, written once to `.purlin/runtime/run.log`."""
    path = os.path.join(project_root, LOG_PATH)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(log) + '\n')
    except (IOError, OSError):
        return None
    return LOG_PATH.replace(os.sep, '/')


# ---------------------------------------------------------------------------
# The audit
# ---------------------------------------------------------------------------

def _plural(count, one, many):
    return one if count == 1 else many


def _audit(project_root, args, features, selected, exit_code):
    """The `--audit` arm, after the tests have written their evidence.

    `audit_run.run` reads the rules of `selected` (`ai_audit RULE-1`), every
    passing one again under `--all`, writes what it found under `audit` in
    each feature's local evidence and prints it. The exit code is the tests'
    (`run_script RULE-48`), or 1 where the audit stopped because the project
    changed while a planted bug ran.
    """
    import audit_run
    print('')
    stopped = audit_run.run(project_root, features, selected, again=args.all,
                            out=sys.stdout)
    sys.stdout.flush()
    return 1 if stopped == 1 else exit_code


# ---------------------------------------------------------------------------
# CI
# ---------------------------------------------------------------------------

def _ci(project_root, args, features, sections, log, os_name, started):
    """The `--ci` arm: this system's sections, written and, when asked,
    committed.

    The run writes only its own operating system's section of
    `.purlin/evidence/ci/<feature>.json`, on whatever branch it is on. With
    `--commit` it makes one commit of the files under `ci/` and of any
    evidence file it removed, naming `started`, HEAD when the run began; it
    commits no spec, test or settings file, and nothing here pushes. The
    audit is not called here: `purlin:audit` runs on a person's machine.
    """
    _write_log(project_root, log)
    print('')
    paths = write_sections(project_root, features, sections, os_name, 'ci')
    removed = _prune(project_root, features)
    print(evidence_writer.written_line(paths, 'ci'))
    if args.commit:
        evidence_writer.commit_ci(project_root, started, removed)


if __name__ == '__main__':
    sys.exit(main())
