"""The three evidence levels of a rule.

One rule, read top to bottom. Each row below is a cell, and the gate decides
how many rows exist: every rule carries every cell up to the gate, and a
cell above the gate is absent, not empty.

    passed  Met when every proof has a passing test in an evidence section
            that is current: its spec, code and tests fingerprint equals the
            one taken now. Only current sections decide the cell.
            `passed`, `partial`, `failed`, `no test`, `not run`,
            `out of date`. A rule no proof line names is answered by the
            tests marked with the rule's own id, and reads `no test` with
            the reason `no proof written` when there are none. The cell carries `platforms`, one
            entry per operating system a current section covers, and reads
            `partial` when the tests passed on some of them and failed or did
            not run on others. `partial` is not met.

    strong  Met when the tests are worth trusting: the AI audit read the
            rule's current text, proof and test and found nothing, and, where
            mutation testing is on and measured a score, the score reaches the
            project minimum. `strong`, `weak`, `not audited`, `manual test`,
            and `no proof` for a rule whose passing test answers no proof:
            proofs are optional at the gate `passed` and required above it.
            `waiting` while the passed cell is not met, because the audit
            reads a test that passes; `weak` means only that the audit found
            fault or a measured strength fell under the minimum.

    signed  Met when a person signed what the rule is now: its text, its
            proof, its test, its feature's code, what the audit found and
            the machines its tests ran on. `signed` or `unsigned`, and
            `waiting` where no signature binds the rule and the strong cell
            is not met, other than by a hand check, which a person signs. A
            signature that no longer binds the rule is read as none. At the
            gate `signed` a rule whose spec names no files in `> Scope:`
            reads `unsigned` whatever was signed, because a signature cannot
            be tied to the code it governs.

A proof marked `@manual` is checked by a person, who signs the rule: a
signature that counts and binds the rule's current hashes is its hand check,
with or without a note, and stands for the test, the audit and the
signature. `hand_checked` says so.

An anchor's rule is signed once in each feature it applies to. Listed under
a feature, it is signed by that feature's signature; listed under the anchor
itself, it is signed when every feature it applies to has signed it.

Each cell carries its reasons, so a surface never has to work out why a word
reads the way it does.

`rule_cells(inp, cfg)` takes one rule's evidence and the resolved gate, and
returns:

    {'cells': {'passed': {...}, 'strong': {...}},
     'level': 'strong',
     'bucket': 'strong',
     'meets_gate': True,
     'blocked_by': None,
     'hand_checked': False,
     'flags': {'failing': False, 'partial': False, 'stale': False,
               'manual': False, 'not_audited': False, 'out_of_date': False,
               'no_proof': False}}

A rule's **bucket** is the one tile it is counted in.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import evidence as evidence_module

# The three cells, in the order the chain reads them. A gate value names the
# deepest cell that exists, so the names are the gate values.
CELLS = ('passed', 'strong', 'signed')

# The strong cell's word for a rule a person checks by hand, and the one
# for a rule no audit has read.
HAND_CHECK_WORDS = ('manual test',)
NOT_AUDITED = 'not audited'

# What a queue row says it needs, from the rule's kind of work left.
HAND_CHECK = 'hand check'
SIGNATURE = 'signature'

# The flags a rollup counts, beside the buckets and never instead of them.
COUNTED_FLAGS = ('stale', 'manual', 'not_audited')

# The strong cell's reasons for what the audit said and could not say.
NOT_AUDITED_REASON = 'no audit has run on this code'
COULD_NOT_RUN = 'the AI audit could not run: %s'
COULD_NOT_DECIDE = 'the AI audit could not decide'
NO_SCORE = 'no mutation score measured'

# Where a pass came from, most trusted first. An evidence file's source is
# the folder it sits in, `.purlin/evidence/ci/` or `.purlin/evidence/local/`.
SOURCES = ('ci', 'local')

OUT_OF_DATE = 'out of date'

# The word a cell reads while the cell below it is not met: the strong cell
# while the tests have not passed, the signed cell while the audit has not
# cleared the rule. It is never met.
WAITING = 'waiting'
WAITING_FOR_TESTS = 'waiting for its tests to pass'
WAITING_FOR_AUDIT = 'waiting for the audit'

# The reason the passed cell gives for a rule no proof line names and no
# test marked with the rule's own id answers.
NO_PROOF_WRITTEN = 'no proof written'

# The strong cell's word for a rule whose tests pass and that has no proof.
NO_PROOF = 'no proof'
NO_PROOF_REASON = 'the rule has a test and no proof'

# The reason the signed cell gives, at the gate `signed`, for a rule whose
# own spec names no files in `> Scope:`.
NAMES_NO_FILES = ('the spec names no files in > Scope:, so a signature cannot '
                  'be tied to the code it governs')


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


def asked_keys(gate):
    """`{rollup key: cell}` for the cells above `passed` the gate reaches.

    Each key counts the rules that carry that cell, which is every rule.
    """
    return {'asks_' + name: name for name in cells_for(gate)[1:]}


def rule_cells(inp, cfg):
    """The cells, the bucket and the flags of one rule.

    `inp` carries:

    `proofs`        `[{'id', 'manual', 'env', 'text', 'tests'}, ...]`
    `rule_id`       the rule's own id, which a test may be marked with when
                    the rule has no proof
    `marked`        the proof and rule ids of the rule's feature that a
                    marker in the test files ties to a test declaration, so
                    a marked test no run has reached reads `not run`
    `sections`      every evidence section of the rule's own feature, each
                    `{source, os, path, section, current, out_of_date}` as
                    `evidence.checked_sections` gives them
    `signatures`    every signature file for this rule, each carrying `counts`
                    and `count_reason` from `signatures.counts`
    `applies_to`, `rule_hash`, `proof_hash`, `test_hash`, `code_hash`,
    `machines`      what a signature is made over, beside `audit_hash`
    `audit_hash`    the hash of what the audit found
    `consumers`     for an anchor's rule listed under the anchor itself,
                    `[{'applies_to', 'code_hash'}, ...]`, one per feature
                    it applies to; each must have signed it. Empty or absent
                    for any other listing
    `audit`         the evidence's audit entry for this rule's current
                    hashes, carrying its `path`, or None
    `could_not_run` why the last audit could not reach the model for this
                    rule's current hashes, or None
    `test_strength` an integer percent, or None when nothing measured it
    `incomplete`    why the rule's own spec names no files, or None; at the
                    gate `signed` the signed cell then reads `unsigned` with
                    `NAMES_NO_FILES`, because a signature cannot be tied to
                    the code it governs
    """
    gate = cfg.gate if cfg and cfg.gate in CELLS else CELLS[0]
    proofs = inp.get('proofs') or []

    signatures = list(inp.get('signatures') or ())
    targets = [dict(target) for target in inp.get('consumers') or ()] or [{}]
    current = [sig for sig in signatures
               if any(_binds(sig, inp, target) for target in targets)]
    # The signatures that settle the rule: one that counts for each feature
    # it applies to, and for any other listing one that counts at all.
    settled = all(any(sig.get('counts') and _binds(sig, inp, target)
                      for sig in signatures) for target in targets)
    counting = [sig for sig in current if sig.get('counts')] if settled else []

    passed = _passed_cell(inp, cfg)
    strong = _strong_cell(inp, cfg, passed, counting)
    signed = _signed_cell(current, counting)
    if (signed['word'] == 'unsigned' and not current
            and not cell_is_met('strong', strong)
            and strong['word'] not in HAND_CHECK_WORDS):
        # A signature binds what the audit found, so a rule the audit has
        # not cleared has nothing to sign yet. A hand check is signed by a
        # person, so it waits on a person and not on the audit.
        signed = dict(signed, word=WAITING, reasons=[WAITING_FOR_AUDIT])
    if inp.get('incomplete') and gate == CELLS[-1]:
        signed = dict(signed, word='unsigned', reasons=[NAMES_NO_FILES])

    cells = {}
    for name, cell in (('passed', passed), ('strong', strong),
                       ('signed', signed)):
        if name in cells_for(gate):
            cells[name] = cell

    flags = {
        'failing': passed['word'] == 'failed',
        'partial': passed['word'] == 'partial',
        'out_of_date': passed['word'] == OUT_OF_DATE,
        'stale': bool(signatures) and not current,
        'manual': 'strong' in cells and strong['word'] == 'manual test',
        'not_audited': 'strong' in cells and strong['word'] == NOT_AUDITED,
        'no_proof': not proofs,
    }

    blocked = _blocked_by(cells, gate)
    return {
        'level': gate,
        'cells': cells,
        'bucket': _bucket(gate, passed, strong, signed),
        'meets_gate': blocked is None,
        'blocked_by': blocked,
        'hand_checked': bool(counting) and any(
            proof.get('manual') for proof in proofs),
        'flags': flags,
    }


# ---------------------------------------------------------------------------
# The passed cell
# ---------------------------------------------------------------------------

def _passed_cell(inp, cfg):
    """Level 1: every proof has a passing test in a current section.

    Only a section whose fingerprint equals the one taken now decides the
    cell. Where the newest section that says anything about the rule is not
    current, the cell reads `out of date` and names what changed since, and
    the next run clears it: a person's own run goes out of date like any
    other, and so does a spec edit or a test edit.

    Over the current sections the question is asked once per operating
    system, and each answer goes in `platforms`. Where those answers disagree
    the cell reads `partial`, because a rule whose tests pass on Linux and
    fail on Windows is neither passed nor failed; `partial` is not met, so it
    blocks the gate exactly as a failure does.

    A `@manual` proof declares that no test is written for it and no proof
    entry is ever produced, so level 1 has no question to ask of it: it is
    read out here and the question moves to level 2, where `manual test` is
    the honest word and a signature with a note is the evidence.
    """
    written = inp.get('proofs') or []
    cell = {'word': 'no test', 'source': None, 'current': False,
            'counts': False, 'missing_env': [], 'platforms': {},
            'reasons': []}

    if not written:
        # A rule with no proof is answered by the tests marked with its own
        # id, read exactly as a proof's tests are.
        rule_id = inp.get('rule_id')
        if not rule_id or not (_rule_marked(inp.get('sections'), rule_id)
                               or rule_id in (inp.get('marked') or ())):
            cell['reasons'] = [NO_PROOF_WRITTEN]
            return cell
        written = [{'id': rule_id, 'manual': False, 'env': None,
                    'tests': [rule_id]}]
    proofs = [proof for proof in written if not proof.get('manual')]

    if not proofs:
        cell.update({'word': 'passed', 'current': True, 'counts': True})
        return cell

    answering = [entry for entry in inp.get('sections') or ()
                 if _word_of(proofs, entry) is not None]
    newest = None
    for entry in answering:
        if newest is None or str(entry['section'].get('at') or '') > str(
                newest['section'].get('at') or ''):
            newest = entry
    if newest is not None and not newest.get('current'):
        cell['word'] = OUT_OF_DATE
        cell['source'] = newest.get('source')
        cell['counts'] = True
        commit = str(newest['section'].get('commit') or '')[:7]
        cell['reasons'] = ['%s changed since %s' % (part, commit)
                           for part in newest.get('out_of_date') or ()]
        return cell

    current = [entry for entry in answering if entry.get('current')]
    # A current section that says nothing about the rule, one from an
    # operating system its `@env` proof does not name, still says which
    # systems ran, so it is what names the one the rule is waiting for.
    ran = [entry for entry in inp.get('sections') or () if entry.get('current')]
    platforms = _platforms(proofs, current)
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

    failing = _failing_where(proofs, current)
    if failing:
        cell['word'] = 'failed'
        cell['reasons'] = ['failing: %s' % where for where in failing]
        cell['source'] = _least_trusted(entry['source'] for entry in current)
        cell['current'] = True
        cell['counts'] = True
        return cell

    passes, missing_env, used = _section_passes(proofs, ran)
    if passes or missing_env:
        cell['source'] = _least_trusted(entry['source'] for entry in used)
        cell['counts'] = True
        cell['current'] = True
        if missing_env:
            cell['word'] = 'not run'
            cell['missing_env'] = list(missing_env)
            cell['reasons'] = ['%s: no run yet' % env for env in missing_env]
            return cell
        cell['word'] = 'passed'
        return cell

    # A test the evidence names, or a marker tied to a test in the source,
    # means the test exists and no counting run has reached it yet.
    marked = inp.get('marked') or ()
    if any(proof.get('tests') or proof.get('id') in marked for proof in proofs):
        cell['word'] = 'not run'
    return cell


def proof_result(proof, sections, marked=()):
    """One proof's own word, read the way the passed cell reads the rule.

    `hand check` for a `@manual` proof, which no test answers. Otherwise the
    current sections from the operating system the proof names, or from every
    system where it names none: `failed` where one of them failed it and
    `passed` where one passed it. With no current answer it reads `not run`
    where a marker in the test files ties it to a test, and `no test` where
    none does, which is how the rollup counts a proof with no test.
    """
    if proof.get('manual'):
        return HAND_CHECK
    env = proof.get('env')
    seen = [evidence_module.proof_results(entry['section']).get(proof.get('id'))
            for entry in sections or ()
            if entry.get('current') and (not env or entry.get('os') == env)]
    if 'fail' in seen:
        return 'failed'
    if 'pass' in seen:
        return 'passed'
    return 'not run' if proof.get('id') in (marked or ()) else 'no test'


def _rule_marked(sections, rule_id):
    """True when an evidence section lists a test marked with the rule's id."""
    for entry in sections or ():
        for listed in (entry.get('section') or {}).get('proofs') or ():
            if isinstance(listed, dict) and listed.get('id') == rule_id:
                return True
    return False


def _word_of(proofs, entry):
    """One section's word for a rule, or None when it has nothing to say."""
    return _word_from_statuses(proofs,
                               evidence_module.proof_results(entry['section']),
                               entry['os'])


def _platforms(proofs, current):
    """`{os: {word, source, at}}` over every operating system a current section covers.

    Where both sources hold a current section for one operating system the
    newer answers. A platform a proof is tagged for with `@env` and no
    current section covers gets an entry too, reading `not run` with no
    source, so the map lists every platform the rule is owed an answer from.
    """
    platforms = {}
    for entry in current:
        word = _word_of(proofs, entry)
        if word is None:
            continue
        at = entry['section'].get('at')
        known = platforms.get(entry['os'])
        if known is None or str(at or '') > str(known.get('at') or ''):
            platforms[entry['os']] = {'word': word, 'source': entry['source'],
                                      'at': at}
    for proof in proofs:
        env = proof.get('env')
        if env and env not in platforms:
            platforms[env] = {'word': 'not run', 'source': None, 'at': None}
    return platforms


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


def _least_trusted(sources):
    """The least trusted of some sources, or None when there are none."""
    found = [name for name in sources if name]
    if not found:
        return None
    return max(found, key=lambda name: SOURCES.index(name)
               if name in SOURCES else len(SOURCES))


def _passing_source(platforms):
    """The least trusted source among the platforms that passed."""
    return _least_trusted(entry.get('source') for entry in platforms.values()
                          if entry.get('word') == 'passed')


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
            reasons.append('%s: no run yet' % name)
        else:
            reasons.append('%s: %s' % (name, entry.get('word')))
    return reasons


def _failing_where(proofs, current):
    """Where a test backing the rule failed: `<os>, <source>` per current section.

    A cell says what the evidence shows, and a failing test is the one thing
    a word like `no test` would hide, so the failure itself is named here. A
    proof tagged `@env` is read only from that operating system's section.
    """
    where = []
    for entry in current:
        statuses = evidence_module.proof_results(entry['section'])
        for proof in proofs or ():
            if proof.get('env') and proof.get('env') != entry['os']:
                continue
            if statuses.get(proof.get('id')) == 'fail':
                where.append('%s, %s' % (entry['os'], entry['source']))
                break
    return where


def _section_passes(proofs, current):
    """`(passes, missing_env, used)` over the current sections.

    A proof with no `@env` is satisfied by any current section. A proof with
    `@env` is satisfied only by a current section from that operating system,
    so a rule whose proofs name two systems needs both.
    """
    if not proofs or not current:
        return False, [], []
    by_os = {}
    for entry in current:
        by_os.setdefault(entry['os'], []).append(entry)
    missing_env = []
    passes = True
    used = []
    for proof in proofs:
        env = proof.get('env')
        if env and env not in by_os:
            missing_env.append(env)
            passes = False
            continue
        candidates = by_os[env] if env else current
        proved = False
        for entry in candidates:
            statuses = evidence_module.proof_results(entry['section'])
            if statuses.get(proof.get('id')) == 'pass':
                proved = True
                if entry not in used:
                    used.append(entry)
                break
        if not proved:
            passes = False
    return passes, sorted(set(missing_env)), used


# ---------------------------------------------------------------------------
# The strong cell
# ---------------------------------------------------------------------------

def _strong_cell(inp, cfg, passed, counting_signatures):
    """Level 2: whether the tests behind a met passed cell are worth trusting.

    The AI audit decides it. An entry for the rule's current text, proof and
    test whose `verdict` is `strong` meets the cell; `weak` carries each
    finding as a reason; `undecided` is build work too, and reads `weak` with
    the audit's own sentence. With mutation testing on and a score measured,
    the score must also reach `min_strength`; with it off, or where nothing
    measured a score, the audit alone decides and the cell says no score was
    measured. A rule the audit has not read reads `not audited`.
    """
    strength = inp.get('test_strength')
    cell = {'word': 'weak', 'strength': strength, 'findings': [],
            'evidence': None, 'reasons': []}

    if passed['word'] != 'passed':
        # The audit reads a test that passes, so until the tests pass there
        # is nothing for it to find fault with: the cell waits, and is not
        # weak.
        cell['word'] = WAITING
        cell['reasons'] = [WAITING_FOR_TESTS]
        return cell

    if not inp.get('proofs'):
        # Proofs are optional at `passed` and required above it: a passing
        # test marked with the rule's own id answers no proof, so the audit
        # has nothing to read it against.
        cell['word'] = NO_PROOF
        cell['reasons'] = [NO_PROOF_REASON]
        return cell

    audit = inp.get('audit') or None
    if audit:
        cell['evidence'] = audit.get('path')
        cell['findings'] = [str(line) for line in
                            (audit.get('findings') or ())]

    if any(proof.get('manual') for proof in inp.get('proofs') or ()):
        # A `@manual` proof has no test for the audit to read. A person
        # checks it and signs, and a signature that counts for the current
        # hashes is what meets the cell, with or without a note.
        if counting_signatures:
            cell['word'] = 'strong'
            cell['reasons'] = ['hand check by %s'
                               % counting_signatures[0].get('signer')]
            return cell
        cell['word'] = 'manual test'
        cell['reasons'] = ['manual proof']
        return cell

    if not audit:
        cell['word'] = NOT_AUDITED
        why = inp.get('could_not_run')
        cell['reasons'] = [COULD_NOT_RUN % why if why else NOT_AUDITED_REASON]
        return cell

    answered = audit.get('verdict')
    reasons = []
    if answered == 'weak':
        reasons.extend(cell['findings'])
    elif answered != 'strong':
        reasons.extend(['%s: %s' % (COULD_NOT_DECIDE, line)
                        for line in cell['findings']] or [COULD_NOT_DECIDE])

    mutation_on = bool(cfg) and (cfg.mutation_engine or 'none') != 'none'
    min_strength = cfg.min_strength if cfg else None
    if (mutation_on and strength is not None and min_strength is not None
            and strength < min_strength):
        reasons.append('strength %d%% under %d%%'
                       % (round(strength), min_strength))

    if reasons:
        cell['word'] = 'weak'
        cell['reasons'] = reasons
        return cell
    cell['word'] = 'strong'
    if not mutation_on or strength is None:
        cell['reasons'] = [NO_SCORE]
    return cell


# ---------------------------------------------------------------------------
# The signed cell
# ---------------------------------------------------------------------------

def _signature_at(signature):
    """When a signature was made: the commit date, else the file's own stamp."""
    return signature.get('committed_at') or signature.get('timestamp')


def _signed_cell(current, counting):
    """Level 3: what the signature files say, whatever the cells below read.

    A signature is a fact about committed files. This cell is computed from
    those files alone and reads `signed` or `unsigned`, and names the
    signer, their name, the key's fingerprint and when. A signature that no
    longer binds the rule is read as none: the rule is back to `unsigned`,
    and nothing says why.
    """
    cell = {'word': 'unsigned', 'signer': None, 'signer_name': None,
            'key_fingerprint': None, 'at': None, 'path': None, 'reasons': []}
    signature = (counting or current or [None])[0]
    if signature is None:
        return cell
    cell.update({'signer': signature.get('signer'),
                 'signer_name': signature.get('signer_name'),
                 'key_fingerprint': signature.get('key_fingerprint'),
                 'at': _signature_at(signature),
                 'path': signature.get('path')})
    if counting:
        cell['word'] = 'signed'
        cell['reasons'] = ['by %s' % signature.get('signer')]
        return cell
    reason = signature.get('count_reason')
    cell['reasons'] = [reason] if reason else []
    return cell


def _binds(signature, inp, target=None):
    """True when a signature still binds the rule as `target` lists it.

    `target` names the feature the signature is made for and that feature's
    code, where it is not the listing `inp` describes.
    """
    from purlin import signatures as signatures_module
    entry = dict(inp, audit_hash=inp.get('audit_hash'))
    entry.update(target or {})
    return signatures_module.is_current(signature, entry)


# ---------------------------------------------------------------------------
# Meeting the gate
# ---------------------------------------------------------------------------

def cell_is_met(name, cell):
    """True when one cell reads the word that meets it."""
    if not cell:
        return False
    return cell['word'] == name


def _blocked_by(cells, gate):
    """The lowest cell up to the gate that is not met, or None."""
    for name in cells_for(gate):
        if not cell_is_met(name, cells.get(name)):
            return name
    return None


def _bucket(gate, passed, strong, signed):
    """The one tile a rule is counted in: the deepest cell it met, up to the gate."""
    if passed['word'] == 'failed':
        return 'failing'
    if passed['word'] == 'partial':
        return 'partial'
    if not cell_is_met('passed', passed):
        return 'untested'
    if gate == 'passed' or not cell_is_met('strong', strong):
        return 'passed'
    if gate == 'strong' or not cell_is_met('signed', signed):
        return 'strong'
    return 'signed'


# ---------------------------------------------------------------------------
# Rollups
# ---------------------------------------------------------------------------

def feature_rollup(rule_results, gate='passed', test_strength=None):
    """One feature's rollup over `{rule_ref: rule_cells result}`.

    Carries how many rules the feature has, `met`, one count per bucket the
    gate reaches, how many rules carry each cell above `passed` the gate
    reaches (`asks_strong`, `asks_signed`), the stale, manual and
    not-audited counts, `queue` and `hand_checks` from each rule's `need`,
    and the test strength.
    """
    keys = bucket_keys(gate)
    counts = {key: 0 for key in keys}
    asked = {key: 0 for key in asked_keys(gate)}
    met = 0
    flagged = {name: 0 for name in COUNTED_FLAGS}
    queue = hand_checks = 0
    for result in rule_results.values():
        for key in asked:
            asked[key] += 1
        bucket = result.get('bucket') or 'untested'
        if bucket not in counts:
            # A bucket above the gate cannot be reached, so it is not counted
            # under a name the rollup does not carry.
            bucket = keys[-1]
        counts[bucket] += 1
        if result.get('meets_gate'):
            met += 1
        need = result.get('need')
        if need:
            queue += 1
        if need == HAND_CHECK:
            hand_checks += 1
        flags = result.get('flags') or {}
        for name in COUNTED_FLAGS:
            flagged[name] += 1 if flags.get(name) else 0
    rollup = {'rules': len(rule_results), 'met': met}
    rollup.update(counts)
    rollup.update(asked)
    rollup.update(flagged)
    rollup.update({'queue': queue, 'hand_checks': hand_checks,
                   'test_strength': test_strength})
    return rollup


def project_rollup(feature_rollups, gate='passed'):
    """The project's summary: the same counts, plus how many features there are."""
    keys = bucket_keys(gate)
    summary = {'features': len(feature_rollups), 'rules': 0, 'met': 0,
               'queue': 0, 'hand_checks': 0}
    keys = keys + list(asked_keys(gate))
    for key in keys:
        summary[key] = 0
    for name in COUNTED_FLAGS:
        summary[name] = 0
    for rollup in feature_rollups.values():
        for key in ('rules', 'met', 'queue', 'hand_checks') + COUNTED_FLAGS:
            summary[key] += rollup.get(key, 0)
        for key in keys:
            summary[key] += rollup.get(key, 0)
    return summary
