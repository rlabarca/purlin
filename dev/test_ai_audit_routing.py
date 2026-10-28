"""The model the audit's planted bugs are written on: `ai_audit` RULE-92.

The model is read from a project's routing files in a temporary folder, and
the start of `claude` is a fake runner that keeps its command line, so no
model is asked.
"""

import json
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

import ai_audit  # noqa: E402


def routing(root, body, local=None):
    os.makedirs(os.path.join(root, '.purlin'), exist_ok=True)
    with open(os.path.join(root, '.purlin', 'routing.json'), 'w',
              encoding='utf-8') as handle:
        json.dump(body, handle)
    if local is not None:
        with open(os.path.join(root, '.purlin', 'routing.local.json'), 'w',
                  encoding='utf-8') as handle:
            json.dump(local, handle)


ON = {'schema': 'purlin-routing/1', 'enabled': True}


# purlin: ai_audit PROOF-217
def test_the_planted_bug_model_is_the_performance_tiers(tmp_path):
    root = str(tmp_path)
    assert ai_audit.planted_bug_model(root) is None
    routing(root, dict(ON, tiers={}))
    assert ai_audit.planted_bug_model(root) == 'opus'
    routing(root, dict(ON, tiers={'performance': 'sonnet'}))
    assert ai_audit.planted_bug_model(root) == 'sonnet'
    routing(root, dict(ON, tiers={'performance': 'sonnet'}),
            local={'tiers': {'performance': 'haiku'}})
    assert ai_audit.planted_bug_model(root) == 'haiku'
    routing(root, dict(ON, enabled=False, tiers={'performance': 'sonnet'}))
    assert ai_audit.planted_bug_model(root) is None


# purlin: ai_audit PROOF-218
def test_the_audit_starts_claude_with_the_routed_model(tmp_path,
                                                        monkeypatch):
    root = str(tmp_path)
    routing(root, dict(ON, tiers={'performance': 'sonnet'}))
    started = []

    def runner(argv, **_kwargs):
        started.append(list(argv))
        body = {'result': 'No bug.', 'is_error': False,
                'modelUsage': {'claude-sonnet-5-5': {}}}
        return types.SimpleNamespace(returncode=0, stdout=json.dumps(body),
                                     stderr='')

    monkeypatch.setattr(ai_audit, 'model_prompt',
                        lambda *_args, **_kwargs: 'the prompt')
    ai_audit.audit_one(root, {'plant': ()}, 'criteria', command='claude',
                       runner=runner, cwd=root)
    assert len(started) == 1
    argv = started[0]
    assert argv[argv.index('--model') + 1] == 'sonnet'
