"""Tests for purlin_version.

Ensures the Purlin version string is defined in exactly one place (the VERSION
file) and all references to it read from that file or match its value.
"""

import json
import os
import re
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
VERSION_FILE = os.path.join(PROJECT_ROOT, 'VERSION')
PLUGIN_MANIFEST = os.path.join(PROJECT_ROOT, '.claude-plugin', 'plugin.json')
PROJECT_CONFIG = os.path.join(PROJECT_ROOT, '.purlin', 'config.json')
BUMP_SCRIPT = os.path.join(PROJECT_ROOT, 'dev', 'bump_version.sh')
SCAFFOLD = os.path.join(PROJECT_ROOT, 'scripts', 'init', 'scaffold.py')

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'run'))
from purlin_run import bash_command

# The bash a shell test runs under. `bash` on PATH is the Windows
# Subsystem for Linux launcher on a Windows runner, which never reads the
# script, so the run script finds Git Bash and this asks it the same
# question rather than asking it again.
BASH = bash_command()


def bash_path(path):
    """`path` with forward slashes, the spelling Git Bash reads on Windows.

    The backslash `os.path.join` builds there is an escape to a shell.
    """
    return str(path).replace(os.sep, '/')


def version_file_text():
    """The checkout's VERSION file, whitespace at either end set aside."""
    with open(VERSION_FILE, encoding='utf-8') as f:
        return f.read().strip()


# --- RULE-1: the VERSION file holds one version --------------------------

def version_text_is_semver(text):
    """True when `text`, whitespace at either end aside, is X.Y.Z alone."""
    return re.fullmatch(r'\d+\.\d+\.\d+', text.strip()) is not None


# purlin: purlin_version PROOF-1
def test_the_version_file_holds_one_version():
    assert os.path.isfile(VERSION_FILE), \
        f"VERSION file not found at {VERSION_FILE}"
    with open(VERSION_FILE, encoding='utf-8') as f:
        content = f.read()
    assert version_text_is_semver(content), \
        f"VERSION file contains {content!r}, expected a version like '1.2.3'"


# purlin: purlin_version PROOF-14
def test_a_letter_before_the_numbers_fails():
    assert not version_text_is_semver('v0.10.0')


# --- RULE-2: the package and its server read the VERSION file ------------

# What a copied package and its server report, printed as one JSON list.
REPORT_PROBE = ('import json, sys\n'
                'sys.path.insert(0, sys.argv[1])\n'
                'import purlin\n'
                'from purlin import server\n'
                'print(json.dumps([purlin.PURLIN_VERSION,'
                ' server.SERVER_INFO["version"]]))\n')


def copied_package(tmp_path, version):
    """A temporary project holding a copy of `scripts/mcp`, with a VERSION
    file reading `version`, or none when `version` is None."""
    shutil.copytree(os.path.join(PROJECT_ROOT, 'scripts', 'mcp'),
                    str(tmp_path / 'scripts' / 'mcp'),
                    ignore=shutil.ignore_patterns('__pycache__'))
    if version is not None:
        (tmp_path / 'VERSION').write_text(version + '\n', encoding='utf-8')
    return tmp_path / 'scripts' / 'mcp'


def reported_versions(tmp_path, mcp_dir):
    """[package version, server version], loaded in a fresh process."""
    answer = subprocess.run(
        [sys.executable, '-c', REPORT_PROBE, str(mcp_dir)],
        capture_output=True, text=True, cwd=str(tmp_path), timeout=60)
    assert answer.returncode == 0, answer.stderr
    return json.loads(answer.stdout.strip().splitlines()[-1])


# purlin: purlin_version PROOF-2
def test_a_copied_package_reports_the_version_file_beside_it(tmp_path):
    mcp_dir = copied_package(tmp_path, '9.8.7')
    reported = reported_versions(tmp_path, mcp_dir)
    assert reported == ['9.8.7', '9.8.7'], reported
    # What the server reports is what it answers when it is asked: the
    # version on its handshake, started there in a fresh process.
    hello = subprocess.run(
        [sys.executable, str(mcp_dir / 'purlin' / 'server.py')],
        input=json.dumps({'jsonrpc': '2.0', 'id': 1,
                          'method': 'initialize', 'params': {}}) + '\n',
        capture_output=True, text=True, cwd=str(tmp_path), timeout=60)
    assert hello.returncode == 0, hello.stderr
    answered = json.loads(hello.stdout.splitlines()[0])
    assert answered['result']['serverInfo']['version'] == '9.8.7', answered


# purlin: purlin_version PROOF-16
def test_the_copied_server_names_that_version_on_the_handshake(tmp_path):
    mcp_dir = copied_package(tmp_path, '9.8.7')
    hello = subprocess.run(
        [sys.executable, str(mcp_dir / 'purlin' / 'server.py')],
        input=json.dumps({'jsonrpc': '2.0', 'id': 1,
                          'method': 'initialize', 'params': {}}) + '\n',
        capture_output=True, text=True, cwd=str(tmp_path), timeout=60)
    assert hello.returncode == 0, hello.stderr
    server_info = json.loads(hello.stdout.splitlines()[0])['result'][
        'serverInfo']
    assert server_info == {'name': 'purlin', 'version': '9.8.7'}, server_info


# --- RULE-3, RULE-5, RULE-6: the JSON files that carry the version -------

def version_field_problem(path, file_version, name):
    """What is wrong with the `version` key of the JSON file at `path`,
    called `name`, against `file_version`, or None when it matches."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if 'version' not in data:
        return f"{name} has no 'version' field"
    if data['version'] != file_version:
        return (f"{name} version is '{data['version']}' "
                f"but VERSION file contains '{file_version}'")
    return None


def copy_without_version(live_path, tmp_path):
    """A copy of the JSON file at `live_path` with its `version` key gone."""
    with open(live_path, encoding='utf-8') as f:
        data = json.load(f)
    copy = tmp_path / 'copy.json'
    copy.write_text(json.dumps({k: v for k, v in data.items()
                                if k != 'version'}), encoding='utf-8')
    return str(copy)


def copy_at_version(live_path, tmp_path, version):
    """A copy of the JSON file at `live_path` with `version` set."""
    with open(live_path, encoding='utf-8') as f:
        data = json.load(f)
    copy = tmp_path / 'copy.json'
    copy.write_text(json.dumps(dict(data, version=version)), encoding='utf-8')
    return str(copy)


def assert_matches_version_file(path, name):
    assert os.path.isfile(path), f"{name} not found at {path}"
    problem = version_field_problem(path, version_file_text(), name)
    assert problem is None, problem


def assert_missing_key_fails(live_path, name, tmp_path):
    copy = copy_without_version(live_path, tmp_path)
    assert version_field_problem(copy, '0.10.0', name) == \
        f"{name} has no 'version' field"


def assert_stale_version_fails(live_path, name, tmp_path):
    copy = copy_at_version(live_path, tmp_path, '0.9.2')
    problem = version_field_problem(copy, '0.10.0', name)
    assert problem and '0.9.2' in problem and '0.10.0' in problem, problem


def _git(root, *args):
    subprocess.run(['git', *args], cwd=str(root), check=True,
                   capture_output=True, text=True)


# purlin: purlin_version PROOF-21
def test_a_project_init_sets_up_is_stamped_with_the_version_file(tmp_path):
    root = tmp_path / 'fresh'
    root.mkdir()
    _git(root, '-c', 'init.defaultBranch=main', 'init', '-q', '.')
    # `--yes` commits the files setup wrote, so the repository carries an
    # identity of its own and signs nothing, whatever this machine's git says.
    _git(root, 'config', 'user.name', 'Purlin Test')
    _git(root, 'config', 'user.email', 'test@example.com')
    _git(root, 'config', 'commit.gpgsign', 'false')
    env = dict(os.environ)
    env.pop('CLAUDE_PLUGIN_ROOT', None)
    env.pop('PURLIN_PROJECT_ROOT', None)
    done = subprocess.run(
        [sys.executable, SCAFFOLD, '--project-root', str(root), '--yes'],
        capture_output=True, encoding='utf-8', env=env,
        stdin=subprocess.DEVNULL, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr
    config_path = root / '.purlin' / 'config.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    assert config.get('version') == version_file_text(), config


# purlin: purlin_version PROOF-5
def test_the_plugin_manifest_carries_the_version_file(tmp_path):
    assert_matches_version_file(PLUGIN_MANIFEST, '.claude-plugin/plugin.json')
    # The check fails a copy with no `version` key and a copy left behind.
    assert_missing_key_fails(PLUGIN_MANIFEST, '.claude-plugin/plugin.json',
                             tmp_path)
    assert_stale_version_fails(PLUGIN_MANIFEST, '.claude-plugin/plugin.json',
                               tmp_path)


# purlin: purlin_version PROOF-6
def test_this_repositorys_settings_carry_the_version_file(tmp_path):
    assert_matches_version_file(PROJECT_CONFIG, '.purlin/config.json')
    # The check fails a copy with no `version` key and a copy left behind.
    assert_missing_key_fails(PROJECT_CONFIG, '.purlin/config.json', tmp_path)
    assert_stale_version_fails(PROJECT_CONFIG, '.purlin/config.json',
                               tmp_path)


# --- RULE-12 and RULE-14: the bump script and its check ------------------

DERIVED = [
    os.path.join('.claude-plugin', 'plugin.json'),
    os.path.join('.purlin', 'config.json'),
]


def fake_project(tmp_path, version):
    """A tree holding a copy of the bump script, VERSION and the derived
    files at `version`.

    The script resolves the root as its own parent, so it runs from a
    dev/ directory inside the tree under test. Returns (root, script)."""
    root = tmp_path / 'proj'
    root.mkdir()
    (root / 'VERSION').write_text(version + '\n', encoding='utf-8')
    for rel in DERIVED:
        write_version(root, rel, version)
    (root / 'dev').mkdir()
    script = root / 'dev' / 'bump_version.sh'
    shutil.copy2(BUMP_SCRIPT, str(script))
    return root, script


def write_version(root, rel, version):
    """Set the `version` key of the JSON file `rel`, or drop it for None."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {} if version is None else {'version': version}
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def read_version(root, rel):
    return json.loads((root / rel).read_text(encoding='utf-8'))['version']


def read_version_file(root):
    return (root / 'VERSION').read_text(encoding='utf-8').strip()


def run_script(script, arg):
    return subprocess.run([BASH, bash_path(script), arg],
                          capture_output=True, text=True, timeout=60)


def check_line(output, rel):
    """The words after the location on the one --check line for `rel`."""
    lines = [ln.split() for ln in output.splitlines()
             if ln.split()[:1] == [rel]]
    assert len(lines) == 1, f"expected one line for {rel}:\n{output}"
    return lines[0][1:]


MANIFEST_REL = '.claude-plugin/plugin.json'
SETTINGS_REL = '.purlin/config.json'


# purlin: purlin_version PROOF-7
def test_the_bump_writes_the_version_file_and_both_json_files(tmp_path):
    root, script = fake_project(tmp_path, '1.2.3')
    assert read_version_file(root) == '1.2.3'
    assert [read_version(root, rel) for rel in DERIVED] == ['1.2.3', '1.2.3']
    bump = run_script(script, '9.8.7')
    assert bump.returncode == 0, \
        f"bump exited {bump.returncode}\n{bump.stdout}\n{bump.stderr}"
    assert read_version_file(root) == '9.8.7'
    assert [read_version(root, rel) for rel in DERIVED] == ['9.8.7', '9.8.7']


# purlin: purlin_version PROOF-29
def test_the_check_names_the_location_that_drifted(tmp_path):
    root, script = fake_project(tmp_path, '9.8.7')
    write_version(root, SETTINGS_REL, '1.2.3')
    bad = run_script(script, '--check')
    assert bad.returncode == 1, \
        f"--check exited {bad.returncode} on a drifted tree, expected 1"
    assert check_line(bad.stdout, SETTINGS_REL) == \
        ['DRIFT', '1.2.3', '(expected', '9.8.7)'], bad.stdout
    assert check_line(bad.stdout, MANIFEST_REL) == ['ok', '9.8.7'], \
        bad.stdout


EXAMPLE_REL = 'docs/running-and-evidence.md'
EXAMPLE = ('      - name: Get Purlin\n'
           '        run: git clone --depth 1 --branch signed/%s '
           'https://github.com/rlabarca/purlin "$RUNNER_TEMP/purlin"\n')


# purlin: purlin_version PROOF-39
def test_the_bump_moves_the_docs_examples_tag_and_the_check_names_its_drift(
        tmp_path):
    root, script = fake_project(tmp_path, '1.2.3')
    page = os.path.join(root, EXAMPLE_REL)
    os.makedirs(os.path.dirname(page))
    with open(page, 'w', encoding='utf-8') as handle:
        handle.write('# Running\n\n' + EXAMPLE % '1.2.3' + '\nMore.\n')
    bump = run_script(script, '9.8.7')
    assert bump.returncode == 0, bump.stdout + bump.stderr
    with open(page, encoding='utf-8') as handle:
        assert handle.read() == '# Running\n\n' + EXAMPLE % '9.8.7' + '\nMore.\n'
    with open(page, 'w', encoding='utf-8') as handle:
        handle.write(EXAMPLE % '1.2.3')
    bad = run_script(script, '--check')
    assert bad.returncode == 1, bad.stdout
    assert check_line(bad.stdout, EXAMPLE_REL) == \
        ['DRIFT', '1.2.3', '(expected', '9.8.7)'], bad.stdout


# --- RULE-16: the marketplace manifest ------------------------------------

MARKETPLACE = os.path.join(PROJECT_ROOT, '.claude-plugin', 'marketplace.json')


def marketplace_problems(manifest):
    """What keeps a marketplace manifest from reading `purlin`, with one
    plugin, `purlin`, whose source is the repository root."""
    problems = []
    if manifest.get('name') != 'purlin':
        problems.append('the marketplace is named %r' % manifest.get('name'))
    plugins = manifest.get('plugins') or []
    if [plugin.get('name') for plugin in plugins] != ['purlin']:
        problems.append('the plugins are %r'
                        % [plugin.get('name') for plugin in plugins])
    elif plugins[0].get('source') != './':
        problems.append('the source is %r' % plugins[0].get('source'))
    return problems


# purlin: purlin_version PROOF-38
def test_the_marketplace_lists_one_plugin_from_the_repository_root():
    with open(MARKETPLACE, encoding='utf-8') as f:
        manifest = json.load(f)
    assert marketplace_problems(manifest) == []
    # A second plugin, and a source other than the root, are found.
    assert marketplace_problems(
        {'name': 'purlin', 'plugins': [{'name': 'purlin', 'source': './'},
                                       {'name': 'other', 'source': './'}]}
    ) == ["the plugins are ['purlin', 'other']"]
    assert marketplace_problems(
        {'name': 'purlin', 'plugins': [{'name': 'purlin',
                                        'source': './plugin'}]}
    ) == ["the source is './plugin'"]
