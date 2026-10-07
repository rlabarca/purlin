"""The two cells of a rule.

One rule, read top to bottom.

    passed  Met when every proof has a passing test in an evidence section
            that is current: its spec, code and tests fingerprint equals the
            one taken now. Only current sections decide the cell.
            `passed`, `graded`, `partial`, `failed`, `no test`, `not run`,
            `out of date`, `checked at sign-off`. `graded` is `passed` for
            a rule one of whose proofs a model grades (`@graded`): it counts
            wherever `passed` does (`passes`). A rule no proof line names
            is answered by the
            tests marked with the rule's own id, and reads `no test` with
            the reason `no proof written` when there are none. A rule some
            of whose proofs no test backs reads `no test`, naming them. The
            cell carries `platforms`, one entry per operating system a
            current section covers, and reads `partial` where two systems
            that each have a current section disagree. `partial` is not met.
            A `@manual` proof is read out of it. A rule whose every proof is
            `@manual` has no test to pass: it reads `checked at sign-off`,
            and `passed` once a sign-off that counts holds a note for it on
            the rule's and the proof's wording as they are, the note its
            reason. A `@slow` proof no
            current section answers for reads `not run`, saying which run
            starts its test. An anchor's proof whose
            every tied test skipped with `nothing to check:` counts as
            passed, its reason kept; on any other spec it reads `not run`.
            An AI proof (`@ai`) is a slow proof read once per model of its
            tag (`model_results`): it passes where every model passed, and
            the cell carries `missing_models`, the models a proof a run has
            tried holds no counting result on.

    strong  What the AI audit found, and nothing waits on it. `strong`,
            `weak`, `spot-checked`, `out of date`, `not audited`, `checked
            at sign-off` for a rule with a hand check, and `no proof` for a
            rule whose passing test answers no proof. `waiting` while the
            passed cell reads none of `passed`, `graded` and `checked at sign-off`,
            because the audit reads a test that passes. The word comes from the rule's audit entry: its
            `verdict` while the entry is current, a weak entry giving its
            findings as the reasons and a spot-checked one saying why no bug
            was caught; `out of date` once the rule, its proof, its test or
            the code it covers changed since, naming each part and the last
            result. A hand check carries the notes of the newest sign-off
            that holds one, and before them what was reworded since.

An anchor's rule is listed once, under the anchor.

Every rule of a spec that writes a rule or proof number twice, or holds a
line left from a merge conflict, reads `failed` with the reasons
`spec_broken` names; the strong cell waits.

Each cell carries its reasons, so a surface never has to work out why a word
reads the way it does.

`rule_cells(inp)` takes one rule's evidence and returns:

    {'cells': {'passed': {...}, 'strong': {...}},
     'bucket': 'passed',
     'flags': {'failing': False, 'partial': False, 'by_hand': False,
               'manual': False, 'not_audited': False, 'out_of_date': False,
               'no_proof': False, 'strong': True, 'weak': False,
               'spot_checked': False, 'audit_out_of_date': False}}

A rule's **bucket** is the one tile it is counted in; the rollup counts the
flags `strong`, `weak`, `spot_checked`, `audit_out_of_date`, `not_audited`
and `manual` beside the buckets. `out_of_date` is the passed cell's;
`audit_out_of_date` is the strong cell's.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import evidence as evidence_module
from purlin import outputs as outputs_module

# The two cells, in the order the chain reads them. Every rule carries both.
CELLS = ('passed', 'strong')

# The strong cell's word for a rule no audit has read.
NOT_AUDITED = 'not audited'

# A `@manual` proof's own word: a person checks it by hand.
HAND_CHECK = 'hand check'

# The flags a rollup counts, beside the buckets and never instead of them.
COUNTED_FLAGS = ('strong', 'weak', 'spot_checked', 'audit_out_of_date',
                 'not_audited', 'manual')

# The strong cell's reason for a rule no audit has read.
NOT_AUDITED_REASON = 'no audit has read this rule'

# The verdicts an audit entry may hold, which are the strong cell's words
# for a current entry. A verdict that is none of these decides nothing.
VERDICTS = ('strong', 'weak', 'spot-checked')
SPOT_CHECKED = 'spot-checked'
# The one reason of a spot-checked rule: these words, then the entry's
# `no_bug` sentences joined by one space.
SPOT_TESTS_FOUND_NOTHING = 'The spot tests found nothing. %s'

# The reasons of a strong cell whose audit entry is out of date: one per
# part that differs, then the entry's last result and its date.
CHANGED_SINCE = '%s changed since %s'              # rule, a1b2c3d
LAST_AUDIT = 'the last audit found it %s on %s'    # strong, 2026-09-13

# The strong cell's word for a rule with a hand check, and the reason each
# note of the newest sign-off holding one gives it: the version, the signer,
# `at this commit`, `1 commit since` or `4 commits since`, the note.
CHECKED_AT_SIGNOFF = 'checked at sign-off'
HAND_NOTE = 'noted at the sign-off of %s by %s, %s: %s'

# The passed cell's reason for a rule checked by hand alone that no sign-off
# that counts has noted, and the reasons a cell reading `checked at sign-off`
# opens with where the rule, or one of its `@manual` proofs, was reworded
# since its newest note: `rule` first, then `proof`.
NOT_CHECKED = 'no sign-off has checked it yet'
HAND_CHANGED = {'rule': "the rule's wording changed since its last note",
                'proof': "the proof's wording changed since its last note"}

# The reason an anchor's proof gives where its every tied test skipped with
# `nothing to check:`: the proof, then the reason after those words.
NOTHING_TO_CHECK = '%s: %s'                                       # PROOF-3, the reason
NOTHING_RESULT = 'nothing to check'

# The passed cell's reason while a `@slow` proof has no result that counts:
# `purlin:test` never starts its test, and this is the run that does.
SLOW_REASON = 'slow: runs with purlin:test --all'

# The passed cell's reason for the proofs of a rule no test backs.
NO_TEST_FOR = 'no test for %s'

# The passed cell's reason for a system a proof is tagged for that no
# current section comes from, the system in the words a person reads.
NO_RUN_YET = '%s: no run yet'

# Where a pass came from. An evidence file's source is the folder it sits
# in, `.purlin/evidence/ci/` or `.purlin/evidence/local/`; a cell names
# `local` whenever a person's own run is among its sources.
SOURCES = ('ci', 'local')

OUT_OF_DATE = 'out of date'

# The word the strong cell reads while the tests have not passed. It is
# never met.
WAITING = 'waiting'
WAITING_FOR_TESTS = 'waiting for its tests to pass'

# The order a person reads systems in, whatever order the evidence names
# them.
SYSTEM_ORDER = ('linux', 'macos', 'windows')

# The reason the passed cell gives for a rule no proof line names and no
# test marked with the rule's own id answers.
NO_PROOF_WRITTEN = 'no proof written'

# The strong cell's word for a rule whose tests pass and that has no proof.
NO_PROOF = 'no proof'
NO_PROOF_REASON = 'the rule has a test and no proof'

# The passed cell's word for a rule that passes with a proof a model grades,
# and a graded proof's own word where it passes. `passes` reads both words.
GRADED = 'graded'
PASSING = ('passed', GRADED)

# The passed cell's reasons for one model of an AI proof: the model, then
# how many of its runs passed where one failed, or how many gave a result
# where the proof still waits for some.
MODEL_FAILED = '%s: %d of %d passed'               # claude-opus-5-5, 2, 3
MODEL_RUN = '%s: %d of %d run'                     # claude-opus-5-5, 3, 5

# The fields of one run of an AI proof's test that a model's result carries,
# as the evidence holds them.
RUN_FIELDS = ('result', 'output', 'made', 'why', 'grade')

# The buckets a rollup counts, one per rule.
BUCKETS = ('untested', 'failing', 'partial', 'by_hand', 'passed')


def rule_cells(inp):
    """The cells, the bucket and the flags of one rule.

    `inp` carries:

    `proofs`        `[{'id', 'manual', 'slow', 'env', 'text', 'tests'}, ...]`,
                    an AI proof also holding `ai`, the models of its tag,
                    `graded`, its grader or None, and `runs`, how many runs
                    are asked now
    `rule_id`       the rule's own id, which a test may be marked with when
                    the rule has no proof
    `marked`        the proof and rule ids of the rule's feature that a
                    marker in the test files ties to a test declaration, so
                    a marked test no run has reached reads `not run`
    `sections`      every evidence section of the rule's own feature, each
                    `{source, os, path, section, current, out_of_date}` as
                    `evidence.checked_sections` gives them
    `anchor`        true for a rule of an anchor, whose proof a test skipped
                    with `nothing to check:` counts as passed
    `audit`         the rule's audit entry as `evidence.audit_entry` gives
                    it, carrying its `path` and `out_of_date`, the parts
                    that changed since it was written; or None
    `hand_notes`    the reasons the newest sign-off holding a note on this
                    rule gives it, `HAND_NOTE` filled; [] before any
    `hand_changed`  what was reworded since that sign-off, `'rule'` then
                    `'proof'`, as `signatures.hand_notes` names it; [] where
                    the note is on the wording as it is
    `spec_broken`   why every rule of the rule's own spec reads `failed`, as
                    `specs.broken_reasons` gives it: a number written twice,
                    a line left from a merge conflict; [] for a sound spec
    """
    inp = dict(inp, sections=read_sections(inp.get('sections'),
                                           inp.get('anchor'),
                                           inp.get('proofs')))
    proofs = inp.get('proofs') or []
    if inp.get('spec_broken'):
        return _broken(inp)

    passed = _passed_cell(inp)
    strong = _strong_cell(inp, passed)
    return {
        'cells': {'passed': passed, 'strong': strong},
        'bucket': _bucket(passed),
        'flags': _flags(passed, strong, proofs),
    }


def passes(word):
    """True for a word that says the tests pass: `passed`, or `graded`.

    The one test of it. A passed cell's word, a proof's `result` and a
    model's word are each read through it, so a graded result counts
    wherever a passed one does.
    """
    return word in PASSING


def read_sections(sections, anchor=False, proofs=()):
    """The sections with each proof's word read once, as `results`.

    `pass`, `fail` or `not run` per proof id. A proof whose every tied test
    skipped with `nothing to check:` reads `pass` on an anchor and `not run`
    on any other spec, its reason under `nothing`. An AI proof among
    `proofs` reads what the models of its tag read in the section
    (`_section_models`, kept under `models`), as `evidence.models_result`
    reads them, a model the section holds nothing for reading `not run`.
    """
    ai = [proof for proof in proofs or () if proof.get('ai')]
    out = []
    for entry in sections or ():
        if 'results' in entry:
            out.append(entry)
            continue
        results, nothing = {}, {}
        for proof_id, (word, reason) in section_results(
                entry.get('section')).items():
            if word == NOTHING_RESULT:
                nothing[proof_id] = reason or ''
                word = 'pass' if anchor else 'not run'
            results[proof_id] = word
        models = {}
        for proof in ai:
            if proof.get('id') not in results:
                continue
            found = _section_models(proof, entry.get('section'))
            models[proof.get('id')] = found
            results[proof.get('id')] = evidence_module.models_result(
                [found.get(name) for name in proof['ai']],
                outputs_module.runs_asked(proof))
        out.append(dict(entry, results=results, nothing=nothing,
                        models=models))
    return out


_MODEL_WORST = {'failed': 2, 'not run': 1, 'passed': 0}


def _section_models(proof, section):
    """`{model: {word, passed, of, runs}}` for the models of an AI proof's
    tag that one section holds an entry for.

    A model's word is `evidence.model_word`'s, against the runs
    `outputs.runs_asked` gives. `passed` and `of` are the entry's
    own, counted from its runs where it holds none. An entry for a model the
    tag does not name is left out. Where several tests back the proof, the
    worst of them answers for a model, and a test with no entry for it
    reads `not run`.
    """
    asked = outputs_module.runs_asked(proof)
    held = [{model['model']: model for model in reversed(
                 [model for model in entry.get('models') or ()
                  if isinstance(model, dict)])}
            for entry in (section or {}).get('proofs') or ()
            if isinstance(entry, dict) and entry.get('id') == proof.get('id')
            and entry.get('test')]
    found = {}
    for name in proof['ai']:
        if not any(name in models for models in held):
            continue
        reads = [_model_read(models.get(name), asked) for models in held]
        found[name] = max(reads, key=lambda read: _MODEL_WORST[read['word']])
    return found


def _model_read(model, asked):
    """`{word, passed, of, runs}` for one model entry of the evidence, None
    for a test that holds none."""
    runs = [run for run in (model or {}).get('runs') or ()
            if isinstance(run, dict)]
    results = [run.get('result') for run in runs]
    return {'word': evidence_module.model_word(model, asked),
            'passed': _count(model, 'passed', results.count('pass')),
            'of': _count(model, 'of', len(runs)),
            'runs': [{key: run[key] for key in RUN_FIELDS if key in run}
                     for run in runs]}


def _count(model, key, counted):
    """A model entry's own whole number under `key`, else `counted`."""
    value = (model or {}).get(key)
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return counted


def model_results(proof, sections, anchor=False):
    """`[{model, word, passed, of, runs}]` for an AI proof, one entry per
    model of its tag in the tag's order; `[]` for any other proof.

    Read from the one current section that decides the proof's own word,
    among those of the operating system it names or of every system where
    it names none: the first that failed it, else the first that passed it,
    else the newest that holds a run of one of its models. `word` is
    `failed`, `not run`, or `passed`, which reads `graded` for a graded
    proof. A model no such section holds an entry for reads `not run` with
    `passed` 0, `of` 0 and no runs. `runs` holds each run's `RUN_FIELDS`.
    """
    if not proof.get('ai'):
        return []
    env = proof.get('env')
    read = [entry for entry in read_sections(sections, anchor, [proof])
            if entry.get('current') and (not env or entry.get('os') == env)
            and proof.get('id') in entry.get('models', {})]
    chosen = None
    for word in ('fail', 'pass'):
        chosen = chosen or next(
            (entry for entry in read
             if entry['results'].get(proof.get('id')) == word), None)
    if chosen is None:
        chosen = max((entry for entry in read
                      if tried(entry['models'][proof.get('id')].values())),
                     key=lambda entry: str(entry['section'].get('at') or ''),
                     default=None)
    found = chosen['models'][proof.get('id')] if chosen else {}
    out = []
    for name in proof['ai']:
        entry = dict(found.get(name) or {'word': 'not run', 'passed': 0,
                                         'of': 0, 'runs': []}, model=name)
        if entry['word'] == 'passed' and proof.get('graded'):
            entry['word'] = GRADED
        out.append(entry)
    return out


def runs_of(entry, asked):
    """The `<n>` of a model's `<k> of <n>`: the runs its entry of
    `model_results` holds, or the runs `asked` now where they are more."""
    return max(entry.get('of') or 0, asked or 0)


def tried(models):
    """True where a run has tried an AI proof: one of its models, as
    `model_results` gives them, holds a run."""
    return any(entry.get('runs') for entry in models or ())


def _model_reasons(proofs, current, anchor=False):
    """`(failed, waiting, missing)` over the AI proofs of a rule a run has
    tried, each reason once, in the order the proofs and their tags give.

    `failed` holds `MODEL_FAILED` for each model a run failed on. `waiting`
    holds, for each model that reads `not run`, `NO_RUN_YET` where it has no
    run and `MODEL_RUN` where some of its runs are still to make; `missing`
    names those models.
    """
    failed, waiting, missing = [], [], []
    for proof in proofs or ():
        found = model_results(proof, current, anchor)
        if not tried(found):
            continue
        asked = outputs_module.runs_asked(proof)
        for entry in found:
            name = entry['model']
            if entry['word'] == 'failed':
                reason = MODEL_FAILED % (name, entry['passed'], entry['of'])
                if reason not in failed:
                    failed.append(reason)
            elif entry['word'] == 'not run':
                counted = sum(1 for run in entry['runs']
                              if run.get('result') in ('pass', 'fail'))
                reason = (MODEL_RUN % (name, counted, runs_of(entry, asked))
                          if entry['runs'] else NO_RUN_YET % name)
                if reason not in waiting:
                    waiting.append(reason)
                if name not in missing:
                    missing.append(name)
    return failed, waiting, missing


def section_results(section):
    """`{proof id: (word, reason)}` for one section, as `evidence.proof_results` reads it.

    The word is `pass`, `fail`, `not run` or `nothing to check`; the reason
    is the text a skip gave, or None.
    """
    out = {}
    for proof_id, found in evidence_module.proof_results(section).items():
        if isinstance(found, dict):
            out[proof_id] = (found.get('result'), found.get('reason'))
        else:
            out[proof_id] = (found, None)
    return out


def _results(entry):
    """`{proof id: pass | fail | not run}` for one section."""
    if 'results' not in entry:
        entry = read_sections([entry])[0]
    return entry['results']


def _flags(passed, strong, proofs):
    """The flags of one rule, read off its two cells."""
    return {
        'failing': passed['word'] == 'failed',
        'partial': passed['word'] == 'partial',
        'by_hand': passed['word'] == CHECKED_AT_SIGNOFF,
        'out_of_date': passed['word'] == OUT_OF_DATE,
        'manual': any(proof.get('manual') for proof in proofs or ()),
        'not_audited': strong['word'] == NOT_AUDITED,
        'no_proof': not proofs,
        'strong': strong['word'] == 'strong',
        'weak': strong['word'] == 'weak',
        'spot_checked': strong['word'] == SPOT_CHECKED,
        'audit_out_of_date': strong['word'] == OUT_OF_DATE,
    }


def _broken(inp):
    """The cells of a rule whose own spec writes a number twice or holds a
    line left from a merge conflict.

    The passed cell reads `failed` with the reasons `spec_broken` gives, the
    strong cell waits as for any failed rule, and the rule is counted
    `failing`. The tests still run, so the source is the one the evidence
    gives.
    """
    passed = dict(_passed_cell(inp), word='failed', current=True,
                  counts=True, reasons=list(inp.get('spec_broken')))
    strong = _strong_cell(inp, passed)
    return {
        'cells': {'passed': passed, 'strong': strong},
        'bucket': 'failing',
        'flags': _flags(passed, strong, inp.get('proofs')),
    }


# ---------------------------------------------------------------------------
# The passed cell
# ---------------------------------------------------------------------------

def _passed_cell(inp):
    """The passed cell: every proof has a passing test in a current section.

    Only a section whose fingerprint equals the one taken now decides the
    cell. Where the newest section that says anything about the rule is not
    current, the cell reads `out of date` and names what changed since, and
    the next run clears it: a person's own run goes out of date like any
    other, and so does a spec edit or a test edit.

    Over the current sections the question is asked once per operating
    system, and each answer goes in `platforms`. Where those answers disagree
    the cell reads `partial`, because a rule whose tests pass on Linux and
    fail on Windows is neither passed nor failed; `partial` is not met, so it
    stops the tests being met exactly as a failure does.

    A `@manual` proof declares that no test is written for it, so the passed
    cell has no question to ask of it: it is read out here, and a person
    checks it at the sign-off. A rule whose every proof is `@manual` is
    `_by_hand_cell`'s.

    `nothing_to_check` lists `{proof, reason}` for each proof whose every
    tied test in a current section skipped with `nothing to check:`.
    """
    written = inp.get('proofs') or []
    cell = {'word': 'no test', 'source': None, 'current': False,
            'counts': False, 'missing_env': [], 'missing_models': [],
            'platforms': {}, 'nothing_to_check': [], 'reasons': []}

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
        return _by_hand_cell(cell, inp)

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
        cell['reasons'] = [CHANGED_SINCE % (part, commit)
                           for part in newest.get('out_of_date') or ()]
        return cell

    current = [entry for entry in answering if entry.get('current')]
    # A current section that says nothing about the rule, one from an
    # operating system its `@env` proof does not name, still says which
    # systems ran, so it is what names the one the rule is waiting for.
    ran = [entry for entry in inp.get('sections') or () if entry.get('current')]
    nothing = _nothing_to_check(proofs, current)
    cell['nothing_to_check'] = nothing
    platforms = _platforms(proofs, current)
    cell['platforms'] = platforms
    # Only systems that each have a current section can disagree: a system
    # a proof is tagged for and no section covers is waited for, not failed.
    words = [entry['word'] for entry in platforms.values()
             if entry.get('source') is not None]
    disagree = 'passed' in words and any(word != 'passed' for word in words)
    if disagree and 'failed' in words:
        # A test failed on one system and passed on another, so neither
        # `passed` nor `failed` is true of the rule. `partial` is the only
        # honest word, it is not met, and like a failure it comes first.
        return _partial(cell, platforms)

    # What the models of the rule's AI proofs read, where a run tried them.
    model_failed, model_reasons, missing_models = _model_reasons(
        proofs, current, inp.get('anchor'))
    failing = _failing_where(proofs, current)
    if failing:
        cell['word'] = 'failed'
        cell['reasons'] = (['failing: %s' % where for where in failing]
                           + model_failed)
        cell['source'] = _named_source(entry['source'] for entry in current)
        cell['current'] = True
        cell['counts'] = True
        return cell

    # A proof no marker ties to a test and no current section lists has no
    # test at all, tagged for this system or another: running again cannot
    # clear it, so the rule reads `no test` and names each such proof.
    if inp.get('proofs'):
        untested = _untested(proofs, ran, inp.get('marked') or ())
        if untested:
            cell['reasons'] = [NO_TEST_FOR % ', '.join(untested)]
            return cell

    if disagree:
        # One system passed and another ran the tests without passing them.
        return _partial(cell, platforms)

    # Where a proof found nothing to check, its reason is the cell's: on an
    # anchor the proof passed with it, on any other spec it is not run.
    said = ([NOTHING_TO_CHECK % (item['proof'], item['reason'])
             for item in nothing] if inp.get('anchor')
            else [item['reason'] for item in nothing])
    passes, missing_env, used = _section_passes(proofs, ran)
    if passes or missing_env:
        cell['source'] = _named_source(entry['source'] for entry in used)
        cell['counts'] = True
        cell['current'] = True
        if missing_env:
            cell['word'] = 'not run'
            cell['missing_env'] = list(missing_env)
            cell['missing_models'] = missing_models
            cell['reasons'] = [NO_RUN_YET % system_word(env)
                               for env in missing_env] + model_reasons + said
            return cell
        # A rule one of whose proofs a model grades passes as `graded`.
        cell['word'] = (GRADED if any(proof.get('graded') for proof in proofs)
                        else 'passed')
        cell['reasons'] = said
        return cell

    # A test the evidence names, or a marker tied to a test in the source,
    # means the test exists and no counting run has reached it yet.
    marked = inp.get('marked') or ()
    if any(proof.get('tests') or proof.get('id') in marked for proof in proofs):
        cell['word'] = 'not run'
        cell['missing_models'] = missing_models
        cell['reasons'] = ([SLOW_REASON] if _slow_waiting(proofs, ran)
                           else []) + model_reasons + said
    return cell


def _hand_reasons(inp):
    """The reasons of a hand check: one `HAND_CHANGED` line per part reworded
    since the newest note, `rule` first, then that sign-off's notes."""
    changed = inp.get('hand_changed') or ()
    return ([HAND_CHANGED[part] for part in ('rule', 'proof')
             if part in changed] + list(inp.get('hand_notes') or ()))


def _by_hand_cell(cell, inp):
    """The passed cell of a rule whose every proof is `@manual`.

    No test runs for it, so it has none to pass. It reads `checked at
    sign-off`, with the reason `NOT_CHECKED`, until a sign-off that counts
    holds a note for it. On the rule's and the proof's wording as they are
    it then reads `passed`, the note its reason; where either was reworded
    since, it reads `checked at sign-off` again, a `HAND_CHANGED` line
    before the note. The cell is current and counts either way: nothing a
    run could write would move it.
    """
    notes = list(inp.get('hand_notes') or ())
    cell.update({'current': True, 'counts': True})
    if notes and not inp.get('hand_changed'):
        cell.update({'word': 'passed', 'reasons': notes})
    else:
        cell.update({'word': CHECKED_AT_SIGNOFF,
                     'reasons': _hand_reasons(inp) or [NOT_CHECKED]})
    return cell


def _slow_waiting(proofs, current):
    """The ids of the `@slow` proofs no current section passes."""
    return [proof.get('id') for proof in proofs
            if proof.get('slow')
            and not any(_results(entry).get(proof.get('id')) == 'pass'
                        and (not proof.get('env')
                             or proof.get('env') == entry['os'])
                        for entry in current or ())]


def _nothing_to_check(proofs, current):
    """`[{proof, reason}]` for the proofs a current section found nothing to check for."""
    found = []
    for proof in proofs:
        for entry in current:
            reason = entry.get('nothing', {}).get(proof.get('id'))
            if reason is not None and (not proof.get('env')
                                       or proof.get('env') == entry['os']):
                found.append({'proof': proof.get('id'), 'reason': reason})
                break
    return found


def _partial(cell, platforms):
    """The passed cell where two systems that each have a current section disagree."""
    cell['word'] = 'partial'
    cell['source'] = _passing_source(platforms)
    cell['current'] = True
    cell['counts'] = True
    cell['missing_env'] = [name for name in sorted(platforms)
                           if platforms[name].get('source') is None]
    cell['reasons'] = _platform_reasons(platforms)
    return cell


def _untested(proofs, current, marked):
    """The ids of the proofs no marker ties to a test and no current section lists with one.

    A section lists a proof with a test only where its entry names the test:
    an entry with no test, such as one a run wrote for a proof it found no
    test for, is not a test.
    """
    return [proof.get('id') for proof in proofs
            if proof.get('id') not in marked
            and not any(evidence_module.proof_tests(entry['section'],
                                                    proof.get('id'))
                        for entry in current or ())]


def proof_result(proof, sections, marked=(), anchor=False):
    """One proof's own word, read the way the passed cell reads the rule.

    `hand check` for a `@manual` proof, which no test answers. Otherwise the
    current sections from the operating system the proof names, or from every
    system where it names none: `failed` where one of them failed it and
    `passed` where one passed it, which reads `graded` for a proof a model
    grades. An AI proof is read per section as `read_sections` reads it.
    With no current answer it reads `not run`
    where a marker in the test files ties it to a test, and `no test` where
    none does, which is how the rollup counts a proof with no test.
    """
    if proof.get('manual'):
        return HAND_CHECK
    env = proof.get('env')
    seen = [_results(entry).get(proof.get('id'))
            for entry in read_sections(sections, anchor, [proof])
            if entry.get('current') and (not env or entry.get('os') == env)]
    if 'fail' in seen:
        return 'failed'
    if 'pass' in seen:
        return GRADED if proof.get('graded') else 'passed'
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
    return _word_from_statuses(proofs, _results(entry), entry['os'])


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
    to answer, so it is left out. A section answers only for the proofs it
    lists: one it does not list is neither passed, failed nor `not run`
    there. A platform with nothing of the rule's to observe answers None and
    is not listed at all.
    """
    mine = [proof for proof in proofs
            if not proof.get('env') or proof.get('env') == os_name]
    seen = [statuses[proof.get('id')] for proof in mine
            if statuses.get(proof.get('id'))]
    if not seen:
        return None
    if 'fail' in seen:
        return 'failed'
    if all(status == 'pass' for status in seen):
        return 'passed'
    return 'not run'


def _named_source(sources):
    """The source a cell names: `local` when any is, else `ci`; None for none."""
    found = [name for name in sources if name]
    if not found:
        return None
    return max(found, key=lambda name: SOURCES.index(name)
               if name in SOURCES else len(SOURCES))


def _passing_source(platforms):
    """The source a cell names among the platforms that passed."""
    return _named_source(entry.get('source') for entry in platforms.values()
                          if entry.get('word') == 'passed')


def system_word(name):
    """`Windows`, `macOS` or `Linux/Unix` for a stored system word."""
    return evidence_module.os_word(name)


def systems_text(names):
    """The systems as a person reads them, `Linux/Unix`, `macOS`, `Windows` in
    that order, joined by `, ` and a last ` and `."""
    words = [system_word(name) for name in _in_order(set(names))]
    if len(words) < 2:
        return ''.join(words)
    return '%s and %s' % (', '.join(words[:-1]), words[-1])


def _platform_reasons(platforms):
    """One reason per platform that did not pass, and one naming those that did."""
    passed = [name for name, entry in platforms.items()
              if entry.get('word') == 'passed']
    reasons = []
    if passed:
        reasons.append('passed on %s' % systems_text(passed))
    for name in _in_order(platforms):
        entry = platforms[name]
        if entry.get('word') == 'passed':
            continue
        if entry.get('source') is None:
            reasons.append(NO_RUN_YET % system_word(name))
        else:
            reasons.append('%s: %s' % (system_word(name), entry.get('word')))
    return reasons


def _in_order(names):
    """The stored system words in the order a person reads them."""
    return ([name for name in SYSTEM_ORDER if name in names]
            + sorted(name for name in names if name not in SYSTEM_ORDER))


def _failing_where(proofs, current):
    """Where a test backing the rule failed: `<os>, <source>` per current section.

    A cell says what the evidence shows, and a failing test is the one thing
    a word like `no test` would hide, so the failure itself is named here. A
    proof tagged `@env` is read only from that operating system's section.
    """
    where = []
    for entry in current:
        statuses = _results(entry)
        for proof in proofs or ():
            if proof.get('env') and proof.get('env') != entry['os']:
                continue
            if statuses.get(proof.get('id')) == 'fail':
                where.append('%s, %s' % (system_word(entry['os']),
                                         entry['source']))
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
            statuses = _results(entry)
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

def _strong_cell(inp, passed):
    """The strong cell: what the AI audit found in the tests behind a met passed cell.

    Nothing waits on it. The word comes from the rule's audit entry. While
    the entry is current it is the entry's verdict: `strong`; `weak`, each
    finding a reason; or `spot-checked`, with the one reason
    `SPOT_TESTS_FOUND_NOTHING` over the entry's `no_bug` sentences. Once the
    rule, its proof, its test or the code it covers changed since the entry
    was written the cell reads `out of date`, with one reason per part that
    differs and last what the audit found and when; the entry's findings
    stay under `findings`. A rule with a `@manual` proof reads `checked at
    sign-off` unless its entry reads `weak` or `spot-checked` or is out of
    date, with one `HAND_CHANGED` reason per part reworded since the newest
    sign-off holding a note, then one reason per note of it. A rule whose
    every proof is `@manual` has no test for an entry to speak of, and reads
    `checked at sign-off` throughout. A rule with no entry reads `not
    audited`.
    """
    cell = {'word': NOT_AUDITED, 'findings': [], 'evidence': None,
            'reasons': []}

    proofs = inp.get('proofs') or ()
    if proofs and all(proof.get('manual') for proof in proofs) \
            and (passes(passed['word'])
                 or passed['word'] == CHECKED_AT_SIGNOFF):
        cell['word'] = CHECKED_AT_SIGNOFF
        cell['reasons'] = _hand_reasons(inp)
        return cell

    if not passes(passed['word']):
        # The audit reads a test that passes, so until the tests pass there
        # is nothing for it to find fault with: the cell waits, and is not
        # weak.
        cell['word'] = WAITING
        cell['reasons'] = [WAITING_FOR_TESTS]
        return cell

    if not inp.get('proofs'):
        # A passing test marked with the rule's own id answers no proof, so
        # the audit has nothing to read it against.
        cell['word'] = NO_PROOF
        cell['reasons'] = [NO_PROOF_REASON]
        return cell

    audit = inp.get('audit') or None
    verdict = audit.get('verdict') if audit else None
    if verdict in VERDICTS:
        cell['evidence'] = audit.get('path')
        cell['findings'] = [str(line) for line in
                            (audit.get('findings') or ())]
    else:
        # A verdict the format does not name decides nothing.
        audit = None
    changed = list(audit.get('out_of_date') or ()) if audit else []

    if verdict == 'weak' and not changed:
        cell['word'] = 'weak'
        cell['reasons'] = list(cell['findings'])
        return cell

    if audit and changed:
        # The entry stays in the evidence and on the page: the cell says
        # what changed since it was written and what it found then.
        commit = str(audit.get('commit') or '')[:7]
        cell['word'] = OUT_OF_DATE
        cell['reasons'] = [CHANGED_SINCE % (part, commit) for part in changed]
        cell['reasons'].append(LAST_AUDIT % (
            verdict, str(audit.get('at') or '')[:10]))
        return cell

    if audit and verdict == SPOT_CHECKED:
        cell['word'] = SPOT_CHECKED
        cell['reasons'] = [SPOT_TESTS_FOUND_NOTHING % ' '.join(
            str(line) for line in audit.get('no_bug') or ())]
        return cell

    if any(proof.get('manual') for proof in inp.get('proofs') or ()):
        # A `@manual` proof has no test for the audit to read: a person
        # checks it at the sign-off, and the newest note says what they saw.
        # What the audit said of the rule's tested proofs comes first: only
        # a current `strong`, or no entry, leaves the cell to the hand check.
        cell['word'] = CHECKED_AT_SIGNOFF
        cell['reasons'] = _hand_reasons(inp)
        return cell

    if not audit:
        cell['reasons'] = [NOT_AUDITED_REASON]
        return cell

    cell['word'] = 'strong'
    return cell


# ---------------------------------------------------------------------------
# Whether a cell is met
# ---------------------------------------------------------------------------

def cell_is_met(name, cell):
    """True when one cell reads a word that meets it: `passes` for the
    passed cell, the cell's own name for the strong cell."""
    if not cell:
        return False
    if name == 'passed':
        return passes(cell['word'])
    return cell['word'] == name


def _bucket(passed):
    """The one tile a rule is counted in, read off its passed cell."""
    if passed['word'] == 'failed':
        return 'failing'
    if passed['word'] == 'partial':
        return 'partial'
    if passed['word'] == CHECKED_AT_SIGNOFF:
        return 'by_hand'
    if not cell_is_met('passed', passed):
        return 'untested'
    return 'passed'


# ---------------------------------------------------------------------------
# Rollups
# ---------------------------------------------------------------------------

def feature_rollup(rule_results):
    """One feature's rollup over `{rule_ref: rule_cells result}`.

    Carries how many rules the feature has, one count per bucket, and the
    counts of `COUNTED_FLAGS`.
    """
    counts = {key: 0 for key in BUCKETS}
    flagged = {name: 0 for name in COUNTED_FLAGS}
    for result in rule_results.values():
        bucket = result.get('bucket') or 'untested'
        counts[bucket if bucket in counts else 'untested'] += 1
        flags = result.get('flags') or {}
        for name in COUNTED_FLAGS:
            flagged[name] += 1 if flags.get(name) else 0
    rollup = {'rules': len(rule_results)}
    rollup.update(counts)
    rollup.update(flagged)
    return rollup


def project_rollup(feature_rollups):
    """The project's summary: the same counts, plus how many features there are."""
    keys = ['rules'] + list(BUCKETS) + list(COUNTED_FLAGS)
    summary = {'features': len(feature_rollups)}
    for key in keys:
        summary[key] = sum(rollup.get(key, 0)
                           for rollup in feature_rollups.values())
    return summary
