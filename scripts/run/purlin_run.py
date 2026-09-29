"""Run a project's marked tests, write the evidence, and audit it on request.

    purlin_run.py [--feature NAME ... | --all]
                  (--test [--remote] [--commit] | --ci)
                  [--arm-timeout SECONDS] [--project-root DIR]
    purlin_run.py [--feature NAME ... | --all] --audit [--commit]
                  [--arm-timeout SECONDS] [--project-root DIR]

**Before anything runs.** With no `.purlin/config.json` the run says so,
names `purlin:init`, writes nothing and exits 1. In a project an older Purlin
set up and nobody upgraded (`update.set_up_by_095`) it names
`purlin:init --update` the same way. With the `tests` setting empty it
writes nothing and exits 1: where it detects a test tool it knows, it prints
that tool's entry to add (`frameworks.suggest`), and otherwise it asks for
`purlin:test`, which reads the project and proposes one.

**Which features run.** `--feature` names them and `--all` runs every one.
With neither, `--test` and `--audit` run the features the change touched:
`fingerprint.selection` selects a feature with no section for this
operating system, one whose newest such section was taken over another
spec, code or tests, one with an untracked file under its scope or beside
its tests, and one whose spec names no files. Before anything runs the run
prints what it selected and why, what it skipped, and each untracked file
that selected a feature; with nothing selected it says so and runs no test.
`--ci` with no feature named runs every feature.

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
every feature it covered and re-renders `.purlin/tests.md` from every
evidence file. It names each rule that fails or has no test, with the
command that fixes it, and ends on the status table, the summary sentence
and `Left to do`, which count every rule under `specs/`. It writes and does
not commit. `--commit` makes two commits under the person's own identity:
the specs of the features run, the test files carrying their markers and
the settings file, then the evidence and the table, which name the first;
nothing here ever pushes. `--remote` hands the run to the git host's runner
instead and brings back what that runner wrote.

`--audit` is what `purlin:audit` runs: the tests, as `--test` runs them, then
the breaks where mutation testing is on, then the AI audit, then the evidence
write. The AI audit reads each own rule of the features run that has a proof
with a test, whose passed cell reads `passed`, and that has no audit entry for
its current rule, proof and test hashes. `--all` runs every feature and reads
every such rule again; with no feature named and no `--all`, the tests run
on the selection above and every feature's rules are read, skipping those
that match their last audit. One model call per rule, `audit_parallel` at
once (`scripts/review/ai_audit.py` makes them). Before the first call the
run prints `AI audit: <n> rules to read, <k> at a time.` and carries on
without asking. What the audit found lands in the same evidence file, under
`audit`, and `--commit` commits it the same way. A rule the model could not
be reached for gets nothing written and reads `not audited`. After the
evidence lines the audit prints one line, `AI audit: <n> rules read, <s>
strong, <w> weak.`, then one line per reason a rule could not be audited,
then the status table, the summary sentence and `Left to do`.

`--ci` is the arm a remote runner runs. On a run branch it writes this
runner's section of `.purlin/evidence/ci/<feature>.json` and always commits
it, through the git host's API, because the evidence exists nowhere else. No
breaks run there and the AI audit is not called. On a tag run it runs the
tests and writes nothing.

A proof the spec tags `@env` for another operating system is not run here.
The run says so in one sentence and names `purlin:test --remote`.

No arm and no engine ever reads this process's stdin, and none may ask git
for a password: a runner is nobody's terminal, and a command that stops for
an answer holds the whole run until the job limit cancels it. Every arm also
gets `--arm-timeout` seconds, 3600 by default; past it the arm is killed,
what it printed is kept, the run reports the timeout as missing evidence and
carries on.

Exit codes for `--test` and `--audit`: 0 everything asked happened; 1 a tied
test failed or did not run, evidence is missing, a marker names nothing a
spec has, there is no settings file, an older Purlin set the project up and
it was not upgraded, no test command is set, or, for `--audit` above the
gate `passed`, a rule it read is weak or could not be audited; 2 the command
line was wrong. `--ci` exits 1 only when a test failed or could not run.

The flow is one pass. Resolve the configuration and the suites, scan the
specs and the markers, run each suite, then check two things no test
framework reports on its own:

  loud failure A  a suite ran and left no report to read
  loud failure B  a marker of a feature this run covers has no passing or
                  failing result: its test was skipped, no case in the report
                  is its test, or no test follows the marker

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
_INIT_DIR = os.path.join(os.path.dirname(_HERE), 'init')
for _path in (_MCP_DIR, _REVIEW_DIR, _INIT_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from config_engine import resolve_config                      # noqa: E402
from purlin import (console as console_module,                # noqa: E402
                    evidence as evidence_reader,
                    fingerprint as fingerprint_module,
                    frameworks as frameworks_module,
                    gate as gate_module, markers as markers_module,
                    payload as payload_module,
                    specs as specs_module,
                    status as status_module)
import evidence as evidence_writer                             # noqa: E402
import reports as reports_module                               # noqa: E402

LOG_PATH = os.path.join('.purlin', 'runtime', 'run.log')

USAGE = (
    'Usage: purlin_run.py [--feature NAME ... | --all] '
    '(--test [--remote] [--commit] | --ci) '
    '[--arm-timeout SECONDS] [--project-root DIR]\n'
    '       purlin_run.py [--feature NAME ... | --all] --audit [--commit] '
    '[--arm-timeout SECONDS] [--project-root DIR]')

# The one line `purlin:test --remote` gets. A remote runner runs the tests,
# so the flag belongs to the test and nowhere else.
REMOTE_IS_A_TEST = ('a remote runner runs the tests, so --remote belongs to '
                    '--test. Run: purlin:test --remote')

# What the run says about a proof tagged for an operating system it is not
# on, each system in the words a person reads.
FOREIGN_PROOF = ('%s %s needs %s; this machine is %s. Run purlin:test '
                 '--remote.')

# The one line `--commit` gets anywhere but `--test` and `--audit`. A runner
# always commits, and a remote run commits nothing here.
COMMIT_IS_A_PERSONS = ('--commit belongs to --test and --audit; a remote run '
                       'commits on the runner')

# How long one arm may take before it is killed. An hour is longer than any
# shipped suite and far shorter than a hosted runner's six-hour job limit, so
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
SUGGESTED_ENTRY = 'Suggested entry: %s'
NO_TEST_TOOL = ('No test command is set in .purlin/config.json, and no test '
                'tool Purlin knows was found, so nothing ran. Run purlin:test '
                'to have one proposed.')

# What the run says about each rule of the features it ran that fails or
# has no test, before the status.
RULE_FAILS = '%s %s fails: %s. Run purlin:build %s.'
RULE_HAS_NO_TEST = '%s %s has no test. Run purlin:build %s.'

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
        self.remote = False
        self.commit = False
        self.arm_timeout = ARM_TIMEOUT_DEFAULT
        self.project_root = '.'
        self.error = None


def parse_args(argv):
    args = Args()
    actions = []
    index = 0
    while index < len(argv):
        token = argv[index]
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
        elif token == '--remote':
            args.remote = True
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
    if args.remote and args.action != 'test':
        args.error = REMOTE_IS_A_TEST
        return args
    if args.commit and (args.action == 'ci' or args.remote):
        args.error = COMMIT_IS_A_PERSONS
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


# ---------------------------------------------------------------------------
# The suites
# ---------------------------------------------------------------------------

def arm_environment(extra=None):
    """The environment every suite and every engine is given.

    `GIT_TERMINAL_PROMPT=0` makes git fail instead of asking for a password.
    A hosted runner is nobody's terminal, so the question would never be
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
    has read the command. Every hosted Windows runner is such a machine.

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


def _run(command, project_root, log, timeout, environment=None,
         keep_stdout=False):
    """Run one command in the project root, echoing it and its output.

    The command gets no stdin: a runner is nobody's terminal, and a prompt
    nobody answers is a run that never ends. It gets `timeout` seconds; past
    them it is killed, whatever it printed is kept, and `TIMED_OUT` comes
    back so the caller names the timeout as missing evidence. With
    `keep_stdout` the answer is `(code, stdout)`, for a suite whose report
    is its standard output.
    """
    log.append('$ %s' % ' '.join(command))
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

    The suites write into the run log, which is a file on the runner and
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
        self.file_results = {}    # path -> pass | fail, for an exit suite
        self.failures = []
        self.failed_tests = False  # it ran, and at least one test failed
        self.problems = []
        self.log = ''


def run_suite(project_root, suite, files, log, timeout=ARM_TIMEOUT_DEFAULT,
              marked=None):
    """Run one suite and read what it saw. A `SuiteRun`.

    `files` is the test files to hand `{files}`, or empty for the whole
    suite. An `exit` suite runs its command once per file, `{files}` being
    that one file, and every file it matches when `files` is empty; each
    file passes when the command exits 0. Any other suite runs once and its
    report is read and tied to the markers in `marked`.
    """
    done = SuiteRun(suite)
    mark = len(log)
    if suite.format == 'exit':
        paths = list(files) or sorted(markers_module.test_files(
            project_root, [suite]))
        failed = []
        for path in paths:
            command = reports_module.command_for(suite, [path])
            code = _run([bash_command(), '-c', command], project_root, log,
                        timeout)
            if code == TIMED_OUT:
                done.failures.append('the %s suite timed out after %d s on '
                                     '%s' % (suite.name, timeout, path))
                continue
            done.file_results[path] = (reports_module.PASS if code == 0
                                       else reports_module.FAIL)
            if code != 0:
                failed.append(path)
        done.failed_tests = bool(failed)
        done.log = '\n'.join(log[mark:])
        return done

    report = suite.report_path()
    reports_module.clear_report(project_root, report)
    command = reports_module.command_for(suite, files, report)
    code, stdout = _run([bash_command(), '-c', command], project_root, log,
                        timeout, keep_stdout=True)
    done.log = '\n'.join(log[mark:])
    if code == TIMED_OUT:
        done.failures.append('the %s suite timed out after %d s'
                             % (suite.name, timeout))
    done.failed_tests = code not in (0, TIMED_OUT)
    cases, problem = reports_module.read_report(suite.format, project_root,
                                                report, stdout)
    if problem:
        # Loud failure A: the suite ran and there is no report to read. A
        # suite that exits non-zero over a report it wrote has only failing
        # tests, which the report itself says.
        done.failures.append('the %s suite %s' % (suite.name, problem))
        return done
    here = {path: found for path, found in (marked or {}).items()
            if markers_module.suite_of(path, [suite]) is suite}
    done.outcomes, done.problems = reports_module.tie(project_root, suite,
                                                      cases, here)
    return done


def marker_results(scan, suites, runs):
    """`{(feature, id): [entry, ...]}` for every marker whose suite ran.

    Each entry is `{status, test_file, test_name, line}`, `status` being
    `pass`, `fail` or `not run`. A marker no test follows gets no entry: the
    run reports it by file and line instead.
    """
    by_name = {run.suite.name: run for run in runs}
    index = {}
    for path in sorted(scan):
        found = scan[path]
        suite = markers_module.suite_of(path, suites)
        done = by_name.get(suite.name) if suite else None
        if done is None:
            continue
        if found.whole:
            status = done.file_results.get(path, reports_module.NOT_RUN)
            for marker in found.markers:
                index.setdefault(marker.key(), []).append({
                    'status': status, 'test_file': path,
                    'test_name': reports_module.test_name(path, None, 'exit'),
                    'line': marker.line})
            continue
        for test in found.tests:
            if not test.markers:
                continue
            status = reports_module.result_of(
                done.outcomes.get((path, test.line), []))
            for marker in test.markers:
                index.setdefault(marker.key(), []).append({
                    'status': status, 'test_file': path,
                    'test_name': reports_module.test_name(path, test,
                                                          suite.format),
                    'line': marker.line})
    return index


def marked_files(scan, suite, selected):
    """The `/` relative paths, sorted, of one suite's files a run gives `{files}`.

    A file is given when it carries a marker of a feature in `selected`. The
    files are read from the disk, tracked or not, so a new test is run
    before anyone has added it.
    """
    wanted = set(selected)
    return sorted(path for path, found in scan.items()
                  if markers_module.suite_of(path, [suite]) is suite
                  and found.features() & wanted)


# ---------------------------------------------------------------------------
# Who ran, and on what
# ---------------------------------------------------------------------------

def runner_name(project_root, args):
    """`ci` on a runner, else the slug of the person's git email."""
    if args.action == 'ci':
        return 'ci'
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


def scope_by_feature(features, selected):
    return {name: list((features.get(name) or {}).get('scope', []))
            for name in selected}


# ---------------------------------------------------------------------------
# The evidence
# ---------------------------------------------------------------------------

def machine_name(args, os_name):
    """What a section names the machine it ran on.

    A person's own run names the host, `unknown` where it has no name; a
    remote runner names its kind and system, `remote runner, Windows`.
    """
    if args.action == 'ci':
        from host import runner_machine
        return runner_machine(os_name)
    return platform.node() or 'unknown'


def build_sections(project_root, args, features, selected, index, os_name):
    """`{feature: section}`, one section per feature this run covered."""
    commit = head_commit(project_root)
    dirty = working_tree_dirty(project_root)
    runner = runner_name(project_root, args)
    markers = fingerprint_module.marker_index(project_root)
    machine = machine_name(args, os_name)
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
        sections[name] = evidence_writer.build_section(
            info, entries, os_name, commit, dirty, runner,
            fingerprint_module.fingerprint(project_root, name, features,
                                           markers),
            machine=machine, hostname=platform.node())
    return sections


def write_sections(project_root, features, sections, os_name, source):
    """Merge each section into its feature's file. The paths.

    Each file is read from disk and only this operating system's section is
    replaced, so a `--feature` run, and a run on another machine, leave
    every other section as it was.
    """
    return [evidence_writer.write_section(
        project_root, source, name, features.get(name) or {}, os_name,
        section) for name, section in sections.items()]


def rule_problems(features, sections, index):
    """One line per rule of the features run that fails or has no test.

    Read from the words this run's sections give each rule, so the lines,
    the evidence and the exit code say the same. A failing rule names each
    of its tests that failed here.
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


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

def main(argv=None):
    # UTF-8 so the table's glyphs survive a cp1252 console, line buffering
    # so a hosted runner's log shows where a long run got to.
    console_module.force_utf8_stdio(line_buffering=True)
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.error:
        print('purlin: %s.' % args.error, file=sys.stderr)
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
    cfg = gate_module.resolve_gate(config)
    for warning in cfg.warnings:
        print(warning)

    if args.remote:
        return _remote(project_root, args, cfg)

    features = specs_module.scan_specs(project_root)
    if not features:
        print(status_module.NO_SPECS)
        return 1
    suites, suite_problems = markers_module.read_suites(project_root, config)
    for problem in suite_problems:
        print('purlin: %s.' % problem)
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
            print('purlin: no spec named %s under specs/.' % name,
                  file=sys.stderr)
        if unknown:
            return 2
    else:
        selected = print_selection(
            fingerprint_module.selection(project_root, features, os_name),
            'purlin:%s' % args.action)
        if not selected:
            return _nothing_to_run(project_root, args, features, cfg)

    foreign = foreign_env_proofs(features, selected, os_name)
    foreign_ids = {(feature, proof_id) for feature, proof_id, _env in foreign}
    # A run over every feature runs every suite whole. A narrower run gives
    # each suite the files that carry a marker of a feature it runs, and a
    # suite with none of those is not started.
    narrow = len(selected) < len(features)
    scan = markers_module.scan(project_root, suites)

    log = []
    failures = []
    runs = []
    for suite in suites:
        files = []
        if narrow:
            files = marked_files(scan, suite, selected)
            if not files:
                continue
        # One line per suite before it starts, so a job log says where a run
        # is while it is still running.
        print('Running the %s suite.' % suite.name)
        done = run_suite(project_root, suite, files, log, args.arm_timeout,
                         scan)
        runs.append(done)
        failures.extend(done.failures)
        if done.failures or done.failed_tests:
            print_arm_output(suite.name, done.log)
        for problem in done.problems:
            print(problem)

    index = marker_results(scan, suites, runs)
    ran_suites = {done.suite.name for done in runs}
    missing = []
    for (feature, marker_id), entries in sorted(index.items()):
        if feature not in selected or (feature, marker_id) in foreign_ids:
            continue
        for entry in entries:
            if entry['status'] in (reports_module.PASS, reports_module.FAIL):
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
            if marker.feature in selected:
                missing.append('%s %s at %s:%d' % (marker.feature, marker.id,
                                                   path, marker.line))
    # A marker naming nothing a spec has fails the run, whatever the tests did.
    wrong = reports_module.marker_problems(scan, features)
    if scan:
        print('')
        print(TIED_LINE % (tied, untied))
        for line in reports_module.untied_lines(scan) + wrong:
            print(line)
    if missing:
        # Loud failure B: a marker of a feature this run covers has no result.
        # Five are named and the rest counted: a reader acts on the first few
        # either way.
        shown = ', '.join(missing[:5])
        more = ('' if len(missing) <= 5
                else ', and %d more' % (len(missing) - 5))
        failures.append('%s no passing or failing result: %s%s'
                        % ('1 marker has' if len(missing) == 1
                           else '%d markers have' % len(missing), shown, more))
    ran = [done.suite.name for done in runs]

    print('Ran %s on %s.'
          % (', '.join(ran) or 'nothing',
             '1 feature' if len(selected) == 1
             else '%d features' % len(selected)))
    if foreign:
        print('')
        for feature, proof_id, env in foreign:
            print(FOREIGN_PROOF % (feature, proof_id,
                                   evidence_reader.os_word(env),
                                   evidence_reader.os_word(os_name)))

    # A failing test is a result the evidence records, so it fails the run
    # without being called missing; only a suite that left nothing to read,
    # or a marker with no result, is missing evidence.
    tests_failed = bool(failures or any(done.failed_tests for done in runs))
    exit_code = 1 if (tests_failed or wrong) else 0
    if failures:
        print('')
        for failure in failures:
            print('Evidence is missing: %s.' % failure)

    work = None
    if args.commit:
        print('')
        work = commit_the_work(project_root,
                               work_paths(scan, features, selected))
    sections = build_sections(project_root, args, features, selected, index,
                              os_name)
    problems = rule_problems(features, sections, index)
    if problems:
        print('')
        for line in problems:
            print(line)

    if args.action == 'ci':
        # Called whatever the arms found: a run that reports missing evidence
        # still commits what it saw, which is where a reader finds out what
        # went missing. Only the tests decide the job's exit code.
        _ci(project_root, features, sections, log, os_name)
        print('')
        print(status_module.sync_status(project_root))
        return 1 if tests_failed else 0

    print('')
    paths = write_sections(project_root, features, sections, os_name, 'local')
    removed = _prune(project_root, features)
    if args.action == 'audit':
        # The tests ran on the selection; the audit reads every feature's
        # rules unless features were named, and skips each rule whose text,
        # proof and test match its last audit.
        return _audit(project_root, args, features,
                      selected if args.features else sorted(features), log,
                      cfg, paths, removed, exit_code, work)
    evidence_writer.write_table(project_root)
    print(evidence_writer.written_line(paths))
    if args.commit:
        commit_the_evidence(project_root, work, removed)

    print('')
    print(status_module.sync_status(project_root))
    return exit_code


def settings_stop(project_root):
    """The line a run stops on before anything runs, or None.

    No settings file, or a project an older Purlin set up that was not
    upgraded: each names the command that puts it right.
    """
    import update as update_module
    if not os.path.isfile(os.path.join(project_root, SETTINGS_PATH)):
        return NO_SETTINGS
    if update_module.set_up_by_095(project_root):
        return SET_UP_BY_AN_OLDER_PURLIN
    return None


def no_test_command_lines(project_root):
    """What a run with no suite prints: the entry to add, or where to get one.

    Where a test tool Purlin knows is detected, its entry, as one line of
    JSON to put under `tests`, and what the tool needs added before it can
    write its report; otherwise `purlin:test`, which reads the project and
    proposes one.
    """
    entry = frameworks_module.suggest(project_root)
    if entry is None:
        return [NO_TEST_TOOL]
    lines = [NO_TEST_COMMAND, SUGGESTED_FOR % (entry['name'], entry['run']),
             SUGGESTED_ENTRY % json.dumps(entry)]
    needs = frameworks_module.NEEDS.get(entry['name'])
    if needs:
        lines.append(needs)
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


def _nothing_to_run(project_root, args, features, cfg):
    """A run with no feature named that selected nothing. The exit code.

    No test runs. `--commit` still commits the settings and evidence an
    earlier run wrote, because that is the command a refused tag names.
    `--audit` goes on to the AI audit, which reads every rule that has no
    audit of its current text, proof and test. The tests this run answers
    with are the ones the evidence already holds: a rule whose tests fail
    there exits 1.
    """
    print(NOTHING_TO_RUN % ('purlin:%s' % args.action))
    exit_code = 1 if failed_rules(project_root) else 0
    work = None
    if args.commit:
        print('')
        work = commit_the_work(project_root, work_paths({}, features, []))
    if args.action == 'audit':
        return _audit(project_root, args, features, sorted(features), [],
                      cfg, [], [], exit_code, work)
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

# What the audit says before its first call, and when it has nothing to read.
TO_READ = 'AI audit: %d %s to read, %d at a time.'
NOTHING_TO_READ = ('AI audit: nothing to read; every rule matches its last '
                   'audit.')

# What it says when it is done.
SKIPPED = ('%d %s skipped; %s text, proof and test match %s last audit. '
           'purlin:audit --all reads them again.')
NOT_ON_PATH_LINE = 'Install Claude Code, then run purlin:audit again.'
TRY_AGAIN_LINE = 'Run purlin:audit again.'


def _plural(count, one, many):
    return one if count == 1 else many


def _audit(project_root, args, features, selected, log, cfg, paths, removed,
           exit_code, work=None):
    """The `--audit` arm, after the tests: the breaks, the AI audit, the write.

    Which rules are read is `ai_audit.is_read`'s answer. The breaks run only
    where mutation testing is on, and only for a feature with a rule being
    read. One model call per rule, `cfg.audit_parallel` at once. What each
    answer found goes under `audit.rules` in the feature's local evidence;
    a rule the model could not be reached for gets nothing, and the reason
    goes to `.purlin/runtime/` for the strong cell to name. `work` is the
    first commit `--commit` made, which the evidence commit names. Returns
    the exit code.
    """
    import ai_audit

    _write_log(project_root, log)
    gate = cfg.gate
    payload = payload_module.build_payload(project_root, generated_by='audit')
    to_read, skipped = [], 0
    for feature in payload.get('features') or ():
        if feature.get('name') not in selected:
            continue
        for rule in feature.get('rules') or ():
            if rule.get('feature') != feature.get('name'):
                continue
            if ai_audit.is_read(rule, again=args.all):
                to_read.append((feature['name'], rule['id']))
            elif ai_audit.is_read(rule, again=True):
                skipped += 1
    to_read.sort(key=lambda pair: (pair[0], _rule_number(pair[1])))

    print('')
    if to_read:
        print(TO_READ % (len(to_read), _plural(len(to_read), 'rule', 'rules'),
                         min(cfg.audit_parallel, len(to_read))))
    else:
        print(NOTHING_TO_READ)

    measured = sorted({feature for feature, _rule in to_read})
    if cfg.breaks and measured:
        breaks = _run_breaks(project_root, args, features, measured)
        commit = head_commit(project_root)
        for name in measured:
            score = (((breaks.get('features') or {}).get(name) or {})
                     .get('scope_score') or {}).get('score')
            mutation = {'engine': breaks.get('engine') or 'none',
                        'score': score, 'at': evidence_writer.now_iso(),
                        'commit': commit}
            evidence_writer.write_audit(project_root, 'local', name,
                                        features.get(name) or {}, {},
                                        mutation, True)
        payload = payload_module.build_payload(project_root,
                                               generated_by='audit')

    readings = [ai_audit.reading_for(project_root, payload, feature, rule)
                for feature, rule in to_read]
    results = ai_audit.audit_all(project_root, readings, cfg.audit_parallel)

    commit = head_commit(project_root)
    entries_by_feature = {}
    failures = {}
    answered = []
    counts = {'strong': 0, 'weak': 0, 'undecided': 0}
    causes = {}
    for (feature, rule_id), found in zip(to_read, results):
        entry = ai_audit.rule_entry(payload, feature, rule_id) or {}
        if found.get('why'):
            causes[found['why']] = causes.get(found['why'], 0) + 1
            failures[(feature, rule_id)] = {
                'rule_hash': entry.get('rule_hash'),
                'proof_hash': entry.get('proof_hash'),
                'test_hash': entry.get('test_hash'), 'why': found['why']}
            continue
        answered.append((feature, rule_id))
        counts[found['verdict']] += 1
        written = evidence_writer.audit_entry(entry, found, commit)
        entries_by_feature.setdefault(feature, {})[rule_id] = written
    for feature, entries in sorted(entries_by_feature.items()):
        evidence_writer.write_audit(project_root, 'local', feature,
                                    features.get(feature) or {}, entries,
                                    None, False)
    evidence_writer.write_could_not_run(project_root, failures, answered)
    evidence_writer.write_table(project_root)

    print('')
    # The files the tests wrote, then any the audit alone wrote into: a run
    # that selected nothing for its tests still writes what the audit found.
    written = list(paths)
    for feature in sorted(entries_by_feature):
        path = evidence_reader.evidence_path('local', feature)
        if path not in written:
            written.append(path)
    if written:
        print(evidence_writer.written_line(written))
    if args.commit:
        commit_the_evidence(project_root, work, removed)
    # The one line the audit keeps before the ending: what it read and found,
    # then why any rule could not be read.
    print(_summary_line(counts, skipped))
    for why in sorted(causes):
        print('%d %s could not be audited: %s. %s'
              % (causes[why], _plural(causes[why], 'rule', 'rules'), why,
                 NOT_ON_PATH_LINE if why == ai_audit.NOT_ON_PATH
                 else TRY_AGAIN_LINE))
    print('')
    print(status_module.sync_status(project_root))
    if gate == 'passed':
        return exit_code
    # Above `passed` a rule it read that is weak, or that it could not
    # audit, fails it. It cannot make a signature appear, so a rule waiting
    # on one does not fail the audit.
    return exit_code or (1 if causes or weak_rules(project_root, answered)
                         else 0)


def weak_rules(project_root, read):
    """How many of the rules `read` names have a strong cell reading `weak`.

    What the model found and the strength the breaks measured both make the
    cell weak, so the cell is what is read.
    """
    wanted = set(read)
    payload = payload_module.build_payload(project_root, generated_by='audit')
    return sum(1 for feature in payload.get('features') or ()
               for rule in feature.get('rules') or ()
               if rule.get('feature') == feature.get('name')
               and (feature['name'], rule.get('id')) in wanted
               and ((rule.get('cells') or {}).get('strong') or {}).get('word')
               == 'weak')


def _summary_line(counts, skipped):
    """`AI audit: <n> rules read, <n> strong, <n> weak.` and what it skipped."""
    read = sum(counts.values())
    parts = ['%d %s read' % (read, _plural(read, 'rule', 'rules')),
             '%d strong' % counts['strong'], '%d weak' % counts['weak']]
    if counts['undecided']:
        parts.append('%d undecided' % counts['undecided'])
    line = 'AI audit: %s.' % ', '.join(parts)
    if skipped:
        line += ' ' + SKIPPED % (skipped, _plural(skipped, 'rule', 'rules'),
                                 _plural(skipped, 'its', 'their'),
                                 _plural(skipped, 'its', 'their'))
    return line


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def _run_breaks(project_root, args, features, selected):
    """The breaks, through the engine the project resolved to.

    `selected` is the features with a rule the audit reads: a score is
    measured for a feature only then.
    """
    import mutation as mutation_module
    from mutation import select_engine, run_breaks
    config = resolve_config(project_root)
    # The suites the settings name, then what detection finds: a suite named
    # for its framework picks that framework's engine first.
    suites, _problems = markers_module.read_suites(project_root, config)
    engine = select_engine(config, [suite.name for suite in suites]
                           + frameworks_module.detect_frameworks(project_root))
    # The engine reaches its own subprocesses, so the cap is set on the
    # module rather than passed down through every adapter.
    mutation_module.ARM_TIMEOUT = args.arm_timeout
    print('Measuring the breaks with the %s engine.' % engine)
    answer = run_breaks(project_root, engine,
                        scope_by_feature(features, selected))
    # An installed engine answers a reason only when it measured nothing it
    # set out to, a timeout being the one case, so the person sees why test
    # strength was not measured rather than finding it in the log.
    if answer.get('available') and answer.get('reason'):
        print('purlin: %s' % answer['reason'])
    return answer


# ---------------------------------------------------------------------------
# CI
# ---------------------------------------------------------------------------

def _ci(project_root, features, sections, log, os_name):
    """The `--ci` arm: on a run branch, this runner's sections, committed.

    A runner writes only its own operating system's section of
    `.purlin/evidence/ci/<feature>.json` and commits it through the git
    host's API, merged on every attempt into what the branch's head holds,
    because its evidence exists nowhere else. No breaks run here and the AI
    audit is not called: `purlin:audit` on a person's machine does both. A
    tag run runs the tests and writes nothing.
    """
    from host import commit_files, commits_here, no_commit_line

    if not commits_here(project_root):
        print('')
        print(no_commit_line(project_root))
        return

    _write_log(project_root, log)
    print('')
    paths = write_sections(project_root, features, sections, os_name, 'ci')
    _prune(project_root, features)
    print(evidence_writer.written_line(paths, 'ci'))
    commit = head_commit(project_root)
    merge = evidence_writer.merge_for_host(
        os_name, {name: list((info or {}).get('rule_order') or ())
                  for name, info in features.items()})
    commit_files(project_root, paths, evidence_writer.COMMIT_SUBJECT
                 % (commit[:7] or 'an unknown commit'), merge)
    print(evidence_writer.COMMITTED)


def _remote(project_root, args, cfg=None):
    """`--test --remote`: let the git host's runner do the run.

    The runner runs the same tests this machine would, writes its own
    operating system's section of each feature's `ci/` evidence, and commits
    it on the run branch; the run pulls that commit back.
    """
    from remote import run_remote
    return run_remote(project_root, args, cfg)


if __name__ == '__main__':
    sys.exit(main())
