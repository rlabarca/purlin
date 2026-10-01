"""The planted bug: one change per proof, in a copy of the project.

A stub from the base commit of `dev/plans/d115-plan.md`: it plants nothing
until the lane `spot` fills it.
"""

STOPPED = ('The audit stopped: %s changed while a break ran. Nothing in the project was '
           'written by the audit.')
SURVIVED = '%s: the test still passes when %s:%d reads "%s"'   # PROOF-N, file, line, the changed line


class ProjectChanged(Exception):
    """Carries the path; audit_run prints STOPPED."""


def break_proof(project_root, feature, proof, tests, scope_files, ask):
    """One planted bug for one proof. `tests` is the proof's own tied tests. `ask(request)`
    is given {'feature','rule','rule_text','proof','proof_text','tests','files'} and
    answers the model's text, or raises ModelUnreachable(reason).
    Returns {'proof','file','line','before','after','result','why','finding'}:
    result 'caught' | 'survived' | 'not made'; finding is SURVIVED filled, or None."""
    return {'result': 'not made', 'why': 'not built yet'}
