import json, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deck', 'project')
MONO = "font-family:'Courier New', monospace"
def m(text):
    return '<span style="%s">%s</span>' % (MONO, text)
SECTION = ('<section id="%s" data-transition="fade" style="background:#0C3444; color:#E4DDD4; '
           'font-family:Arial, sans-serif; padding:96px 128px 160px; display:flex; '
           'flex-direction:column; gap:%dpx">')
ROW = ('<div style="display:flex; align-items:center; gap:32px; padding:%dpx 24px; '
       'background:#092936; border-radius:10px">%s</div>')
NUM = '<p style="font-size:32px; color:#BFCED5; width:48px">%s</p>'
PILL = ('<p style="font-size:24px; letter-spacing:2px; width:150px; text-align:center; '
        'padding:8px 0; border:2px solid #C0793F; border-radius:999px; color:#C0793F">LOCAL</p>')
CMD = '<p style="' + MONO + '; font-size:32px; color:#E6BEB0; width:%dpx">%s</p>'
WHAT = '<p style="font-size:32px; color:#E4DDD4; flex:1">%s</p>'
def slide(sid, eyebrow, headline, rows, closing, footer, notes, pill=True, gap=20, pad=18):
    out = [SECTION % (sid, gap),
           '<p style="font-size:24px; letter-spacing:3px; text-transform:uppercase; color:#C0793F">%s</p>' % eyebrow,
           '<h2 style="font-size:64px; font-weight:600; line-height:1.1">%s</h2>' % headline,
           '<div style="flex:1"></div>']
    for i, (cmd, what) in enumerate(rows, 1):
        cells = NUM % i + (PILL + CMD % (560, cmd) if pill else CMD % (742, cmd)) + WHAT % what
        out.append(ROW % (pad, cells))
    out += ['<div style="flex:1"></div>',
            '<p style="font-size:32px; color:#E4DDD4">%s</p>' % closing,
            '<p style="position:absolute; left:128px; bottom:64px; width:1664px; font-size:24px; color:#BFCED5">%s</p>' % footer,
            '<aside>%s</aside>' % notes, '</section>', '']
    with open(os.path.join(ROOT, 'slides', sid + '.html'), 'w', encoding='utf-8') as h:
        h.write('\n'.join(out))
FOOT = 'Every step is on your machine. Only you push.'
slide('passed', 'Gate passed', 'Did the rules pass their tests?', [
    ('purlin:spec', 'Rules written.'),
    ('purlin:build', 'Code and tests written. One comment above each test.'),
    ('purlin:test', 'Each rule: passed, failed, no test, out of date.'),
    ('git push', 'You push. Nothing runs when you do.'),
], '<b>Red</b> means a test failed, a rule has no test, or a rule is out of date.', FOOT,
 'At passed a project needs a rule and a test that names it. purlin:test runs only what your change '
 'touched, writes the evidence, and commits it only when you pass --commit. Its last line is the '
 'check: gate passed, or gate not met.')
slide('strong', 'Gate strong', 'Are the tests worth trusting?', [
    ('spec, build, test', 'The passed loop, with a proof for every rule.'),
    ('purlin:audit', 'A model reads each test against its proof. A finding blocks.'),
    ('mutation testing', 'Optional, and off unless you turned it on.'),
    ('the evidence', 'One file per feature. Committed when you ask, with %s.' % m('--commit')),
    ('git push', 'You push. Your evidence counts.'),
], '<b>Red</b> means a rule is weak, not audited, or has no proof.', FOOT,
 'A proof says in plain language how a rule is shown; QA writes and reviews them, and AI may draft '
 'them. The audit reads one rule per call, several at once, says how many it will read before it '
 'starts, and names the model on every finding. A rule whose text, proof and test have not changed '
 'is not read again.',
 gap=int(sys.argv[1]) if len(sys.argv) > 1 else 20, pad=int(sys.argv[2]) if len(sys.argv) > 2 else 18)
slide('signed', 'Gate signed', 'Did a person sign it?', [
    ('the strong steps', 'Tests and audit, with the evidence committed.'),
    ('purlin:sign', 'Walks the queue: hand checks and signatures.'),
    ('the signature', 'One file per rule, in a signed commit: who, when, on which machine.'),
    ('the package and the tag', 'The evidence package is committed, and %s is written on it.' % m('signed/1.4.0')),
    ('git push origin signed/1.4.0', 'You push the tag. That is the claim.'),
], '<b>Red</b> means a rule needs a signature and has none, or the one it had went stale. '
   'No tag is written.', FOOT,
 'Signing is the formal lock on all the evidence together: the rule, its proof, its test and what '
 'the audit found. Change any of them and the signature goes stale. A signature belongs to no '
 'machine; it records where it was made. The tag itself is signed.',
 gap=int(sys.argv[1]) if len(sys.argv) > 1 else 20, pad=int(sys.argv[2]) if len(sys.argv) > 2 else 18)
slide('remote', 'The remote runner', 'When does anything leave your machine?', [
    ('another operating system', 'A proof is tagged %s for a system this machine is not, so only a runner can show it. %s brings its evidence home.' % (m('@env'), m('purlin:test --remote'))),
    ('you said not to trust this one', 'You chose not to trust this machine, so the tests a signature rests on run on a clean one.'),
], 'With neither, %s writes no runner file at any gate.' % m('purlin:init'),
 'REMOTE is the git host\'s runner. It starts on a pushed tag or a run branch, and on nothing else.',
 'Two reasons and no others. Where a runner exists it runs on a pushed signed tag and on the run '
 'branch purlin:test --remote creates, waits on and deletes. The tag run reruns the tests on a clean '
 'machine, checks every signature against the tagged code, and checks that every file in the ci '
 'folder was committed by the runner itself.', pill=False)
slide('touches', 'In your project', 'What does Purlin put in your project?', [
    ('a settings file', '%s, a folder for evidence, and a few lines in %s.' % (m('.purlin/config.json'), m('.gitignore'))),
    ('your specs', 'Markdown you write, under %s.' % m('specs/')),
    ('one comment per test', '%s above the test. The test is unchanged.' % m('# purlin: login PROOF-4')),
    ('your test command', 'Your framework, your suite. Nothing is installed in it.'),
    ('nothing on its own', 'Nothing committed unless you ask. Nothing runs unless you ran it.'),
], 'If you leave, the markers are comments.',
 'Ten minutes: install, write three rules, add one comment above each of three tests, run purlin:test.',
 'Purlin reads the report your test framework already writes and ties each result to its comment by '
 'the name of the test. A test with no comment runs as always and is ignored. A test Purlin wrote '
 'and a test you wrote differ in nothing but who typed them. Setup also copies the dashboard page '
 'into the project, where git ignores it.', pill=False,
 gap=int(sys.argv[1]) if len(sys.argv) > 1 else 20, pad=int(sys.argv[2]) if len(sys.argv) > 2 else 18)
slide('regulated', 'Regulated work', 'Where does Purlin stop?', [
    ('Purlin produces', 'Evidence, signatures, the signed tag and the evidence package.'),
    ('you hand over', 'The package: one data file for the version, made by %s.' % m('purlin:export')),
    ('the regulated system', 'Holds the document, decides who signs it off, and carries the signature that counts.'),
], 'Purlin makes no claim that software is compliant with any regulation.',
 'Purlin is an input to a system of record. It is not one.',
 'The package holds, for each rule: its words, its proofs, its tests, each result with when and '
 'where it ran, what the audit found and which model judged, and who signed, when and on which '
 'machine. A requirement number such as (URS-042) reaches it as a note in the rule\'s own words. '
 'The same tag always gives the same package, byte for byte.', pill=False)
deck = {"v": 4, "createdOnFiles": {"v": 1, "at": "2026-09-26T18:00:00Z"},
        "title": "Purlin gate workflows",
        "order": ["touches", "passed", "strong", "signed", "remote", "regulated"],
        "sections": {"s1": {"description": "What Purlin puts in a project, and how little that is", "start": "touches"},
                     "s2": {"description": "One slide per gate, all on one machine: what you run, what it leaves behind, what red means", "start": "passed"},
                     "s3": {"description": "The two reasons a remote runner exists, and where Purlin stops in regulated work", "start": "remote"}},
        "faces": {}, "designSystems": []}
with open(os.path.join(ROOT, 'deck.json'), 'w', encoding='utf-8') as h:
    json.dump(deck, h, indent=2); h.write('\n')
