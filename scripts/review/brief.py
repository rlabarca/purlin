#!/usr/bin/env python3
"""Build the review brief a person reads before approving one rule.

    brief.py --feature <f> [--rule RULE-N] [--ai] [--project-root DIR]

The brief answers one question: does this test prove this rule? It gathers the
evidence in layers, cheapest first, and stops when it has enough for the rule's
risk:

    low     the free checks on the proof text and on the test body
    medium  plus the test strength from the latest record
    high    plus the model review

The criteria are `references/review_criteria.md` and nothing else: the free
checks below are named there, the four verdicts are named there, and the model
prompt is that file verbatim followed by this rule's evidence. Nothing here
grades a rule on its own account.

The brief is written beside the approval it informs, as
`specs/<category>/<feature>.approvals/<RULE-N>.<hash8>.brief.json` with a text
rendering beside it. A brief is named for the triple it was built from, so a
brief for text that has since changed is simply not found again.

Exit codes: 0 a brief was built, 1 the rule is not in the project, 2 the
command line was wrong.
"""

import glob
import json
import os
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
from purlin import (approvals as approvals_module, checks,     # noqa: E402
                    console as console_module,
                    gate as gate_module, payload as payload_module,
                    specs as specs_module)

import approve as approve_module                              # noqa: E402

SCHEMA = 'purlin-brief/1'
USAGE = ('Usage: brief.py --feature <f> [--rule RULE-N] [--ai] '
         '[--project-root DIR]')

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2

CRITERIA = os.path.join('references', 'review_criteria.md')

# The four words a brief writes, and the only four a reviewer uses.
READY = 'ready'
ADD_A_CASE = 'add a case'
REWRITE = 'rewrite the proof'
NEEDS_A_HUMAN = 'needs a human'
VERDICTS = (READY, ADD_A_CASE, REWRITE, NEEDS_A_HUMAN)

# The layers, cheapest first, and the lowest risk each one is built for.
LAYERS = ('proof text', 'test body', 'test strength', 'model review')
_LAYERS_BY_RISK = {
    'low': LAYERS[:2],
    'medium': LAYERS[:3],
    'high': LAYERS,
}

ATTACHMENTS = os.path.join('.purlin', 'runtime', 'attachments')


# ---------------------------------------------------------------------------
# One brief
# ---------------------------------------------------------------------------

def build_brief(project_root, payload, feature, rule, ai=False):
    """The brief for one rule, as a dict. None when the rule is not there."""
    payload = approve_module.load_payload(project_root, payload)
    entry = approve_module.rule_entry(payload, feature, rule)
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
        'state': entry.get('state'),
        'rule_text': entry.get('text'),
        'proofs': proofs,
        'rule_hash': entry.get('rule_hash'),
        'proof_hash': entry.get('proof_hash'),
        'test_hash': entry.get('test_hash'),
        'test_hash_kind': entry.get('test_hash_kind'),
        'design_hash': entry.get('design_hash'),
        'triple_hash': approve_module.triple_for(entry),
        'layers': list(layers),
        'tests': _test_layer(project_root, feature, entry),
        'test_strength': None,
        'min_strength': min_strength,
        'record': (feature_entry.get('latest_record') or {}).get('path'),
        'design': _design_layer(project_root, payload, feature, entry),
        'ai_review': None,
        'generated_at': payload_module.now_iso(),
    }

    if 'test strength' in layers:
        brief['test_strength'] = feature_entry.get('test_strength')

    if 'model review' in layers and (entry.get('flags') or {}).get(
            'needs_ai_review'):
        brief['ai_review'] = (_model_review(project_root, brief) if ai
                              else 'not available')

    brief['verdict'], brief['reasons'] = verdict_for(brief)
    return brief


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
                                      'approver\'s note, not a test.']})
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
                project_root, feature, proof_id, path)
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
        for result in results:
            if result.get('proof_id') != proof_id:
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


def model_prompt(project_root, brief):
    """The criteria verbatim, then this rule's rule, proof, test and numbers."""
    parts = [criteria_text(project_root),
             '',
             '---',
             '',
             'Review one rule against the criteria above. Answer with one of '
             'the four verdicts on the first line and at most five sentences '
             'after it.',
             '',
             '%s %s (risk %s, origin %s)'
             % (brief.get('feature'), brief.get('rule'), brief.get('risk'),
                brief.get('origin')),
             'Rule: %s' % (brief.get('rule_text') or '')]
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
        return 'not available'
    try:
        result = subprocess.run(
            ['claude', '-p', model_prompt(project_root, brief)],
            capture_output=True, text=True, cwd=project_root, timeout=300)
    except (subprocess.SubprocessError, OSError):
        return 'not available'
    if result.returncode != 0 or not result.stdout.strip():
        return 'not available'
    return result.stdout.strip()


def model_verdict(answer):
    """The verdict a model answer opens with, or None."""
    if not answer or answer == 'not available':
        return None
    first = answer.strip().splitlines()[0].strip().strip('.').lower()
    for word in VERDICTS:
        if first.startswith(word):
            return word
    return None


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------

def verdict_for(brief):
    """`(verdict, reasons)` from the layers the brief actually ran."""
    reasons = []
    blocking = []
    advisory = []
    for proof in brief.get('proofs') or ():
        for finding in proof.get('findings') or ():
            (blocking if finding in checks.BLOCKING else advisory).append(
                '%s %s: %s' % (proof.get('id'), finding,
                               checks.describe(finding)))
    test_findings = []
    manual = False
    for test in brief.get('tests') or ():
        for finding in test.get('findings') or ():
            if finding == 'manual':
                manual = True
                continue
            test_findings.append('%s %s' % (test.get('proof'), finding))
    reasons.extend(blocking)

    if blocking:
        return REWRITE, reasons

    reasons.extend(test_findings)
    if test_findings:
        return NEEDS_A_HUMAN, reasons

    if manual:
        reasons.append('A manual proof is always read by a person.')
        return NEEDS_A_HUMAN, reasons

    design = brief.get('design')
    if design is not None and not design.get('screenshot'):
        reasons.append('A design rule needs the screenshot the test captured '
                       'beside the mock, and none was found.')
        return NEEDS_A_HUMAN, reasons

    from_model = model_verdict(brief.get('ai_review'))
    if from_model:
        reasons.append('The model review answered %s.' % from_model)
        return from_model, reasons

    reasons.extend(advisory)
    if any('happy_path_only' in reason for reason in advisory):
        return ADD_A_CASE, reasons

    strength = brief.get('test_strength')
    minimum = brief.get('min_strength') or 0
    if strength is not None and strength < minimum:
        reasons.append('Test strength is %d percent, below the minimum of %d.'
                       % (strength, minimum))
        return ADD_A_CASE, reasons

    return READY, reasons


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def brief_paths(project_root, feature, rule, triple):
    """`(json_path, text_path)` for one brief, or `(None, None)`."""
    info = specs_module.scan_specs(project_root).get(feature)
    directory = approvals_module.approvals_dir(project_root, info or {})
    if not directory:
        return None, None
    stem = os.path.join(directory, '%s.%s.brief' % (rule, str(triple)[:8]))
    return stem + '.json', stem + '.txt'


def write_brief(project_root, brief):
    """Write one brief and its text rendering. Returns the JSON path."""
    json_path, text_path = brief_paths(
        project_root, brief['feature'], brief['rule'], brief['triple_hash'])
    if not json_path:
        return None
    directory = os.path.dirname(json_path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with open(json_path, 'w', encoding='utf-8') as handle:
        json.dump(brief, handle, indent=2, sort_keys=True)
        handle.write('\n')
    with open(text_path, 'w', encoding='utf-8') as handle:
        handle.write(render_brief(brief))
    return os.path.relpath(json_path, project_root).replace(os.sep, '/')


def write_briefs(project_root, payload=None, rules=None, ai=False):
    """Write a brief for every rule on the review list. Returns their paths.

    `rules` narrows the list: each entry is `(feature, rule)` or a dict with
    `feature` and `rule`. Without it the review list the payload computed is
    the list, which is what CI writes so a reviewer opens a brief rather than
    waiting for one.
    """
    payload = approve_module.load_payload(project_root, payload)
    targets = []
    for item in (rules if rules is not None else payload.get('review_list') or ()):
        if isinstance(item, dict):
            pair = (item.get('owner') or item.get('feature'), item.get('rule'))
        else:
            pair = tuple(item)
        if pair[0] and pair[1] and pair not in targets:
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
    """The brief as text: the rule, the proof, the test, and what was found."""
    lines = []
    lines.append('%s %s   risk %s   origin %s'
                 % (brief.get('feature'), brief.get('rule'),
                    brief.get('risk'), brief.get('origin')))
    lines.append('state %s   verdict %s'
                 % (brief.get('state'), brief.get('verdict')))
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
    if brief.get('ai_review'):
        lines.append('')
        lines.append('Model review')
        for line in str(brief['ai_review']).splitlines():
            lines.append('  %s' % line)
    lines.append('')
    lines.append('Verdict: %s' % brief.get('verdict'))
    for reason in brief.get('reasons') or ():
        lines.append('  %s' % reason)
    lines.append('')
    return '\n'.join(lines)


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

    payload = approve_module.load_payload(args.project_root)
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
