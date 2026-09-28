"""Tests for the committed consumer-CI fixture.

`dev/fixtures/consumer-ci/` is a complete minimal consumer project: what
`purlin:init` writes for a `strong` gate, plus one spec, one module and one
test file. It carries no Purlin `scripts/` and no `dev/`, exactly as a project
that installed Purlin from the marketplace does, so its workflow has to clone
the tooling on the runner.

The fixture's value is that it is the documentation, executed. The workflow is
rendered from `templates/purlin.yml` and compared with the committed file, so
the fixture cannot drift from the template without a red test; the rest asserts
the project is complete, that its structure is what a runner will read, and
that Purlin reads it as one feature with one Linux-scoped proof.
"""

import json
import os
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'run'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import workflow as workflow_module  # noqa: E402
from purlin import payload as payload_module  # noqa: E402

FIXTURE = os.path.join(ROOT, 'dev', 'fixtures', 'consumer-ci')
FIXTURE_REL = 'dev/fixtures/consumer-ci'
WORKFLOW_REL = '.github/workflows/purlin.yml'

# Every file the fixture is made of. `.purlin/runtime/` and the dashboard page
# are deliberately absent: they are generated state that the fixture's own
# `.gitignore` excludes, and a fixture that shipped them would
# ship a claim about a run that did not happen here.
FIXTURE_FILES = (
    '.github/workflows/purlin.yml',
    '.gitignore',
    '.purlin/config.json',
    'greeting.py',
    'specs/core/greeting.md',
    'tests/test_greeting.py',
)

# The Purlin release a consumer's runner clones. The fixture is rendered at the
# version this repository is on, so a release bump and the fixture move
# together.
with open(os.path.join(ROOT, 'VERSION'), encoding='utf-8') as _handle:
    PURLIN_REF = 'v' + _handle.read().strip()


def read(rel, root=FIXTURE):
    with open(os.path.join(root, rel), encoding='utf-8') as handle:
        return handle.read()


def tracked(rel):
    """True when `rel` is tracked by git, not merely present on disk."""
    listed = subprocess.run(['git', 'ls-files', '--error-unmatch', '--', rel],
                            cwd=ROOT, capture_output=True, text=True)
    return listed.returncode == 0


# ---------------------------------------------------------------------------
# A structural read of the workflow, with the standard library alone
# ---------------------------------------------------------------------------

def parse_blocks(text):
    """`{top-level key: [line, ...]}` for a YAML document of plain mappings.

    This is not a YAML parser and does not pretend to be one. It checks the
    shape a workflow file has to have: comments and blank lines between
    blocks, every other line indented under a key at column zero, no tabs, and
    every indent a multiple of two. Anything else raises, which is the point:
    a rendered file that is not shaped like a workflow must fail here rather
    than on a runner.
    """
    blocks = {}
    current = None
    for number, line in enumerate(text.splitlines(), 1):
        if '\t' in line:
            raise ValueError('line %d has a tab' % number)
        if line.rstrip() != line:
            raise ValueError('line %d has trailing whitespace' % number)
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip(' '))
        if indent % 2:
            raise ValueError('line %d is indented by %d' % (number, indent))
        if indent == 0:
            if ':' not in line:
                raise ValueError('line %d is not a key: %r' % (number, line))
            current = line.split(':', 1)[0]
            blocks[current] = []
        elif current is None:
            raise ValueError('line %d is indented under nothing' % number)
        else:
            blocks[current].append(line)
    return blocks


def step_names(lines):
    """Every `- name:` and `- uses:` in a job's lines, in order."""
    found = []
    for line in lines:
        stripped = line.strip()
        for prefix in ('- name: ', '- uses: '):
            if stripped.startswith(prefix):
                found.append(stripped[len(prefix):])
    return found


# ---------------------------------------------------------------------------
# The workflow
# ---------------------------------------------------------------------------

# purlin: host PROOF-17
def test_the_fixture_workflow_is_what_the_template_renders():
    rendered = workflow_module.render_workflow('github', ['linux'], PURLIN_REF)
    committed = read(WORKFLOW_REL)
    if rendered != committed:
        expected = rendered.splitlines()
        actual = committed.splitlines()
        for index in range(max(len(expected), len(actual))):
            left = expected[index] if index < len(expected) else '<end of file>'
            right = actual[index] if index < len(actual) else '<end of file>'
            if left != right:
                raise AssertionError(
                    '%s/%s differs from the rendered template at line %d:\n'
                    '  template renders: %r\n'
                    '  fixture carries:  %r'
                    % (FIXTURE_REL, WORKFLOW_REL, index + 1, left, right))
        raise AssertionError('the two texts differ only in trailing bytes')


# purlin: host PROOF-17
def test_the_template_still_carries_the_placeholders():
    """A substitution that has become a no-op proves nothing."""
    template = read(os.path.join('templates', 'purlin.yml'), root=ROOT)
    assert '<<MATRIX>>' in template
    assert '<<PURLIN_REF>>' in template


# purlin: host PROOF-17
def test_the_triggers_name_a_run_branch_and_the_signing_tag_and_nothing_else():
    named = workflow_module.render_workflow('github', ['linux'], PURLIN_REF)
    assert "branches: ['run/**']" in named
    assert "tags: ['signed/**']" in named
    assert 'pull_request' not in named


# purlin: host PROOF-17
def test_a_workflow_is_written_for_two_reasons_and_no_others():
    wanted, reasons = workflow_module.wanted([], 'local', 'macos')
    assert wanted is False and reasons == []
    wanted, reasons = workflow_module.wanted(['windows'], 'local', 'macos')
    assert wanted is True and len(reasons) == 1
    assert 'windows' in reasons[0]
    wanted, reasons = workflow_module.wanted([], 'remote', 'macos')
    assert wanted is True and len(reasons) == 1
    assert 'trust' in reasons[0].lower() or 'signing' in reasons[0]
    wanted, reasons = workflow_module.wanted(['macos'], 'local', 'macos')
    assert wanted is False, reasons


# purlin: host PROOF-18
def test_the_workflow_is_shaped_like_a_workflow():
    blocks = parse_blocks(read(WORKFLOW_REL))
    assert sorted(blocks) == ['jobs', 'name', 'on', 'permissions']
    assert 'contents: write' in read(WORKFLOW_REL)
    assert 'pull-requests' not in read(WORKFLOW_REL)
    assert '\n'.join(blocks['on']) == (
        "  push:\n    branches: ['run/**']\n    tags: ['signed/**']")
    for placeholder in ('<<MATRIX>>', '<<PURLIN_REF>>'):
        assert placeholder not in read(WORKFLOW_REL), (
            '%s was left unfilled' % placeholder)


# purlin: host PROOF-18
def test_the_workflow_names_the_test_step_and_uploads_nothing():
    jobs = '\n'.join(parse_blocks(read(WORKFLOW_REL))['jobs'])
    names = step_names(jobs.splitlines())
    assert 'actions/checkout@v4' in names
    assert 'Locate Purlin' in names
    assert 'Run the tests' in names
    assert 'actions/upload-artifact@v4' not in names, (
        'a run uploads nothing: the two runs are a remote run and a tag run')
    assert names[-1] == 'Check the gate', (
        'the gate check is the last word of every run')
    assert 'scripts/run/purlin_run.py" --all --ci' in jobs
    assert 'scripts/ci/gate_check.py" --check --verify' in jobs


# purlin: host PROOF-18
def test_the_job_is_named_purlin():
    jobs = parse_blocks(read(WORKFLOW_REL))['jobs']
    assert jobs[0].strip() == 'purlin:', jobs[0]


# purlin: host PROOF-19
def test_the_matrix_is_the_one_operating_system_the_spec_names():
    jobs = '\n'.join(parse_blocks(read(WORKFLOW_REL))['jobs'])
    assert 'os: [ubuntu-latest]' in jobs
    assert 'windows-latest' not in jobs
    assert workflow_module.env_tags_in_specs(FIXTURE) == ['linux']


# purlin: host PROOF-19
def test_the_matrix_is_one_job_per_named_operating_system():
    """Linux always leads, the order is fixed, and an unknown name is ignored."""
    assert workflow_module.runners_for(['windows', 'linux']) == [
        'ubuntu-latest', 'windows-latest']
    assert workflow_module.runners_for([]) == ['ubuntu-latest']
    assert workflow_module.runners_for(['plan9']) == ['ubuntu-latest']


# purlin: host PROOF-19
def test_the_matrix_always_carries_linux_first():
    """Every untagged proof is proved somewhere, so the Linux job always runs."""
    assert workflow_module.runners_for(['windows']) == [
        'ubuntu-latest', 'windows-latest']
    assert workflow_module.runners_for(['linux']) == ['ubuntu-latest']
    assert workflow_module.runners_for(['macos', 'windows']) == [
        'ubuntu-latest', 'macos-latest', 'windows-latest']
    rendered = workflow_module.render_workflow('github', ['windows'], PURLIN_REF)
    assert 'os: [ubuntu-latest, windows-latest]' in rendered


# purlin: host PROOF-18
def test_the_workflow_clones_the_release_the_project_pins():
    jobs = '\n'.join(parse_blocks(read(WORKFLOW_REL))['jobs'])
    assert 'ref="%s"' % PURLIN_REF in jobs, (
        'a consumer runner has no plugin, so the ref it clones must be pinned')
    assert 'https://github.com/rlabarca/purlin' in jobs
    assert 'vars.PURLIN_REF' in jobs, 'the pin must be movable without an edit'


# purlin: host PROOF-18
def test_no_pull_request_starts_a_run_at_all():
    """A fork's read-only token was the awkward case; there is no such run."""
    text = read(WORKFLOW_REL)
    assert 'pull_request' not in text
    assert 'fork' not in text


# ---------------------------------------------------------------------------
# The project
# ---------------------------------------------------------------------------

# purlin: host PROOF-20
def test_the_fixture_is_complete_and_every_file_is_tracked():
    on_disk = set()
    for folder, dirnames, filenames in os.walk(FIXTURE):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        for name in filenames:
            rel = os.path.relpath(os.path.join(folder, name), FIXTURE)
            on_disk.add(rel.replace(os.sep, '/'))

    assert on_disk == set(FIXTURE_FILES), (
        'the fixture holds %s and is missing %s'
        % (sorted(on_disk - set(FIXTURE_FILES)),
           sorted(set(FIXTURE_FILES) - on_disk)))
    for rel in FIXTURE_FILES:
        assert tracked(FIXTURE_REL + '/' + rel), (
            '%s/%s is on disk but not tracked, so a clone of this repository '
            'would not carry it' % (FIXTURE_REL, rel))


# purlin: host PROOF-20
def test_the_config_is_the_shape_this_release_reads():
    config = json.loads(read('.purlin/config.json'))
    assert config['gate'] == 'strong'
    assert [suite['name'] for suite in config['tests']] == ['pytest']
    assert config['version'] == PURLIN_REF[1:]
    template = json.loads(read(os.path.join('templates', 'config.json'),
                               root=ROOT))
    assert list(config) == list(template), (
        'the fixture config carries %s where init writes %s'
        % (list(config), list(template)))


# purlin: host PROOF-20
def test_purlin_reads_the_fixture_as_one_feature_with_a_linux_proof():
    data = payload_module.build_payload(FIXTURE, generated_by='test')
    assert data['warnings'] == []
    assert [f['name'] for f in data['features']] == ['greeting']
    greeting = data['features'][0]
    assert [r['id'] for r in greeting['rules']] == ['RULE-1', 'RULE-2']

    envs = {proof['id']: proof['env']
            for rule in greeting['rules'] for proof in rule['proofs']}
    assert envs == {'PROOF-1': None, 'PROOF-2': 'linux'}
    assert data['gate']['gate'] == 'strong'
    assert data['gate']['min_strength'] == 70
    assert data['evidence'] == {}, 'no run has happened in the fixture'


# purlin: host PROOF-20
def test_the_fixtures_tests_pass_against_its_own_module():
    sys.path.insert(0, FIXTURE)
    try:
        import greeting
    finally:
        sys.path.remove(FIXTURE)
    assert greeting.greet('Ada') == 'Hello, Ada!'
    assert greeting.greet('') == 'Hello, world!'
    assert isinstance(greeting.os_tag(), str)
