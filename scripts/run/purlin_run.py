"""Run a project's tagged tests, write the evidence, and audit it on request.

    purlin_run.py [--feature NAME ... | --all]
                  (--test [--remote] [--commit] | --ci)
                  [--arm-timeout SECONDS] [--project-root DIR]
    purlin_run.py [--feature NAME ... | --all] --audit [--commit]
                  [--arm-timeout SECONDS] [--project-root DIR]

**Which features run.** `--feature` names them and `--all` runs every one.
With neither, `--test` and `--audit` run the features the change touched:
`fingerprint.selection` selects a feature with no section for this
operating system, one whose newest such section was taken over another
spec, code or tests, one with an untracked file under its scope or beside
its tests, and one whose spec names no files. Before anything runs the run
prints what it selected and why, what it skipped, and each untracked file
that selected a feature; with nothing selected it says so, runs no test,
and exits on the gate. Every arm then runs only the test files that carry a
marker of a feature being run, except xUnit, whose `dotnet test` runs the
whole suite. `--ci` with no feature named runs every feature.

`--test` is what `purlin:test` runs: the plugins run the tagged tests into
`.purlin/runtime/proofs/`, and the run writes this operating system's section
of `.purlin/evidence/local/<feature>.json` for every feature it covered,
re-renders `.purlin/tests.md` from every evidence file, prints the table and
ends with `gate passed: <n> of <rules>` or `gate not met: <n> of <rules>`.
It writes and does not commit. `--commit` commits the evidence and the table
under the person's own identity as `purlin: evidence at <sha7>`; nothing here
ever pushes. `--remote` hands the commit to the git host's runner instead and
brings back what that runner wrote.

`--audit` is what `purlin:audit` runs: the tests, as `--test` runs them, then
the breaks where mutation testing is on, then the AI audit, then the evidence
write. The AI audit reads each own rule of the features run that has a proof
with a test, whose passed cell reads `passed`, and that has no audit entry for its
current rule, proof and test hashes; under a gate above `passed` a rule whose
level is `passed` is not read. `--all` runs every feature and reads every
such rule again; with no feature named and no `--all`, the tests run on the
selection above and every feature's rules are read, skipping those that
match their last audit. One model call per
rule, `audit_parallel` at once (`scripts/review/ai_audit.py` makes them).
Before the first call the run prints `AI audit: <n> rules to read, <k> at a
time.` and carries on without asking. What the audit found lands in the same
evidence file, under `audit`, and `--commit` commits it the same way. A rule
the model could not be reached for gets nothing written and reads `not
audited`; at `strong` and above that exits 1. At the gate `passed` the audit
blocks nothing and the run ends on `Audit: <n> strong, <n> weak. Nothing
blocks at the gate passed.`; otherwise it ends with `gate strong: <n> of
<rules>` or `gate not met: <n> of <rules>` and exits 1 when the gate is not
met.

`--ci` is the arm the CI job runs. On a run branch it writes this runner's
section of `.purlin/evidence/ci/<feature>.json` and always commits it,
through the git host's API, because the evidence exists nowhere else. No
breaks run there and the AI audit is not called. On a tag run it writes
nothing at all: the rerun and the gate check with `--verify` are what a tag
run is for.

A proof the spec tags `@env` for another operating system is not run here. The
run says so in one sentence and names the command that adds a remote runner.

No arm and no engine ever reads this process's stdin, and none may ask git
for a password: a runner is nobody's terminal, and a command that stops for
an answer holds the whole run until the job limit cancels it. Every arm also
gets `--arm-timeout` seconds, 3600 by default; past it the arm is killed,
what it printed is kept, the run reports the timeout as missing evidence and
carries on.

Exit codes: 0 everything asked for happened, 1 a test failed, evidence is
missing or the gate is not met, 2 the command line was wrong.

The flow is one pass. Resolve the configuration and the frameworks, scan the
specs, run one arm per framework, then check two things the arms cannot check
themselves:

  loud failure A  an arm ran and its plugin appended nothing
  loud failure B  a marker sits in a test source and this run produced no
                  proof entry for it

Both are silent by default in every test framework there is, and both leave a
reader looking at a proof file from an earlier run believing it describes this
one. `references/formats/evidence_format.md` is the shape of what the run
then writes.
"""

import os
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
_REVIEW_DIR = os.path.join(os.path.dirname(_HERE), 'review')
for _path in (_MCP_DIR, _REVIEW_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from config_engine import resolve_config                      # noqa: E402
from purlin import (console as console_module,                # noqa: E402
                    evidence as evidence_reader,
                    fingerprint as fingerprint_module,
                    frameworks as frameworks_module,
                    gate as gate_module, payload as payload_module,
                    proofs as proofs_module,
                    specs as specs_module, states as states_module,
                    status as status_module)
import evidence as evidence_writer                             # noqa: E402

ARROW = '→'
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

# What the run says about a proof tagged for an operating system it is not on.
FOREIGN_PROOF = ('%s %s needs %s; this machine is %s. A remote runner runs '
                 'it: purlin:init adds one.')

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

# How many lines of a failing arm's own output the run prints. Everything an
# arm prints is captured into the run log, which a job log never shows, so an
# arm that exits non-zero or is killed would otherwise leave a reader with a
# failure and no reason. Sixty lines carry the summary and the first failing
# assertion of every framework this release runs.
ARM_TAIL_LINES = 60



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
# The markers in the test sources
# ---------------------------------------------------------------------------

# The marker patterns and the directories no marker is read from are the
# fingerprint's, so the run and the fingerprint read the same markers.
_MARKER_PATTERNS = fingerprint_module.MARKER_PATTERNS
_SKIP_DIRS = fingerprint_module.SKIP_DIRS


def _source_files(project_root, extensions):
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith('.') and d not in _SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith(extensions):
                yield os.path.join(dirpath, name)


def shell_tests(project_root):
    """Every `*.test.sh` under the project, as sorted `/` relative paths."""
    return sorted(
        os.path.relpath(path, project_root).replace(os.sep, '/')
        for path in _source_files(project_root, ('.test.sh',)))


def scan_markers(project_root, framework):
    """`{(feature, proof_id)}` every marker of one framework's syntax."""
    return {(feature, proof_id) for feature, proof_id, _path
            in _marker_hits(project_root, framework)}


def marker_paths(project_root, framework, selected):
    """The `/` relative paths, sorted, of the test files one arm runs.

    A file is run when it carries a marker, in the framework's own syntax,
    of a feature in `selected`. The files are read from the disk, tracked or
    not, so a new test is run before anyone has added it.
    """
    wanted = set(selected)
    return sorted({path for feature, _proof, path
                   in _marker_hits(project_root, framework)
                   if feature in wanted})


def _marker_hits(project_root, framework):
    extensions, pattern = _MARKER_PATTERNS.get(framework, ((), None))
    if pattern is None:
        return
    for path in _source_files(project_root, extensions):
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                text = handle.read()
        except (IOError, OSError, UnicodeDecodeError):
            continue
        rel = os.path.relpath(path, project_root).replace(os.sep, '/')
        for match in pattern.finditer(text):
            yield match.group(1), match.group(2), rel


# ---------------------------------------------------------------------------
# The runner arms
# ---------------------------------------------------------------------------

def plugin_path(project_root, basename):
    """The project's copy of a plugin, else the one shipped beside this file."""
    local = os.path.join(project_root, '.purlin', 'plugins', basename)
    if os.path.isfile(local):
        return local
    return os.path.join(os.path.dirname(_HERE), 'proof', basename)


def arm_environment(extra=None):
    """The environment every arm and every engine is given.

    `GIT_TERMINAL_PROMPT=0` makes git fail instead of asking for a password.
    A hosted runner is nobody's terminal, so the question would never be
    answered and the run would sit there until the job limit cancelled it.
    """
    environment = dict(os.environ)
    environment['GIT_TERMINAL_PROMPT'] = '0'
    environment.update(extra or {})
    return environment


def bash_command():
    """The bash that runs a shell test, found rather than taken from PATH.

    Everywhere but Windows the answer is `bash` on PATH. On Windows PATH
    normally finds `C:\\Windows\\System32\\bash.exe` first, and that is not a
    shell at all: it is the launcher for the Windows Subsystem for Linux,
    which on a machine with no distribution installed prints "Windows
    Subsystem for Linux has no installed distributions" and exits 1 before it
    has read the script. Every hosted Windows runner is such a machine.

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


def bash_path(path):
    """A path spelled the way bash reads it, on every operating system.

    Git Bash reads `C:/work/x.sh` as the file it names; the backslash spelling
    of the same path is what `os.path.join` builds on Windows, and a backslash
    is an escape to a shell. Nothing changes anywhere else, because there the
    separator already is the one bash wants.
    """
    return str(path).replace(os.sep, '/')


def _run(command, project_root, log, timeout, environment=None):
    """Run one command in the project root, echoing it and its output.

    The command gets no stdin: a runner is nobody's terminal, and a prompt
    nobody answers is a run that never ends. It gets `timeout` seconds; past
    them it is killed, whatever it printed is kept, and `TIMED_OUT` comes
    back so the caller names the timeout as missing evidence.
    """
    log.append('$ %s' % ' '.join(command))
    try:
        result = subprocess.run([*command], cwd=project_root,
                                stdin=subprocess.DEVNULL,
                                capture_output=True, text=True,
                                timeout=timeout,
                                env=environment or arm_environment())
    except subprocess.TimeoutExpired as expired:
        for stream in (expired.stdout, expired.stderr):
            if stream:
                log.append(stream.decode('utf-8', 'replace')
                           if isinstance(stream, bytes) else stream)
        log.append('timed out after %d s' % timeout)
        return TIMED_OUT
    except (OSError, subprocess.SubprocessError) as error:
        log.append(str(error))
        return 127
    for stream in (result.stdout, result.stderr):
        if stream:
            log.append(stream.rstrip('\n'))
    return result.returncode


def print_arm_output(framework, text):
    """Print the tail of one arm's captured output, as soon as it failed.

    The arms write into the run log, which is a file on the runner and never
    reaches a job log, so an arm that exits non-zero or is killed reads there
    as a bare exit code. This puts the last `ARM_TAIL_LINES` lines of that
    arm's own output on stdout, flushed, before the missing-evidence lines,
    so the reason is in the job log every time.
    """
    lines = text.splitlines()
    print('--- %s output (last %d lines) ---' % (framework, ARM_TAIL_LINES))
    if lines:
        for line in lines[-ARM_TAIL_LINES:]:
            print(line)
    else:
        print('The %s arm printed nothing.' % framework)
    print('--- end of %s output ---' % framework)
    sys.stdout.flush()


def run_framework(project_root, framework, config, log,
                  timeout=ARM_TIMEOUT_DEFAULT, only=None):
    """Run one framework's tagged tests. The exit code its runner gave.

    `only` is the list of test files to run, `marker_paths`' answer, or None
    to run the framework's whole suite. xUnit runs its whole suite either
    way: `dotnet test` runs a project, not a file.

    `TIMED_OUT` comes back when the arm ran past `timeout` seconds and was
    killed. Every command runs without stdin and without a git password
    prompt, because both are ways for a run on a hosted runner to stop for an
    answer that never arrives.
    """
    files = list(only or ())
    if framework == 'pytest':
        # `mutants/` is mutmut's copy of the project, tests included. A test
        # collected twice under one module name stops pytest before a single
        # test runs, so the copy is never collected.
        command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                   '--ignore=mutants'] + files
        code = _run(command, project_root, log, timeout)
        # pytest exits 5 when it collected nothing. No tests is not a failure
        # here; the two loud failures below are what report that.
        return 0 if code == 5 else code
    if framework == 'jest':
        return _run(['npx', 'jest', '--passWithNoTests'] + files,
                    project_root, log, timeout)
    if framework == 'vitest':
        return _run(['npx', 'vitest', 'run', '--passWithNoTests'] + files,
                    project_root, log, timeout)
    if framework == 'xunit':
        return _run(['dotnet', 'test', '--logger', 'purlin'], project_root,
                    log, timeout)
    if framework == 'shell':
        # Every `*.test.sh` in the project, the root and each subdirectory
        # alike, run from the root by its relative path in sorted order.
        code = 0
        for path in shell_tests(project_root):
            if only is not None and path not in files:
                continue
            code = _run([bash_command(), path], project_root, log, timeout)
            if code != 0:
                break
        return code
    if framework == 'sql':
        engine = config.get('sql_engine') or 'sqlite3'
        harness = plugin_path(project_root, 'sql_purlin.sh')
        tests_dir = os.path.join(project_root, 'tests')
        code = 0
        environment = arm_environment({'PURLIN_SQL_ENGINE': engine})
        for name in sorted(os.listdir(tests_dir)
                           if os.path.isdir(tests_dir) else []):
            if not name.endswith('.sql'):
                continue
            if only is not None and 'tests/' + name not in files:
                continue
            code = _run([bash_command(), bash_path(harness),
                         os.path.join('tests', name)],
                        project_root, log, timeout, environment)
            if code != 0:
                break
        return code
    log.append('purlin: no runner arm for "%s"; its tests were not run.'
               % framework)
    return 0


# ---------------------------------------------------------------------------
# The evidence this run produced
# ---------------------------------------------------------------------------

def proof_index(project_root):
    """`{(feature, proof_id): [entry, ...]}` from the runtime proof files."""
    index = {}
    for feature, entries in proofs_module.load_proofs(project_root).items():
        for entry in entries:
            index.setdefault((feature, entry.get('id', '')), []).append(entry)
    return index


def clear_proofs(project_root):
    """Empty `.purlin/runtime/proofs/` so this run's evidence is this run's.

    Proof files are runtime, so nothing is lost: what a previous run observed
    is either still true, in which case this run observes it again, or stale,
    in which case keeping it is what hides the failure.
    """
    directory = proofs_module.proof_dir(project_root)
    try:
        names = os.listdir(directory)
    except OSError:
        return
    for name in names:
        if name.endswith('.json'):
            try:
                os.remove(os.path.join(directory, name))
            except OSError:
                continue


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


def tests_by_rule(features, selected, index):
    out = {}
    for name in selected:
        info = features.get(name) or {}
        for rule_id, proof_ids in (info.get('proofs_by_rule') or {}).items():
            tests = []
            for proof_id in proof_ids:
                for entry in index.get((name, proof_id), []):
                    tests.append({'file': entry.get('test_file', ''),
                                  'name': entry.get('test_name', ''),
                                  'plugin': entry.get('plugin', '')})
            if tests:
                out[(name, rule_id)] = tests
    return out


# ---------------------------------------------------------------------------
# The evidence
# ---------------------------------------------------------------------------

def write_sections(project_root, args, features, selected, index, os_name,
                   source):
    """One section per feature this run covered, merged into its file. The paths.

    Each file is read from disk and only this operating system's section is
    replaced, so a `--feature` run, and a run on another machine, leave
    every other section as it was.
    """
    commit = head_commit(project_root)
    dirty = working_tree_dirty(project_root)
    runner = runner_name(project_root, args)
    markers = fingerprint_module.marker_index(project_root)
    paths = []
    for name in selected:
        info = features.get(name) or {}
        entries = {}
        for proof_id in sorted(info.get('proofs') or {}):
            found = index.get((name, proof_id), [])
            if found:
                entries[proof_id] = found
        section = evidence_writer.build_section(
            info, entries, os_name, commit, dirty, runner,
            fingerprint_module.fingerprint(project_root, name, features,
                                           markers))
        paths.append(evidence_writer.write_section(
            project_root, source, name, info, os_name, section))
    return paths


def _prune(project_root, features):
    """Delete the evidence of every feature no spec defines, one line each."""
    removed = evidence_writer.prune(project_root, features)
    for path in removed:
        print(evidence_writer.REMOVED
              % (path, path.rsplit('/', 1)[-1][:-len('.json')]))
    return removed


def gate_line(met, rules, level='passed'):
    """The one line a run ends on, and the exit code with it.

    `level` is the cell the run answered: `passed` for `purlin:test`,
    `strong` for `purlin:audit` where that cell exists. One shape for both,
    so a reader learns the line once.
    """
    if rules and met == rules:
        return 'gate %s: %d of %d' % (level, met, rules), 0
    return 'gate not met: %d of %d' % (met, rules), 1


def project_gate_line(project_root, level='passed'):
    """`(line, exit code)` for one cell, over every rule under specs/.

    Each rule is counted once, under the feature that owns it, and the
    project is counted rather than the run, so a `--feature` run answers for
    every rule and not only for the features it ran. `purlin:test` counts
    the passed cell. `purlin:audit` counts a rule whose passed cell is met
    and, where its level asks for one, its strong cell too: a rule whose
    level is `passed` is never audited under a higher gate, and its tests
    are what it answers with.
    """
    payload = payload_module.build_payload(project_root, generated_by='run')
    met = rules = 0
    for feature in payload.get('features') or ():
        for rule in feature.get('rules') or ():
            if rule.get('feature') != feature.get('name'):
                continue
            rules += 1
            cells = rule.get('cells') or {}
            if level == 'passed':
                if states_module.cell_is_met('passed', cells.get('passed')):
                    met += 1
            elif rule.get('blocked_by') not in ('passed', 'strong'):
                met += 1
    return gate_line(met, rules, level)


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

    resolved, unknown_frameworks = frameworks_module.resolve_frameworks(
        project_root, cfg.test_framework)
    for name in unknown_frameworks:
        print('purlin: "%s" is not a framework this release ships a plugin '
              'for; its tests were not run.' % name)

    foreign = foreign_env_proofs(features, selected, os_name)
    foreign_ids = {(feature, proof_id) for feature, proof_id, _env in foreign}
    # A run over every feature runs every arm whole. A narrower run gives
    # each arm the files that carry a marker of a feature it runs, and an
    # arm with none of those is not started.
    narrow = len(selected) < len(features)

    log = []
    arm_logs = {}
    clear_proofs(project_root)
    failures = []
    ran = []
    for framework in resolved:
        markers = scan_markers(project_root, framework)
        markers = {pair for pair in markers if pair[0] in selected}
        only = None
        if narrow and framework != 'xunit':
            only = marker_paths(project_root, framework, selected)
            if not only:
                continue
        before = set(proof_index(project_root))
        # One line per arm before it starts, so a job log says where a run
        # is while it is still running.
        print('Running the %s arm.' % framework)
        mark = len(log)
        code = run_framework(project_root, framework, config,
                             log, args.arm_timeout, only)
        arm_logs[framework] = '\n'.join(log[mark:])
        after = set(proof_index(project_root))
        ran.append(framework)
        if code == TIMED_OUT:
            failures.append('the %s runner timed out after %d s'
                            % (framework, args.arm_timeout))
            print_arm_output(framework, arm_logs[framework])
        elif code != 0:
            failures.append('the %s runner exited %d' % (framework, code))
            print_arm_output(framework, arm_logs[framework])
        wanted = {pair for pair in markers if pair not in foreign_ids}
        if wanted and after == before:
            # Loud failure A: the arm ran and its plugin appended nothing.
            failures.append(
                'the %s arm ran and its plugin wrote no proof entry, though '
                '%d marked test(s) sit in the tree' % (framework, len(wanted)))

    index = proof_index(project_root)
    missing_markers = []
    for framework in resolved:
        for pair in sorted(scan_markers(project_root, framework)):
            if pair[0] not in selected or pair in foreign_ids:
                continue
            if pair not in index:
                missing_markers.append('%s %s (%s)'
                                       % (pair[0], pair[1], framework))
    if missing_markers:
        # Loud failure B: a marker in a test source and no entry from this run.
        # Five are named and the rest counted: a project mid-migration has
        # hundreds, and a reader acts on the first few either way.
        shown = ', '.join(missing_markers[:5])
        more = ('' if len(missing_markers) <= 5
                else ', and %d more' % (len(missing_markers) - 5))
        failures.append('%d marker(s) produced no proof entry: %s%s'
                        % (len(missing_markers), shown, more))

    print('Ran %s on %d feature(s).'
          % (', '.join(ran) or 'nothing', len(selected)))
    if foreign:
        print('')
        for feature, proof_id, env in foreign:
            print(FOREIGN_PROOF % (feature, proof_id, env, os_name))

    exit_code = 0
    if failures:
        exit_code = 1
        print('')
        for failure in failures:
            print('Evidence is missing: %s.' % failure)

    if args.action == 'ci':
        # Called whatever the arms found: a run that reports missing evidence
        # still commits what it saw, which is where a reader finds out what
        # went missing.
        ci_code = _ci(project_root, args, features, selected, index, log,
                      os_name)
        print('')
        print(status_module.sync_status(project_root))
        return exit_code or ci_code

    print('')
    paths = write_sections(project_root, args, features, selected, index,
                           os_name, 'local')
    removed = _prune(project_root, features)
    if args.action == 'audit':
        # The tests ran on the selection; the audit reads every feature's
        # rules unless features were named, and skips each rule whose text,
        # proof and test match its last audit.
        return _audit(project_root, args, features,
                      selected if args.features else sorted(features), log,
                      cfg, paths, removed, exit_code)
    evidence_writer.write_table(project_root)
    print(evidence_writer.written_line(paths))
    if args.commit:
        print(evidence_writer.commit_local(project_root,
                                           head_commit(project_root), removed))

    print('')
    print(status_module.sync_status(project_root))
    line, gate_code = project_gate_line(project_root, 'passed')
    print('')
    print(line)
    return exit_code or gate_code


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

    No test runs. `--commit` still commits evidence an earlier run wrote,
    because that is the command a refused signature names. `--audit` goes
    on to the AI audit, which reads every rule that has no audit of its
    current text, proof and test. Otherwise the run ends on the gate line,
    exiting 0 where the gate is met and 1 where it is not.
    """
    print(NOTHING_TO_RUN % ('purlin:%s' % args.action))
    if args.action == 'audit':
        return _audit(project_root, args, features, sorted(features), [],
                      cfg, [], [], 0)
    if args.commit:
        print('')
        print(evidence_writer.commit_local(project_root,
                                           head_commit(project_root)))
    print('')
    print(status_module.sync_status(project_root))
    line, gate_code = project_gate_line(project_root, 'passed')
    print('')
    print(line)
    return gate_code


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
NOT_MEASURED_OFF = 'Test strength: not measured; mutation testing is off.'
NOT_MEASURED_PASSED = 'Test strength: not measured; the gate is passed.'
NOT_ON_PATH_LINE = 'Install Claude Code, then run purlin:audit again.'
TRY_AGAIN_LINE = 'Run purlin:audit again.'
WENT_STALE = '%d %s went stale: %s audit findings changed.'
NOTHING_BLOCKS = 'Audit: %d strong, %d weak. Nothing blocks at the gate passed.'


def _plural(count, one, many):
    return one if count == 1 else many


def _audit(project_root, args, features, selected, log, cfg, paths, removed,
           exit_code):
    """The `--audit` arm, after the tests: the breaks, the AI audit, the write.

    Which rules are read is `ai_audit.is_read`'s answer. The breaks run only
    where mutation testing is on, and only for a feature with a rule being
    read. One model call per rule, `cfg.audit_parallel` at once. What each
    answer found goes under `audit.rules` in the feature's local evidence;
    a rule the model could not be reached for gets nothing, and the reason
    goes to `.purlin/runtime/` for the strong cell to name. Returns the exit
    code.
    """
    import ai_audit
    from purlin import signatures as signatures_module

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
            if ai_audit.is_read(rule, gate, again=args.all):
                to_read.append((feature['name'], rule['id']))
            elif ai_audit.is_read(rule, gate, again=True):
                skipped += 1
    to_read.sort(key=lambda pair: (pair[0], _rule_number(pair[1])))

    print('')
    if to_read:
        print(TO_READ % (len(to_read), _plural(len(to_read), 'rule', 'rules'),
                         min(cfg.audit_parallel, len(to_read))))
    else:
        print(NOTHING_TO_READ)

    measured = sorted({feature for feature, _rule in to_read})
    strength_line = (NOT_MEASURED_PASSED if gate == 'passed'
                     else NOT_MEASURED_OFF)
    if cfg.breaks and measured:
        breaks = _run_breaks(project_root, args, features, measured)
        strength_line = _strength_line(breaks, measured, cfg)
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
    elif cfg.breaks:
        strength_line = ('Test strength: not measured; no rule was read, so '
                         'no feature was measured.')

    readings = [ai_audit.reading_for(project_root, payload, feature, rule)
                for feature, rule in to_read]
    results = ai_audit.audit_all(project_root, readings, cfg.audit_parallel)

    commit = head_commit(project_root)
    signatures = signatures_module.load_signatures(project_root, features)
    entries_by_feature = {}
    failures = {}
    answered = []
    counts = {'strong': 0, 'weak': 0, 'undecided': 0}
    causes = {}
    went_stale = 0
    for (feature, rule_id), reading, found in zip(to_read, readings, results):
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
        before = entry.get('audit_hash')
        after = signatures_module.audit_hash(written,
                                             reading.get('test_strength'))
        if after != before:
            for signature in signatures.get((feature, rule_id)) or ():
                if signatures_module.is_current(
                        signature, entry.get('rule_hash'),
                        entry.get('proof_hash'), entry.get('test_hash'),
                        before):
                    went_stale += 1
    for feature, entries in sorted(entries_by_feature.items()):
        evidence_writer.write_audit(project_root, 'local', feature,
                                    features.get(feature) or {}, entries,
                                    None, False)
    evidence_writer.write_could_not_run(project_root, failures, answered)
    evidence_writer.write_table(project_root)

    print('')
    print(status_module.sync_status(project_root))
    print('')
    print(_summary_line(counts, skipped))
    print(strength_line)
    for why in sorted(causes):
        print('%d %s could not be audited: %s. %s'
              % (causes[why], _plural(causes[why], 'rule', 'rules'), why,
                 NOT_ON_PATH_LINE if why == ai_audit.NOT_ON_PATH
                 else TRY_AGAIN_LINE))
    if went_stale:
        print(WENT_STALE % (went_stale,
                            _plural(went_stale, 'signature', 'signatures'),
                            _plural(went_stale, 'its', 'their')))
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
        print(evidence_writer.commit_local(project_root,
                                           head_commit(project_root), removed))
    if gate == 'passed':
        print(NOTHING_BLOCKS % _project_verdicts(project_root))
        return exit_code
    line, gate_code = project_gate_line(project_root, 'strong')
    print(line)
    return exit_code or (1 if causes else 0) or gate_code


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


def _strength_line(breaks, measured, cfg):
    """`Test strength: <feature> <n>%, ... (minimum <m>).`, or why it is not."""
    scores = []
    for name in measured:
        score = (((breaks.get('features') or {}).get(name) or {})
                 .get('scope_score') or {}).get('score')
        scores.append((name, score))
    if not breaks.get('available') or all(score is None
                                          for _name, score in scores):
        reason = breaks.get('reason') or ('no mutation engine covers this '
                                          "project's tests")
        return 'Test strength: not measured; %s.' % str(reason).rstrip('.')
    return 'Test strength: %s (minimum %s).' % (
        ', '.join('%s %s' % (name, 'n/a' if score is None else '%d%%' % score)
                  for name, score in scores),
        'n/a' if cfg.min_strength is None else '%d%%' % cfg.min_strength)


def _project_verdicts(project_root):
    """`(strong, weak)` over every rule's audit entry for its current hashes."""
    payload = payload_module.build_payload(project_root, generated_by='run')
    strong = weak = 0
    for feature in payload.get('features') or ():
        for rule in feature.get('rules') or ():
            if rule.get('feature') != feature.get('name'):
                continue
            answered = (rule.get('audit') or {}).get('verdict')
            if answered == 'strong':
                strong += 1
            elif answered:
                weak += 1
    return strong, weak


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def _run_breaks(project_root, args, features, selected):
    """The breaks, through the engine the project resolved to.

    `selected` is the features with a rule the audit reads: a score is
    measured for a feature only then.
    """
    try:
        import mutation as mutation_module
        from mutation import select_engine, run_breaks
    except ImportError:
        print('purlin: the break engines are not available; test strength is '
              'not measured for this run.')
        return {'engine': None, 'available': False, 'features': {}}
    config = resolve_config(project_root)
    cfg = gate_module.resolve_gate(config)
    resolved, _unknown = frameworks_module.resolve_frameworks(
        project_root, cfg.test_framework)
    engine = select_engine(config, resolved)
    index = proof_index(project_root)
    # The engine reaches its own subprocesses, so the cap is set on the
    # module rather than passed down through every adapter.
    mutation_module.ARM_TIMEOUT = args.arm_timeout
    print('Measuring the breaks with the %s engine.' % engine)
    answer = run_breaks(project_root, engine,
                        scope_by_feature(features, selected),
                        tests_by_rule(features, selected, index))
    # An installed engine answers a reason only when it measured nothing it
    # set out to, a timeout being the one case, so the person sees why the
    # strength reads n/a rather than finding it in the log.
    if answer.get('available') and answer.get('reason'):
        print('purlin: %s' % answer['reason'])
    return answer


# ---------------------------------------------------------------------------
# CI
# ---------------------------------------------------------------------------

def _ci(project_root, args, features, selected, index, log, os_name):
    """The `--ci` arm: on a run branch, this runner's sections, committed.

    A runner writes only its own operating system's section of
    `.purlin/evidence/ci/<feature>.json` and commits it through the git
    host's API, merged on every attempt into what the branch's head holds,
    because its evidence exists nowhere else. No breaks run here and the AI
    audit is not called: `purlin:audit` on a person's machine does both. A
    tag run writes nothing: what it is for is the rerun on a clean machine
    and the check the gate step makes over what is already committed.
    """
    from host import commit_files, commits_here, no_commit_line

    if not commits_here(project_root):
        print('')
        print(no_commit_line(project_root))
        return 0

    _write_log(project_root, log)
    print('')
    paths = write_sections(project_root, args, features, selected, index,
                           os_name, 'ci')
    _prune(project_root, features)
    print(evidence_writer.written_line(paths, 'ci'))
    commit = head_commit(project_root)
    merge = evidence_writer.merge_for_host(
        os_name, {name: list((info or {}).get('rule_order') or ())
                  for name, info in features.items()})
    commit_files(project_root, paths, evidence_writer.COMMIT_SUBJECT
                 % (commit[:7] or 'an unknown commit'), merge)
    print(evidence_writer.COMMITTED)
    return 0


def _remote(project_root, args, cfg=None):
    """`--test --remote`: let the git host's runner do the run.

    The runner runs the same tests this machine would, writes its own
    operating system's section of each feature's `ci/` evidence, and commits
    it on the run branch; the run pulls that commit back.
    """
    try:
        from remote import run_remote
    except ImportError:
        print('purlin: --remote is not available in this checkout.',
              file=sys.stderr)
        return 1
    return run_remote(project_root, args, cfg)


if __name__ == '__main__':
    sys.exit(main())
