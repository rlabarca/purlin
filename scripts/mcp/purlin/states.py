"""The seven states of a rule, and the rollups over them.

    Drafted      no proof
    Proof ready  the proof text passes the free checks
    Tested       a tagged test passes locally
    Recorded     a record that counts under the gate exists at HEAD and passes
    Reviewed     a brief exists for the current hashes
    Approved     a current approval exists and the record passes
    Stale        the rule, the proof or the test changed after the approval

A separate flag, `re_verify_pending`, means only the code changed: the
approval stands and CI clears it on the next run.

`rule_state(inp, cfg)` takes one rule's evidence and the resolved gate, and
returns a dict:

    {'state': 'Recorded',
     'flags': {'re_verify_pending': False, 'auto_approvable': True,
               'needs_ai_review': False},
     'missing_env': ['windows'],
     'reasons': ['windows: no record yet']}

`missing_env` names the operating systems a proof asked for and no record
supplied, so the rollup can say "windows: no record yet" rather than adding an
eighth state.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import checks, gate as gate_module

DRAFTED = 'Drafted'
PROOF_READY = 'Proof ready'
TESTED = 'Tested'
RECORDED = 'Recorded'
REVIEWED = 'Reviewed'
APPROVED = 'Approved'
STALE = 'Stale'

# Stale sorts lowest: a feature holding one is the feature a person must look
# at first, whatever the rest of its rules reached.
STATE_ORDER = (STALE, DRAFTED, PROOF_READY, TESTED, RECORDED, REVIEWED, APPROVED)
STATES = STATE_ORDER


def _rank(state):
    try:
        return STATE_ORDER.index(state)
    except ValueError:
        return 0


def rule_state(inp, cfg):
    """The state and flags of one rule.

    `inp` carries:

    `proofs`        `[{'id', 'tier', 'env', 'text', 'findings'}, ...]`
    `local_status`  `{proof_id: 'pass' | 'fail' | None}` from the runtime files
    `records`       `{os_or_None: record}`, already filtered to the records
                    that count under the gate
    `head`          the sha the working tree is on
    `scope_tree`    the current scope tree of the rule's spec
    `approvals`     every approval file for this rule
    `rule_hash`, `proof_hash`, `test_hash`, `design_hash`, `risk`
    `brief`         the review brief for this rule, or None
    `test_strength` an integer percent, or None when nothing measured it
    """
    proofs = inp.get('proofs') or []
    risk = inp.get('risk') or 'low'
    approvals = inp.get('approvals') or []
    records = inp.get('records') or {}
    head = inp.get('head')
    reasons = []

    current_approvals = [a for a in approvals if _approval_current(a, inp)]

    passes, missing_env, at_head, scope_matches = _record_verdict(
        proofs, records, head, inp.get('scope_tree'))
    for env in missing_env:
        reasons.append('%s: no record yet' % env)

    # A record describes the current commit when it observed that commit, or
    # when the scoped files still hash to what it recorded. The second is what
    # makes the first usable at all: CI writes its record as a commit of its
    # own on top of the one it observed, so a record is almost never at the
    # literal HEAD and the scope tree is the honest comparison.
    current = at_head or scope_matches
    re_verify_pending = bool(passes and current_approvals and not current)

    flags = {
        're_verify_pending': re_verify_pending,
        'auto_approvable': _auto_approvable(inp, cfg, passes, proofs),
        'needs_ai_review': _needs_ai_review(inp, cfg, approvals,
                                            current_approvals),
    }

    if approvals and not current_approvals:
        return _result(STALE, flags, missing_env, reasons)

    if current_approvals and passes:
        return _result(APPROVED, flags, missing_env, reasons)

    brief = inp.get('brief')
    if brief and _brief_matches(brief, inp):
        return _result(REVIEWED, flags, missing_env, reasons)

    if passes and current:
        return _result(RECORDED, flags, missing_env, reasons)

    if proofs and _local_passes(proofs, inp.get('local_status') or {}):
        return _result(TESTED, flags, missing_env, reasons)

    if proofs and not any(checks.blocks_proof_ready(p.get('findings') or [])
                          for p in proofs):
        return _result(PROOF_READY, flags, missing_env, reasons)

    return _result(DRAFTED, flags, missing_env, reasons)


def _result(state, flags, missing_env, reasons):
    return {'state': state, 'flags': flags,
            'missing_env': list(missing_env), 'reasons': reasons}


def _approval_current(approval, inp):
    from purlin import approvals as approvals_module
    return approvals_module.is_current(
        approval, inp.get('rule_hash'), inp.get('proof_hash'),
        inp.get('test_hash'), inp.get('risk') or 'low',
        inp.get('design_hash'))


def _brief_matches(brief, inp):
    from purlin import approvals as approvals_module
    expected = approvals_module.triple_hash(
        inp.get('rule_hash'), inp.get('proof_hash'), inp.get('test_hash'))
    return brief.get('triple_hash') == expected


def _record_verdict(proofs, records, head, scope_tree):
    """`(passes, missing_env, at_head, scope_matches)` over the records.

    A proof with no `@env` is satisfied by any record. A proof with `@env` is
    satisfied only by a record from that operating system, so a rule whose
    proofs name two systems needs both.
    """
    if not proofs or not records:
        return False, [], False, False

    from purlin import records as records_module

    missing_env = []
    passes = True
    used = []
    for proof in proofs:
        env = proof.get('env')
        candidates = ([records[env]] if env in records
                      else [] if env else list(records.values()))
        if env and env not in records:
            missing_env.append(env)
            passes = False
            continue
        proved = False
        for record in candidates:
            if records_module.proof_statuses(record).get(proof.get('id')) == 'pass':
                proved = True
                used.append(record)
                break
        if not proved:
            passes = False
    if not used:
        return False, sorted(set(missing_env)), False, False
    at_head = all(records_module.at_head(record, head) for record in used)
    scope_matches = all(
        not scope_tree or not record.get('scope_tree')
        or record.get('scope_tree') == scope_tree for record in used)
    return passes, sorted(set(missing_env)), at_head, scope_matches


def _local_passes(proofs, local_status):
    """True when every proof of the rule passed in the last local test run."""
    if not local_status:
        return False
    for proof in proofs:
        if local_status.get(proof.get('id')) != 'pass':
            return False
    return True


def _auto_approvable(inp, cfg, passes, proofs):
    """Low risk, a passing record, and test strength at or above the minimum.

    A project with no breaks engine has no strength to compare, so the free
    checks stand in for it: nothing else would ever auto-approve there.
    """
    if (inp.get('risk') or 'low') != 'low' or not passes:
        return False
    strength = inp.get('test_strength')
    if strength is None:
        return not any(checks.blocks_proof_ready(p.get('findings') or [])
                       for p in proofs)
    return strength >= (cfg.min_strength if cfg else 0)


def _needs_ai_review(inp, cfg, approvals, current_approvals):
    """Whether a rule goes on the review list for a model to read first."""
    if cfg is None:
        return False
    risk = inp.get('risk') or 'low'
    threshold = cfg.ai_review_at
    if not inp.get('mutation_engine_available', True):
        threshold = gate_module.one_level_lower(threshold)
    if gate_module.risk_at_or_above(risk, threshold):
        return True
    if approvals and not current_approvals:
        return True
    strength = inp.get('test_strength')
    if strength is not None and strength < cfg.min_strength:
        return True
    return False


# ---------------------------------------------------------------------------
# Rollups
# ---------------------------------------------------------------------------

def feature_rollup(rule_results, latest_record=None, test_strength=None):
    """One feature's rollup over `{rule_ref: rule_state result}`.

    Carries the count per state, the lowest state any rule reached, how many
    rules are Stale or re-verify pending, the counts by risk, and the latest
    record.
    """
    counts = {state: 0 for state in STATE_ORDER}
    by_risk = {}
    stale = 0
    pending = 0
    review_needed = 0
    missing_env = set()
    for result in rule_results.values():
        state = result.get('state', DRAFTED)
        counts[state] = counts.get(state, 0) + 1
        risk = result.get('risk', 'low')
        by_risk.setdefault(risk, {}).setdefault(state, 0)
        by_risk[risk][state] += 1
        if state == STALE:
            stale += 1
        flags = result.get('flags') or {}
        if flags.get('re_verify_pending'):
            pending += 1
        if flags.get('needs_ai_review'):
            review_needed += 1
        missing_env.update(result.get('missing_env') or ())
    total = len(rule_results)
    lowest = None
    for state in STATE_ORDER:
        if counts.get(state):
            lowest = state
            break
    proved = sum(counts.get(state, 0)
                 for state in (TESTED, RECORDED, REVIEWED, APPROVED))
    return {
        'rules': total,
        'proved': proved,
        'counts': {state: counts[state] for state in STATE_ORDER if counts[state]},
        'lowest_state': lowest or DRAFTED,
        'stale': stale,
        're_verify_pending': pending,
        'needs_review': review_needed,
        'by_risk': by_risk,
        'missing_env': sorted(missing_env),
        'test_strength': test_strength,
        'latest_record': latest_record,
    }


def project_rollup(feature_rollups):
    """The project's rollup: one count per state, plus the totals."""
    counts = {state: 0 for state in STATE_ORDER}
    rules = 0
    stale = 0
    pending = 0
    review_needed = 0
    for rollup in feature_rollups.values():
        rules += rollup.get('rules', 0)
        stale += rollup.get('stale', 0)
        pending += rollup.get('re_verify_pending', 0)
        review_needed += rollup.get('needs_review', 0)
        for state, count in (rollup.get('counts') or {}).items():
            counts[state] = counts.get(state, 0) + count
    lowest = None
    for state in STATE_ORDER:
        if counts.get(state):
            lowest = state
            break
    return {
        'features': len(feature_rollups),
        'rules': rules,
        'counts': {state: counts[state] for state in STATE_ORDER if counts[state]},
        'lowest_state': lowest or DRAFTED,
        'stale': stale,
        're_verify_pending': pending,
        'needs_review': review_needed,
    }


def lowest(states):
    """The lowest state in an iterable, by `STATE_ORDER`."""
    found = list(states)
    if not found:
        return DRAFTED
    return min(found, key=_rank)
