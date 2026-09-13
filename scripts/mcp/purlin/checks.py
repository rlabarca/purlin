"""The free checks on proof text.

Free because they need nothing but the spec: no test code, no run, no model
call. `states.py` uses them to decide whether a rule is Proof ready, and the
review brief prints them beside the proof they name.

Every check is a pure function of the text (and, for one of them, the tier),
and every finding is one of six names:

`no_expected_value`   the description names no literal, number, quoted string
                      or named constant, so almost any assertion satisfies it
`vague_verb`          "works", "correctly", "as expected" with no value beside it
`missing_trigger`     nothing runs before the assertion, so the proof reads an
                      artifact that exists whether or not the code is right
`tier_mismatch`       an `@e2e` proof described as a function call
`implementation_coupling`
                      the description names a private symbol, a CSS selector or
                      a file path instead of an observable outcome
`happy_path_only`     a rule whose proofs never name a rejection, an error or
                      a boundary

The first four block Proof ready. The last two are advisory: a rule can be
legitimately positive-only, and a grep proof legitimately names a path.
"""

import re

BLOCKING = ('no_expected_value', 'vague_verb', 'missing_trigger', 'tier_mismatch')
ADVISORY = ('implementation_coupling', 'happy_path_only')
FINDINGS = BLOCKING + ADVISORY

# A concrete expected value: a number, a quoted string, a backticked token, a
# named constant, or one of the words that fixes a value on its own.
_CONCRETE_RE = re.compile(
    r'(?:\d|"[^"]+"|\'[^\']+\'|`[^`]+`|\bexactly\b|\bzero\b|\bempty\b|'
    r'\bnone\b|\btrue\b|\bfalse\b|[A-Z]{2,}(?:_[A-Z0-9]+)+)',
    re.IGNORECASE)

_VAGUE_RE = re.compile(
    r'\b(?:works?|working|correctly|properly|as\s+expected|appropriately|'
    r'successfully|handles?\s+(?:it|them|errors?))\b',
    re.IGNORECASE)

# Something runs before the assertion, so the proof is behavioural.
_TRIGGER_RE = re.compile(
    r'\b(?:call|invoke|run|write|create|POST|GET|PUT|DELETE|load|render|launch|'
    r'navigate|click|type|submit|execute|spawn|start|seed|patch|set|configure|'
    r'initialize|init|mock|simulate|trigger|send|drive|grep|read|scan|parse|'
    r'open|build|import|publish|emit)\b',
    re.IGNORECASE)

# An `@e2e` description that reads as a function call rather than a person's
# action is tagged at the wrong tier.
_INTERNAL_CALL_RE = re.compile(r'\b(?:call|invoke)\b[^.;]{0,40}?\w+\(', re.IGNORECASE)

# A private symbol, a CSS selector or a source path in place of an outcome.
_COUPLING_RE = re.compile(
    r'(?:\b_[a-z][a-z0-9_]{2,}\b|(?:^|\s)[#.][a-zA-Z][\w-]{2,}(?=\s|$))')

# Words that mark a rejection, an error or a boundary.
_NEGATIVE_RE = re.compile(
    r'\b(?:reject|rejects|rejected|invalid|error|errors|fail|fails|failing|'
    r'missing|absent|denied|denies|refuse|refuses|refused|locked|expired|'
    r'empty|zero|none|no\s+matches|4\d\d|5\d\d|raises?|throws?|warns?)\b',
    re.IGNORECASE)


def proof_findings(text, tier='unit'):
    """The findings on one proof description, in a stable order."""
    text = (text or '').strip()
    found = []
    if not text:
        return ['no_expected_value', 'missing_trigger']
    concrete = bool(_CONCRETE_RE.search(text))
    if tier == 'e2e' and _INTERNAL_CALL_RE.search(text):
        found.append('tier_mismatch')
    if _VAGUE_RE.search(text) and not concrete:
        found.append('vague_verb')
    if not concrete:
        found.append('no_expected_value')
    if not _TRIGGER_RE.search(text):
        found.append('missing_trigger')
    if _COUPLING_RE.search(text):
        found.append('implementation_coupling')
    return found


def rule_findings(proof_texts):
    """The findings that need every proof of one rule at once.

    Only `happy_path_only` so far: a rule none of whose proofs name a
    rejection, an error or a boundary has been proved in one direction.
    """
    if not proof_texts:
        return []
    if any(_NEGATIVE_RE.search(text or '') for text in proof_texts):
        return []
    return ['happy_path_only']


def blocks_proof_ready(findings):
    """True when a finding in `findings` keeps a rule out of Proof ready."""
    return any(name in BLOCKING for name in findings)


def describe(finding):
    """One sentence for a finding name, for a brief or a status line."""
    return _DESCRIPTIONS.get(finding, finding)


_DESCRIPTIONS = {
    'no_expected_value': (
        'Names no literal, number, quoted string or named constant, so almost '
        'any assertion would satisfy it.'),
    'vague_verb': (
        'Uses a vague verb with no expected value beside it. A proof should be '
        'readable straight into a test.'),
    'missing_trigger': (
        'Nothing runs before the assertion, so the proof reads an artifact that '
        'exists whether or not the code is right.'),
    'tier_mismatch': (
        'An @e2e proof must read as an observable flow. Drive the real interface '
        'or retag the proof to the tier it exercises.'),
    'implementation_coupling': (
        'Names a private symbol, a selector or a path instead of an observable '
        'outcome, so a refactor breaks the proof without changing behaviour.'),
    'happy_path_only': (
        'No proof of this rule names a rejection, an error or a boundary.'),
}
