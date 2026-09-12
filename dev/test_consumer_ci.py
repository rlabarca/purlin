"""Tests for consumer_ci: 2 proofs covering the committed consumer-CI fixture.

`dev/fixtures/consumer-ci/` is a complete minimal consumer project: what
`purlin:init` writes, plus the one spec, the one test file, the platform
registry entry and the two workflows a consumer needs to prove an
`@on(ubuntu-24)` proof on a real Ubuntu runner.

The fixture's value is that it is the documentation, executed. PROOF-1 renders
both workflows from the reference templates and compares them to the committed
files byte for byte, so the fixture cannot drift from the docs without a red
test; PROOF-2 asserts the project is complete and that Purlin reads it as one
feature with one proof awaiting `ubuntu-24`.

RULE-3, the live dry run itself, is `@manual`: it creates a real GitHub
repository under the user's account and deletes it again, so there is nothing
here to run.
"""

import json
import os
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import purlin_server  # noqa: E402

FIXTURE = os.path.join(ROOT, 'dev', 'fixtures', 'consumer-ci')
FIXTURE_REL = 'dev/fixtures/consumer-ci'
REFERENCE = os.path.join(ROOT, 'references', 'remote_verification.md')
REPO_VERIFY_GATE = os.path.join(ROOT, '.github', 'workflows', 'verify-gate.yml')

# ---------------------------------------------------------------------------
# The substitutions (consumer_ci RULE-1)
# ---------------------------------------------------------------------------
# `<platform-id>` and `<runs-on>` are the two the reference template names. The
# third is the tooling pin: the template pins `--branch v<VERSION>`, and this
# branch is not pushed and not released yet, so the fixture pins the branch
# instead. It becomes `--branch v<VERSION>` when main is pushed and the release
# is cut.
# `<test files>` is the fourth: the template leaves the test command's argument
# as a placeholder for the project to fill, and a fixture that keeps the
# placeholder is not runnable.
PLATFORM_ID = 'ubuntu-24'
RUNS_ON = 'ubuntu-24.04'
TOOLING_PIN = 'two-gauges-remote-verification'
TEST_FILES = 'tests/test_greeting.py'

SUBSTITUTIONS = (
    ('<platform-id>', PLATFORM_ID),
    ('<runs-on>', RUNS_ON),
    ('--branch v<VERSION>', '--branch ' + TOOLING_PIN),
    ('<test files>', TEST_FILES),
)

# Every file the fixture is made of (consumer_ci RULE-2). `.purlin/runtime/`,
# `.purlin/cache/` and `purlin-report.html` are deliberately absent: they are
# gitignored generated state, not part of a project.
FIXTURE_FILES = (
    '.github/workflows/purlin-ubuntu-24-proofs.yml',
    '.github/workflows/verify-gate.yml',
    '.gitignore',
    '.purlin/config.json',
    '.purlin/plugins/pytest_purlin.py',
    'conftest.py',
    'greeting.py',
    'specs/core/greeting.md',
    'tests/test_greeting.py',
)


# ---------------------------------------------------------------------------
# Rendering the two workflows from their templates
# ---------------------------------------------------------------------------

def _substitute(text):
    for placeholder, value in SUBSTITUTIONS:
        text = text.replace(placeholder, value)
    return text


def workflow_template(path=REFERENCE):
    """The runner-workflow template: the yaml fence under `### Workflow template`."""
    with open(path, encoding='utf-8') as f:
        text = f.read()
    heading = text.index('### Workflow template')
    start = text.index('```yaml\n', heading) + len('```yaml\n')
    end = text.index('\n```', start) + 1
    return text[start:end]


def render_proofs_workflow():
    """`purlin-ubuntu-24-proofs.yml`: the template with the substitutions applied."""
    return _substitute(workflow_template())


def _lift(text, first_line_prefix, stop_line_prefix):
    """The slice of `text` from one line to just before another, both by prefix."""
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith(first_line_prefix)]
    stops = [i for i, line in enumerate(lines) if line.startswith(stop_line_prefix)]
    assert starts, 'template has no line starting {!r}'.format(first_line_prefix)
    assert stops, 'template has no line starting {!r}'.format(stop_line_prefix)
    start = starts[0]
    stop = next(i for i in stops if i > start)
    return ''.join(lines[start:stop]).rstrip('\n') + '\n'


def render_verify_gate_workflow():
    """`verify-gate.yml`, consumer form.

    This repository's own `.github/workflows/verify-gate.yml` is the template.
    A consumer checkout holds no Purlin `scripts/`, so
    `references/remote_verification.md` states the adaptation: the job carries
    `PURLIN_PLUGIN_ROOT`, clones the pinned tooling into it, and reaches every
    Purlin script through it. The four operations below are that adaptation and
    nothing else; the trigger paths, the comments and the gate's own arguments
    are the template's, unchanged.
    """
    with open(REPO_VERIFY_GATE, encoding='utf-8') as f:
        text = f.read()
    proofs = render_proofs_workflow()

    # D1: the job gains `PURLIN_PLUGIN_ROOT`, lifted from the proofs template.
    # `PURLIN_PLATFORM` is not lifted with it: the gate proves nothing and
    # names no platform, and an env var that steers proof filenames has no
    # business in a job that writes no proof file.
    env_block = _lift(proofs, '      # Where the Purlin tooling is checked out.',
                      '    steps:')
    text = text.replace('    steps:\n', '    env:\n' + env_block + '    steps:\n', 1)

    # D2: the `Install Purlin tooling` step, lifted verbatim, after setup-python.
    install = _lift(proofs, '      - name: Install Purlin tooling',
                    '      - name: Preflight')
    text = text.replace('      # Prints the declared mode',
                        install + '\n      # Prints the declared mode', 1)

    # D3: the gate is reached through `$PURLIN_PLUGIN_ROOT`, on bash.
    text = text.replace(
        '        run: python3 scripts/ci/verify_gate.py --check --project-root .\n',
        '        shell: bash\n'
        '        run: python3 "$PURLIN_PLUGIN_ROOT/scripts/ci/verify_gate.py"'
        ' --check --project-root .\n', 1)

    # D4: the repo-only step that runs this repository's own dev suite is
    # dropped. `dev/test_verify_gate.py` does not exist in a consumer checkout.
    text = text[:text.index('\n      - name: Run the verify_gate proofs')] + '\n'
    return text


RENDERERS = {
    '.github/workflows/purlin-ubuntu-24-proofs.yml': render_proofs_workflow,
    '.github/workflows/verify-gate.yml': render_verify_gate_workflow,
}


def _first_difference(expected, actual, rel):
    """The first differing line, 1-based, or None when the texts are equal."""
    if expected == actual:
        return None
    exp_lines = expected.splitlines()
    act_lines = actual.splitlines()
    for i in range(max(len(exp_lines), len(act_lines))):
        e = exp_lines[i] if i < len(exp_lines) else '<end of file>'
        a = act_lines[i] if i < len(act_lines) else '<end of file>'
        if e != a:
            return ('{} differs from the rendered template at line {}:\n'
                    '  template renders: {!r}\n'
                    '  fixture carries:  {!r}'.format(rel, i + 1, e, a))
    return '{}: the two texts differ only in trailing bytes'.format(rel)


def _tracked(rel):
    """True when `rel` is tracked by git (not merely present on disk)."""
    listed = subprocess.run(
        ['git', 'ls-files', '--error-unmatch', '--', rel],
        cwd=ROOT, capture_output=True, text=True)
    return listed.returncode == 0


# ---------------------------------------------------------------------------
# Proofs
# ---------------------------------------------------------------------------

@pytest.mark.proof("consumer_ci", "PROOF-1", "RULE-1")
def test_fixture_workflows_equal_the_rendered_templates():
    """RULE-1: both fixture workflows equal their templates after substitution."""
    template = workflow_template()
    # The placeholders must really be in the template, or the substitutions
    # are no-ops and the comparison proves only that a file equals itself.
    for placeholder, _value in SUBSTITUTIONS:
        assert placeholder in template, (
            '{!r} is not in the reference template, so substituting it proves '
            'nothing'.format(placeholder))

    for rel, render in sorted(RENDERERS.items()):
        path = os.path.join(FIXTURE, rel)
        assert os.path.isfile(path), '{}/{} is missing'.format(FIXTURE_REL, rel)
        with open(path, encoding='utf-8') as f:
            actual = f.read()
        difference = _first_difference(render(), actual, FIXTURE_REL + '/' + rel)
        assert difference is None, difference

    # The pin is temporary and RULE-1 says so; assert the fixture carries the
    # branch pin and no `v<VERSION>` tag pin, so the day it is retagged both
    # the rule and this assertion are the thing that has to be updated.
    proofs_yml = os.path.join(FIXTURE, '.github', 'workflows',
                              'purlin-ubuntu-24-proofs.yml')
    with open(proofs_yml, encoding='utf-8') as f:
        rendered = f.read()
    assert '--branch ' + TOOLING_PIN in rendered
    assert '--branch v<VERSION>' not in rendered
    assert 'PURLIN_PLATFORM: ' + PLATFORM_ID in rendered
    assert 'runs-on: ' + RUNS_ON in rendered


@pytest.mark.proof("consumer_ci", "PROOF-2", "RULE-2")
def test_fixture_is_a_complete_tracked_consumer_project():
    """RULE-2: every named file is tracked, and Purlin reads the project."""
    for rel in FIXTURE_FILES:
        path = os.path.join(FIXTURE, rel)
        assert os.path.isfile(path), '{}/{} is missing'.format(FIXTURE_REL, rel)
        assert _tracked(FIXTURE_REL + '/' + rel), (
            '{}/{} is on disk but not tracked, so a clone of this repository '
            'would not carry it'.format(FIXTURE_REL, rel))

    # The plugin copy is the plugin, byte for byte: a stale copy is what the
    # workflow's migrate.py preflight exists to catch.
    with open(os.path.join(FIXTURE, '.purlin/plugins/pytest_purlin.py'),
              'rb') as f:
        copied = f.read()
    with open(os.path.join(ROOT, 'scripts/proof/pytest_purlin.py'), 'rb') as f:
        source = f.read()
    assert copied == source, ('.purlin/plugins/pytest_purlin.py is not a '
                              'byte-identical copy of scripts/proof/pytest_purlin.py')

    with open(os.path.join(FIXTURE, '.purlin/config.json'), encoding='utf-8') as f:
        config = json.load(f)
    assert config['test_framework'] == 'pytest'
    assert config['remote_verification'] == 'optional'
    assert config['platforms']['ubuntu-24'] == {
        'os': 'linux', 'distro': 'ubuntu', 'version': '24.04',
        'arch': 'x86_64', 'label': 'Ubuntu 24.04 LTS',
        'runner': {'provider': 'github', 'runs_on': 'ubuntu-24.04',
                   'workflow': 'purlin-ubuntu-24-proofs'},
    }

    payload = purlin_server.read_report_payload(FIXTURE)
    assert payload is not None, 'Purlin cannot read the fixture as a project'
    assert payload['platforms']['errors'] == []
    assert payload['platforms']['remote'] == ['ubuntu-24']
    assert payload['remote_verification'] == 'optional'

    features = payload['features']
    assert [f['name'] for f in features] == ['greeting']
    greeting = features[0]
    assert [r['id'] for r in greeting['rules']] == ['RULE-1', 'RULE-2']
    assert greeting['awaiting_runner'] == [
        {'id': 'PROOF-2', 'tier': 'unit', 'platform': 'ubuntu-24'}]

    summary = payload['platforms']['summary']['ubuntu-24']
    assert summary['features'] == 1
    assert summary['proofs'] == {'declared': 1, 'proved': 0, 'failed': 0,
                                 'awaiting': 1}
