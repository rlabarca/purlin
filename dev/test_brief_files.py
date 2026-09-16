"""Tests for the files a review brief leaves in a project.

The brief's JSON is evidence: CI commits it, the rule reads Reviewed because it
exists, and an approval names it. Reading a brief a second time must not rewrite
it, and the text rendering written beside it is a local view that `.gitignore`
keeps out of every commit, in a new project and in one the update migrates.
"""

import copy
import json
import os
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'init'))

import brief as brief_module  # noqa: E402
import update  # noqa: E402
from test_signatures import Project, git, write  # noqa: E402
from test_init_update import LAYOUTS, _project, _read  # noqa: E402

TEMPLATE = os.path.join(ROOT, 'templates', 'gitignore.purlin')


@pytest.fixture
def proved():
    made = Project()
    made.proofs()
    made.record()
    yield made
    made.close()


def _bytes(root, rel):
    with open(os.path.join(root, rel), 'rb') as handle:
        return handle.read()


class TestASecondWrite:

    @pytest.mark.proof("brief", "PROOF-42", "RULE-27", tier="integration")
    def test_when_it_was_built_is_not_a_change(self, proved):
        built = brief_module.build_brief(proved.root, None, 'login', 'RULE-1')
        path = brief_module.write_brief(proved.root, built)
        first = _bytes(proved.root, path)
        again = copy.deepcopy(built)
        again['generated_at'] = '2031-01-01T00:00:00Z'
        again['state'] = 'Reviewed'
        again['record'] = '.purlin/records/login/20310101T000000Z-abc1234-ci.json'
        assert brief_module.write_brief(proved.root, again) == path
        assert _bytes(proved.root, path) == first, \
            'a brief with the same evidence rewrote the committed file'

    @pytest.mark.proof("brief", "PROOF-43", "RULE-27", tier="integration")
    def test_a_changed_verdict_is_written(self, proved):
        built = brief_module.build_brief(proved.root, None, 'login', 'RULE-1')
        path = brief_module.write_brief(proved.root, built)
        assert json.loads(_bytes(proved.root, path))['verdict'] != 'rewrite the proof'
        changed = copy.deepcopy(built)
        changed['verdict'] = 'rewrite the proof'
        brief_module.write_brief(proved.root, changed)
        assert json.loads(_bytes(proved.root, path))['verdict'] == 'rewrite the proof'


class TestTheTextRenderingIsIgnored:

    @pytest.mark.proof("scaffold", "PROOF-41", "RULE-41", tier="integration")
    def test_the_template_keeps_the_rendering_out_of_git(self, tmp_path):
        root = str(tmp_path)
        git(root, 'init', '-q')
        with open(TEMPLATE, encoding='utf-8') as handle:
            write(os.path.join(root, '.gitignore'), handle.read())
        stem = os.path.join(root, 'specs', 'auth', 'login.signatures',
                            'RULE-1.0123abcd.brief')
        write(stem + '.json', '{}\n')
        write(stem + '.txt', 'login RULE-1\n')
        status = subprocess.run(
            ['git', 'status', '--porcelain', '--untracked-files=all'],
            cwd=root, capture_output=True, text=True).stdout
        assert 'specs/auth/login.signatures/RULE-1.0123abcd.brief.json' in status
        assert '.brief.txt' not in status, status


@pytest.mark.parametrize('layout', LAYOUTS)
@pytest.mark.proof("update", "PROOF-22", "RULE-22")
def test_the_update_adds_the_rendering_to_gitignore(tmp_path, layout):
    root = _project(tmp_path, layout)
    write(os.path.join(root, '.gitignore'),
          '.purlin/runtime/\n.purlin/report-data.js\n.purlin/report-stamp.js\n')
    assert 'untracked-files' in [item['id'] for item in update.pending(root)]
    assert update.main(['--yes', '--project-root', root]) == 0
    lines = _read(root, '.gitignore').splitlines()
    assert lines.count('*.brief.txt') == 1, lines
    assert 'untracked-files' not in [item['id'] for item in update.pending(root)]
