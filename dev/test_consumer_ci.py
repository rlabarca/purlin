"""Tests for the runner file Purlin renders for a consumer project.

`scripts/run/workflow.py` fills `templates/purlin.yml` for GitHub and
`templates/purlin.azure-pipelines.yml` for Azure DevOps with the jobs the
project's `@env` tags call for and the Purlin release the runner clones. These
tests read what it renders: what starts a run, which jobs it holds, and that
the step running the tests is the last.
"""

import os
import sys

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'run'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import workflow as workflow_module  # noqa: E402

# The Purlin release a consumer's runner clones: the version this repository
# is on.
with open(os.path.join(ROOT, 'VERSION'), encoding='utf-8') as _handle:
    PURLIN_REF = 'v' + _handle.read().strip()


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


# ---------------------------------------------------------------------------
# The runner file
# ---------------------------------------------------------------------------

# purlin: host PROOF-142
def test_both_runner_files_start_on_a_run_branch_alone_and_no_tag():
    github = workflow_module.render_workflow('github', ['windows'], PURLIN_REF)
    azure = workflow_module.render_workflow('azure', ['windows'], PURLIN_REF)
    assert parse_blocks(github)['on'] == [
        '  push:', "    branches: ['run/**']"]
    assert parse_blocks(azure)['trigger'] == [
        '  branches:', '    include:', '      - run/*']
    assert parse_blocks(azure)['pr'] == []
    assert 'pr: none' in azure.splitlines()
    for text in (github, azure):
        keys = [line.strip() for line in text.splitlines()
                if not line.lstrip().startswith('#')]
        assert not [key for key in keys if key.startswith('tags')], keys


# purlin: host PROOF-47
def test_the_azure_pipeline_reads_pr_none_and_ends_on_run_the_tests():
    pipeline = workflow_module.render_workflow('azure', ['windows'],
                                               PURLIN_REF)
    blocks = parse_blocks(pipeline)
    assert 'pr: none' in pipeline.splitlines()
    steps = [line.strip() for line in blocks['jobs']
             if line.strip().startswith('- ')]
    assert steps[-1] == ('- bash: python3 "$PURLIN_ROOT/scripts/run/'
                         'purlin_run.py" --all --ci'), steps
    tail = pipeline.split('purlin_run.py" --all --ci', 1)[1]
    assert 'displayName: Run the tests' in tail
    assert '- bash:' not in tail and '- task:' not in tail


# purlin: host PROOF-48
def test_a_project_that_names_windows_alone_gets_one_windows_job():
    assert workflow_module.runners_for(['windows']) == ['windows-latest']
    rendered = workflow_module.render_workflow('github', ['windows'],
                                               PURLIN_REF)
    assert 'os: [windows-latest]' in rendered
    assert 'ubuntu-latest' not in rendered
