import json, os
# DECK_ROOT names the folder the deck's files are written under; the default sits beside this script.
ROOT = os.environ.get('DECK_ROOT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deck', 'project')
MONO = "font-family:'Courier New', monospace"
# A command or a file name inside a sentence: the viewer keeps the colour and drops the face.
def m(text):
    return '<span style="%s; color:#E6BEB0">%s</span>' % (MONO, text)
def mt(text):
    return '<span style="%s">%s</span>' % (MONO, text)
SECTION = ('<section id="%s" data-transition="fade" style="background:#0C3444; color:#E4DDD4; '
           'font-family:Arial, sans-serif; padding:96px 128px 160px; display:flex; '
           'flex-direction:column; gap:%dpx">')
CARD = ('<div style="display:flex; flex-direction:column; gap:14px; padding:%dpx 24px; '
        'background:#092936; border-radius:10px">%s</div>')
LINE = '<div style="display:flex; align-items:center; gap:32px">%s</div>'
NUM = '<p style="font-size:32px; color:#BFCED5; width:48px">%s</p>'
CMD = '<p style="' + MONO + '; font-size:32px; color:#E6BEB0; width:%dpx">%s</p>'
WHAT = '<p style="font-size:32px; color:#E4DDD4; flex:1">%s</p>'
# A part of a step: no number, set in under the step it belongs to.
PART = ('<div style="display:flex; align-items:center; gap:32px; padding:0 0 0 80px">'
        '<p style="' + MONO + '; font-size:28px; color:#BFCED5; width:%dpx">%s</p>'
        '<p style="font-size:28px; color:#BFCED5; flex:1">%s</p></div>')
def slide(sid, eyebrow, headline, rows, closing, notes, lead='', width=620, gap=20, pad=18):
    out = [SECTION % (sid, gap),
           '<p style="font-size:24px; letter-spacing:3px; text-transform:uppercase; color:#C0793F">%s</p>' % eyebrow,
           '<h2 style="font-size:64px; font-weight:600; line-height:1.1">%s</h2>' % headline]
    if lead:
        out.append('<p style="font-size:32px; color:#BFCED5">%s</p>' % lead)
    out.append('<div style="flex:1"></div>')
    for i, row in enumerate(rows, 1):
        name, what, parts = row[0], row[1], row[2] if len(row) > 2 else ()
        head = CMD % (width, name.strip('`'))
        lines = [LINE % (NUM % i + head + WHAT % what)]
        lines += [PART % (width, part, said) for part, said in parts]
        out.append(CARD % (pad, ''.join(lines)))
    out.append('<div style="flex:1"></div>')
    if closing:
        out.append('<p style="font-size:32px; color:#E4DDD4">%s</p>' % closing)
    out += ['<aside>%s</aside>' % notes, '</section>', '']
    with open(os.path.join(ROOT, 'slides', sid + '.html'), 'w', encoding='utf-8') as h:
        h.write('\n'.join(out))
os.makedirs(os.path.join(ROOT, 'slides'), exist_ok=True)
slide('touches', 'Your project and your workflow', 'How little does Purlin change your project?', [
    ('A settings file', '%s, a folder for evidence, and a few lines in %s.' % (m('.purlin/config.json'), m('.gitignore'))),
    ('Your specs', 'Markdown files you write, under %s. Each holds the rules of one feature.' % m('specs/')),
    ('One comment per test', '%s above the test. The test itself does not change.' % m('# purlin: login RULE-4')),
    ('Your test command', 'Purlin runs your tests the way you already do. Nothing is installed in your test suite.'),
    ('Your workflow', 'You commit and push as before. Purlin commits only when you ask, and adds no git hook and no background job.'),
], '',
 'Purlin reads the report your test framework already writes and ties each result to its comment by '
 'the name of the test. A test with no comment runs as always and is ignored. A test Purlin wrote '
 'and a test you wrote differ in nothing but who typed them. Setup also copies the dashboard page '
 'into the project, where git ignores it.', pad=16)
slide('start', 'Getting started', 'Start in under ten minutes', [
    ('Install the plugin', 'Inside Claude Code: %s.' % m('/plugin install purlin@purlin')),
    ('`purlin:init`', 'Sets the project up. It asks how far every rule must go; answer %s.' % m('passed')),
    ('`purlin:spec`', 'Say in your own words what must be true. It writes the rules for you, one line each.'),
    ('`purlin:build`', 'Writes the code and its tests, or finds the tests you have. It adds one comment above each: %s.' % m('# purlin: cart RULE-1')),
    ('`purlin:test`', 'Runs your tests and prints %s' % m('Tests: 3 of 3 rules pass.')),
], '',
 'You need git, Python 3.9 or later and Claude Code. The marketplace is added once per project with '
 'claude plugin marketplace add. Setup reads the test framework from the project; where it finds '
 'none it asks for the command that runs the tests.', pad=16)
slide('passed', 'The first gate', 'Gate %s: only check that rules pass their tests' % mt('passed'), [
    ('`purlin:spec`', 'You say what must be true. It is written down as rules.'),
    ('`purlin:build`', 'The code and its tests are written. One comment above each test names the rule it shows.'),
    ('`purlin:test`', 'Runs the tests and reports each rule: passed, failed, no test, or out of date, which means something changed since its test ran.'),
], '<b>The gate is met</b> when every rule has a test that passed, and nothing has changed since it ran.',
 'At passed a project needs a rule and a test that names it. Out of date means the code, the rule or '
 'the test changed after the last run. purlin:test runs only what your change touched, writes the '
 'evidence, and commits it only when you pass --commit.',
 lead='A gate is how far every rule must go before a version counts as proven. You choose one of three.')
slide('strong', 'The second gate', 'Gate %s: also check that the tests are good enough' % mt('strong'), [
    ('`spec, build, test`', 'As before. Every rule also gets a proof: one plain sentence saying how the rule is shown to hold.'),
    ('`purlin:audit`', 'An AI model reads each test against its proof and reports any test that shows less than its proof says.', [
        ('Mutation testing', 'Optional. The code is broken on purpose to see whether the tests notice.'),
        ('The evidence', 'What ran and what the audit found, one file per feature. Committed when you ask.')]),
], '<b>The gate is met</b> when every rule also has a proof, and an audit that found no fault.',
 'A proof says in plain language how a rule is shown; QA writes and reviews them, and AI may draft '
 'them. The audit reads one rule per call, several at once, says how many it will read before it '
 'starts, and names the model on every finding. A rule whose text, proof and test have not changed '
 'is not read again.')
slide('signed', 'The third gate', 'Gate %s: also have a person sign every rule' % mt('signed'), [
    ('`test, audit`', 'As before. Every rule passes its tests and its audit.'),
    ('`purlin:sign`', 'Shows you each rule with its proof, its tests and what the audit found. You sign it.', [
        ('The signature', 'One file per rule, in a signed commit. It records who signed and when.'),
        ('The package and the tag', 'When every rule is signed, the evidence is written as one file and the version is tagged %s.' % m('signed/1.4.0'))]),
    ('`git push origin signed/1.4.0`', 'You publish the tag. It says every rule of this version is signed.'),
], '<b>The gate is met</b> when every rule has a signature. A signature stops counting when its rule, proof or test changes.',
 'Signing is the formal lock on all the evidence together: the rule, its proof, its test and what '
 'the audit found. Change any of them and the signature goes stale. A signature belongs to no '
 'machine; it records where it was made. The tag itself is signed.', pad=16)
slide('remote', 'Remote runners', 'When does Purlin use a remote runner in your repository?', [
    ('A rule must hold on another operating system', 'You work on a Mac and a rule must hold on Windows. %s runs those tests on a runner and brings the results back.' % m('purlin:test --remote')),
    ('You want the tests run on a clean machine', 'You choose at setup that results from a developer\'s machine do not count toward a signature. The tests run on a runner instead.'),
], 'In every other case Purlin uses no runner and adds no pipeline file to your repository.',
 'Two reasons and no others. Where a runner exists it runs on a pushed signed tag and on the run '
 'branch purlin:test --remote creates, waits on and deletes. The tag run reruns the tests on a clean '
 'machine, checks every signature against the tagged code, and checks that every file in the ci '
 'folder was committed by the runner itself.',
 lead='A remote runner is a machine your git host starts to run a job, as GitHub Actions does.')
slide('regulated', 'Regulated work', 'Purlin supplies evidence. It does not claim compliance.', [
    ('Purlin produces', 'Evidence for each rule: its tests and their results, what the audit found, and who signed.'),
    ('You hand over', 'The evidence package: one file for the version, made by %s.' % m('purlin:export')),
    ('Your system of record', 'The validated system your company uses for approval. It holds the document, decides who approves, and carries the approval that counts.'),
], '',
 'The package holds, for each rule: its words, its proofs, its tests, each result with when and '
 'where it ran, what the audit found and which model judged, and who signed, when and on which '
 'machine. A requirement number such as (URS-042) reaches it as a note in the rule\'s own words. '
 'The same tag always gives the same package, byte for byte.')
deck = {"v": 4, "createdOnFiles": {"v": 1, "at": "2026-09-26T18:00:00Z"},
        "title": "Purlin gate workflows",
        "order": ["touches", "start", "passed", "strong", "signed", "remote", "regulated"],
        "sections": {"s1": {"description": "How little Purlin changes in a project and a workflow, and how to start in under ten minutes", "start": "touches"},
                     "s2": {"description": "One slide per gate: what the gate checks, what you run, and when the gate is met", "start": "passed"},
                     "s3": {"description": "The two cases where Purlin uses a remote runner, and where Purlin stops in regulated work", "start": "remote"}},
        "faces": {}, "designSystems": []}
with open(os.path.join(ROOT, 'deck.json'), 'w', encoding='utf-8') as h:
    json.dump(deck, h, indent=2); h.write('\n')
