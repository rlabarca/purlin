"""Run a project's tagged tests, write the evidence, and audit it on request.

    purlin_run.py (--feature NAME ... | --all)
                  (--test [--remote] [--commit] | --audit [--commit] | --ci)
                  [--arm-timeout SECONDS]
                  [--project-root DIR]

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
the breaks where the gate asks for them and the AI audit, printed per rule as
the strength beside the minimum and the audit's observations. Both land in the
same evidence file, under `audit`, and `--commit` commits them the same way.
It ends with `gate strong: <n> of <rules>` or `gate not met: <n> of <rules>`
and exits 1 when the gate is not met.

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
    'Usage: purlin_run.py (--feature NAME ... | --all) '
    '(--test [--remote] [--commit] | --audit [--commit] | --ci) '
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
    if not args.all and not args.features:
        args.error = 'name at least one --feature, or --all'
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
    extensions, pattern = _MARKER_PATTERNS.get(framework, ((), None))
    found = set()
    if pattern is None:
        return found
    for path in _source_files(project_root, extensions):
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                text = handle.read()
        except (IOError, OSError, UnicodeDecodeError):
            continue
        for match in pattern.finditer(text):
            found.add((match.group(1), match.group(2)))
    return found


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
                  timeout=ARM_TIMEOUT_DEFAULT):
    """Run one framework's tagged tests. The exit code its runner gave.

    `TIMED_OUT` comes back when the arm ran past `timeout` seconds and was
    killed. Every command runs without stdin and without a git password
    prompt, because both are ways for a run on a hosted runner to stop for an
    answer that never arrives.
    """
    if framework == 'pytest':
        # `mutants/` is mutmut's copy of the project, tests included. A test
        # collected twice under one module name stops pytest before a single
        # test runs, so the copy is never collected.
        command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                   '--ignore=mutants']
        code = _run(command, project_root, log, timeout)
        # pytest exits 5 when it collected nothing. No tests is not a failure
        # here; the two loud failures below are what report that.
        return 0 if code == 5 else code
    if framework == 'jest':
        return _run(['npx', 'jest', '--passWithNoTests'], project_root, log,
                    timeout)
    if framework == 'vitest':
        return _run(['npx', 'vitest', 'run', '--passWithNoTests'],
                    project_root, log, timeout)
    if framework == 'xunit':
        return _run(['dotnet', 'test', '--logger', 'purlin'], project_root,
                    log, timeout)
    if framework == 'shell':
        # Every `*.test.sh` in the project, the root and each subdirectory
        # alike, run from the root by its relative path in sorted order.
        code = 0
        for path in shell_tests(project_root):
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
    the passed cell; `purlin:audit` counts the strong cell where one exists,
    and the passed cell under the gate `passed`, where none does.
    """
    payload = payload_module.build_payload(project_root, generated_by='run')
    met = rules = 0
    for feature in payload.get('features') or ():
        for rule in feature.get('rules') or ():
            if rule.get('feature') != feature.get('name'):
                continue
            rules += 1
            cell = (rule.get('cells') or {}).get(level)
            if states_module.cell_is_met(level, cell):
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
    if args.all:
        selected = sorted(features)
    else:
        selected = [name for name in args.features if name in features]
        unknown = [name for name in args.features if name not in features]
        for name in unknown:
            print('purlin: no spec named %s under specs/.' % name,
                  file=sys.stderr)
        if unknown:
            return 2
    if not selected:
        print(status_module.NO_SPECS)
        return 1

    resolved, unknown_frameworks = frameworks_module.resolve_frameworks(
        project_root, cfg.test_framework)
    for name in unknown_frameworks:
        print('purlin: "%s" is not a framework this release ships a plugin '
              'for; its tests were not run.' % name)

    os_name = host_os()
    foreign = foreign_env_proofs(features, selected, os_name)
    foreign_ids = {(feature, proof_id) for feature, proof_id, _env in foreign}

    log = []
    arm_logs = {}
    clear_proofs(project_root)
    failures = []
    ran = []
    for framework in resolved:
        markers = scan_markers(project_root, framework)
        markers = {pair for pair in markers if pair[0] in selected}
        before = set(proof_index(project_root))
        # One line per arm before it starts, so a job log says where a run
        # is while it is still running.
        print('Running the %s arm.' % framework)
        mark = len(log)
        code = run_framework(project_root, framework, config,
                             log, args.arm_timeout)
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
    level = 'passed'
    if args.action == 'audit':
        _audit(project_root, args, features, selected, log, cfg)
        level = 'passed' if cfg.gate == 'passed' else 'strong'
    evidence_writer.write_table(project_root)
    print(evidence_writer.written_line(paths))
    if args.commit:
        print(evidence_writer.commit_local(project_root,
                                           head_commit(project_root), removed))

    print('')
    print(status_module.sync_status(project_root))
    line, gate_code = project_gate_line(project_root, level)
    print('')
    print(line)
    return exit_code or gate_code


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

def _audit(project_root, args, features, selected, log, cfg):
    """The `--audit` arm: how good the tests are, written into the evidence.

    The breaks run where the gate asks for them and their score goes under
    each feature's `audit.mutation`. Each rule the AI audit reads gets an
    entry under `audit.rules`, keyed by the rule, proof and test hashes it
    read. Both land in `.purlin/evidence/local/<feature>.json`, beside the
    section the tests just wrote; nothing here commits.
    """
    breaks = (_run_breaks(project_root, args, features, selected)
              if cfg.breaks else _no_breaks(cfg.gate))
    _write_log(project_root, log)
    commit = head_commit(project_root)
    break_features = breaks.get('features') or {}
    for name in selected:
        score = ((break_features.get(name) or {}).get('scope_score')
                 or {}).get('score')
        mutation = {'engine': breaks.get('engine') or 'none', 'score': score,
                    'at': evidence_writer.now_iso(), 'commit': commit}
        evidence_writer.write_audit(project_root, 'local', name,
                                    features.get(name) or {}, {}, mutation,
                                    cfg.breaks)
    print('')
    _audit_report(project_root, features, selected, break_features, commit)


def _audit_report(project_root, features, selected, break_features, commit):
    """One block per feature: the strength, then each rule's observations.

    Each rule whose bar asks for the AI audit is read, and what the audit
    found goes into the feature's evidence as that rule's entry.
    """
    try:
        from brief import asks_for_a_review, build_brief, rule_entry
    except ImportError:
        print('purlin: the AI audit is not available in this checkout; it '
              'did not run.')
        return
    payload = payload_module.build_payload(project_root,
                                           generated_by='audit')
    minimum = (payload.get('gate') or {}).get('min_strength') or 0
    for name in selected:
        score = ((break_features.get(name) or {}).get('scope_score')
                 or {}).get('score')
        print('%s: test strength %s, minimum %s'
              % (name, 'n/a' if score is None else '%d percent' % score,
                 minimum or 'n/a'))
        entries = {}
        for rule_id in sorted(_own_rules(payload, name), key=_rule_number):
            entry = rule_entry(payload, name, rule_id)
            if entry is None:
                continue
            observations = []
            settled = None
            if asks_for_a_review(entry):
                built = build_brief(project_root, payload, name, rule_id)
                if built is not None:
                    observations = built.get('observations') or []
                    settled = built.get('settled')
                    entries[rule_id] = evidence_writer.audit_entry(
                        entry, built, commit)
            print('  %s %s' % (name, rule_id))
            for observation in observations:
                print('    observation: %s' % observation)
            if settled is not None:
                print('    settled: %s' % ('yes' if settled else 'no'))
            if not observations and settled is None:
                print('    nothing to report')
        evidence_writer.write_audit(project_root, 'local', name,
                                    features.get(name) or {}, entries, None,
                                    False)
        print('')


def _own_rules(payload, feature):
    """The rule ids one feature's own spec writes, unsorted."""
    for entry in payload.get('features') or ():
        if entry.get('name') != feature:
            continue
        return [rule['id'] for rule in entry.get('rules') or ()
                if rule.get('feature') == feature]
    return []


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def _no_breaks(gate):
    """What a gate that asks for no breaks hands the audit instead.

    Under `passed` nothing measures test strength, so there is no number to
    print and the run says so on its own line, because a blank where a
    percentage usually sits reads as a missing engine rather than a setting.
    """
    print('Strength n/a: the gate is %s.' % gate)
    return {'engine': None, 'available': False, 'features': {}}


def _run_breaks(project_root, args, features, selected):
    """The breaks, through the engine the project resolved to."""
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
