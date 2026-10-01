"""The audit's run: the spot tests, the planted bugs, the model's reading.

`purlin_run.py --audit` runs the tests, then calls `run`. For each rule the
audit reads (`ai_audit.is_read`, ai_audit RULE-1) it runs, in this order:

1. the heuristic spot tests over each test tied to the rule's proofs
   (`plain_checks.check`), with no model;
2. one planted bug per proof whose tests or feature's code changed since its
   last planted bug (`targeted_break.break_proof`), none for an anchor's
   rule or a `@manual` proof; a proof whose `break_key` is unchanged keeps
   its last result (ai_audit RULE-36);
3. the model's reading (`ai_audit.audit_all`), one call per rule, four at
   once, which becomes the explanation and sets no verdict.

A rule reads `weak` when a spot test fires on one of its tests or a planted
bug survived, else `strong` (ai_audit RULE-33). One `audit.rules` entry per
rule read is written through `evidence.write_audit`. What the model cost is
written to `.purlin/runtime/audit_run.json`, which git ignores. The run
prints the findings, the cost line and, last, the share of rules found
strong (ai_audit RULE-35).

A project file that changes while a bug is planted stops the run before
anything is written (planted_bug RULE-6).
"""

import functools
import hashlib
import json
import math
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
for _path in (os.path.join(_SCRIPTS, 'mcp'), os.path.join(_SCRIPTS, 'run'),
              _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import ai_audit                                               # noqa: E402
import evidence as evidence_writer                            # noqa: E402
import plain_checks                                           # noqa: E402
import targeted_break                                         # noqa: E402
from purlin import evidence as evidence_reader                 # noqa: E402
from purlin import fingerprint as fingerprint_module           # noqa: E402
from purlin import payload as payload_module                   # noqa: E402
from purlin import specs as specs_module                       # noqa: E402

RUNTIME_PATH = os.path.join('.purlin', 'runtime', 'audit_run.json')

# The last line, and the line before it.
SHARE = 'The audit found %d of %d rules strong (%d%%).'
NO_RULE_PASSES = 'The audit found no rule that passes its tests.'
COST = 'The model was asked %d %s for %d %s: $%.2f in all, $%.2f a rule.'

# What a rule read prints: its name and verdict, then one line per finding.
RULE_LINE = '%s %s   %s'
FINDING_LINE = '  %s'
NOT_PLANTED = '  %s: no bug was planted: %s.'
NO_EXPLANATION = ('%d %s read without the model\'s explanation: %s. Run '
                  'purlin:audit --all once it can be reached.')

# The language a test file is read in, for a spot test that cannot read it.
LANGUAGES = (
    (('.sh', '.bash', '.bats'), 'shell'), (('.sql',), 'SQL'),
    (('.py',), 'Python'), (('.js', '.jsx', '.mjs', '.cjs'), 'JavaScript'),
    (('.ts', '.tsx', '.mts', '.cts'), 'TypeScript'), (('.cs',), 'C#'),
    (('.go',), 'Go'),
)


def _plural(count, one, many):
    return one if count == 1 else many


def _git(project_root, *args):
    return subprocess.run(['git'] + list(args), cwd=project_root,
                          capture_output=True, text=True)


def head_commit(project_root):
    """The full sha of HEAD, or '' outside a repository with a commit."""
    found = _git(project_root, 'rev-parse', 'HEAD')
    return found.stdout.strip() if found.returncode == 0 else ''


def language_of(path):
    """The language word a spot test that cannot read a file names."""
    ext = os.path.splitext(str(path or ''))[1].lower()
    for endings, word in LANGUAGES:
        if ext in endings:
            return word
    return ext.lstrip('.') or 'these'


# ---------------------------------------------------------------------------
# Which rules are read
# ---------------------------------------------------------------------------

def code_changed(project_root, info, commit):
    """True when a file the feature covers differs from what `commit` held.

    An anchor covers the whole project but the records Purlin writes. An
    entry with no commit, or a commit this checkout does not hold, reads as
    changed.
    """
    if not commit:
        return True
    if (info or {}).get('is_anchor'):
        paths = list(fingerprint_module.RECORDS)
    else:
        paths = [fingerprint_module.pathspec(entry)
                 for entry in (info or {}).get('scope') or () if entry.strip()]
        if not paths:
            return False
    found = _git(project_root, 'diff', '--quiet', commit, '--', *paths)
    return found.returncode != 0


def rules_to_read(project_root, payload, features, selected, again=False):
    """`[(feature, rule entry)]` the audit reads, by feature then rule number.

    A rule is its feature's own (an anchor's rules are read once, as the
    anchor's), and `ai_audit.is_read` says whether it is read.
    """
    found = []
    for feature in payload.get('features') or ():
        name = feature.get('name')
        if name not in selected:
            continue
        info = features.get(name) or {}
        for rule in feature.get('rules') or ():
            if rule.get('feature') != name:
                continue
            entry = rule.get('audit') or {}
            changed = bool(entry) and code_changed(project_root, info,
                                                   entry.get('commit'))
            if ai_audit.is_read(rule, again=again, code_changed=changed):
                found.append((name, rule))
    found.sort(key=lambda pair: (pair[0], _number(pair[1].get('id'))))
    return found


def counted_rules(payload, selected):
    """`[(feature, rule entry)]` the share counts: each rule of a selected
    feature that passes its tests and has a tested proof."""
    return [(feature.get('name'), rule)
            for feature in payload.get('features') or ()
            if feature.get('name') in selected
            for rule in feature.get('rules') or ()
            if rule.get('feature') == feature.get('name')
            and ai_audit.passes(rule) and ai_audit.tested(rule)]


def _number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def last_entry(project_root, feature, rule_id):
    """The newest audit entry of a rule in either source, whatever hashes it
    was written for, or {}: what its planted bugs last found."""
    loaded = evidence_reader.load(project_root, feature)
    best = {}
    for source in evidence_reader.SOURCES:
        data = loaded['files'].get(source) or {}
        audit = data.get('audit')
        rules = audit.get('rules') if isinstance(audit, dict) else None
        entry = rules.get(rule_id) if isinstance(rules, dict) else None
        if isinstance(entry, dict) and str(entry.get('at') or '') >= str(
                best.get('at') or ''):
            best = entry
    return best


# ---------------------------------------------------------------------------
# One rule
# ---------------------------------------------------------------------------

def _sha256(text):
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()


def test_source_hash(tests):
    """The sha256 of the sorted lines `<file> <name> <sha256 of its source>`."""
    return _sha256('\n'.join(sorted(
        '%s %s %s' % (test.get('file'), test.get('name'),
                      _sha256(test.get('source') or ''))
        for test in tests)))


def _proof_tests(reading, proof_id):
    return [{'file': test.get('file'), 'name': test.get('name'),
             'source': test.get('body')}
            for test in reading.get('tests') or ()
            if test.get('proof') == proof_id and not test.get('manual')
            and test.get('file')]


def spot_tests(project_root, reading, not_read):
    """The spot tests' findings for one rule, in order and once each.
    `not_read` gains `(check, language)` for each check a test's language
    cannot be read for."""
    findings = []
    texts = {proof['id']: proof.get('text') for proof in reading['proofs']}
    for test in reading.get('tests') or ():
        if test.get('manual') or not test.get('file') or test.get('body') is None:
            continue
        found = plain_checks.check(
            project_root, reading['feature'],
            {'id': test['proof'], 'text': texts.get(test['proof'])},
            {'file': test['file'], 'name': test['name'],
             'source': test['body']})
        for check, finding in found or ():
            if finding is None:
                not_read.add((check, language_of(test['file'])))
            elif finding not in findings:
                findings.append(finding)
    return findings


def _survived_finding(proof_id, kept, last):
    """The finding a kept `survived` result carries, as its entry wrote it."""
    start = '%s: the test still passes when' % proof_id
    for line in last.get('findings') or ():
        if str(line).startswith(start):
            return line
    changed = (str(kept.get('after') or '').strip().splitlines() or [''])[0]
    return targeted_break.SURVIVED % (proof_id, kept.get('file'),
                                      kept.get('line') or 0, changed.strip())


def planted_bugs(project_root, reading, info, last, ask, code_part):
    """`(breaks, findings, not_planted, asked)` for one rule's proofs.

    `breaks` is `{proof: entry}` as the evidence holds it; `findings` the
    sentence of each bug that survived; `not_planted` `[(proof, why)]`;
    `asked` `{proof: result}` for the bugs planted this run. Raises
    `targeted_break.ProjectChanged`.
    """
    breaks, findings, not_planted, asked = {}, [], [], {}
    if reading.get('anchor'):
        return breaks, findings, not_planted, asked
    scope_files = fingerprint_module.expand_scope(
        project_root, info.get('scope') or [])[0]
    kept_breaks = last.get('breaks') if isinstance(last.get('breaks'),
                                                   dict) else {}
    for proof in reading.get('proofs') or ():
        if proof.get('manual'):
            continue
        tests = _proof_tests(reading, proof['id'])
        if not tests:
            continue
        key = ai_audit.break_key(test_source_hash(tests), code_part)
        kept = kept_breaks.get(proof['id'])
        if isinstance(kept, dict) and kept.get('break_key') == key:
            breaks[proof['id']] = kept
            if kept.get('result') == 'survived':
                findings.append(_survived_finding(proof['id'], kept, last))
            continue
        result = targeted_break.break_proof(
            project_root, reading['feature'],
            {'id': proof['id'], 'text': proof.get('text'),
             'rule': reading['rule'], 'rule_text': reading.get('rule_text')},
            tests, scope_files, ask)
        result = dict(result or {})
        entry = {'file': result.get('file'), 'line': result.get('line'),
                 'before': result.get('before'), 'after': result.get('after'),
                 'result': result.get('result') or 'not made',
                 'why': result.get('why') or '', 'break_key': key}
        breaks[proof['id']] = entry
        asked[proof['id']] = entry['result']
        if entry['result'] == 'survived':
            findings.append(result.get('finding') or _survived_finding(
                proof['id'], entry, {}))
        elif entry['result'] == 'not made':
            not_planted.append((proof['id'], entry['why']))
    return breaks, findings, not_planted, asked


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

def run(project_root, features, selected, again=False, out=None):
    """For each rule the audit reads (ai_audit RULE-1; `again` reads every passing rule):
    the spot tests, then one planted bug per proof that needs one, then the model's
    reading. Writes one audit.rules entry per rule read, through evidence.write_audit;
    writes .purlin/runtime/audit_run.json; prints the findings, the cost line and, last,
    the share. Returns 0, or 1 when a planted bug stopped it (planted_bug RULE-6)."""
    out = out or sys.stdout

    def say(line=''):
        print(line, file=out)

    started = time.time()
    if features is None:
        features = specs_module.scan_specs(project_root)
    selected = set(features if selected is None else selected)
    payload = payload_module.build_payload(project_root, generated_by='audit')
    to_read = rules_to_read(project_root, payload, features, selected, again)

    not_read = set()
    done = []          # one dict per rule read, in order
    code_parts = {}
    try:
        for feature, rule in to_read:
            info = features.get(feature) or {}
            reading = ai_audit.reading_for(project_root, payload, feature,
                                           rule['id'])
            spent = []
            ask = functools.partial(ai_audit.ask_for_bug, project_root,
                                    spent=spent)
            if feature not in code_parts:
                code_parts[feature] = fingerprint_module.code_part(
                    project_root, info)
            spot = spot_tests(project_root, reading, not_read)
            breaks, survived, not_planted, asked = planted_bugs(
                project_root, reading, info,
                last_entry(project_root, feature, rule['id']), ask,
                code_parts[feature])
            findings = spot + [line for line in survived if line not in spot]
            reading['findings'] = findings
            done.append({'feature': feature, 'rule': rule, 'reading': reading,
                         'findings': findings, 'breaks': breaks,
                         'not_planted': not_planted, 'asked': asked,
                         'spent': spent,
                         'verdict': 'weak' if (spot or survived) else 'strong'})
    except targeted_break.ProjectChanged as stopped:
        say(targeted_break.STOPPED % _changed_path(project_root, stopped))
        return 1

    answers = ai_audit.audit_all(project_root,
                                 [item['reading'] for item in done])
    criteria = ai_audit.criteria_hash(ai_audit.criteria_text(project_root))
    commit = head_commit(project_root)
    by_feature = {}
    unreached = {}
    for item, answer in zip(done, answers):
        reached = not answer.get('why')
        if not reached:
            unreached[answer['why']] = unreached.get(answer['why'], 0) + 1
        item['answer'] = answer
        found = {'verdict': item['verdict'], 'findings': item['findings'],
                 'breaks': item['breaks'],
                 'explanation': answer.get('explanation') or [],
                 'notes': answer.get('notes') or [],
                 'model': answer.get('model') if reached else 'unknown',
                 'criteria': answer.get('criteria') or criteria}
        by_feature.setdefault(item['feature'], {})[item['rule']['id']] = \
            evidence_writer.audit_entry(item['rule'], found, commit)
    for feature, entries in sorted(by_feature.items()):
        evidence_writer.write_audit(project_root, 'local', feature,
                                    features.get(feature) or {}, entries)

    for check, language in sorted(not_read):
        say(plain_checks.NOT_READ % (check, language))
    for item in done:
        rule_id = item['rule']['id']
        say(RULE_LINE % (item['feature'], rule_id, item['verdict']))
        for line in item['findings']:
            say(FINDING_LINE % line)
        for proof_id, why in item['not_planted']:
            say(NOT_PLANTED % (proof_id, str(why).rstrip('.')))
    for why, count in sorted(unreached.items()):
        say(NO_EXPLANATION % (count, _plural(count, 'rule was', 'rules were'),
                              why))

    costs = write_costs(project_root, done, commit, time.time() - started)
    if costs['cost_usd'] is not None and done:
        say(COST % (costs['calls'], _plural(costs['calls'], 'time', 'times'),
                    len(done), _plural(len(done), 'rule', 'rules'),
                    costs['cost_usd'], costs['cost_usd'] / len(done)))
    say(share_line(payload, selected, done))
    return 0


def _changed_path(project_root, stopped):
    path = getattr(stopped, 'path', None) or (stopped.args[0] if stopped.args
                                              else '')
    path = str(path)
    if os.path.isabs(path):
        path = os.path.relpath(path, project_root)
    return path.replace(os.sep, '/')


def share_line(payload, selected, done):
    """The last line: the share of the rules that pass their tests the audit
    found strong, over what it read now and the entries still current."""
    now = {(item['feature'], item['rule']['id']): item['verdict']
           for item in done}
    counted = counted_rules(payload, selected)
    if not counted:
        return NO_RULE_PASSES
    strong = 0
    for feature, rule in counted:
        verdict = now.get((feature, rule.get('id')))
        if verdict is None:
            verdict = (rule.get('audit') or {}).get('verdict')
        strong += verdict == 'strong'
    return SHARE % (strong, len(counted),
                    int(math.floor(100.0 * strong / len(counted))))


def write_costs(project_root, done, commit, seconds):
    """Write `.purlin/runtime/audit_run.json`; the totals it holds."""
    rules = {}
    calls, total, any_cost = 0, 0.0, False
    for item in done:
        spent = list(item['spent'])
        answer = item.get('answer') or {}
        if answer.get('why') != ai_audit.NOT_ON_PATH:
            spent.append({'cost_usd': answer.get('cost_usd'),
                          'seconds': answer.get('seconds') or 0.0})
        costs = [one['cost_usd'] for one in spent
                 if one.get('cost_usd') is not None]
        cost = round(sum(costs), 6) if costs else None
        any_cost = any_cost or bool(costs)
        calls += len(spent)
        total += sum(costs)
        rules['%s %s' % (item['feature'], item['rule']['id'])] = {
            'calls': len(spent), 'cost_usd': cost,
            'seconds': int(round(sum(one.get('seconds') or 0.0
                                     for one in spent))),
            'breaks': dict(item['asked'])}
    data = {'at': evidence_writer.now_iso(), 'commit': commit, 'calls': calls,
            'cost_usd': round(total, 6) if any_cost else None,
            'seconds': int(round(seconds)), 'rules': rules}
    path = os.path.join(project_root, RUNTIME_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write('\n')
    return data
