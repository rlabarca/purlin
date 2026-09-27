"""The hints the audit reads off a proof's own text.

Free because they need nothing but the spec: no test code, no run, no model
call. They are hints and nothing more. `scripts/review/brief.py` hands them
to the AI audit as plain sentences, beside the rule, the proof and the test
body, and the audit writes what it observed; a settled audit that observed a
gap reads `weak` with its own sentence as the reason. Nothing here decides a
cell on its own, and no name from here reaches a surface.

Six scans, each a pure function of the text and, for one of them, the tier:

    the proof names no literal, number, quoted string or named constant
    the proof says "works" or "correctly" with no value beside it
    nothing runs before the assertion
    an `@e2e` proof is described as a function call
    the proof names a private symbol, a selector or a path
    no proof of the rule names a failure or an edge case

A rule's spec status does not read them. `ready` means the rule has a proof,
and what the proof is worth is the audit's question, answered by a model that
read the test beside it rather than by a regular expression that read the
description alone.
"""

import re

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
# An underscore word right after `/` is a path or URL segment the reader can
# see (`specs/_anchors/`, `/_git/`), not a private name, so it never counts.
_COUPLING_RE = re.compile(
    r'(?:(?<![\w/])_[a-z][a-z0-9_]{2,}\b|'
    r'(?:^|\s)[#.][a-zA-Z][\w-]{2,}(?=\s|$))')

# Words that mark a rejection, an error or a boundary.
_NEGATIVE_RE = re.compile(
    r'\b(?:reject|rejects|rejected|invalid|error|errors|fail|fails|failing|'
    r'missing|absent|denied|denies|refuse|refuses|refused|locked|expired|'
    r'empty|zero|none|no\s+matches|4\d\d|5\d\d|raises?|throws?|warns?)\b',
    re.IGNORECASE)

NO_EXPECTED_VALUE = (
    'This proof names no literal, number, quoted string or named constant, '
    'so almost any assertion would satisfy it.')
VAGUE_VERB = (
    'This proof uses a vague verb with no expected value beside it.')
MISSING_TRIGGER = (
    'Nothing runs before the assertion in this proof, so it reads an '
    'artifact that exists whether or not the code is right.')
TIER_MISMATCH = (
    'This proof is tagged @e2e and reads as a function call rather than as '
    'an observable flow.')
COUPLING = (
    'This proof names a private symbol, a selector or a path instead of an '
    'observable outcome.')
NO_NEGATIVE_CASE = (
    'No proof of this rule names a failure or an edge case.')


def proof_hints(text, tier='unit'):
    """The hints on one proof description, as sentences, in a stable order."""
    text = (text or '').strip()
    if not text:
        return [NO_EXPECTED_VALUE, MISSING_TRIGGER]
    found = []
    concrete = bool(_CONCRETE_RE.search(text))
    if tier == 'e2e' and _INTERNAL_CALL_RE.search(text):
        found.append(TIER_MISMATCH)
    if _VAGUE_RE.search(text) and not concrete:
        found.append(VAGUE_VERB)
    if not concrete:
        found.append(NO_EXPECTED_VALUE)
    if not _TRIGGER_RE.search(text):
        found.append(MISSING_TRIGGER)
    if _COUPLING_RE.search(text):
        found.append(COUPLING)
    return found


def names_a_negative_case(proof_texts):
    """True when a proof of the rule names a rejection, an error or a boundary.

    Asked of every proof of one rule at once: a rule proved in one direction
    is a property of the set, not of any one line. The drift report reads
    this for its `rules_without_a_negative_case` view.
    """
    return any(_NEGATIVE_RE.search(text or '') for text in proof_texts or ())


def rule_hints(proof_texts):
    """The hints that need every proof of one rule at once, as sentences."""
    if not proof_texts or names_a_negative_case(proof_texts):
        return []
    return [NO_NEGATIVE_CASE]
