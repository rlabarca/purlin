"""The install the README and the getting-started page give, run for real.

`specs/instructions/install.md` holds five rules. The first is read off the
two pages. The other four run the pages' own commands with the real `claude`
program in a project this file makes, the marketplace address swapped for
this checkout, so the code installed is the code under test.

The install is made under a Claude Code configuration folder of its own,
named by `CLAUDE_CONFIG_DIR`, so nothing is written to the person's own.
One prompt goes to the smallest model, to ask which `purlin:` commands
Claude Code offers. Where the environment carries a credential of its own,
`ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`, that prompt runs under the
same folder as the install. Where the only credential is the person's login,
which that folder cannot read, the prompt runs under the person's login with
the installed plugin's folder loaded for the one session and the project's
settings left out, so the person's own plugins and marketplaces stay as they
were.

`dev/conftest.py` puts a fake `claude` first on the path. This file is the
one place that steps past it: it finds the real program on the rest of the
path and skips with `claude is not installed here` where there is none.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ADDRESS = 'https://github.com/rlabarca/purlin.git'
SHELLS = ('bash', 'sh', 'shell', 'console')
NOT_INSTALLED = 'claude is not installed here'
PROMPT = ('List every slash command or skill available to you whose name '
          'starts with purlin: and nothing else. Answer with the names '
          'only, one per line. Use no tool.')
OWN_CREDENTIALS = ('ANTHROPIC_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN')


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


# --- The commands the pages give -------------------------------------------

def shell_lines(text):
    """The lines of every fenced shell block of `text`, in order, blank
    lines left out."""
    lines, inside = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('```'):
            inside = not inside and stripped[3:].strip() in SHELLS
            continue
        if inside and stripped:
            lines.append(stripped)
    return lines


def readme_install_lines(text=None):
    """The fenced shell lines under the README's heading `Install`."""
    if text is None:
        text = read(os.path.join(ROOT, 'README.md'))
    section, inside = [], False
    for line in text.splitlines():
        if line.startswith('## '):
            inside = line[3:].strip() == 'Install'
            continue
        if inside:
            section.append(line)
    return shell_lines('\n'.join(section))


def getting_started_install_lines(text=None):
    """The fenced shell lines under step 1 of the getting-started page: from
    the line that opens `**1. ` to the line that opens `**2. `."""
    if text is None:
        text = read(os.path.join(ROOT, 'docs', 'getting-started.md'))
    section, inside = [], False
    for line in text.splitlines():
        if line.startswith('**1. '):
            inside = True
        elif line.startswith('**2. '):
            inside = False
        if inside:
            section.append(line)
    return shell_lines('\n'.join(section))


def marketplace_addresses(lines):
    """What follows `claude plugin marketplace add` on each line that runs
    it."""
    found = []
    for line in lines:
        words = shlex.split(line)
        if words[:4] == ['claude', 'plugin', 'marketplace', 'add']:
            found.append(words[4])
    return found


# purlin: install PROOF-1
def test_both_pages_give_the_same_install_lines_and_this_repositorys_address():
    readme = readme_install_lines()
    guide = getting_started_install_lines()
    assert len(readme) >= 2, readme
    assert readme == guide
    assert marketplace_addresses(readme) == [ADDRESS]
    assert marketplace_addresses(guide) == [ADDRESS]
    # A page whose block sits under another heading gives no install lines,
    # and a line that differs by one word is not the same line.
    other = '## Run from a checkout\n\n```bash\nclaude --plugin-dir x\n```\n'
    assert readme_install_lines(other) == []
    assert [line.replace('project', 'user') for line in readme] != guide


# --- The real program -------------------------------------------------------

def path_past(fake_directory):
    """The search path without the folder the fake `claude` stands in."""
    return os.pathsep.join(
        entry for entry in os.environ.get('PATH', '').split(os.pathsep)
        if entry and os.path.realpath(entry) != os.path.realpath(
            fake_directory))


def environment(fake_directory, config=None):
    """This process's environment with the fake off the path and no plugin
    folder named; with `config`, Claude Code keeps its own files there."""
    env = dict(os.environ)
    env['PATH'] = path_past(fake_directory)
    for name in ('CLAUDE_PLUGIN_ROOT', 'PURLIN_PROJECT_ROOT'):
        env.pop(name, None)
    if config is not None:
        env['CLAUDE_CONFIG_DIR'] = config
    return env


def run(command, cwd, env, timeout=300):
    return subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                          text=True, encoding='utf-8', timeout=timeout,
                          stdin=subprocess.DEVNULL)


def listed(claude, what, cwd, env):
    """What `claude plugin list --json` or `claude plugin marketplace list
    --json` prints, read as JSON."""
    command = {'plugins': [claude, 'plugin', 'list', '--json'],
               'marketplaces': [claude, 'plugin', 'marketplace', 'list',
                                '--json']}[what]
    done = run(command, cwd, env)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def the_persons_own(claude, fake_directory):
    """The plugins and marketplaces of the person's own Claude Code."""
    env = environment(fake_directory)
    return {'plugins': listed(claude, 'plugins', ROOT, env),
            'marketplaces': listed(claude, 'marketplaces', ROOT, env)}


def run_the_pages_lines(lines, claude, base, env):
    """Run each install line as the pages give it, `cd` moving into the
    folder it names and every other line run with the real `claude`, the
    marketplace address replaced by this checkout's folder. Returns the
    folder the lines ended in."""
    cwd = base
    for line in lines:
        words = shlex.split(line)
        if words[0] == 'cd':
            cwd = os.path.join(cwd, words[1])
            continue
        assert words[0] == 'claude', line
        command = [claude] + [ROOT if word == ADDRESS else word
                              for word in words[1:]]
        done = run(command, cwd, env)
        assert done.returncode == 0, '%s\n%s\n%s' % (line, done.stdout,
                                                     done.stderr)
    return cwd


@pytest.fixture(scope='module')
def installed(no_real_model):
    """The pages' install, made once in a fresh project: the real `claude`,
    the project, its own configuration folder, and the person's plugins and
    marketplaces as they read before it."""
    claude = shutil.which('claude', path=path_past(no_real_model))
    if claude is None:
        pytest.skip(NOT_INSTALLED)
    before = the_persons_own(claude, no_real_model)
    base = os.path.realpath(tempfile.mkdtemp(prefix='purlin-install-'))
    project = os.path.join(base, 'my-project')
    config = os.path.join(base, 'claude-config')
    os.makedirs(project)
    os.makedirs(config)
    subprocess.run(['git', '-c', 'init.defaultBranch=main', 'init', '-q',
                    '.'], cwd=project, check=True, capture_output=True)
    env = environment(no_real_model, config)
    try:
        lines = readme_install_lines()
        assert lines == getting_started_install_lines()
        ended_in = run_the_pages_lines(lines, claude, base, env)
        assert ended_in == project, ended_in
        yield {'claude': claude, 'fake': no_real_model, 'base': base,
               'project': project, 'config': config, 'env': env,
               'before': before}
    finally:
        shutil.rmtree(base, ignore_errors=True)


def purlin_entry(installed):
    """The row `claude plugin list` gives `purlin@purlin` for the test's
    project."""
    rows = [row for row in listed(installed['claude'], 'plugins',
                                  installed['project'], installed['env'])
            if row['id'] == 'purlin@purlin']
    assert len(rows) == 1, rows
    return rows[0]


def skill_folders():
    """Each folder under `skills/` of this checkout that holds a skill."""
    skills = os.path.join(ROOT, 'skills')
    return sorted(name for name in os.listdir(skills)
                  if os.path.isfile(os.path.join(skills, name, 'SKILL.md')))


# purlin: install PROOF-2
def test_the_pages_commands_leave_purlin_installed_and_enabled(request):
    # The install is asked for here, in the test: where the pages' commands
    # do not install the plugin, this test fails.
    installed = request.getfixturevalue('installed')
    row = purlin_entry(installed)
    assert row['enabled'] is True
    assert row['scope'] == 'project'
    assert os.path.realpath(row['projectPath']) == installed['project']
    shown = run([installed['claude'], 'plugin', 'list'],
                installed['project'], installed['env'])
    assert 'purlin@purlin' in shown.stdout
    assert 'enabled' in shown.stdout


# purlin: install PROOF-3
def test_every_skill_of_this_checkout_landed_byte_for_byte(installed):
    home = purlin_entry(installed)['installPath']
    # The folder the installed plugin reads its skills from is the one its
    # own manifest names, and `skills` where the manifest names none. It is
    # one folder, inside the installed plugin.
    manifest = json.loads(read(os.path.join(home, '.claude-plugin',
                                            'plugin.json')))
    assert manifest['name'] == 'purlin', manifest
    named = manifest.get('skills', './skills')
    assert isinstance(named, str), named
    folder = os.path.realpath(os.path.join(home, named))
    assert folder.startswith(os.path.realpath(home) + os.sep), named
    assert os.path.isdir(folder), folder
    names = skill_folders()
    assert len(names) >= 9, names
    # It holds those skills and no other.
    assert sorted(
        name for name in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, name, 'SKILL.md'))) == names
    for name in names:
        landed = os.path.join(folder, name, 'SKILL.md')
        assert os.path.isfile(landed), landed
        with open(landed, 'rb') as theirs, open(
                os.path.join(ROOT, 'skills', name, 'SKILL.md'),
                'rb') as ours:
            assert theirs.read() == ours.read(), name


def own_credential():
    """True where the environment carries a credential the install's own
    configuration folder can use."""
    return any(os.environ.get(name) for name in OWN_CREDENTIALS)


def the_one_prompt(installed):
    """The command and environment of the one prompt to the smallest
    model, run in the test's project."""
    command = [installed['claude'], '-p', PROMPT, '--model', 'haiku',
               '--output-format', 'json', '--no-session-persistence',
               '--strict-mcp-config', '--mcp-config', '{"mcpServers": {}}']
    if own_credential():
        return command, installed['env']
    # The person's login is the only credential, and the install's own
    # configuration folder cannot read it.
    command += ['--plugin-dir', purlin_entry(installed)['installPath'],
                '--setting-sources', 'user']
    return command, environment(installed['fake'])


def session_folder(config, project):
    """The folder Claude Code keeps for a project's sessions under a
    configuration folder: the project's path with every character but a
    letter and a digit read as `-`."""
    return os.path.join(config, 'projects',
                        re.sub(r'[^A-Za-z0-9]', '-', project))


def remove_if_empty(folder):
    """Remove `folder` where it holds no file, only empty folders; a
    folder holding any file is left as it is. True where it is gone."""
    if not os.path.isdir(folder):
        return True
    if any(files for _, _, files in os.walk(folder)):
        return False
    shutil.rmtree(folder)
    return True


# purlin: install PROOF-4
def test_claude_code_offers_every_purlin_skill_to_the_model(installed):
    command, env = the_one_prompt(installed)
    try:
        done = run(command, installed['project'], env, timeout=600)
    finally:
        if not own_credential():
            # A session under the person's login leaves an empty folder
            # named after the test's project; it goes with the project.
            remove_if_empty(session_folder(
                os.environ.get('CLAUDE_CONFIG_DIR')
                or os.path.join(os.path.expanduser('~'), '.claude'),
                installed['project']))
    assert done.returncode == 0, '%s\n%s' % (done.stdout, done.stderr)
    answer = json.loads(done.stdout)
    assert answer.get('is_error') is False, answer
    names = skill_folders()
    assert len(names) >= 9, names
    offered = set(re.findall(r'purlin:([a-z][a-z-]*)', answer['result']))
    assert [name for name in names if name not in offered] == [], \
        answer['result']


# purlin: install PROOF-5
def test_the_persons_own_claude_code_reads_the_same_afterwards(request):
    # The install is asked for here, in the test: where it cannot be made
    # as the pages give it, this test fails.
    installed = request.getfixturevalue('installed')
    after = the_persons_own(installed['claude'], installed['fake'])
    assert after['plugins'] == installed['before']['plugins']
    assert after['marketplaces'] == installed['before']['marketplaces']
    shutil.rmtree(installed['base'])
    assert not os.path.exists(installed['project'])
