"""The spec status and the three evidence levels of a rule.

One rule, read top to bottom. Each row below is a cell, and the project's gate
decides how many rows exist: a cell above the gate is absent, not empty.

    spec    Met when the proof text clears the blocking free checks.
            `drafted` no proof line names the rule, or a blocking finding
            stands against the proof text; `ready` otherwise.

    passed  Met when every proof has a passing test from a source that counts
            under the gate, and that pass describes the current checkout.
            `passed`, `failed`, `no test`, `not run`, `code changed`.

    strong  Met when the tests are worth trusting: test strength at or above
            the project minimum, no finding standing against the proof text or
            the test body, a settled model review where the risk asks for one,
            and nobody holding the rule.
            `strong`, `weak`, `needs a person`.

    signed  Met when a named person signed the rule, proof and test hashes,
            or when the rule's risk is below `sign_at` and no hold is current.
            `signed`, `unsigned`, `stale`, `held`, `not required`.

Each cell carries its reasons, so a surface never has to work out why a word
reads the way it does.

`rule_cells(inp, cfg)` takes one rule's evidence and the resolved gate, and
returns:

    {'spec': 'ready',
     'cells': {'passed': {...}, 'strong': {...}},
     'bucket': 'strong',
     'meets_gate': True,
     'blocked_by': None,
     'flags': {'failing': False, 'stale': False, 'held': False,
               'needs_person': False, 'code_changed': False}}

A rule's **bucket** is the one tile it is counted in, and the two flags
`stale` and `held` are counted beside the buckets, never instead of them.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import checks, gate as gate_module

# The three cells, in the order the chain reads them. A gate value names the
# deepest cell that exists, so the names are the gate values.
CELLS = ('passed', 'strong', 'signed')

# The one tile a rule is counted in, weakest first.
BUCKETS = ('untested', 'failing', 'passed', 'strong', 'signed')

# The two flags counted beside the buckets, and the two counted only in a rule.
FLAGS = ('failing', 'stale', 'held', 'needs_person', 'code_changed')

# Where a pass came from, most trusted first.
SOURCES = ('ci', 'developer', 'local')

DRAFTED = 'drafted'
READY = 'ready'


def cells_for(gate):
    """The cells that exist under `gate`, `passed` first."""
    if gate not in CELLS:
        gate = CELLS[0]
    return CELLS[:CELLS.index(gate) + 1]


def bucket_keys(gate):
    """The bucket names a rollup counts under `gate`."""
    keys = ['untested', 'failing', 'passed']
    if gate in ('strong', 'signed'):
        keys.append('strong')
    if gate == 'signed':
        keys.append('signed')
    return keys


def spec_status(proofs):
    """`ready` when a proof names the rule and no blocking finding stands."""
    if not proofs:
        return DRAFTED
    if any(checks.blocks_ready(proof.get('findings') or [])
           for proof in proofs):
        return DRAFTED
    return READY


def rule_cells(inp, cfg):
    """The spec status, the cells, the bucket and the flags of one rule.

    `inp` carries:

    `proofs`        `[{'id', 'tier', 'env', 'text', 'findings', 'tests'}, ...]`
    `local_status`  `{proof_id: 'pass' | 'fail' | None}` from the runtime files
    `records`       `{os_or_None: record}`, already filtered to the records
                    that count under the gate
    `uncounted`     `{os_or_None: record}`, the records that do not
    `head`          the sha the working tree is on
    `scope_tree`    the current scope tree of the rule's spec
    `signatures`    every signature file for this rule, each carrying `counts`
                    and `count_reason` from `signatures.counts`
    `holds`         every hold a person committed for this rule
    `rule_hash`, `proof_hash`, `test_hash`, `design_hash`, `risk`
    `brief`         the brief for this rule's current hashes, or None
    `brief_path`    where that brief was read from, or None
    `test_strength` an integer percent, or None when nothing measured it
    """
    gate = cfg.gate if cfg else CELLS[0]
    proofs = inp.get('proofs') or []
    spec = spec_status(proofs)

    holds = [hold for hold in inp.get('holds') or () if _binds(hold, inp)]
    signatures = list(inp.get('signatures') or ())
    current = [sig for sig in signatures if _binds(sig, inp)]
    counting = [sig for sig in current if sig.get('counts')]

    passed = _passed_cell(inp, cfg)
    strong = _strong_cell(inp, cfg, passed, holds, counting)
    signed = _signed_cell(inp, cfg, holds, signatures, current, counting)

    cells = {}
    for name, cell in (('passed', passed), ('strong', strong),
                       ('signed', signed)):
        if name in cells_for(gate):
            cells[name] = cell

    flags = {
        'failing': passed['word'] == 'failed',
        'code_changed': passed['word'] == 'code changed',
        # A hold and a signature are facts about committed files, so they are
        # read the same at every gate. Needing a person is the strong cell's
        # word, and that cell does not exist under `passed`.
        'held': bool(holds) and not counting,
        'stale': bool(signatures) and not current,
        'needs_person': (gate != 'passed'
                         and strong['word'] == 'needs a person'
                         and not (holds and not counting)),
    }

    met = _met(spec, cells, gate)
    return {
        'spec': spec,
        'cells': cells,
        'bucket': _bucket(spec, cells, gate, passed, strong, signed),
        'meets_gate': met,
        'blocked_by': _blocked_by(spec, cells, gate),
        'flags': flags,
    }


# ---------------------------------------------------------------------------
# The passed cell
# ---------------------------------------------------------------------------

def _passed_cell(inp, cfg):
    """Level 1: every proof has a passing test from a counting source.

    A `@manual` proof declares that no test is written for it and no proof
    entry is ever produced, so level 1 has no question to ask of it: it is
    read out here and the question moves to level 2, where `needs a person` is
    the honest word and a signature with a note is the evidence.
    """
    gate = cfg.gate if cfg else CELLS[0]
    written = inp.get('proofs') or []
    proofs = [proof for proof in written
              if (proof.get('tier') or '') != 'manual']
    records = inp.get('records') or {}
    local_status = inp.get('local_status') or {}
    cell = {'word': 'no test', 'source': None, 'current': False,
            'counts': False, 'missing_env': [], 'reasons': []}

    if written and not proofs:
        cell.update({'word': 'passed', 'current': True, 'counts': True})
        return cell

    failing = _failing_where(proofs, records, local_status)
    if failing:
        cell['word'] = 'failed'
        cell['reasons'] = ['failing: %s' % where for where in failing]
        label = _label_of(records) or 'local'
        cell['source'] = label
        cell['current'] = True
        cell['counts'] = True
        return cell

    passes, missing_env, at_head, scope_matches = _record_passes(
        proofs, records, inp.get('head'), inp.get('scope_tree'))
    if passes or missing_env:
        cell['source'] = _label_of(records)
        cell['counts'] = True
        current = at_head or scope_matches
        if missing_env:
            cell['word'] = 'not run'
            cell['missing_env'] = list(missing_env)
            cell['current'] = current
            cell['reasons'] = ['%s: no record yet' % env for env in missing_env]
            return cell
        if current:
            cell['word'] = 'passed'
            cell['current'] = True
            return cell
        cell['word'] = 'code changed'
        cell['current'] = False
        head = inp.get('head') or ''
        commit = _record_commit(records) or head
        cell['reasons'] = ['code changed since %s' % (commit or '')[:7]]
        return cell

    # Nothing that counts passed. A record the gate does not read, and then
    # this checkout's own run, each say what they are and why they do not
    # count, because "no test" would be a different and wrong answer.
    uncounted = inp.get('uncounted') or {}
    if uncounted:
        would_pass, _env, at_head, scope_matches = _record_passes(
            proofs, uncounted, inp.get('head'), inp.get('scope_tree'))
        if would_pass:
            label = _label_of(uncounted)
            cell['word'] = 'not run'
            cell['source'] = label
            cell['current'] = at_head or scope_matches
            cell['reasons'] = ['%s record does not count under %s'
                               % (label, gate)]
            return cell

    if proofs and _local_passes(proofs, local_status):
        cell['source'] = 'local'
        cell['current'] = True
        if gate == CELLS[0]:
            cell['word'] = 'passed'
            cell['counts'] = True
        else:
            cell['word'] = 'not run'
            cell['reasons'] = ['local run does not count under %s' % gate]
        return cell

    if any(proof.get('tests') for proof in proofs):
        cell['word'] = 'not run'
    return cell


def _label_of(records):
    """The least trusted label among the records a pass was read from."""
    labels = [record.get('label') for record in (records or {}).values()
              if record.get('label')]
    if not labels:
        return None
    return max(labels, key=lambda name: SOURCES.index(name)
               if name in SOURCES else len(SOURCES))


def _record_commit(records):
    for record in (records or {}).values():
        if record.get('commit'):
            return record['commit']
    return None


def _failing_where(proofs, records, local_status):
    """Where a test backing the rule last failed: each record, then this checkout.

    A cell says what the evidence shows, and a failing test is the one thing a
    word like `no test` would hide, so the failure itself is named here. A
    proof tagged `@env` is read only from that operating system's record.
    """
    from purlin import records as records_module

    where = []
    for os_name in sorted(records or {}, key=lambda name: name or ''):
        statuses = records_module.proof_statuses(records[os_name])
        for proof in proofs or ():
            if proof.get('env') and proof.get('env') != os_name:
                continue
            if statuses.get(proof.get('id')) == 'fail':
                where.append('%s record' % (os_name or 'the'))
                break
    if any(local_status.get(proof.get('id')) == 'fail' for proof in proofs or ()):
        where.append('this checkout')
    return where


def _record_passes(proofs, records, head, scope_tree):
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
    # A record describes the current commit when it observed that commit, or
    # when the scoped files still hash to what the record named. The second is
    # what makes the first usable at all: CI writes its record as a commit of
    # its own on top of the one it observed, so a record is almost never at the
    # literal HEAD and the scope tree is the honest comparison.
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


# ---------------------------------------------------------------------------
# The strong cell
# ---------------------------------------------------------------------------

def _strong_cell(inp, cfg, passed, holds, counting_signatures):
    """Level 2: whether the tests behind a met passed cell are worth trusting."""
    strength = inp.get('test_strength')
    cell = {'word': 'weak', 'strength': strength, 'findings': [],
            'observations': [], 'brief': None, 'settled': None, 'reasons': []}

    if passed['word'] != 'passed':
        cell['reasons'] = ['not passed']
        return cell

    proofs = inp.get('proofs') or []
    findings = _findings(proofs)
    brief = inp.get('brief') or None
    if brief:
        cell['brief'] = inp.get('brief_path')
        cell['observations'] = [str(line) for line in
                                (brief.get('observations') or ())]
        cell['settled'] = brief.get('settled')
        for finding in _test_findings(brief):
            if finding not in findings:
                findings.append(finding)
    cell['findings'] = findings

    min_strength = cfg.min_strength if cfg else None
    notes = []
    if strength is None:
        # Nothing measured a strength, so the free checks are the whole of
        # what level 2 has to read, and the cell says so.
        notes.append('no engine: free checks only')
        cell['word'] = ('weak' if checks.blocks_ready(findings) else 'strong')
    elif min_strength is not None and strength < min_strength:
        notes.append('strength %d%% under %d%%' % (round(strength), min_strength))
        cell['word'] = 'weak'
    else:
        cell['word'] = 'strong'
    if _test_findings(brief):
        cell['word'] = 'weak'

    person = _needs_person(inp, cfg, brief, holds, counting_signatures)
    if person:
        cell['word'] = 'needs a person'

    # A cell that reads `strong` names only what a reader could not work out
    # from the word: nothing at all where an engine measured the strength.
    reasons = list(person) + list(notes)
    if cell['word'] != 'strong':
        for finding in findings:
            if finding not in reasons:
                reasons.append(finding)
    cell['reasons'] = reasons
    return cell


def _needs_person(inp, cfg, brief, holds, counting_signatures):
    """The reasons level 2 cannot be settled without a person.

    A signature for the current hashes outranks every one of them: under
    `strong` a signature from anyone counts, because what it clears there is a
    question the machine could not settle.
    """
    if counting_signatures:
        return []
    if holds:
        return ['held by %s: %s' % (hold.get('signer') or hold.get('holder')
                                    or 'a person', hold.get('reason') or '')
                for hold in holds]
    reasons = []
    if any((proof.get('tier') or '') == 'manual' for proof in
           inp.get('proofs') or ()):
        reasons.append('manual proof')
    risk = inp.get('risk') or 'low'
    threshold = review_threshold(
        cfg, inp.get('mutation_engine_available', True))
    if gate_module.risk_at_or_above(risk, threshold):
        if not brief:
            reasons.append('no brief for the current hashes')
        elif brief.get('settled') is not True:
            reasons.append('review not settled')
        else:
            reasons.extend(str(line) for line in
                           (brief.get('observations') or ()))
    return reasons


def _findings(proofs):
    """Every free-check finding on the rule's proof text, deduped, in order."""
    found = []
    for proof in proofs or ():
        for finding in proof.get('findings') or ():
            if finding not in found:
                found.append(finding)
    return found


def _test_findings(brief):
    """The findings a brief raised against a test body, deduped, in order."""
    found = []
    for test in (brief or {}).get('tests') or ():
        for finding in test.get('findings') or ():
            if finding and finding != 'manual' and finding not in found:
                found.append(finding)
    return found


def review_threshold(cfg, mutation_engine_available=True):
    """The risk at or above which a rule's own risk asks for a model review.

    With no break engine the threshold drops one level, so more rules get a
    look rather than fewer. The brief asks the same question when it decides
    which rules to write, so the answer is computed here once.
    """
    if cfg is None:
        return None
    threshold = cfg.ai_review_at
    if not mutation_engine_available:
        threshold = gate_module.one_level_lower(threshold)
    return threshold


# ---------------------------------------------------------------------------
# The signed cell
# ---------------------------------------------------------------------------

def _signed_cell(inp, cfg, holds, signatures, current, counting):
    """Level 3: what the signature files say, whatever the cells below read.

    A signature is a fact about committed files, so this cell is computed from
    them alone. Whether the rule needed one is `required`.
    """
    risk = inp.get('risk') or 'low'
    sign_at = cfg.sign_at if cfg else None
    required = gate_module.risk_at_or_above(risk, sign_at)
    cell = {'word': 'not required', 'required': required, 'signer': None,
            'path': None, 'reasons': []}

    if counting:
        signature = counting[0]
        cell['word'] = 'signed'
        cell['signer'] = signature.get('signer')
        cell['path'] = signature.get('path')
        cell['reasons'] = ['by %s' % signature.get('signer')]
        return cell

    if holds:
        hold = holds[0]
        cell['word'] = 'held'
        cell['path'] = hold.get('path')
        cell['reasons'] = ['held by %s: %s'
                           % (hold.get('signer') or hold.get('holder')
                              or 'a person', hold.get('reason') or '')]
        return cell

    if current:
        signature = current[0]
        cell['word'] = 'unsigned'
        cell['signer'] = signature.get('signer')
        cell['path'] = signature.get('path')
        reason = signature.get('count_reason')
        cell['reasons'] = [reason] if reason else []
        return cell

    if signatures:
        signature = signatures[0]
        cell['word'] = 'stale'
        cell['signer'] = signature.get('signer')
        cell['path'] = signature.get('path')
        cell['reasons'] = ['hashes changed after the signature']
        return cell

    if required:
        cell['word'] = 'unsigned'
    return cell


def _binds(signature, inp):
    """True when a signature or a hold still binds the rule's current hashes."""
    from purlin import signatures as signatures_module
    return signatures_module.is_current(
        signature, inp.get('rule_hash'), inp.get('proof_hash'),
        inp.get('test_hash'), inp.get('risk') or 'low',
        inp.get('design_hash'))


# ---------------------------------------------------------------------------
# Meeting the gate
# ---------------------------------------------------------------------------

def cell_is_met(name, cell):
    """True when one cell reads a word that meets its level."""
    if not cell:
        return False
    if name == 'passed':
        return cell['word'] == 'passed'
    if name == 'strong':
        return cell['word'] == 'strong'
    return cell['word'] in ('signed', 'not required')


def _met(spec, cells, gate):
    if spec != READY:
        return False
    return all(cell_is_met(name, cells.get(name)) for name in cells_for(gate))


def _blocked_by(spec, cells, gate):
    """The lowest cell that is not met, or None when the rule meets the gate."""
    if spec != READY:
        return 'spec'
    for name in cells_for(gate):
        if not cell_is_met(name, cells.get(name)):
            return name
    return None


def _bucket(spec, cells, gate, passed, strong, signed):
    """The one tile a rule is counted in."""
    if passed['word'] == 'failed':
        return 'failing'
    if spec != READY or not cell_is_met('passed', passed):
        return 'untested'
    if gate == 'passed' or not cell_is_met('strong', strong):
        return 'passed'
    if gate == 'strong' or not cell_is_met('signed', signed):
        return 'strong'
    return 'signed'


# ---------------------------------------------------------------------------
# Rollups
# ---------------------------------------------------------------------------

def feature_rollup(rule_results, gate='passed', latest_record=None,
                   test_strength=None):
    """One feature's rollup over `{rule_ref: rule_cells result}`.

    Carries how many rules the feature has, how many meet the gate, one count
    per bucket the gate reaches, the stale, held and needs-a-person counts,
    the latest record and the test strength.
    """
    keys = bucket_keys(gate)
    counts = {key: 0 for key in keys}
    met = 0
    stale = held = needs_person = 0
    for result in rule_results.values():
        bucket = result.get('bucket') or 'untested'
        if bucket not in counts:
            # A bucket above the gate cannot be reached, so it is not counted
            # under a name the rollup does not carry.
            bucket = keys[-1]
        counts[bucket] += 1
        if result.get('meets_gate'):
            met += 1
        flags = result.get('flags') or {}
        stale += 1 if flags.get('stale') else 0
        held += 1 if flags.get('held') else 0
        needs_person += 1 if flags.get('needs_person') else 0
    rollup = {'rules': len(rule_results), 'met': met}
    rollup.update(counts)
    rollup.update({'stale': stale, 'held': held, 'needs_person': needs_person,
                   'test_strength': test_strength,
                   'latest_record': latest_record})
    return rollup


def project_rollup(feature_rollups, gate='passed'):
    """The project's summary: the same counts, plus how many features there are."""
    keys = bucket_keys(gate)
    summary = {'features': len(feature_rollups), 'rules': 0, 'met': 0}
    for key in keys:
        summary[key] = 0
    for name in ('stale', 'held', 'needs_person'):
        summary[name] = 0
    for rollup in feature_rollups.values():
        for key in ('rules', 'met', 'stale', 'held', 'needs_person'):
            summary[key] += rollup.get(key, 0)
        for key in keys:
            summary[key] += rollup.get(key, 0)
    return summary
