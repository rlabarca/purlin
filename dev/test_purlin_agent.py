"""What the agent definition, `agents/purlin.md`, must name.

One test per proof of `specs/instructions/purlin_agent.md`. The readers are
in `dev/skill_checks.py`.
"""

from skill_checks import AGENT, not_named, read, sentences_with

COMMANDS = ('sync_status', 'purlin:drift', 'purlin:spec', 'purlin:build',
            'purlin:test', 'purlin:test --all --commit',
            'purlin:test --remote', 'purlin:status', 'purlin:audit',
            'purlin:sign')
FILES = ('references/glossary.md', 'references/evidence_and_signoff.md',
         'references/spec_quality_guide.md',
         'references/formats/marker_format.md',
         '.purlin/evidence/<source>/<name>.json')


# purlin: purlin_agent PROOF-49
def test_the_agent_definition_holds_each_command_and_file():
    assert not_named(read(AGENT), COMMANDS + FILES) == []


# purlin: purlin_agent PROOF-50
def test_one_sentence_names_a_worktree_merging_the_status_and_the_main_checkout():
    found = sentences_with(
        AGENT, ('worktree', 'merge', 'purlin:status', 'main checkout'))
    assert len(found) == 1, found
