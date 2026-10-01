"""The structured project payload, schema 14.

One reader assembles specs and evidence into the cells of every rule, and
every surface renders that: the status table, the dashboard, the evidence
package and the drift report. A surface that parsed the rendered table would
be coupled to a layout; this is the shape they all read instead.

    {
      "schema_version": 14,
      "generated_at": "2026-10-01T12:00:00Z",
      "generated_by": "sync_status",
      "project": "labconnect",
      "version": "<the VERSION file>",
      "branch": "main",
      "commit": "<40 hex>",
      "dirty": false,
      "summary": {"rules": 8, "features": 4, "failing": 0,
                  "partial": 1, "untested": 2, "passed": 5, "strong": 3,
                  "weak": 1, "not_audited": 1, "manual": 0,
                  "incomplete": 0,
                  "steps": {"passed": 5},
                  "audit": {"strong": 3, "weak": 1, "not_audited": 1},
                  "sentence": "8 rules. 5 pass their tests. The audit found 3 of 5 rules strong (60%)."},
      "features": [
        {"name": "login", "category": "auth", "spec_path": "specs/auth/login.md",
         "is_anchor": false, "source": null, "pinned": null,
         "scope": ["src/auth/"], "incomplete": false,
         "incomplete_reason": null, "broken": [],
         "rollup": {"rules": 2, "untested": 0, "failing": 0, "partial": 0,
                    "passed": 2, "strong": 1, "weak": 1, "not_audited": 0,
                    "manual": 0, "proofs": 6, "proofs_without_test": 1,
                    "proofs_without_test_ids": ["PROOF-4"],
                    "incomplete": false},
         "current": true,
         "evidence": {"local": {"path": ".purlin/evidence/local/login.json",
                                "committed": true,
                                "platforms": {"macos": {"commit": ..., "at": ...,
                                                        "current": true}}},
                      "ci": null},
         "rules": [
           {"id": "RULE-1", "feature": "login", "text": "...",
            "rule_hash": "<sha256>", "proof_hash": "<sha256>",
            "test_hash": "<sha256>", "test_hash_kind": "test",
            "machines": {"macos": "jane-laptop"},
            "left": "to_strengthen",
            "audit": {"verdict": "weak", "findings": ["..."], "notes": [],
                      "explanation": ["..."],
                      "breaks": {"PROOF-1": {"file": "src/login.py", "line": 12,
                                             "before": "...", "after": "...",
                                             "result": "survived", "why": "",
                                             "break_key": "<sha256>"}},
                      "model": "<model>", "at": "...", "commit": "<sha>",
                      "path": ".purlin/evidence/local/login.json"},
            "bucket": "passed", "flags": {...},
            "cells": {"passed": {...}, "strong": {...}},
            "proofs": [{"id": "PROOF-1", "manual": false, "slow": false,
                        "env": null,
                        "text": "...", "result": "passed",
                        "tests": [{"file": "tests/test_login.py",
                                   "name": "test_sign_in",
                                   "result": "pass"}]}],
            "tests": []}
         ]}
      ],
      "left": [{"kind": "to_strengthen", "count": 1,
                "text": "1 rule to strengthen", "command": "purlin:build"}],
      "met": true,
      "signoff": {"word": "signed <version>, 4 commits since", "version": "<version>",
                  "commit": "<40 hex>", "since": 4},
      "last_line": "Every rule passes its tests on the committed evidence. To sign it: purlin:sign",
      "os_words": {"windows": {"word": "Windows", "short": "Win"},
                   "macos": {"word": "macOS", "short": "Mac"},
                   "linux": {"word": "Linux/Unix", "short": "Lin"}},
      "evidence": {"login": {"local": {"macos": {"commit": ..., "at": ...,
                                                 "result": "pass",
                                                 "current": true,
                                                 "path": ...}}}},
      "information": ["..."],
      "warnings": ["..."]
    }

`branch` is the branch HEAD is on, or null on a detached HEAD; `commit` is
HEAD's full sha. `project` is read from the project's own files each time
(`project.project_name`).

`rules[].tests` lists the tests marked with the rule's own id, which is how
a rule with no proof names its tests: `[{"file": "tests/test_login.py",
"name": "test_locks", "result": "pass"}]`, where `result` is `pass`, `fail`,
`missing` or `not run`. A rule whose tests carry its proofs' ids lists them
under each proof and an empty `tests`.

Each proof carries its own `result`, `passed`, `failed`, `not run`, `no test`
or `hand check`, as `states.proof_result` reads it, and each of its tests the
`result` a current run gave it, `pass` or `fail`, or `not run` where no
current run lists it.

A spec's `rules` holds its own rules and no other, anchors' included. Each
carries `feature`, the name of the spec that owns it, so a rule is always
addressed by its owner and its id: two features' `RULE-1` are two rules. An
anchor's entry carries `scope: []` and `incomplete: false`.

A feature spec with no `> Scope:` line, or a scope that reaches no tracked
file, carries `incomplete: true` and `incomplete_reason` (`no > Scope: line`
or `> Scope: names nothing that exists`), its rollup carries `incomplete:
true`, and `summary.incomplete` counts such specs. An anchor is never
incomplete. Every cell reads as usual.

`summary.steps` counts the rules that pass their tests, `summary.audit` what
the audit found among them, and `summary.sentence` says it in one line.
`left` is the work left, one entry per kind in the order it is done, each
with its count, its text and the command that clears it, `to_correct`
counting test comments and `to_commit` features; `met` is true where no
entry of `left` is of a blocking kind; `signoff` is `facts.signoff_fact`'s
answer; `last_line` is the status's last line, or null where it prints none.
Each rule carries its own `left`, the one kind it is counted under, or null.
`scripts/mcp/purlin/summary.py` is the one place those words are written.

A rule carries `rule_hash`, `proof_hash`, `test_hash` and `test_hash_kind`,
what the audit entry and the evidence package are read against, and
`machines`, `{os: machine}` over the current sections that speak for it.

A feature carries `broken`, the reasons every rule of its spec reads
`failed`, as `specs.broken_reasons` gives them: a rule or proof number
written twice, a line left from a merge conflict; `[]` for a sound spec.
Each rule of a broken spec has the `left` `to_repair`, and `Left to do`
counts such specs, not their rules.

`information` holds one line per spec whose `> Scope:` names files git does
not have yet, as `status.not_written_lines` words it. `warnings` holds every
other line: an evidence file left out, a spec mistake, each test comment to
correct as `wording.stale_comments` words it.

`write_report_data` writes the payload to `.purlin/report-data.js` as
`const PURLIN_DATA = {...};`, which is gitignored and is what the local
dashboard page loads.
"""

import datetime
import hashlib
import json
import os
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from config_engine import resolve_config, settings_warnings
from purlin import (PURLIN_VERSION,
                    evidence as evidence_module,
                    facts as facts_module,
                    fingerprint as fingerprint_module,
                    markers as markers_module,
                    project as project_module,
                    signatures as signatures_module,
                    specs as specs_module, states,
                    summary as summary_module,
                    wording as wording_module)

SCHEMA_VERSION = 14
REPORT_DATA_PATH = os.path.join('.purlin', 'report-data.js')
_PREFIX = 'const PURLIN_DATA = '


def now_iso():
    """The current time, ISO 8601 UTC with `Z`, the one format used anywhere."""
    return datetime.datetime.now(
        datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def build_payload(project_root, generated_by='sync_status', config=None):
    """The whole payload for a project root."""
    from purlin import status as status_module
    config = resolve_config(project_root) if config is None else config
    warnings = list(settings_warnings(config))

    features = specs_module.scan_specs(project_root)
    tag_warning = specs_module.unknown_tag_warning(features)
    if tag_warning:
        warnings.append(tag_warning)
    for name in sorted(features):
        unnumbered = features[name].get('unnumbered_lines') or []
        if unnumbered:
            lines = ('1 line' if len(unnumbered) == 1
                     else '%d lines' % len(unnumbered))
            verb = 'is' if len(unnumbered) == 1 else 'are'
            warnings.append(
                '%s: %s under ## Rules %s not numbered; a rule is '
                '`- RULE-N: <text>`. Run purlin:spec %s.'
                % (name, lines, verb, name))
    for line in specs_module.spec_mistakes(project_root, features):
        warnings.append(line)

    # Every feature's evidence, checked against a fingerprint taken now. A
    # section decides a cell only while it is current, so this is read once
    # here rather than once per rule.
    evidence = _read_evidence(project_root, features, warnings)
    incomplete = {name: fingerprint_module.incomplete_reason(
        project_root, name, features) for name in sorted(features)}
    could_not_run = evidence_module.could_not_run(project_root)
    head = head_sha(project_root)
    here_os = evidence_module.host_os()
    hand_notes = _hand_notes(project_root)

    # Which proofs have a test is read from the markers in the test files,
    # not from the evidence: a marked test that has not run yet is a test.
    suites = markers_module.read_suites(project_root, config)[0]
    scanned = markers_module.scan(project_root, suites)
    tied = markers_module.tied_ids(project_root, scanned)
    # Every comment above a test that names nothing a spec has, names a rule
    # that has proofs, or names a proof reworded since the test last changed
    # is counted under `to_correct`; the reworded ones are warned of here.
    stale = wording_module.stale_comments(project_root, features, scanned)
    warnings.extend(entry['text'] for entry in stale)
    corrections = (len(markers_module.marker_problems(scanned, features))
                   + len(stale))
    sources = {'suites': suites, 'tests': {}, 'blobs': {}}

    feature_entries = []
    own_results = {}
    for name in sorted(features):
        entry, _rollup = _feature_entry(
            project_root, name, features[name], evidence, sources,
            own_results, could_not_run, incomplete, tied, here_os, hand_notes)
        feature_entries.append(entry)

    summary = states.project_rollup({'': states.feature_rollup(own_results)})
    summary['features'] = len(features)
    summary['incomplete'] = sum(1 for reason in incomplete.values() if reason)
    own_rules = [rule for entry in feature_entries for rule in entry['rules']]
    summary.update(proof_counts(own_rules, tied))
    summary['steps'] = summary_module.steps(own_rules)
    summary['audit'] = summary_module.audit_counts(own_rules)
    summary['sentence'] = summary_module.sentence(summary)
    uncommitted = [entry['name'] for entry in feature_entries
                   if any(found and not found.get('committed')
                          for found in (entry['evidence'] or {}).values())]
    left = summary_module.left(feature_entries, here_os, corrections,
                               uncommitted)
    signoff = facts_module.signoff_fact(project_root)

    payload = {
        'schema_version': SCHEMA_VERSION,
        'generated_at': now_iso(),
        'generated_by': generated_by,
        'project': project_module.project_name(project_root),
        'version': PURLIN_VERSION,
        'branch': branch_name(project_root),
        'commit': head,
        'dirty': _is_dirty(project_root),
        'summary': summary,
        'features': feature_entries,
        'left': left,
        'met': None,
        'signoff': signoff,
        'last_line': summary_module.last_line(left, signoff),
        'os_words': {name: {'word': evidence_module.os_word(name),
                            'short': evidence_module.os_short(name)}
                     for name in evidence_module.PLATFORMS},
        'evidence': _evidence_map(evidence),
        'information': status_module.not_written_lines(project_root, features),
        'warnings': warnings,
    }
    payload['met'] = facts_module.tests_fact(payload) == facts_module.TESTS_MET
    return payload


def proof_counts(rule_entries, tied=None):
    """`{proofs, proofs_without_test, proofs_without_test_ids}` over some rules.

    A proof with no marked test is the gap between what a spec claims to
    observe and what anything actually runs, so the count is carried beside
    the proof total rather than worked out again by each surface. Each proof
    is counted once under the rule that writes it, so a rule an anchor
    declares is not counted twice in the one row that proves it.

    A `@manual` proof is left out of the count: it declares that no test is
    written for it, so naming it as a gap would report the spec's own answer
    as a fault. A proof has a test when a marker naming it is tied to a test
    declaration, `tied` being `markers.tied_ids`' answer, so a marked test
    that has not run yet is a test and its rule reads `not run`.
    """
    seen = set()
    total = 0
    without = []
    for rule in rule_entries or ():
        for proof in rule.get('proofs') or ():
            key = (rule.get('feature'), proof.get('id'))
            if key in seen:
                continue
            seen.add(key)
            total += 1
            if proof.get('manual'):
                continue
            if (rule.get('feature'), proof.get('id')) not in (tied or ()):
                without.append(proof.get('id'))
    return {'proofs': total, 'proofs_without_test': len(without),
            'proofs_without_test_ids': without}


def _feature_entry(project_root, name, info, evidence, sources,
                   own_results=None, could_not_run=None, incomplete=None,
                   tied=None, here_os=None, hand_notes=None):
    incomplete = incomplete or {}
    anchor = bool(info.get('is_anchor'))
    own = evidence.get(name) or _no_evidence(name)

    rule_entries = []
    rule_results = {}
    marked = {rule for feature, rule in (tied or ()) if feature == name}
    broken = spec_broken(info)
    for rule_id in info.get('rule_order') or ():
        result = _rule_entry(
            project_root, name, info, rule_id, own, sources, could_not_run,
            marked, here_os, broken, (hand_notes or {}).get((name, rule_id)))
        rule_entries.append(result)
        summary = {'bucket': result['bucket'], 'flags': result['flags']}
        rule_results[(name, rule_id)] = summary
        if own_results is not None:
            own_results[(name, rule_id)] = summary

    rollup = states.feature_rollup(rule_results)
    rollup.update(proof_counts(rule_entries, tied))
    rollup['incomplete'] = bool(incomplete.get(name))

    entry = {
        'name': name,
        'category': info.get('category', ''),
        'spec_path': info.get('spec_path', ''),
        'is_anchor': anchor,
        'description': info.get('description'),
        'scope': [] if anchor else info.get('scope', []),
        'incomplete': bool(incomplete.get(name)),
        'incomplete_reason': incomplete.get(name),
        'broken': broken,
        'source': info.get('source'),
        'source_path': info.get('source_path'),
        'pinned': info.get('pinned'),
        'rollup': rollup,
        'current': own['current'],
        'evidence': own['summary'],
        'rules': rule_entries,
    }
    return entry, rollup


def spec_broken(info):
    """Why every rule of a spec reads `failed`, `specs.broken_reasons`' answer."""
    return list(specs_module.broken_reasons(info))


# ---------------------------------------------------------------------------
# The evidence
# ---------------------------------------------------------------------------

def _read_evidence(project_root, features, warnings):
    """`{feature: {loaded, sections, current, summary}}` for every spec.

    `sections` is every section of the feature's two files, each checked
    against a fingerprint taken now; `current` says the newest of them is
    current; `summary` is the `features[].evidence` object. A file the
    reader ignores adds its warning once.
    """
    markers = fingerprint_module.marker_index(project_root)
    uncommitted = _uncommitted_evidence(project_root)
    out = {}
    for name in sorted(features):
        loaded = evidence_module.load(project_root, name)
        for warning in loaded['warnings']:
            if warning not in warnings:
                warnings.append(warning)
        sections = []
        if any(loaded['files'].values()):
            now = fingerprint_module.fingerprint(project_root, name, features,
                                                 markers)
            sections = evidence_module.checked_sections(loaded, now)
        newest = None
        for entry in sections:
            if newest is None or str(entry['section'].get('at') or '') > str(
                    newest['section'].get('at') or ''):
                newest = entry
        summary = {}
        for source in evidence_module.SOURCES:
            if loaded['files'].get(source) is None:
                summary[source] = None
                continue
            path = loaded['paths'][source]
            summary[source] = {
                'path': path,
                'committed': path not in uncommitted,
                'platforms': {
                    entry['os']: {'commit': entry['section'].get('commit'),
                                  'at': entry['section'].get('at'),
                                  'current': entry['current']}
                    for entry in sections if entry['source'] == source},
            }
        out[name] = {'loaded': loaded, 'sections': sections,
                     'current': bool(newest and newest['current']),
                     'summary': summary}
    return out


def _no_evidence(name):
    """What `_read_evidence` answers for a feature that has no spec of its own."""
    return {'loaded': {'feature': name, 'files': {'local': None, 'ci': None},
                       'paths': {}, 'warnings': []},
            'sections': [], 'current': False,
            'summary': {'local': None, 'ci': None}}


def _uncommitted_evidence(project_root):
    """The evidence paths whose file is not tracked or differs from HEAD.

    One `git status` answers every file: a path it lists is not committed as
    it stands, and a path it does not list is tracked and matches HEAD.
    Outside a repository nothing is committed, so every path counts as not.
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain', '--untracked-files=all', '--',
             evidence_module.EVIDENCE_DIR],
            capture_output=True, text=True, cwd=project_root, timeout=15)
    except (subprocess.SubprocessError, OSError):
        return _AllPaths()
    if result.returncode != 0:
        return _AllPaths()
    listed = set()
    for line in result.stdout.splitlines():
        if len(line) > 3:
            listed.add(line[3:].strip('"').split(' -> ')[-1])
    return listed


class _AllPaths(object):
    """A set that holds every path: outside git, nothing is committed."""

    def __contains__(self, _path):
        return True


def _evidence_map(evidence):
    """`{feature: {source: {os: {commit, at, result, current, path}}}}`.

    `result` is `fail` where any proof the section observed failed and `pass`
    otherwise, so two sections with nothing but their operating system to
    tell them apart still say which one failed.
    """
    out = {}
    for name in sorted(evidence):
        for entry in evidence[name]['sections']:
            results = {proof: word for proof, (word, _reason) in
                       states.section_results(entry['section']).items()}
            out.setdefault(name, {}).setdefault(entry['source'], {})[
                entry['os']] = {
                    'commit': entry['section'].get('commit'),
                    'at': entry['section'].get('at'),
                    'result': 'fail' if 'fail' in results.values() else 'pass',
                    'current': entry['current'],
                    'path': entry['path'],
                }
    return out


def _rule_entry(project_root, owner, owner_info, rule_id, owner_evidence,
                sources, could_not_run=None, marked=None, here_os=None,
                broken=None, hand_notes=None):
    text = owner_info['rules'].get(rule_id, '')
    anchor = bool(owner_info.get('is_anchor'))
    proof_ids = owner_info.get('proofs_by_rule', {}).get(rule_id, [])
    sections = owner_evidence['sections']

    proof_dicts = []
    for proof_id in proof_ids:
        proof = owner_info['proofs'][proof_id]
        ran = _current_results(sections, proof_id, proof['env'])
        entry = {
            'id': proof_id,
            'manual': proof['manual'],
            'slow': bool(proof.get('slow')),
            'env': proof['env'],
            'text': proof['text'],
            'tests': [{'file': f, 'name': n,
                       'result': ran.get((f, n), 'not run')}
                      for f, n in _backing_tests(sections, proof_id)],
        }
        entry['result'] = states.proof_result(entry, sections, marked, anchor)
        proof_dicts.append(entry)

    rule_hash = specs_module.rule_text_hash(text)
    proof_hash = specs_module.proof_text_hash(
        '\n'.join('%s %s' % (p['id'], p['text']) for p in proof_dicts))
    test_hash, hash_kind = _test_hash(project_root, proof_dicts, sources)
    # The machine each system's results came from, which the evidence
    # package records beside them.
    machines = _machines(sections, proof_dicts, rule_id)

    # The audit entry for this rule's current hashes, in either source. An
    # entry taken over other text, another proof or another test does not
    # answer, which is what keeps the strong cell honest.
    audit = evidence_module.audit_entry(owner_evidence['loaded'], rule_id,
                                        rule_hash, proof_hash, test_hash)
    result = states.rule_cells({
        'anchor': anchor,
        'proofs': proof_dicts,
        'rule_id': rule_id,
        'sections': sections,
        'audit': audit,
        # Why the last audit could not reach the model for these hashes,
        # which is what the strong cell says while it reads `not audited`.
        'could_not_run': evidence_module.why_not_audited(
            could_not_run, owner, rule_id, rule_hash, proof_hash, test_hash),
        # The owner's proof and rule ids a marker ties to a test declaration,
        # so a marked test that has not run reads `not run`, not `no test`.
        'marked': marked or set(),
        # What the newest sign-off holding a note on this rule noted.
        'hand_notes': list(hand_notes or ()),
        # Why the rule's own spec is broken, which fails it.
        'spec_broken': list(broken or ()),
    })

    entry = {
        'id': rule_id,
        'feature': owner,
        'text': text,
        'rule_hash': rule_hash,
        'proof_hash': proof_hash,
        'test_hash': test_hash,
        'test_hash_kind': hash_kind,
        'machines': machines,
        'audit': audit_summary(audit),
        'cells': result['cells'],
        'bucket': result['bucket'],
        'flags': result['flags'],
        'proofs': proof_dicts,
        'tests': _rule_tests(sections, rule_id),
    }
    entry['left'] = summary_module.rule_kind(entry, here_os, broken)
    return entry


def test_hash_kind(proofs, kinds=()):
    """What the test hash was taken from, which the evidence package records.

    `manual` is a proof with no test at all, checked by hand. `file` is a
    test covered by its whole file: one of an `exit` suite, or one not found
    by its name. `test` is a test covered by its own source. `none` is a
    rule with nothing behind it yet. `kinds` holds `file` and `test` as the
    hash read them; the first that applies wins.
    """
    if any(proof.get('manual') for proof in proofs or ()):
        return 'manual'
    for kind in ('file', 'test'):
        if kind in kinds:
            return kind
    return 'none'


def _machines(sections, proofs, rule_id):
    """`{os: machine}` over the current sections that speak for the rule.

    A section speaks for the rule when one of the rule's proofs ran there,
    passing or failing, read from its own system only where the proof names
    one, or for the rule's own id where it has no proof. Each section's `machine`
    names where it ran; a section that names none is left out, and where
    both sources hold one for a system the newer answers.
    """
    wanted = [(proof['id'], proof.get('env')) for proof in proofs
              if not proof.get('manual')] or [(rule_id, None)]
    found = {}
    for entry in sections or ():
        if not entry.get('current'):
            continue
        section = entry['section']
        machine = section.get('machine')
        if not machine:
            continue
        results = {proof: word for proof, (word, _reason) in
                   states.section_results(section).items()}
        if not any(results.get(proof_id) in ('pass', 'fail')
                   and (not env or env == entry['os'])
                   for proof_id, env in wanted):
            continue
        at = str(section.get('at') or '')
        known = found.get(entry['os'])
        if known is None or at > known[0]:
            found[entry['os']] = (at, machine)
    return {name: found[name][1] for name in sorted(found)}


def audit_summary(audit):
    """`rules[].audit`: what the audit found for the current hashes, or None.

    The `verdict` and the findings, the notes, the model's `explanation` and
    the planted bugs under `breaks`, both exactly as the entry holds them, the
    model that read the rule, when and at which commit, and the evidence file
    the entry sits in. An entry that holds no `explanation` carries `[]` and
    one that holds no `breaks` carries `{}`, which is what an entry with none
    is written with. An entry whose verdict the format does not name answers
    nothing.
    """
    if not audit or audit.get('verdict') not in ('strong', 'weak'):
        return None
    explanation = audit.get('explanation')
    breaks = audit.get('breaks')
    return {'verdict': audit.get('verdict'),
            'findings': [str(line) for line in audit.get('findings') or ()],
            'notes': [str(line) for line in audit.get('notes') or ()],
            'explanation': [] if explanation is None else explanation,
            'breaks': {} if breaks is None else breaks,
            'model': audit.get('model') or 'unknown',
            'at': audit.get('at'),
            'commit': audit.get('commit'),
            'path': audit.get('path')}


def _backing_tests(sections, proof_id):
    """`[(test_file, test_name), ...]` backing one proof, the same on every machine.

    The tests the current sections list come first, every operating system
    and both sources together, because a section is the one list every
    checkout reads alike. Where no current section lists one, every section
    answers, so a code change that leaves a section out of date does not
    change which tests back the proof, and the test hash moves only when a
    test does.
    """
    for wanted in (True, False):
        observed = []
        for entry in sections or ():
            if wanted and not entry.get('current'):
                continue
            for pair in evidence_module.proof_tests(entry['section'],
                                                    proof_id):
                if pair not in observed:
                    observed.append(pair)
        if observed:
            return observed
    return []


def _current_results(sections, proof_id, env=None):
    """`{(file, name): result}` for one proof's tests, over current sections.

    A proof's test reads what a current run found, `fail` where either source
    failed it and `pass` where one passed it, so a test and the proof above it
    never disagree. A test no current section lists is not in the map, and
    reads `not run`. A proof that names an operating system is read from that
    system's sections alone, as its own result is.
    """
    results = {}
    for entry in sections or ():
        if not entry.get('current') or (env and entry.get('os') != env):
            continue
        for item in (entry['section'].get('proofs') or ()):
            if not isinstance(item, dict) or item.get('id') != proof_id:
                continue
            path, _, name = (item.get('test') or '').partition('::')
            result = item.get('result')
            if not path or result not in ('pass', 'fail'):
                continue
            if results.get((path, name)) != 'fail':
                results[(path, name)] = result
    return results


def _rule_tests(sections, rule_id):
    """`[{file, name, result}]` for the tests marked with the rule's own id.

    Read from the same sections as `_backing_tests`, current ones first. A
    test two sections list reads `fail` where either failed, then `pass`
    where either passed, and otherwise the first word a section wrote.
    """
    for wanted in (True, False):
        order = []
        results = {}
        for entry in sections or ():
            if wanted and not entry.get('current'):
                continue
            for item in (entry['section'].get('proofs') or ()):
                if not isinstance(item, dict) or item.get('id') != rule_id:
                    continue
                path, _, name = (item.get('test') or '').partition('::')
                if not path:
                    continue
                key = (path, name)
                result = item.get('result')
                if key not in results:
                    order.append(key)
                    results[key] = result
                elif result == 'fail' or (result == 'pass'
                                          and results[key] != 'fail'):
                    results[key] = result
        if order:
            return [{'file': path, 'name': name, 'result': results[(path, name)]}
                    for path, name in order]
    return []


def _test_hash(project_root, proof_dicts, sources):
    """`(test hash, kind)`: the tests tied to the rule's proofs, each by its own source.

    One line per test, `<file> <test name> <sha256 of the test's source>`,
    the source as its marker bounds it with line ends read as `\n`, so
    editing another test of the same file leaves the hash where it was. A
    test of an `exit` suite, or one not found by its name, gives
    `<file> <test name> <blob id>` and the kind `file`. Which tests back each
    proof is `_backing_tests`' answer, read from the evidence so it does not
    depend on the machine.
    """
    parts = []
    kinds = set()
    for proof in proof_dicts:
        for test in proof['tests']:
            path, name = test['file'], test['name']
            own = _test_sources(project_root, path, sources).get(name)
            if own is not None:
                kinds.add('test')
                parts.append('%s %s %s' % (path, name, own))
                continue
            kinds.add('file')
            if path not in sources['blobs']:
                sources['blobs'][path] = fingerprint_module.blob_id(
                    project_root, path)
            parts.append('%s %s %s' % (path, name, sources['blobs'][path]))
    digest = hashlib.sha256()
    digest.update('\n'.join(sorted(parts)).encode('utf-8'))
    return digest.hexdigest(), test_hash_kind(proof_dicts, kinds)


def _test_sources(project_root, path, sources):
    """`{test name: sha256 of its source}` for one test file; `{}` for a file run whole."""
    cache = sources['tests']
    if path in cache:
        return cache[path]
    cache[path] = {}
    suite = markers_module.suite_of(path, sources['suites'] or ())
    if suite is not None and suite.format == 'exit':
        return cache[path]
    try:
        full = os.path.join(project_root, *path.split('/'))
        with open(full, 'r', encoding='utf-8', newline='') as handle:
            text = handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return cache[path]
    declared = markers_module.declared_tests(
        text, os.path.splitext(path)[1].lower()) or ()
    for test in declared:
        bounds = wording_module.test_source(path, text, test)
        if bounds is None:
            continue
        name = markers_module.test_name(path, test)
        cache[path].setdefault(name, hashlib.sha256(
            bounds[2].encode('utf-8')).hexdigest())
    return cache[path]


def branch_name(project_root):
    """The branch HEAD is on, or None on a detached HEAD or outside git."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return None
    name = result.stdout.strip() if result.returncode == 0 else ''
    return name if name and name != 'HEAD' else None


def _hand_notes(project_root):
    """`{(feature, rule): [reason]}` from the newest sign-off holding a note on each rule.

    Every sign-off file of every version is read, whatever code it was taken
    on. Each note becomes `states.HAND_NOTE`: the version, the signer, how
    far HEAD is from the signed commit, the note. The signed commit is the
    one `signed/<version>` names, or the commit that added the file.
    """
    folder = os.path.join(project_root, *signatures_module.PACKAGE_DIR.split('/'))
    try:
        versions = sorted(name for name in os.listdir(folder)
                          if name.endswith('.signoffs'))
    except OSError:
        return {}
    signoffs = []
    for name in versions:
        directory = os.path.join(folder, name)
        for basename in sorted(os.listdir(directory)):
            if not basename.endswith('.json'):
                continue
            try:
                full = os.path.join(directory, basename)
                with open(full, 'r', encoding='utf-8') as handle:
                    data = json.load(handle)
            except (IOError, OSError, UnicodeDecodeError, ValueError):
                continue
            if isinstance(data, dict) and isinstance(data.get('notes'), list):
                rel = '%s/%s/%s' % (signatures_module.PACKAGE_DIR, name, basename)
                signoffs.append((str(data.get('timestamp') or ''), rel, data))
    found = {}
    distances = {}
    for _at, rel, data in sorted(signoffs, key=lambda item: item[:2],
                                 reverse=True):
        version = str(data.get('version') or '')
        held = {}
        for note in data['notes']:
            if isinstance(note, dict) and note.get('feature') and note.get('rule'):
                held.setdefault((note['feature'], note['rule']), []).append(
                    str(note.get('note') or ''))
        for key, notes in held.items():
            if key in found:
                continue
            if rel not in distances:
                distances[rel] = _distance(project_root, version, rel)
            found[key] = [states.HAND_NOTE % (version, data.get('signer'),
                                              distances[rel], note)
                          for note in notes]
    return found


def _distance(project_root, version, rel):
    """How far HEAD is from the commit a sign-off signed, as a note says it."""
    commit = facts_module.git_line(project_root, 'rev-list', '-n', '1',
                               facts_module.TAG_PREFIX + version)
    if not commit:
        commit = facts_module.git_line(project_root, 'log', '-n', '1',
                                   '--diff-filter=A', '--format=%H', '--', rel)
    if not commit:
        return facts_module.AT_THIS_COMMIT
    return facts_module.distance(project_root, commit)


def head_sha(project_root):
    """The full sha at HEAD, or None outside a git checkout."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _is_dirty(project_root):
    """True when the working tree differs from the commit the payload names.

    `.purlin/` is excluded. What Purlin writes about a project is not a change
    to the project, and counting it would make the answer depend on whether
    the report had been written yet: two builds of one unchanged tree would
    then disagree.
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True, text=True, cwd=project_root, timeout=15)
    except (subprocess.SubprocessError, OSError):
        return False
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        if len(line) > 3 and not line[3:].strip('"').startswith('.purlin/'):
            return True
    return False


# ---------------------------------------------------------------------------
# The dashboard's data file
# ---------------------------------------------------------------------------

def report_data_path(project_root):
    return os.path.join(project_root, REPORT_DATA_PATH)


def write_report_data(project_root, payload):
    """Write the payload as `const PURLIN_DATA = {...};`. Returns the path."""
    path = report_data_path(project_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = json.dumps(payload, indent=2, sort_keys=True, default=str)
    text = _PREFIX + body + ';\n'

    tmp_path = path + '.tmp'
    # `newline='\n'` keeps every line ending a line feed on Windows too.
    with open(tmp_path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)
    os.replace(tmp_path, path)
    return path
