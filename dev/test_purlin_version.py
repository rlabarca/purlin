"""Tests for purlin_version.

Ensures the Purlin version string is defined in exactly one place (the VERSION
file) and all references to it read from that file or match its value.
"""

import ast
import glob
import json
import os
import re
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
VERSION_FILE = os.path.join(PROJECT_ROOT, 'VERSION')
PLUGIN_MANIFEST = os.path.join(PROJECT_ROOT, '.claude-plugin', 'plugin.json')
PACKAGE_DIR = os.path.join(PROJECT_ROOT, 'scripts', 'mcp', 'purlin')
PROJECT_CONFIG = os.path.join(PROJECT_ROOT, '.purlin', 'config.json')
BUMP_SCRIPT = os.path.join(PROJECT_ROOT, 'dev', 'bump_version.sh')
SCAFFOLD = os.path.join(PROJECT_ROOT, 'scripts', 'init', 'scaffold.py')

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'run'))
import purlin as purlin_package
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


# purlin: purlin_version PROOF-11
def test_a_version_with_whitespace_at_either_end_passes():
    assert version_text_is_semver('  0.10.0\n')


# purlin: purlin_version PROOF-12
def test_an_empty_version_file_fails():
    assert not version_text_is_semver('')


# purlin: purlin_version PROOF-13
def test_two_numbers_are_not_a_version():
    assert not version_text_is_semver('0.10')


# purlin: purlin_version PROOF-14
def test_a_letter_before_the_numbers_fails():
    assert not version_text_is_semver('v0.10.0')


# purlin: purlin_version PROOF-15
def test_two_versions_on_two_lines_fail():
    assert not version_text_is_semver('0.10.0\n0.11.0\n')


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


# purlin: purlin_version PROOF-17
def test_with_no_version_file_the_package_and_server_report_zero(tmp_path):
    mcp_dir = copied_package(tmp_path, None)
    reported = reported_versions(tmp_path, mcp_dir)
    assert reported == ['0.0.0', '0.0.0'], reported


# purlin: purlin_version PROOF-18
def test_this_checkout_reports_its_own_version_file():
    assert purlin_package.PURLIN_VERSION == version_file_text(), \
        (f"the package reports '{purlin_package.PURLIN_VERSION}' but the "
         f"VERSION file reads '{version_file_text()}'")


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
    env = dict(os.environ)
    env.pop('CLAUDE_PLUGIN_ROOT', None)
    env.pop('PURLIN_PROJECT_ROOT', None)
    done = subprocess.run(
        [sys.executable, SCAFFOLD, '--project-root', str(root), '--yes',
         '--gate', 'passed'],
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


# --- RULE-4: no version literal in the package ---------------------------

def release_literals(package_dir):
    """(module, literal) for each quoted X.Y.Z outside whole-line comments
    in the package's modules, the 0.0.0 placeholder aside."""
    semver_pattern = re.compile(r'["\'](\d+\.\d+\.\d+)["\']')
    found = []
    for path in sorted(glob.glob(os.path.join(package_dir, '*.py'))):
        with open(path, encoding='utf-8') as f:
            for line in f.read().splitlines():
                if line.lstrip().startswith('#'):
                    continue
                found += [(os.path.basename(path), v)
                          for v in semver_pattern.findall(line)
                          if v != '0.0.0']
    return found


def package_copy_with(tmp_path, added):
    """A copy of the package with `added` appended to its server module."""
    copy = tmp_path / 'purlin'
    shutil.copytree(PACKAGE_DIR, str(copy),
                    ignore=shutil.ignore_patterns('__pycache__'))
    with open(copy / 'server.py', 'a', encoding='utf-8') as f:
        f.write('\n' + added + '\n')
    return str(copy)


# purlin: purlin_version PROOF-4
def test_the_package_carries_no_version_literal(tmp_path):
    found = release_literals(PACKAGE_DIR)
    assert found == [], (
        f"Found release version string(s) in the package outside "
        f"comments: {found}. The version is read from the VERSION file.")
    # The check finds a literal added to a copy of one module.
    copy = package_copy_with(tmp_path, "RELEASE = '0.10.0'")
    assert release_literals(copy) == [('server.py', '0.10.0')]


# purlin: purlin_version PROOF-23
def test_a_version_on_a_whole_line_comment_is_not_found(tmp_path):
    copy = package_copy_with(tmp_path, "# the release was '0.9.0'")
    assert release_literals(copy) == []


# --- RULE-7: nothing but the bump script sets a new number ---------------

# A module that writes one of these files is one a `version` field is
# written from.
VERSION_FILES = ('config.json', 'plugin.json')


def _version_values(tree):
    """(line, value) for each value given a `version` key: in a dict
    written out, to `x['version'] = ...`, or as `version=...`."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            found += [(value.lineno, value)
                      for key, value in zip(node.keys, node.values)
                      if isinstance(key, ast.Constant)
                      and key.value == 'version']
        elif isinstance(node, ast.Assign):
            found += [(node.lineno, node.value) for target in node.targets
                      if isinstance(target, ast.Subscript)
                      and isinstance(target.slice, ast.Constant)
                      and target.slice.value == 'version']
        elif isinstance(node, ast.Call):
            found += [(keyword.value.lineno, keyword.value)
                      for keyword in node.keywords
                      if keyword.arg == 'version']
    return found


def _reads_version_file(value, source, readers):
    """True when `value` gives no number (None), or reads the VERSION file:
    its text names `VERSION`, or it calls a function of the same module
    whose body names the file."""
    if isinstance(value, ast.Constant) and value.value is None:
        return True
    text = ast.get_source_segment(source, value) or ''
    if 'VERSION' in text:
        return True
    return any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
               and node.func.id in readers for node in ast.walk(value))


def version_writes_not_from_the_file(scripts_dir):
    """`<path>:<line>: <value>` for each `version` value, in a module under
    `scripts_dir` that names the settings file or the plugin manifest,
    that is not read from the VERSION file."""
    found = []
    for path in sorted(glob.glob(os.path.join(scripts_dir, '**', '*.py'),
                                 recursive=True)):
        with open(path, encoding='utf-8') as f:
            source = f.read()
        if not any(name in source for name in VERSION_FILES):
            continue
        tree = ast.parse(source)
        readers = {node.name for node in ast.walk(tree)
                   if isinstance(node, ast.FunctionDef)
                   and "'VERSION'" in (ast.get_source_segment(source, node)
                                       or '')}
        rel = os.path.relpath(path, scripts_dir).replace(os.sep, '/')
        found += ['%s:%d: %s' % (rel, line,
                                 ast.get_source_segment(source, value))
                  for line, value in _version_values(tree)
                  if not _reads_version_file(value, source, readers)]
    return found


# purlin: purlin_version PROOF-37
def test_every_version_field_the_scripts_write_is_read_from_the_file(
        tmp_path):
    scripts_dir = os.path.join(PROJECT_ROOT, 'scripts')
    assert version_writes_not_from_the_file(scripts_dir) == []
    # The scan finds a number written into a copy of the upgrade.
    copy = tmp_path / 'scripts'
    shutil.copytree(scripts_dir, str(copy),
                    ignore=shutil.ignore_patterns('__pycache__'))
    upgrade = copy / 'init' / 'update.py'
    text = upgrade.read_text(encoding='utf-8')
    assert "'version': _version()," in text
    upgrade.write_text(text.replace("'version': _version(),",
                                    "'version': '9.9.9',", 1),
                       encoding='utf-8')
    found = version_writes_not_from_the_file(str(copy))
    assert len(found) == 1 and found[0].startswith('init/update.py:'), found
    assert found[0].endswith(": '9.9.9'"), found


# --- RULE-12, RULE-13, RULE-14: the bump script and its check -------------

DERIVED = [
    os.path.join('.claude-plugin', 'plugin.json'),
    os.path.join('.purlin', 'config.json'),
]


def fake_project(tmp_path, version, with_settings=True):
    """A tree holding a copy of the bump script, VERSION and the derived
    files at `version`; `.purlin/config.json` is left out when asked.

    The script resolves the root as its own parent, so it runs from a
    dev/ directory inside the tree under test. Returns (root, script)."""
    root = tmp_path / 'proj'
    root.mkdir()
    (root / 'VERSION').write_text(version + '\n', encoding='utf-8')
    for rel in DERIVED:
        if rel.startswith('.purlin') and not with_settings:
            continue
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
def test_the_bump_writes_the_version_everywhere(tmp_path):
    root, script = fake_project(tmp_path, '1.2.3')
    bump = run_script(script, '9.8.7')
    assert bump.returncode == 0, \
        f"bump exited {bump.returncode}\n{bump.stdout}\n{bump.stderr}"
    assert read_version_file(root) == '9.8.7'
    for rel in DERIVED:
        assert read_version(root, rel) == '9.8.7', rel


# purlin: purlin_version PROOF-28
def test_the_check_passes_a_project_that_agrees(tmp_path):
    root, script = fake_project(tmp_path, '9.8.7')
    ok = run_script(script, '--check')
    assert ok.returncode == 0, f"{ok.stdout}\n{ok.stderr}"
    for rel in (MANIFEST_REL, SETTINGS_REL):
        assert check_line(ok.stdout, rel) == ['ok', '9.8.7'], ok.stdout


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


# purlin: purlin_version PROOF-30
def test_the_check_names_a_location_with_no_version_key(tmp_path):
    root, script = fake_project(tmp_path, '9.8.7')
    write_version(root, MANIFEST_REL, None)
    bad = run_script(script, '--check')
    assert bad.returncode == 1, \
        f"--check exited {bad.returncode} with a key missing, expected 1"
    assert check_line(bad.stdout, MANIFEST_REL) == \
        ['FAIL', 'no', '"version"', 'key'], bad.stdout


# purlin: purlin_version PROOF-31
def test_the_bump_refuses_a_non_version_and_writes_nothing(tmp_path):
    root, script = fake_project(tmp_path, '1.2.3')
    bad = run_script(script, 'not-a-version')
    assert bad.returncode == 2, f"expected exit 2, got {bad.returncode}"
    assert read_version_file(root) == '1.2.3', \
        "VERSION was modified despite an invalid argument"
    for rel in DERIVED:
        assert read_version(root, rel) == '1.2.3', \
            f"{rel} was modified despite an invalid argument"


# purlin: purlin_version PROOF-32
def test_the_bump_skips_absent_settings_without_creating_them(tmp_path):
    root, script = fake_project(tmp_path, '1.2.3', with_settings=False)
    run = run_script(script, '2.0.0')
    assert run.returncode == 0, \
        f"bump failed with the settings file absent:\n{run.stdout}\n{run.stderr}"
    assert read_version_file(root) == '2.0.0'
    assert read_version(root, MANIFEST_REL) == '2.0.0'
    assert not (root / SETTINGS_REL).exists(), \
        "the bump created the absent .purlin/config.json"


# purlin: purlin_version PROOF-33
def test_the_check_reports_absent_settings_and_passes(tmp_path):
    root, script = fake_project(tmp_path, '2.0.0', with_settings=False)
    check = run_script(script, '--check')
    assert check.returncode == 0, \
        f"--check failed with the settings file absent:\n{check.stdout}"
    assert check_line(check.stdout, SETTINGS_REL)[0] == 'absent', \
        check.stdout
    assert check_line(check.stdout, MANIFEST_REL) == ['ok', '2.0.0'], \
        check.stdout


# --- RULE-8: the one table row that describes the version field ----------

OWNER = 'references/drift_criteria.md'
ROW_START = '| `version` |'
SEMVER_LITERAL = re.compile(r'\d+\.\d+\.\d+')


def version_rows(path):
    """The table rows of the Markdown file at `path` whose first cell is
    `version`."""
    with open(path, encoding='utf-8') as f:
        return [ln.strip() for ln in f.read().splitlines()
                if ln.strip().startswith(ROW_START)]


def owner_row_problems(rows):
    """What each of the owner's `version` rows gets wrong: a restated
    number, or no mention of the VERSION file."""
    problems = []
    for row in rows:
        for literal in SEMVER_LITERAL.findall(row):
            problems.append(f"restates {literal}: {row}")
        if 'VERSION' not in row:
            problems.append(f"does not name the VERSION file: {row}")
    return problems


def second_copies(root):
    """Every Markdown file under skills/ and references/ of `root`, other
    than the owner, holding a `version` row, as a sorted list of paths."""
    copies = []
    for base in ('skills', 'references'):
        for dirpath, _dirs, files in os.walk(os.path.join(root, base)):
            for name in files:
                if not name.endswith('.md'):
                    continue
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, root).replace(os.sep, '/')
                if rel != OWNER and version_rows(path):
                    copies.append(rel)
    return sorted(copies)


# purlin: purlin_version PROOF-8
def test_the_one_version_row_names_the_version_file():
    rows = version_rows(os.path.join(PROJECT_ROOT, OWNER))
    assert rows, f"no `version` field row found in {OWNER}"
    assert owner_row_problems(rows) == []
    # The check finds a copy of the row that restates a number.
    restated = [row.replace('`VERSION`', '`0.9.0`') for row in rows]
    assert all('VERSION' not in row for row in restated), restated
    problems = owner_row_problems(restated)
    for row in restated:
        assert f"restates 0.9.0: {row}" in problems, problems
        assert f"does not name the VERSION file: {row}" in problems, problems


# purlin: purlin_version PROOF-34
def test_no_second_copy_of_the_version_row_exists(tmp_path):
    copies = second_copies(PROJECT_ROOT)
    assert copies == [], (
        f"a second `version` field row lives in {copies}; "
        f"{OWNER} is the field's one documented home")
    # The check finds a row added to a copy of the init skill.
    for base in ('skills', 'references'):
        shutil.copytree(os.path.join(PROJECT_ROOT, base),
                        str(tmp_path / base))
    with open(tmp_path / 'skills' / 'init' / 'SKILL.md', 'a',
              encoding='utf-8') as f:
        f.write('\n| `version` | `"0.9.0"` |\n')
    assert second_copies(str(tmp_path)) == ['skills/init/SKILL.md']
