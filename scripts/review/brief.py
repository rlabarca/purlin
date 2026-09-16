#!/usr/bin/env python3
"""Build the brief the machine writes about one rule.

    brief.py --feature <f> [--rule RULE-N] [--ai] [--project-root DIR]

The brief reports; it recommends nothing. It gathers the evidence in layers,
cheapest first, and stops when it has enough for the rule's risk:

    low     the free checks on the proof text and on the test body
    medium  plus the test strength from the latest record
    high    plus the model review

What it ends with is four things and no judgment: the test strength beside the
project minimum, the free-check findings under the names
`references/review_criteria.md` gives them, the model review's observations one
sentence at a time, and whether the review settled the question. A rule whose
brief settled with nothing observed is one the machine could read; anything
else needs a person.

The brief lands beside the records, as
`.purlin/briefs/<feature>/<RULE-N>.<hash8>.brief.json`, with a text rendering
beside it. A brief is named for the triple it was built from, so a brief for
text that has since changed is simply not found again.

The JSON is evidence: CI commits it with the record and a signature names it.
Building a brief again for the same triple leaves that file untouched unless
the evidence in it changed, so reading a brief does not dirty the tree. The
`.brief.txt` beside it is a local view, named in `.gitignore` and never
committed.

Exit codes: 0 a brief was built, 1 the rule is not in the project, 2 the
command line was wrong.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _path in (_MCP_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import static_checks                                          # noqa: E402
from purlin import (checks,                                    # noqa: E402
                    console as console_module,
                    gate as gate_module, payload as payload_module,
                    signatures as signatures_module, states)

SCHEMA = 'purlin-brief/2'
USAGE = ('Usage: brief.py --feature <f> [--rule RULE-N] [--ai] '
         '[--project-root DIR]')

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2

CRITERIA = os.path.join('references', 'review_criteria.md')

# Where CI commits the briefs, beside the records and under the same branch
# rule.
BRIEFS_DIR = os.path.join('.purlin', 'briefs')

# The layers, cheapest first, and the lowest risk each one is built for.
LAYERS = ('proof text', 'test body', 'test strength', 'model review')
_LAYERS_BY_RISK = {
    'low': LAYERS[:2],
    'medium': LAYERS[:3],
    'high': LAYERS,
}

ATTACHMENTS = os.path.join('.purlin', 'runtime', 'attachments')

NOT_AVAILABLE = 'not available'


# ---------------------------------------------------------------------------
# One brief
# ---------------------------------------------------------------------------

def load_payload(project_root, payload=None):
    """The payload to read, built when the caller did not hand one over."""
    if payload is not None:
        return payload
    return payload_module.build_payload(project_root, generated_by='brief')


def rule_entry(payload, feature, rule):
    """The rule dict for `<feature> <rule>`, or None.

    A required rule belongs to the feature its own `feature` field names, so a
    brief is built where the rule lives and not once per consumer.
    """
    for entry in (payload or {}).get('features') or ():
        for item in entry.get('rules') or ():
            if item.get('feature') == feature and item.get('id') == rule:
                return item
    return None


def triple_for(entry):
    """The triple hash of one rule entry."""
    return signatures_module.triple_hash(
        entry.get('rule_hash'), entry.get('proof_hash'), entry.get('test_hash'))


def build_brief(project_root, payload, feature, rule, ai=False):
    """The brief for one rule, as a dict. None when the rule is not there."""
    payload = load_payload(project_root, payload)
    entry = rule_entry(payload, feature, rule)
    if entry is None:
        return None

    risk = entry.get('risk') or 'low'
    layers = _LAYERS_BY_RISK.get(risk, _LAYERS_BY_RISK['low'])
    gate = payload.get('gate') or {}
    min_strength = gate.get('min_strength') or 0
    feature_entry = _feature_entry(payload, feature)

    proofs = [{'id': proof.get('id'), 'tier': proof.get('tier'),
               'env': proof.get('env'), 'text': proof.get('text'),
               'findings': list(proof.get('findings') or [])}
              for proof in entry.get('proofs') or ()]

    brief = {
        'schema': SCHEMA,
        'feature': feature,
        'rule': rule,
        'risk': risk,
        'origin': entry.get('origin'),
        'rule_text': entry.get('text'),
        'proofs': proofs,
        'rule_hash': entry.get('rule_hash'),
        'proof_hash': entry.get('proof_hash'),
        'test_hash': entry.get('test_hash'),
        'test_hash_kind': entry.get('test_hash_kind'),
        'design_hash': entry.get('design_hash'),
        'triple_hash': triple_for(entry),
        'layers': list(layers),
        'tests': _test_layer(project_root, feature, entry),
        'test_strength': None,
        'min_strength': min_strength,
        'record': (feature_entry.get('latest_record') or {}).get('path'),
        'design': _design_layer(project_root, payload, feature, entry),
        'ai_review': None,
        'observations': [],
        'settled': None,
        'generated_at': payload_module.now_iso(),
    }

    if 'test strength' in layers:
        brief['test_strength'] = feature_entry.get('test_strength')

    if 'model review' in layers and asks_for_a_review(payload, entry):
        brief['ai_review'] = (_model_review(project_root, brief) if ai
                              else NOT_AVAILABLE)
        brief['observations'], brief['settled'] = model_observations(
            brief['ai_review'])

    return brief


def asks_for_a_review(payload, entry):
    """True when a rule's own risk is at or above the project's review level.

    The strong cell asks the same question when it decides whether a brief was
    owed, so the answer is computed from the one place that knows it.
    """
    cfg = gate_module.resolve_gate(payload.get('gate') or {})
    threshold = states.review_threshold(
        cfg, cfg.mutation_engine not in (None, 'none'))
    return gate_module.risk_at_or_above(entry.get('risk') or 'low', threshold)


def _feature_entry(payload, feature):
    for entry in (payload or {}).get('features') or ():
        if entry.get('name') == feature:
            return entry
    return {}


def _test_layer(project_root, feature, entry):
    """One record per test backing the rule: its body and its free findings."""
    proof_ids = set()
    for proof in entry.get('proofs') or ():
        if proof.get('id'):
            proof_ids.add(proof['id'])

    seen = set()
    tests = []
    for proof in entry.get('proofs') or ():
        if proof.get('tier') == 'manual':
            tests.append({'proof': proof.get('id'), 'file': None, 'name': None,
                          'body': None, 'findings': ['manual'],
                          'reasons': ['The evidence for a manual proof is the '
                                      "signer's note, not a test."]})
            continue
        for test in proof.get('tests') or ():
            key = (proof.get('id'), test.get('file'), test.get('name'))
            if key in seen:
                continue
            seen.add(key)
            tests.append(_one_test(project_root, feature, proof.get('id'),
                                   test, proof_ids))
    return tests


def _one_test(project_root, feature, proof_id, test, proof_ids):
    path = test.get('file') or ''
    body = None
    if path:
        try:
            body = static_checks._extract_test_code(
                project_root, feature, proof_id, path, test.get('name'))
        except (OSError, UnicodeDecodeError, ValueError):
            body = None
    findings = []
    reasons = []
    full = os.path.join(project_root, *path.split('/')) if path else ''
    if full and os.path.isfile(full):
        try:
            results = static_checks.analyze_test_file(full, feature)
        except (OSError, UnicodeDecodeError, ValueError, SyntaxError):
            results = []
        results = [result for result in results
                   if result.get('proof_id') == proof_id]
        # Several tests may back one proof: a finding belongs to the test it
        # was found in. A name the checks cannot place keeps every finding for
        # the proof, so nothing found is ever hidden.
        named = static_checks.test_name_matches(
            test.get('name'), [result.get('test_name') for result in results])
        for index, result in enumerate(results):
            if named and index not in named:
                continue
            if result.get('status') != 'fail':
                continue
            findings.append(result.get('check'))
            reasons.append(result.get('reason') or result.get('check'))
    return {'proof': proof_id, 'file': path or None,
            'name': test.get('name'), 'body': body,
            'findings': findings, 'reasons': reasons}


def _design_layer(project_root, payload, feature, entry):
    """The mock beside the screenshot, for a rule a designer owns."""
    if entry.get('origin') != 'design':
        return None
    owner = _feature_entry(payload, entry.get('feature') or feature)
    patterns = list(owner.get('source_globs') or ())
    if owner.get('source_path'):
        patterns.append(owner['source_path'])
    elif owner.get('source') and not owner.get('source_globs'):
        patterns.append(owner['source'])
    mocks = []
    for pattern in patterns:
        matched = sorted(glob.glob(os.path.join(project_root, pattern)))
        if matched:
            mocks.extend(os.path.relpath(path, project_root).replace(os.sep, '/')
                         for path in matched)
        else:
            mocks.append(pattern)
    shots = []
    for proof in entry.get('proofs') or ():
        rel = os.path.join(ATTACHMENTS, feature, '%s.png' % proof.get('id'))
        if os.path.isfile(os.path.join(project_root, rel)):
            shots.append(rel.replace(os.sep, '/'))
    return {'mock': mocks, 'screenshot': shots,
            'pinned': entry.get('design_hash')}


# ---------------------------------------------------------------------------
# The model review
# ---------------------------------------------------------------------------

def criteria_text(project_root):
    """`references/review_criteria.md`, verbatim, from the plugin or project."""
    for base in (_ROOT, project_root):
        path = os.path.join(base, CRITERIA)
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as handle:
                return handle.read()
    return ''


# What the model is asked for: what the test observes set against what the
# proof names, one sentence at a time, and a plain statement when it cannot
# tell. Never a recommendation and never a grade: the brief reports, and the
# person reading it decides.
INSTRUCTION = (
    'Read one rule against the criteria above and report what you see. Answer '
    'in this shape and nothing else:',
    '',
    '    settled: yes',
    '    - <one sentence, naming the proof it concerns>',
    '',
    'Write `settled: yes` when you could tell what each test observes against '
    'what its proof names, and `settled: no` when you could not.',
    'Write one line per observation, each opening with `- `, each one sentence '
    'long, and each naming the proof it concerns. Write no line at all when '
    'you observed nothing.',
    'Do not recommend a change, do not grade the rule and do not score it. A '
    'person reads what you write and decides.',
)


def model_prompt(project_root, brief):
    """The criteria verbatim, then this rule's rule, proof, test and numbers."""
    parts = [criteria_text(project_root), '', '---', '']
    parts.extend(INSTRUCTION)
    parts.extend([
        '',
        '%s %s (risk %s, origin %s)'
        % (brief.get('feature'), brief.get('rule'), brief.get('risk'),
           brief.get('origin')),
        'Rule: %s' % (brief.get('rule_text') or '')])
    for proof in brief.get('proofs') or ():
        parts.append('%s (@%s): %s' % (proof.get('id'), proof.get('tier'),
                                       proof.get('text')))
        if proof.get('findings'):
            parts.append('  findings: %s' % ', '.join(proof['findings']))
    for test in brief.get('tests') or ():
        parts.append('')
        parts.append('Test for %s: %s::%s'
                     % (test.get('proof'), test.get('file'), test.get('name')))
        if test.get('findings'):
            parts.append('  findings: %s' % ', '.join(test['findings']))
        if test.get('body'):
            parts.append(test['body'])
    strength = brief.get('test_strength')
    parts.append('')
    parts.append('Test strength: %s (minimum %s)'
                 % ('n/a' if strength is None else '%d percent' % strength,
                    brief.get('min_strength')))
    return '\n'.join(parts)


def _model_review(project_root, brief):
    """The model's answer, or `not available` when no model can be reached."""
    if not shutil.which('claude'):
        return NOT_AVAILABLE
    try:
        result = subprocess.run(
            ['claude', '-p', model_prompt(project_root, brief)],
            capture_output=True, text=True, cwd=project_root, timeout=300)
    except (subprocess.SubprocessError, OSError):
        return NOT_AVAILABLE
    if result.returncode != 0 or not result.stdout.strip():
        return NOT_AVAILABLE
    return result.stdout.strip()


_SETTLED_RE = re.compile(r'^\s*settled\s*:\s*(yes|no|true|false)\s*$', re.I)
_OBSERVATION_RE = re.compile(r'^\s*[-*]\s+(.*\S)\s*$')


def model_observations(answer):
    """`(observations, settled)` read out of one model answer.

    An answer nobody could get, or one that never says whether it settled,
    leaves `settled` None: the strong cell reads that as a question still
    open, which is the honest reading of an answer that is not there.
    """
    if not answer or answer == NOT_AVAILABLE:
        return [], None
    settled = None
    observations = []
    for line in str(answer).splitlines():
        found = _SETTLED_RE.match(line)
        if found:
            settled = found.group(1).lower() in ('yes', 'true')
            continue
        found = _OBSERVATION_RE.match(line)
        if found:
            observations.append(found.group(1))
    return observations, settled


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def brief_paths(project_root, feature, rule, triple):
    """`(json_path, text_path)` for one brief, beside the records."""
    stem = os.path.join(project_root, BRIEFS_DIR, feature,
                        '%s.%s.brief' % (rule, str(triple)[:8]))
    return stem + '.json', stem + '.txt'


# What says when and where a brief was built, not what it found. A brief that
# differs from the one on disk only here is the same evidence.
_WHEN_BUILT = ('generated_at', 'record')


def same_evidence(one, other):
    """True when two briefs differ at most in when and where they were built."""
    if not isinstance(one, dict) or not isinstance(other, dict):
        return False

    def evidence(brief):
        # Through JSON, so a tuple built in memory equals the list read back.
        return json.loads(json.dumps({key: value for key, value in brief.items()
                                      if key not in _WHEN_BUILT}))
    return evidence(one) == evidence(other)


def write_brief(project_root, brief):
    """Write one brief and its text rendering. Returns the JSON path.

    The JSON is left untouched when the brief already on disk for this triple
    holds the same evidence, so a second read of a brief changes no tracked file.
    """
    json_path, text_path = brief_paths(
        project_root, brief['feature'], brief['rule'], brief['triple_hash'])
    if not json_path:
        return None
    directory = os.path.dirname(json_path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    try:
        with open(json_path, 'r', encoding='utf-8') as handle:
            existing = json.load(handle)
    except (OSError, ValueError, UnicodeDecodeError):
        existing = None
    if not same_evidence(existing, brief):
        with open(json_path, 'w', encoding='utf-8') as handle:
            json.dump(brief, handle, indent=2, sort_keys=True)
            handle.write('\n')
    with open(text_path, 'w', encoding='utf-8') as handle:
        handle.write(render_brief(brief))
    return os.path.relpath(json_path, project_root).replace(os.sep, '/')


def write_briefs(project_root, payload=None, rules=None, ai=False):
    """Write a brief for every rule a review is owed for. Returns their paths.

    A review is owed when the rule's risk is at or above `ai_review_at` and its
    passed cell counts: below that risk nothing asks the model a question, and
    with no counting pass there is no test result to set the proof against.

    `rules` narrows the list: each entry is `(feature, rule)` or a dict with
    `feature` and `rule`. CI writes these with the record, so a person opens a
    brief rather than waiting for one.
    """
    payload = load_payload(project_root, payload)
    targets = []
    if rules is not None:
        for item in rules:
            if isinstance(item, dict):
                pair = (item.get('owner') or item.get('feature'),
                        item.get('rule'))
            else:
                pair = tuple(item)
            if pair[0] and pair[1] and pair not in targets:
                targets.append(pair)
    else:
        for feature_entry in payload.get('features') or ():
            for entry in feature_entry.get('rules') or ():
                if entry.get('feature') != feature_entry.get('name'):
                    continue
                if not asks_for_a_review(payload, entry):
                    continue
                if not ((entry.get('cells') or {}).get('passed')
                        or {}).get('counts'):
                    continue
                pair = (entry['feature'], entry['id'])
                if pair not in targets:
                    targets.append(pair)

    written = []
    for feature, rule in targets:
        brief = build_brief(project_root, payload, feature, rule, ai=ai)
        if brief is None:
            continue
        path = write_brief(project_root, brief)
        if path:
            written.append(path)
    return written


# ---------------------------------------------------------------------------
# The text a person reads
# ---------------------------------------------------------------------------

def render_brief(brief):
    """The brief as text: the rule, the proof, the test, and what it found."""
    lines = []
    lines.append('%s %s   risk %s   origin %s'
                 % (brief.get('feature'), brief.get('rule'),
                    brief.get('risk'), brief.get('origin')))
    lines.append('')
    lines.append('Rule')
    lines.append('  %s' % (brief.get('rule_text') or ''))
    lines.append('')
    lines.append('Proof')
    for proof in brief.get('proofs') or ():
        lines.append('  %s (@%s%s): %s'
                     % (proof.get('id'), proof.get('tier'),
                        ', %s' % proof['env'] if proof.get('env') else '',
                        proof.get('text')))
        for finding in proof.get('findings') or ():
            lines.append('    %s: %s' % (finding, checks.describe(finding)))
    lines.append('')
    lines.append('Test')
    if not brief.get('tests'):
        lines.append('  Nothing backs this rule yet.')
    for test in brief.get('tests') or ():
        if test.get('file'):
            lines.append('  %s  %s::%s' % (test.get('proof'), test['file'],
                                           test.get('name')))
        else:
            lines.append('  %s  manual' % test.get('proof'))
        for reason in test.get('reasons') or ():
            lines.append('    %s' % reason)
        for line in (test.get('body') or '').splitlines():
            lines.append('    %s' % line)
    lines.append('')
    strength = brief.get('test_strength')
    if 'test strength' in (brief.get('layers') or ()):
        lines.append('Test strength: %s   minimum %s'
                     % ('n/a' if strength is None else '%d percent' % strength,
                        brief.get('min_strength')))
    if brief.get('record'):
        lines.append('Record: %s' % brief['record'])
    design = brief.get('design')
    if design:
        lines.append('Mock: %s' % (', '.join(design.get('mock') or ())
                                   or 'none pinned'))
        lines.append('Screenshot: %s'
                     % (', '.join(design.get('screenshot') or ()) or 'none'))
    # The model review is printed only where one was asked for, so a brief
    # for a rule whose risk never reaches `ai_review_at` says nothing about a
    # review that was never owed.
    if brief.get('ai_review') is not None:
        if brief['ai_review'] != NOT_AVAILABLE:
            lines.append('')
            lines.append('Model review')
            for line in str(brief['ai_review']).splitlines():
                lines.append('  %s' % line)
        lines.append('')
        lines.append('Observations')
        for observation in brief.get('observations') or ():
            lines.append('  %s' % observation)
        if not brief.get('observations'):
            lines.append('  None.')
        lines.append('Settled: %s' % _settled_word(brief.get('settled')))
    lines.append('')
    return '\n'.join(lines)


def _settled_word(settled):
    """`yes`, `no` or `not answered`, the three states of a model review."""
    if settled is True:
        return 'yes'
    if settled is False:
        return 'no'
    return 'not answered'


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class _Args(object):
    """One parsed invocation, or the reason it could not be parsed."""

    __slots__ = ('feature', 'rule', 'ai', 'project_root', 'error', 'help')

    def __init__(self):
        self.feature = None
        self.rule = None
        self.ai = False
        self.project_root = '.'
        self.error = None
        self.help = False


def _parse(argv):
    args = _Args()
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item in ('-h', '--help'):
            args.help = True
            return args
        if item == '--ai':
            args.ai = True
        elif item in ('--feature', '--rule', '--project-root'):
            if not rest:
                args.error = '%s needs a value.' % item
                return args
            value = rest.pop(0)
            setattr(args, item[2:].replace('-', '_'), value)
        else:
            args.error = 'unexpected argument %s' % item
            return args
    if not args.feature:
        args.error = '--feature is required.'
    return args


def main(argv=None):
    console_module.force_utf8_stdio()
    args = _parse(sys.argv[1:] if argv is None else argv)
    if args.help:
        print(__doc__.strip())
        return EXIT_OK
    if args.error:
        print(USAGE, file=sys.stderr)
        print('brief.py: %s' % args.error, file=sys.stderr)
        return EXIT_BAD_INVOCATION
    if not os.path.isdir(args.project_root or '.'):
        print('brief.py: not a directory: %r' % args.project_root,
              file=sys.stderr)
        return EXIT_BAD_INVOCATION

    payload = load_payload(args.project_root)
    rules = ([args.rule] if args.rule
             else _rules_of(payload, args.feature))
    if not rules:
        print('brief: no rule of %s is in this project.' % args.feature)
        return EXIT_NOTHING

    built = 0
    for rule in rules:
        brief = build_brief(args.project_root, payload, args.feature, rule,
                            ai=args.ai)
        if brief is None:
            continue
        write_brief(args.project_root, brief)
        print(render_brief(brief))
        built += 1
    return EXIT_OK if built else EXIT_NOTHING


def _rules_of(payload, feature):
    entry = _feature_entry(payload, feature)
    return [rule['id'] for rule in entry.get('rules') or ()
            if rule.get('feature') == feature]


if __name__ == '__main__':
    sys.exit(main())
