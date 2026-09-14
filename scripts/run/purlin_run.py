"""Run a project's tagged tests, and on request write the record.

    purlin_run.py (--feature NAME ... | --all)
                  (--quick | --record [--commit] [--ci] [--tag NAME] | --remote)
                  [--tier unit|all] [--project-root DIR]

`--quick` is what `purlin:test` runs: the plugins run the tagged tests into
`.purlin/runtime/proofs/` and the state table is printed. Seconds, tests only.

`--record` is what `purlin:verify` runs: the tests, then the breaks, then a
record. `--commit` commits the record under the developer's identity, which is
the default at gate `tested`. `--ci` commits it through the git host API,
auto-approves what may be auto-approved, writes the briefs, posts the pull
request comment and publishes the dashboard.

`--remote` is what `purlin:verify --remote` runs: push the current branch,
wait for the workflow, pull the records CI committed, print the table.

A proof the spec tags `@env` for another operating system is not run here: it
is listed as `needs <os>` and the rule waits for a record from that runner.

Exit codes: 0 everything asked for happened, 1 a test failed or evidence is
missing, 2 the command line was wrong.

The flow is one pass. Resolve the configuration and the frameworks, scan the
specs, run one arm per framework, then check two things the arms cannot check
themselves:

  loud failure A  an arm ran and its plugin appended nothing
  loud failure B  a marker sits in a test source and this run produced no
                  proof entry for it

Both are silent by default in every test framework there is, and both leave a
reader looking at a proof file from an earlier run believing it describes this
one. Under `--record` the run then measures the breaks per spec scope, hashes
the attachments, builds the `purlin-record/1` dict and hands it to the record
writer.
"""

import hashlib
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
_REVIEW_DIR = os.path.join(os.path.dirname(_HERE), 'review')
for _path in (_MCP_DIR, _REVIEW_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from config_engine import resolve_config                      # noqa: E402
from purlin import (frameworks as frameworks_module,          # noqa: E402
                    gate as gate_module, payload as payload_module,
                    proofs as proofs_module, records as records_module,
                    specs as specs_module, status as status_module)

ARROW = '→'
RECORD_SCHEMA = 'purlin-record/1'
# The `schema_version` the record format carries; see references/formats/.
RECORD_SCHEMA_VERSION = 1
ATTACHMENT_DIR = os.path.join('.purlin', 'runtime', 'attachments')
LOG_PATH = os.path.join('.purlin', 'runtime', 'run.log')

USAGE = (
    'Usage: purlin_run.py (--feature NAME ... | --all) '
    '(--quick | --record [--commit] [--ci] [--tag NAME] | --remote) '
    '[--tier unit|all] [--project-root DIR]')

TIERS = ('unit', 'all')

# The three operating systems `@env` names, and how `sys.platform` spells them.
_OS_NAMES = (('win', 'windows'), ('darwin', 'macos'), ('linux', 'linux'))


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class Args(object):
    """One parsed invocation, or the reason it could not be parsed."""

    def __init__(self):
        self.features = []
        self.all = False
        self.action = None          # 'quick', 'record' or 'remote'
        self.commit = False
        self.ci = False
        self.tag = None
        self.tier = 'all'
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
        elif token in ('--quick', '--record', '--remote'):
            actions.append(token[2:])
        elif token == '--commit':
            args.commit = True
        elif token == '--ci':
            args.ci = True
        elif token == '--tag':
            index += 1
            if index >= len(argv):
                args.error = '--tag needs a name'
                return args
            args.tag = argv[index]
        elif token == '--tier':
            index += 1
            if index >= len(argv) or argv[index] not in TIERS:
                args.error = '--tier is unit or all'
                return args
            args.tier = argv[index]
        elif token == '--project-root':
            index += 1
            if index >= len(argv):
                args.error = '--project-root needs a directory'
                return args
            args.project_root = argv[index]
        else:
            args.error = 'unknown argument %s' % token
            return args
        index += 1

    if len(actions) != 1:
        args.error = 'name exactly one of --quick, --record and --remote'
        return args
    args.action = actions[0]
    if args.all and args.features:
        args.error = 'name features or --all, not both'
        return args
    if not args.all and not args.features:
        args.error = 'name at least one --feature, or --all'
        return args
    if args.action != 'record' and (args.commit or args.ci or args.tag):
        args.error = '--commit, --ci and --tag belong to --record'
        return args
    return args


# ---------------------------------------------------------------------------
# The operating system, and the proofs another one owns
# ---------------------------------------------------------------------------

def host_os():
    """`windows`, `macos` or `linux` for the machine this run is on."""
    for prefix, name in _OS_NAMES:
        if sys.platform.startswith(prefix):
            return name
    return sys.platform


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

# One pattern per framework, reading the same marker its plugin reads, so the
# run can say that a marked test produced no entry. A pattern that drifted
# from its plugin would report a missing proof for a test that never had one,
# which is why each is the plugin's own marker written once.
_MARKER_PATTERNS = {
    'pytest': (('.py',), re.compile(
        r'@pytest\.mark\.proof\(\s*["\'](\w+)["\']\s*,\s*["\'](PROOF-\d+)["\']')),
    'jest': (('.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx'), re.compile(
        r'\[proof:(\w+):(PROOF-\d+):')),
    'vitest': (('.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx'), re.compile(
        r'\[proof:(\w+):(PROOF-\d+):')),
    'xunit': (('.cs',), re.compile(
        r'\[Trait\(\s*"PurlinProof"\s*,\s*"(\w+):(PROOF-\d+):')),
    'shell': (('.sh',), re.compile(
        r'purlin_proof\s+"(\w+)"\s+"(PROOF-\d+)"')),
    'sql': (('.sql',), re.compile(
        r'^--\s*@purlin\s+(\w+)\s+(PROOF-\d+)\b', re.MULTILINE)),
}

_SKIP_DIRS = ('node_modules', 'bin', 'obj')


def _source_files(project_root, extensions):
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith('.') and d not in _SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith(extensions):
                yield os.path.join(dirpath, name)


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


def _run(command, project_root, log):
    """Run one command in the project root, echoing it and its output."""
    log.append('$ %s' % ' '.join(command))
    try:
        result = subprocess.run([*command], cwd=project_root,
                                capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as error:
        log.append(str(error))
        return 127
    for stream in (result.stdout, result.stderr):
        if stream:
            log.append(stream.rstrip('\n'))
    return result.returncode


def run_framework(project_root, framework, tier, config, log):
    """Run one framework's tagged tests. The exit code its runner gave."""
    if framework == 'pytest':
        command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider']
        if tier == 'unit':
            # The tier a proof marker names is also a pytest marker on the
            # test, so this expression actually deselects something.
            command.extend(['-m', 'not integration and not e2e'])
        code = _run(command, project_root, log)
        # pytest exits 5 when it collected nothing. No tests is not a failure
        # here; the two loud failures below are what report that.
        return 0 if code == 5 else code
    if framework == 'jest':
        command = ['npx', 'jest', '--passWithNoTests']
        if tier == 'unit':
            command.append('--testPathPattern=unit')
        return _run(command, project_root, log)
    if framework == 'vitest':
        return _run(['npx', 'vitest', 'run', '--passWithNoTests'],
                    project_root, log)
    if framework == 'xunit':
        return _run(['dotnet', 'test', '--logger', 'purlin'], project_root, log)
    if framework == 'shell':
        code = 0
        for name in sorted(os.listdir(project_root)):
            if not name.endswith('.test.sh'):
                continue
            code = _run(['bash', name], project_root, log)
            if code != 0:
                break
        return code
    if framework == 'sql':
        engine = config.get('sql_engine') or 'sqlite3'
        harness = plugin_path(project_root, 'sql_purlin.sh')
        tests_dir = os.path.join(project_root, 'tests')
        code = 0
        environment = dict(os.environ, PURLIN_SQL_ENGINE=engine)
        for name in sorted(os.listdir(tests_dir)
                           if os.path.isdir(tests_dir) else []):
            if not name.endswith('.sql'):
                continue
            log.append('$ bash %s tests/%s' % (harness, name))
            try:
                result = subprocess.run(
                    ['bash', harness, os.path.join('tests', name)],
                    cwd=project_root, capture_output=True, text=True,
                    env=environment)
            except (OSError, subprocess.SubprocessError) as error:
                log.append(str(error))
                return 127
            if result.stderr:
                log.append(result.stderr.rstrip('\n'))
            if result.returncode != 0:
                code = result.returncode
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
# The record
# ---------------------------------------------------------------------------

def runner_identity(project_root, args):
    """`(slug, environment)` naming who this run was.

    The slug is the record's `runner`, matching the file name, and the rest
    goes under `environment`: what kind of run it was, which job it was, and
    which machine. None of it claims who wrote the record, because the label on
    a record comes from the commit and never from the file.
    """
    kind = 'ci' if args.ci else ('developer' if args.commit else 'local')
    if args.ci:
        slug = 'ci'
    else:
        slug = records_module.runner_slug(_git_email(project_root))
    job = (os.environ.get('GITHUB_JOB')
           or os.environ.get('BUILD_DEFINITIONNAME') or None)
    host = os.environ.get('RUNNER_NAME') or _hostname()
    return slug, {'kind': kind, 'job': job, 'host': host}


def _hostname():
    try:
        return os.uname().nodename
    except AttributeError:
        return os.environ.get('COMPUTERNAME', '')


def _git_email(project_root):
    try:
        result = subprocess.run(['git', 'config', 'user.email'],
                                capture_output=True, text=True,
                                cwd=project_root, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ''
    return result.stdout.strip()


def environment_id():
    """A short name for the machine's shape, for the record to carry."""
    try:
        uname = os.uname()
        return '%s-%s' % (uname.sysname.lower(), uname.machine)
    except AttributeError:
        return host_os()


def head_commit(project_root):
    return records_module.head_sha(project_root) or ''


def working_tree_dirty(project_root):
    try:
        result = subprocess.run(['git', 'status', '--porcelain'],
                                capture_output=True, text=True,
                                cwd=project_root, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return bool(result.stdout.strip())


def attachments_for(project_root, feature, proof_ids):
    """`[{proof, sha256, artifact}]` for the captures a test wrote."""
    directory = os.path.join(project_root, ATTACHMENT_DIR, feature)
    out = []
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return out
    for name in names:
        proof_id = os.path.splitext(name)[0]
        if proof_id not in proof_ids:
            continue
        path = os.path.join(directory, name)
        digest = hashlib.sha256()
        try:
            with open(path, 'rb') as handle:
                for block in iter(lambda: handle.read(65536), b''):
                    digest.update(block)
        except (IOError, OSError):
            continue
        out.append({
            'proof': proof_id,
            'sha256': digest.hexdigest(),
            'artifact': '%s/%s/%s' % (ATTACHMENT_DIR.replace(os.sep, '/'),
                                      feature, name),
        })
    return out


def build_record(project_root, args, features, selected, index, plugins,
                 breaks, log_digest, gate='tested'):
    """The record dict `references/formats/record_format.md` describes.

    Every field that file marks REQUIRED is filled here; `os`, `timestamp` and
    `runner` are finished by the record writer, which owns the file name they
    have to agree with. The run's own detail (`features`, `plugins`,
    `missing`, `log`, `dirty`) rides along as optional fields a reader that
    does not know them ignores.
    """
    runner, environment = runner_identity(project_root, args)
    record = {
        'schema': RECORD_SCHEMA,
        'schema_version': RECORD_SCHEMA_VERSION,
        'gate': gate,
        # One record per feature: the record writer files it under
        # `.purlin/records/<feature>/` and prunes that folder, and the
        # retention rule counts per feature per operating system.
        'feature': selected[0] if len(selected) == 1 else '',
        'commit': head_commit(project_root),
        'dirty': working_tree_dirty(project_root),
        # The slug, the same string the file name carries. What kind of run it
        # was, which job and which machine go under `environment`, so nothing
        # here has to be rewritten by the writer to agree with the name.
        'runner': runner,
        'timestamp': _now_iso(),
        'environment': {
            'os': host_os(),
            'id': environment_id(),
            'kind': environment['kind'],
            'job': environment['job'],
            'host': environment['host'],
            'engines': [breaks.get('engine')] if breaks.get('engine') else [],
        },
        'plugins': list(plugins),
        'missing': [],
        'features': {},
        # The git tree hash of the record's own feature scope, one string: the
        # record is per feature, so there is nothing else to key it by.
        'scope_tree': '',
        # The percentage of the deliberate breaks the tests caught over this
        # feature's scope, or None when no engine measured it.
        'test_strength': None,
        # One entry per proof this run observed, which is what the reader
        # compares a rule's proofs against.
        'proofs': [],
        'log': log_digest,
    }
    break_features = (breaks.get('features') or {})
    for name in selected:
        info = features.get(name) or {}
        feature_breaks = break_features.get(name) or {}
        rules = {}
        own = name == record['feature']
        for rule_id in info.get('rule_order', []):
            proof_ids = info.get('proofs_by_rule', {}).get(rule_id, [])
            tests = []
            statuses = []
            for proof_id in proof_ids:
                proof = (info.get('proofs') or {}).get(proof_id) or {}
                for entry in index.get((name, proof_id), []):
                    tests.append({
                        'file': entry.get('test_file', ''),
                        'name': entry.get('test_name', ''),
                        'status': entry.get('status', ''),
                        'plugin': entry.get('plugin', ''),
                    })
                    statuses.append(entry.get('status'))
                    if own:
                        record['proofs'].append({
                            'id': proof_id,
                            'rule': rule_id,
                            'status': entry.get('status', ''),
                            'tier': proof.get('tier', ''),
                            'env': proof.get('env'),
                            'test_file': entry.get('test_file', ''),
                            'test_name': entry.get('test_name', ''),
                        })
            if not statuses:
                result = 'missing'
                record['missing'].append('%s %s' % (name, rule_id))
            elif 'fail' in statuses:
                result = 'fail'
            else:
                result = 'pass'
            rules[rule_id] = {
                'proofs': list(proof_ids),
                'tests': tests,
                'result': result,
                'test_strength': (feature_breaks.get('rules') or {}).get(
                    rule_id) or _no_strength(breaks),
                'attachments': attachments_for(project_root, name,
                                               set(proof_ids)),
            }
        record['features'][name] = {
            'spec': info.get('spec_path', ''),
            'rules': rules,
            'scope_score': feature_breaks.get('scope_score'),
        }
        if own:
            record['scope_tree'] = specs_module.scope_tree(
                project_root, info.get('scope', []))
            record['test_strength'] = (
                feature_breaks.get('scope_score') or {}).get('score')
    return record


def _no_strength(breaks):
    return {'engine': breaks.get('engine') or 'none', 'score': None,
            'killed': 0, 'survived': 0, 'attribution': 'unavailable'}


def _now_iso():
    import datetime

    return datetime.datetime.now(
        datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


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
# The run
# ---------------------------------------------------------------------------

def main(argv=None):
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

    if args.action == 'remote':
        return _remote(project_root, args)

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
    clear_proofs(project_root)
    failures = []
    ran = []
    for framework in resolved:
        markers = scan_markers(project_root, framework)
        markers = {pair for pair in markers if pair[0] in selected}
        before = set(proof_index(project_root))
        code = run_framework(project_root, framework, args.tier, config, log)
        after = set(proof_index(project_root))
        ran.append(framework)
        if code != 0:
            failures.append('the %s runner exited %d' % (framework, code))
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

    print('Ran %s on %d feature(s) at tier %s.'
          % (', '.join(ran) or 'nothing', len(selected), args.tier))
    if foreign:
        print('')
        print('Proofs another operating system owns:')
        for feature, proof_id, env in foreign:
            print('  %s %s: needs %s' % (feature, proof_id, env))

    exit_code = 0
    if failures:
        exit_code = 1
        print('')
        for failure in failures:
            print('Evidence is missing: %s.' % failure)

    if args.action == 'record':
        record_code = _record(project_root, args, features, selected, index,
                              ran, log, cfg.gate)
        exit_code = exit_code or record_code

    print('')
    print(status_module.sync_status(project_root))
    return exit_code


def _write_log(project_root, log):
    """The run's console log, written once and hashed into the record."""
    path = os.path.join(project_root, LOG_PATH)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = '\n'.join(log) + '\n'
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
    except (IOError, OSError):
        return {'sha256': '', 'path': LOG_PATH.replace(os.sep, '/')}
    return {'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'path': LOG_PATH.replace(os.sep, '/')}


def _record(project_root, args, features, selected, index, plugins, log,
            gate='tested'):
    """The `--record` arm: breaks, the records, the commit, the CI extras.

    One record per feature, because that is what the record writer files and
    prunes: `.purlin/records/<feature>/` keeps the newest three per operating
    system, which it cannot do for a file covering several features at once.
    """
    breaks = _run_breaks(project_root, args, features, selected, index)
    log_digest = _write_log(project_root, log)

    from records import write_record, commit_records, tag_validated

    print('')
    paths = []
    head = ''
    for name in selected:
        record = build_record(project_root, args, features, [name], index,
                              plugins, breaks, log_digest, gate)
        head = record['commit']
        path = write_record(project_root, record, record['runner'],
                            os_name=record['environment']['os'])
        paths.append(path)
        print('Record written: %s' % path)

    if args.commit or args.ci:
        identity = 'ci' if args.ci else 'developer'
        commit_records(project_root, paths, identity,
                       'purlin: record for %s' % head[:7])
        print('Record committed as %s.' % identity)
    if args.tag:
        tag_validated(project_root, args.tag, paths)
        print('Validation tag written: validated/%s' % args.tag)
    if args.ci:
        _ci_extras(project_root)
    return 0


def _run_breaks(project_root, args, features, selected, index):
    """The breaks, through the engine the project resolved to."""
    try:
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
    return run_breaks(project_root, engine,
                      scope_by_feature(features, selected),
                      tests_by_rule(features, selected, index), args.tier)


def _ci_extras(project_root):
    """Auto-approvals, briefs, the pull request comment, the dashboard."""
    try:
        from approve import auto_approve
        from brief import write_briefs
    except ImportError:
        print('purlin: the review helpers are not available; nothing was '
              'auto-approved and no brief was written.')
    else:
        payload = payload_module.build_payload(project_root,
                                               generated_by='verify')
        approved = auto_approve(project_root, payload)
        briefs = write_briefs(project_root, payload)
        print('Auto-approved %d low-risk rule%s; %d brief%s written.'
              % (len(approved), '' if len(approved) == 1 else 's',
                 len(briefs), '' if len(briefs) == 1 else 's'))
    try:
        from ci import post_pr_comment, publish_dashboard
    except ImportError:
        print('purlin: the CI helpers are not available; no comment was '
              'posted and no dashboard was published.')
        return
    post_pr_comment(project_root, status_module.sync_status(project_root))
    publish_dashboard(project_root,
                      os.path.join(project_root, '.purlin', 'runtime', 'report'))


def _remote(project_root, args):
    try:
        from remote import run_remote
    except ImportError:
        print('purlin: --remote is not available in this checkout.',
              file=sys.stderr)
        return 1
    return run_remote(project_root, args)


if __name__ == '__main__':
    sys.exit(main())
