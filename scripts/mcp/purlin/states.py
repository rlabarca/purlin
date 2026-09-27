"""The spec status and the three evidence levels of a rule.

One rule, read top to bottom. Each row below is a cell, and the project's gate
decides how many rows exist: a cell above the gate is absent, not empty.

    spec    Met when a proof line names the rule.
            `drafted` no proof line names it; `ready` one or more do. What
            the proof is worth is the audit's question, not this one.

    passed  Met when every proof has a passing test from a source that counts
            under the gate, on every operating system a counting run covered,
            and that pass describes the current checkout.
            `passed`, `partial`, `failed`, `no test`, `not run`,
            `code changed`. The cell carries `platforms`, one entry per
            operating system a counting run covered, and reads `partial` when
            the tests passed on some of them and failed or did not run on
            others. `partial` is not met.

    strong  Met when the tests are worth trusting: test strength at or above
            the project minimum, a settled AI audit that observed nothing
            where the bar asks for one, and nobody holding the rule.
            `strong`, `weak`, `not audited`, `unsettled`, `manual test`,
            `held`.

    signed  Met when a named person signed the rule, proof and test hashes.
            `signed`, `unsigned`, `stale`, `held`. The cell says under
            `required` whether the rule needed one at all.

Every rule carries a **bar**, `passed` or `strong`: the evidence it must have
before it can be signed. A rule tagged `[bar: ...]` carries what it names, and
a rule tagged with none takes the project's gate as its bar. The bar decides
which rules the AI audit runs on, which rules need a signature, and what the
rule has to clear to meet the gate.

Each cell carries its reasons, so a surface never has to work out why a word
reads the way it does.

`rule_cells(inp, cfg)` takes one rule's evidence and the resolved gate, and
returns:

    {'spec': 'ready',
     'cells': {'passed': {...}, 'strong': {...}},
     'bar': 'strong',
     'cleared': True,
     'signable': False,
     'bucket': 'strong',
     'meets_gate': True,
     'blocked_by': None,
     'flags': {'failing': False, 'partial': False, 'stale': False,
               'held': False, 'manual': False, 'unsettled': False,
               'not_audited': False, 'code_changed': False}}

A rule's **bucket** is the one tile it is counted in, and the two flags
`stale` and `held` are counted beside the buckets, never instead of them.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import gate as gate_module

# The three cells, in the order the chain reads them. A gate value names the
# deepest cell that exists, so the names are the gate values.
CELLS = ('passed', 'strong', 'signed')

# The one tile a rule is counted in, weakest first.
BUCKETS = ('untested', 'failing', 'partial', 'passed', 'strong', 'signed')

# The two flags counted beside the buckets, and the four read only on a rule.
# `manual`, `unsettled` and `not_audited` are the three strong-cell words the
# machine cannot move on its own.
FLAGS = ('failing', 'partial', 'stale', 'held', 'manual', 'unsettled',
         'not_audited', 'code_changed')

# The strong cell's words that put a rule in front of a person, and the one
# that waits for the audit instead. `not audited` is on no list: running
# `purlin:audit` settles it.
REVIEW_WORDS = ('manual test', 'unsettled', 'held')
NOT_AUDITED = 'not audited'

# What a brief writes under `ai_review` when no model could be reached. The
# AI audit did not run, so it settled nothing and it observed nothing: the
# strength is the whole of level 2. `scripts/review/brief.py` reads this name
# from here so the two cannot drift.
NO_MODEL = 'not available'

# The flags a rollup counts, beside the buckets and never instead of them.
COUNTED_FLAGS = ('stale', 'held', 'manual', 'unsettled', 'not_audited')

# Where a pass came from, most trusted first. A record's source is the folder
# it sits in, `.purlin/records/ci/` or `.purlin/records/local/`; the test
# results `purlin:test` commits are `local`.
SOURCES = ('ci', 'local')

DRAFTED = 'drafted'
READY = 'ready'


def cells_for(gate):
    """The cells that exist under `gate`, `passed` first."""
    if gate not in CELLS:
        gate = CELLS[0]
    return CELLS[:CELLS.index(gate) + 1]


def bucket_keys(gate):
    """The bucket names a rollup counts under `gate`."""
    keys = ['untested', 'failing', 'partial', 'passed']
    if gate in ('strong', 'signed'):
        keys.append('strong')
    if gate == 'signed':
        keys.append('signed')
    return keys


def spec_status(proofs):
    """`ready` when a proof line names the rule, `drafted` when none does.

    Nothing else is read. A scan of the description used to hold a rule at
    `drafted`, and it was a regular expression deciding what a proof is
    worth from the words alone. That question belongs to the audit, which
    reads the test beside the proof and writes what it saw.
    """
    return READY if proofs else DRAFTED


def rule_cells(inp, cfg):
    """The spec status, the cells, the bucket and the flags of one rule.

    `inp` carries:

    `proofs`        `[{'id', 'manual', 'env', 'text', 'tests'}, ...]`
    `local_status`  `{proof_id: 'pass' | 'fail' | None}` from the runtime files
                    and the committed test results, whichever is newer
    `local_os`      the operating system that local source ran on, or None
    `local_at`      when it ran, ISO 8601 UTC, or None
    `records`       `{os_or_None: record}`, the latest record per platform
    `runs`          `{os: record}`, the test results a remote run committed,
                    read beside the records and never as an audit
    `head`          the sha the working tree is on
    `scope_tree`    the current scope tree of the rule's spec
    `signatures`    every signature file for this rule, each carrying `counts`
                    and `count_reason` from `signatures.counts`
    `holds`         every hold a person committed for this rule
    `rule_hash`, `proof_hash`, `test_hash`, `bar`
    `audit_hash`    the hash of the brief's own evidence, which a signature
                    binds beside the triple
    `brief`         the brief for this rule's current hashes, or None
    `brief_path`    where that brief was read from, or None
    `test_strength` an integer percent, or None when nothing measured it
    """
    gate = cfg.gate if cfg else CELLS[0]
    bar = bar_of(inp.get('bar'), gate)
    proofs = inp.get('proofs') or []
    spec = spec_status(proofs)

    audit = inp.get('audit_hash')
    holds = [hold for hold in inp.get('holds') or ()
             if _binds(hold, inp, bar)]
    signatures = list(inp.get('signatures') or ())
    current = [sig for sig in signatures if _binds(sig, inp, bar, audit)]
    counting = [sig for sig in current if sig.get('counts')]

    passed = _passed_cell(inp, cfg)
    strong = _strong_cell(inp, cfg, bar, passed, holds, counting)
    signed = _signed_cell(inp, cfg, bar, holds, signatures, current, counting)

    cells = {}
    for name, cell in (('passed', passed), ('strong', strong),
                       ('signed', signed)):
        if name in cells_for(gate):
            cells[name] = cell

    flags = {
        'failing': passed['word'] == 'failed',
        'partial': passed['word'] == 'partial',
        'code_changed': passed['word'] == 'code changed',
        # A hold and a signature are facts about committed files, so they are
        # read the same at every gate. `manual test`, `unsettled` and
        # `not audited` are the strong cell's own words, and that cell does
        # not exist under `passed`.
        'held': bool(holds) and not counting,
        'stale': bool(signatures) and not current,
        'manual': gate != 'passed' and strong['word'] == 'manual test',
        'unsettled': gate != 'passed' and strong['word'] == 'unsettled',
        'not_audited': gate != 'passed' and strong['word'] == NOT_AUDITED,
    }

    cleared = _cleared(spec, bar, passed, strong)
    blocked = _blocked_by(spec, cells, gate, bar)
    return {
        'spec': spec,
        'bar': bar,
        'cleared': cleared,
        'signable': bool(cleared and signed.get('required')
                         and signed['word'] != 'signed'),
        'cells': cells,
        'bucket': _bucket(spec, cells, gate, passed, strong, signed),
        'meets_gate': blocked is None,
        'blocked_by': blocked,
        'flags': flags,
    }


def bar_of(bar, gate):
    """The bar a rule carries: the one it tagged, else the project's gate."""
    return bar if bar in gate_module.BARS else gate_module.default_bar(gate)


# ---------------------------------------------------------------------------
# The passed cell
# ---------------------------------------------------------------------------

def _passed_cell(inp, cfg):
    """Level 1: every proof has a passing test from a counting source.

    The question is asked once per operating system a counting run named, and
    each answer goes in `platforms`. Where those answers disagree the cell
    reads `partial`, because a rule whose tests pass on Linux and fail on
    Windows is neither passed nor failed; `partial` is not met, so it blocks
    the gate exactly as a failure does. Where they agree, or where no run
    named an operating system at all, the records and this checkout's own
    run answer as one.

    A `@manual` proof declares that no test is written for it and no proof
    entry is ever produced, so level 1 has no question to ask of it: it is
    read out here and the question moves to level 2, where `manual test` is
    the honest word and a signature with a note is the evidence.
    """
    written = inp.get('proofs') or []
    proofs = [proof for proof in written if not proof.get('manual')]
    records = _runs_and_records(inp.get('records') or {}, inp.get('runs') or {})
    # This checkout's own run is the `local` source, and it counts at every
    # gate: the tests it ran are the tests CI runs.
    local_status = inp.get('local_status') or {}
    cell = {'word': 'no test', 'source': None, 'current': False,
            'counts': False, 'missing_env': [], 'platforms': {},
            'reasons': []}

    if written and not proofs:
        cell.update({'word': 'passed', 'current': True, 'counts': True})
        return cell

    platforms = _platforms(inp, proofs, records)
    cell['platforms'] = platforms
    words = [entry['word'] for entry in platforms.values()]
    if 'passed' in words and any(word != 'passed' for word in words):
        # The platforms disagree, so neither `passed` nor `failed` is true of
        # the rule. `partial` is the only honest word, and it is not met.
        cell['word'] = 'partial'
        cell['source'] = _passing_source(platforms)
        cell['current'] = True
        cell['counts'] = True
        cell['missing_env'] = [name for name in sorted(platforms)
                               if platforms[name].get('source') is None]
        cell['reasons'] = _platform_reasons(platforms)
        return cell

    failing = _failing_where(proofs, records, local_status)
    if failing:
        cell['word'] = 'failed'
        cell['reasons'] = ['failing: %s' % where for where in failing]
        cell['source'] = _label_of(records) or 'local'
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

    # No record answered. This checkout's own run is the last thing to read,
    # and it counts, so a rule whose tests have just run here reads `passed`
    # before any record exists.
    if proofs and _local_passes(proofs, local_status):
        cell['word'] = 'passed'
        cell['source'] = 'local'
        cell['current'] = True
        cell['counts'] = True
        return cell

    if any(proof.get('tests') for proof in proofs):
        cell['word'] = 'not run'
    return cell


def _runs_and_records(records, runs):
    """One map per platform over the records and the committed test results.

    A record an audit wrote and the results a remote run committed are the
    same news about one platform in two files, so the passed cell reads them
    as one thing and the newer answers. They are kept apart everywhere else:
    only an audit measures how good the tests are, and only a record says one
    did.
    """
    if not runs:
        return records
    merged = dict(records)
    for name, run in runs.items():
        held = merged.get(name)
        if held is None or str(run.get('timestamp') or '') >= str(
                held.get('timestamp') or ''):
            merged[name] = run
    return merged


def platform_of(record):
    """The operating system a record observed: its own, else its environment's."""
    return (record or {}).get('os') or (
        (record or {}).get('environment') or {}).get('os')


def _platforms(inp, proofs, records):
    """`{os: {word, source, at}}` over every platform a counting run covered.

    A record names the operating system it ran on, and so do the test results
    `purlin:test` commits, so each is one platform's answer about this rule.
    Where two runs cover one platform the newer answers. A platform a proof
    is tagged for with `@env` and nothing ran on gets an entry too, reading
    `not run` with no source, so the map lists every platform the rule is
    owed an answer from.
    """
    candidates = []
    for record in (records or {}).values():
        name = platform_of(record)
        if not name:
            continue
        candidates.append((name, record.get('timestamp'),
                           record.get('source') or record.get('label'),
                           _word_from_record(proofs, record, name)))
    local_os = inp.get('local_os')
    if local_os and (inp.get('local_status') or {}):
        candidates.append((local_os, inp.get('local_at'), 'local',
                           _word_from_statuses(
                               proofs, inp.get('local_status') or {},
                               local_os)))

    platforms = {}
    for name, at, source, word in candidates:
        if word is None:
            continue
        held = platforms.get(name)
        if held is None or str(at or '') >= str(held.get('at') or ''):
            platforms[name] = {'word': word, 'source': source, 'at': at}
    for proof in proofs:
        env = proof.get('env')
        if env and env not in platforms:
            platforms[env] = {'word': 'not run', 'source': None, 'at': None}
    return platforms


def _word_from_record(proofs, record, os_name):
    """One platform's word for a rule, read off one record, or None."""
    from purlin import records as records_module
    return _word_from_statuses(proofs, records_module.proof_statuses(record),
                               os_name)


def _word_from_statuses(proofs, statuses, os_name):
    """`passed`, `failed` or `not run` for one platform, or None when it is idle.

    A proof tagged `@env` for another operating system is not this platform's
    to answer, so it is left out. A platform with nothing of the rule's to
    observe answers None and is not listed at all.
    """
    mine = [proof for proof in proofs
            if not proof.get('env') or proof.get('env') == os_name]
    if not mine:
        return None
    seen = [statuses.get(proof.get('id')) for proof in mine]
    if not any(seen):
        return None
    if 'fail' in seen:
        return 'failed'
    if all(status == 'pass' for status in seen):
        return 'passed'
    return 'not run'


def _passing_source(platforms):
    """The least trusted source among the platforms that passed."""
    sources = [entry.get('source') for entry in platforms.values()
               if entry.get('word') == 'passed' and entry.get('source')]
    if not sources:
        return None
    return max(sources, key=lambda name: SOURCES.index(name)
               if name in SOURCES else len(SOURCES))


def _platform_reasons(platforms):
    """One reason per platform that did not pass, and one naming those that did."""
    passed = sorted(name for name, entry in platforms.items()
                    if entry.get('word') == 'passed')
    reasons = []
    if passed:
        reasons.append('passed on %s' % ', '.join(passed))
    for name in sorted(platforms):
        entry = platforms[name]
        if entry.get('word') == 'passed':
            continue
        if entry.get('source') is None:
            reasons.append('%s: no record yet' % name)
        else:
            reasons.append('%s: %s' % (name, entry.get('word')))
    return reasons


def _label_of(records):
    """The least trusted source among the records a pass was read from."""
    sources = [record.get('source') or record.get('label')
               for record in (records or {}).values()
               if record.get('source') or record.get('label')]
    if not sources:
        return None
    return max(sources, key=lambda name: SOURCES.index(name)
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

def _strong_cell(inp, cfg, bar, passed, holds, counting_signatures):
    """Level 2: whether the tests behind a met passed cell are worth trusting."""
    strength = inp.get('test_strength')
    cell = {'word': 'weak', 'strength': strength,
            'observations': [], 'brief': None, 'settled': None, 'reasons': []}

    # A hold wins. A person read the brief and said the test does not prove
    # the proof, and that answer stands whatever the tests are doing: a
    # failing test is work in front of the hold, not instead of it. Reading
    # anything else here would leave a held rule off the Review list, which
    # is the one place the hold is meant to appear. A signature for the
    # current hashes outranks it.
    if holds and not counting_signatures:
        cell['word'] = 'held'
        cell['reasons'] = _hold_reasons(holds)
        return cell

    if passed['word'] != 'passed':
        cell['reasons'] = ['not passed']
        return cell

    brief = inp.get('brief') or None
    if brief:
        cell['brief'] = inp.get('brief_path')
        cell['observations'] = [str(line) for line in
                                (brief.get('observations') or ())]
        cell['settled'] = brief.get('settled')

    min_strength = cfg.min_strength if cfg else None
    notes = []
    if strength is None and bar == 'strong' and not brief:
        # The audit is what measures a rule whose bar is `strong`, and
        # `not audited` below is the word for one it has not reached.
        # Nothing is noted here, so the cell does not say it twice.
        pass
    elif strength is None and not inp.get('audited', True):
        # Level 2 asks how good the tests are, and only an audit measures
        # that. With no record of one there is nothing to read, so the cell
        # says the work is outstanding rather than passing the rule on
        # nothing at all.
        notes.append('no audit has run')
        cell['word'] = 'weak'
    elif strength is None:
        # An audit ran and no engine measured a strength, so what level 2 has
        # to read is the audit's own observations. The cell says so rather
        # than leaving a blank where a percentage usually sits.
        notes.append('no engine: nothing measured a strength')
        cell['word'] = 'strong'
    elif min_strength is not None and strength < min_strength:
        notes.append('strength %d%% under %d%%' % (round(strength), min_strength))
        cell['word'] = 'weak'
    else:
        cell['word'] = 'strong'
    # A review that settled and still observed something answered the
    # question: the test does not read what the proof names, which is build
    # work, so the observation lands in the weak cell rather than on a
    # person's list.
    observed = cell['observations'] if cell['settled'] is True else []
    if observed:
        cell['word'] = 'weak'

    word, person = _outstanding(inp, bar, brief, counting_signatures)
    if word:
        cell['word'] = word

    # A cell that reads `strong` names only what a reader could not work out
    # from the word: nothing at all where an engine measured the strength.
    cell['reasons'] = list(person) + list(notes) + list(observed)
    return cell


def _hold_reasons(holds):
    """One reason per current hold: who wrote it and the case they named."""
    return ['held by %s: %s'
            % (hold.get('signer') or hold.get('holder') or 'a person',
               hold.get('reason') or '')
            for hold in holds or ()]


def _outstanding(inp, bar, brief, counting_signatures):
    """`(word, reasons)` when level 2 is not the machine's to settle alone.

    Each word names the work that is outstanding. `manual test` is a proof no
    test can back, `unsettled` is an AI audit that ran and could not tell,
    and `not audited` is a rule the audit has not reached: that one waits for
    `purlin:audit` rather than for a person, which is why it is on no list. A
    hold is read before any of these, in `_strong_cell`. A signature for the
    current hashes outranks them: under `strong` a signature from anyone
    counts, because what it clears there is a question the machine could not
    settle. The word is None when nothing is outstanding.
    """
    if counting_signatures:
        return None, []
    if any(proof.get('manual') for proof in inp.get('proofs') or ()):
        return 'manual test', ['manual proof']
    if bar == 'strong':
        # The AI audit runs on every rule whose bar is `strong` and on no
        # other, so a missing brief here means the audit has not run over
        # this code and the strength beside it is not the question yet.
        if not brief:
            return NOT_AUDITED, ['no audit has run on this code']
        # A brief whose model could not be reached is not an unsettled
        # question: nothing asked one. The audit's other layers answer,
        # as they do where no break engine measured a strength.
        if brief.get('ai_review') in (None, NO_MODEL):
            return None, []
        if brief.get('settled') is not True:
            return 'unsettled', ['the AI audit could not settle']
    return None, []


# ---------------------------------------------------------------------------
# The signed cell
# ---------------------------------------------------------------------------

def _signature_at(signature):
    """When a signature was made: the commit date, else the file's own stamp."""
    return signature.get('committed_at') or signature.get('timestamp')


def _signed_cell(inp, cfg, bar, holds, signatures, current, counting):
    """Level 3: what the signature files say, whatever the cells below read.

    A signature is a fact about committed files. This cell is computed from
    those files alone and reads `signed`, `unsigned`, `stale` or `held`.
    Whether the rule needed one is `required`: true at the gate `signed` when
    `sign_at` is `all` or the rule's bar is `strong`. A rule that needs none
    still says whether anyone signed it, and either answer meets the level.
    """
    gate = cfg.gate if cfg else CELLS[0]
    sign_at = cfg.sign_at if cfg else None
    required = gate_module.needs_signature(gate, sign_at, bar)
    cell = {'word': 'unsigned', 'required': required, 'signer': None,
            'at': None, 'path': None, 'reasons': []}

    if counting:
        signature = counting[0]
        cell['word'] = 'signed'
        cell['signer'] = signature.get('signer')
        cell['at'] = _signature_at(signature)
        cell['path'] = signature.get('path')
        cell['reasons'] = ['by %s' % signature.get('signer')]
        return cell

    if holds:
        hold = holds[0]
        cell['word'] = 'held'
        cell['path'] = hold.get('path')
        cell['reasons'] = _hold_reasons([hold])
        return cell

    if current:
        signature = current[0]
        cell['word'] = 'unsigned'
        cell['signer'] = signature.get('signer')
        cell['at'] = _signature_at(signature)
        cell['path'] = signature.get('path')
        reason = signature.get('count_reason')
        cell['reasons'] = [reason] if reason else []
        return cell

    if signatures:
        signature = signatures[0]
        cell['word'] = 'stale'
        cell['signer'] = signature.get('signer')
        cell['at'] = _signature_at(signature)
        cell['path'] = signature.get('path')
        cell['reasons'] = ['hashes changed after the signature']
        return cell

    return cell


def _binds(signature, inp, bar, audit=None):
    """True when a signature or a hold still binds the rule's current evidence.

    `audit` is passed for a signature and left out for a hold: a hold says
    the test does not prove the proof, which is a statement about the rule,
    the proof and the test, and a re-audit does not answer it.
    """
    from purlin import signatures as signatures_module
    return signatures_module.is_current(
        signature, inp.get('rule_hash'), inp.get('proof_hash'),
        inp.get('test_hash'), bar, audit)


# ---------------------------------------------------------------------------
# Meeting the gate
# ---------------------------------------------------------------------------

def cell_is_met(name, cell):
    """True when one cell reads a word that meets its level.

    The signed cell of a rule that needs no signature is met whichever way it
    reads, except `held`: a hold is a person saying the test does not prove
    the proof, and it blocks at `strong` and at `signed` whatever the bar.
    """
    if not cell:
        return False
    if name == 'passed':
        return cell['word'] == 'passed'
    if name == 'strong':
        return cell['word'] == 'strong'
    if cell['word'] == 'held':
        return False
    return cell['word'] == 'signed' or not cell.get('required')


def _cleared(spec, bar, passed, strong):
    """True when a rule has the evidence its bar asks for.

    Bar `passed` asks for a passing test; bar `strong` asks for the strong
    cell too. It is the one question the `Signable` column and the sign list
    are built on.
    """
    if spec != READY:
        return False
    if bar == 'strong':
        return cell_is_met('strong', strong)
    return cell_is_met('passed', passed)


def _cell_blocks(name, cell, bar):
    """True when one cell keeps a rule from meeting the gate.

    The strong cell blocks a rule whose bar is `strong`; it does not block a
    rule whose bar is `passed`, whose evidence is the tests. A hold blocks
    either way. The signed cell blocks only where a signature is required.
    """
    if name == 'passed':
        return not cell_is_met('passed', cell)
    if name == 'strong':
        if (cell or {}).get('word') == 'held':
            return True
        return bar == 'strong' and not cell_is_met('strong', cell)
    return not cell_is_met('signed', cell)


def _blocked_by(spec, cells, gate, bar):
    """The lowest cell that blocks, or None when the rule meets the gate."""
    if spec != READY:
        return 'spec'
    for name in cells_for(gate):
        if _cell_blocks(name, cells.get(name), bar):
            return name
    return None


def _bucket(spec, cells, gate, passed, strong, signed):
    """The one tile a rule is counted in."""
    if passed['word'] == 'failed':
        return 'failing'
    if passed['word'] == 'partial':
        return 'partial'
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
    per bucket the gate reaches, the stale, held, manual, unsettled and
    not-audited counts, how many rules are signable, the latest record and
    the test strength.
    """
    keys = bucket_keys(gate)
    counts = {key: 0 for key in keys}
    met = 0
    flagged = {name: 0 for name in COUNTED_FLAGS}
    signable = 0
    for result in rule_results.values():
        bucket = result.get('bucket') or 'untested'
        if bucket not in counts:
            # A bucket above the gate cannot be reached, so it is not counted
            # under a name the rollup does not carry.
            bucket = keys[-1]
        counts[bucket] += 1
        if result.get('meets_gate'):
            met += 1
        if result.get('signable'):
            signable += 1
        flags = result.get('flags') or {}
        for name in COUNTED_FLAGS:
            flagged[name] += 1 if flags.get(name) else 0
    rollup = {'rules': len(rule_results), 'met': met}
    rollup.update(counts)
    rollup.update(flagged)
    rollup.update({'signable': signable, 'test_strength': test_strength,
                   'latest_record': latest_record})
    return rollup


def project_rollup(feature_rollups, gate='passed'):
    """The project's summary: the same counts, plus how many features there are."""
    keys = bucket_keys(gate)
    summary = {'features': len(feature_rollups), 'rules': 0, 'met': 0,
               'signable': 0}
    for key in keys:
        summary[key] = 0
    for name in COUNTED_FLAGS:
        summary[name] = 0
    for rollup in feature_rollups.values():
        for key in ('rules', 'met', 'signable') + COUNTED_FLAGS:
            summary[key] += rollup.get(key, 0)
        for key in keys:
            summary[key] += rollup.get(key, 0)
    return summary
