"""The audit's run: the spot tests, the planted bugs, the model's reading.

A stub from the base commit of `dev/plans/d115-plan.md`: it reads nothing and
answers 0 until the lane `audit` fills it.
"""


def run(project_root, features, selected, again=False, out=None):
    """For each rule the audit reads (ai_audit RULE-1; `again` reads every passing rule):
    the spot tests, then one planted bug per proof that needs one, then the model's
    reading. Writes one audit.rules entry per rule read, through evidence.write_audit;
    writes .purlin/runtime/audit_run.json; prints the findings, the cost line and, last,
    the share. Returns 0, or 1 when a planted bug stopped it (planted_bug RULE-6)."""
    return 0
