import json, os, re
# DECK_ROOT names the folder the deck's files are written under; the default sits beside this script.
ROOT = os.environ.get('DECK_ROOT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deck', 'project')
MONO = "font-family:'Courier New', monospace"
# A command or a file name inside a sentence: the viewer keeps the colour and drops the face.
def m(text):
    return '<span style="%s; color:#E6BEB0">%s</span>' % (MONO, text)
def mt(text):
    return '<span style="color:#C0793F">%s</span>' % text
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
# The mark and the name, pinned to the top right of every slide. The mark is
# design/assets/logo.svg, the one for navy grounds, without its metadata.
def brand():
    svg = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'design', 'assets', 'logo.svg'), encoding='utf-8').read()
    svg = re.sub(r'<metadata>.*?</metadata>', '', svg, flags=re.S).replace(' xmlns:c2pa="http://c2pa.org/manifest"', '')
    svg = svg.replace('width="670" height="330"', 'aria-label="Purlin" style="width:106px; height:52px"')
    return ('<div style="position:absolute; right:128px; top:80px; width:260px; display:flex; align-items:center; '
            'justify-content:flex-end; gap:16px">%s<p style="font-size:36px; font-weight:600; color:#E4DDD4">Purlin</p></div>' % svg)
# numbers=False drops the count at the start of each row: a slide with one case has nothing to count.
def slide(sid, eyebrow, headline, rows, closing, notes, lead='', width=620, gap=20, pad=18, numbers=True):
    out = [SECTION % (sid, gap),
           '<p style="font-size:24px; letter-spacing:3px; text-transform:uppercase; color:#C0793F">%s</p>' % eyebrow,
           '<h2 style="font-size:64px; font-weight:600; line-height:1.1">%s</h2>' % headline]
    if lead:
        out.append('<p style="font-size:32px; color:#BFCED5">%s</p>' % lead)
    out.append('<div style="flex:1"></div>')
    for i, row in enumerate(rows, 1):
        name, what, parts = row[0], row[1], row[2] if len(row) > 2 else ()
        head = CMD % (width, name.strip('`'))
        lines = [LINE % ((NUM % i if numbers else '') + head + WHAT % what)]
        lines += [PART % (width, part, said) for part, said in parts]
        out.append(CARD % (pad, ''.join(lines)))
    out.append('<div style="flex:1"></div>')
    if closing:
        out.append('<p style="font-size:32px; color:#E4DDD4">%s</p>' % closing)
    out += [brand(), '<aside>%s</aside>' % notes, '</section>', '']
    with open(os.path.join(ROOT, 'slides', sid + '.html'), 'w', encoding='utf-8') as h:
        h.write('\n'.join(out))
os.makedirs(os.path.join(ROOT, 'slides'), exist_ok=True)
slide('why', 'What Purlin is for', 'Why use Purlin?', [
    ('Tests pass. Do they cover what was asked?', 'You write each requirement as a rule. Purlin ties every rule to the tests that show it, and calls out every rule that doesn\'t have a test.'),
    ('AI writes code &amp; tests fast. Are they any good?', 'An AI audit reads each test against what it claims to show, and names the tests that show too little.'),
    ('Something changed. Is the result still true?', 'A result stops counting when the rule, the test or the code changes, until the tests are run again.'),
    ('Someone has to sign it off.', 'A person signs each rule, and the version gets a signed tag. The evidence is one file you hand over.'),
], '',
 'Purlin is a Claude Code plugin for spec-driven development. Its intended use is to produce '
 'evidence, in the repository, for the people who build the software and for whoever must sign it '
 'off. A team chooses how far to go: tests only, an audit too, or a signature too. Purlin cannot '
 'prove your code is correct, and it makes no claim of compliance.',
 lead='Purlin shows, rule by rule, that your software does what you said it must.', width=700)
slide('touches', 'Your project and your workflow', 'Purlin workflows don\'t change your project much', [
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
slide('fromcode', 'An existing codebase', 'Starting from code you already have', [
    ('Reads the code', 'It surveys the project and proposes a list of features. You merge, split and rename until the list is right.'),
    ('Writes the rules', 'One file per feature. Each rule says what the code does today, with a plain sentence saying how that is shown.'),
    ('Uses the tests you have', 'Where a test already shows a rule, it offers to add the comment above that test. It writes no new test.'),
    ('Reports where you stand', 'How many rules it wrote, how many already pass, and which have no test yet.'),
], '<b>A person reads every rule.</b> A rule read from code says what the code does, not what it should do.',
 'Run purlin:init first, then purlin:spec-from-code once. Twenty to forty features is normal for a '
 'mid-sized service. Each spec is committed on its own, and a session that ends halfway resumes at '
 'the next feature. Every rule is asked what the gate asks. Rules with no test go to purlin:build.',
 lead='%s is run once. It turns a codebase with no rules into one whose rules can be proven.' % m('purlin:spec-from-code'), width=560, pad=16)
slide('passed', 'The first gate', 'Gate %s: only check that rules pass their tests' % mt('passed'), [
    ('`purlin:spec`', 'You say what must be true. It is written down as rules.'),
    ('`purlin:build`', 'The code and its tests are written. One comment above each test names the rule it shows.'),
    ('`purlin:test`', 'Runs the tests and reports each rule: passed, failed, no test, or out of date, which means something changed since its test ran.'),
], '<b>A version is finished</b> when every rule has a test that passed, and nothing has changed since it ran.',
 'At passed a project needs a rule and a test that names it. Out of date means the code, the rule or '
 'the test changed after the last run. purlin:test runs only what your change touched, writes the '
 'evidence, and commits it only when you pass --commit.',
 lead='A gate is how far every rule must go before a version counts as proven. You choose one of three.')
slide('strong', 'The second gate', 'Gate %s: also check that the tests are good' % mt('strong'), [
    ('`spec, build, test`', 'As before. Every rule also gets a proof: one plain sentence saying how the rule is shown to hold.'),
    ('`purlin:audit`', 'An AI model reads each test against its proof and reports any test that shows less than its proof says.', [
        ('Mutation testing', 'Optional. The code is broken on purpose to see whether the tests notice.'),
        ('The evidence', 'What ran and what the audit found, one file per feature. Committed when you ask.')]),
], '<b>A version is finished</b> when the audit finds every rule strong: meaning its test actually shows what its proof says.',
 'A proof says in plain language how a rule is shown; QA writes and reviews them, and AI may draft '
 'them. The audit reads one rule per call, several at once, says how many it will read before it '
 'starts, and names the model on every finding. A rule whose text, proof and test have not changed '
 'is not read again.')
slide('signed', 'The third gate', 'Gate %s: a person signs to lock each rule to exactly what they reviewed' % mt('signed'), [
    ('`test, audit`', 'As before. Every rule passes its tests and its audit.'),
    ('`purlin:sign`', 'Shows you each rule with its proof, its tests and what the audit found. You sign it.', [
        ('The signature', 'One file per rule, in a signed commit. It records who signed and when.'),
        ('The package and the tag', 'When every rule is signed, the evidence is written as one file and the version is tagged %s.' % m('signed/1.4.0'))]),
    ('`git push origin signed/1.4.0`', 'You publish the tag. It says every rule of this version is signed.'),
], '<b>A version is finished</b> when every rule has a signature. This means the rule, its proof, its test, the code, what the audit found and where the tests ran are all tied together under the signature.',
 'Signing is the formal lock on one exact set: the rule, its proof, its test, the code the rule '
 'covers, what the audit found and the operating systems the tests ran on. Change any of them and '
 'the signature stops counting, and a person signs again. A signature belongs to no machine; it is '
 'bound to where the tests ran, not to where it was signed. The tag itself is signed.', pad=16)
slide('remote', 'Remote runners', 'When does Purlin use a remote runner in your repository?', [
    ('A rule must hold on another operating system', 'You work on a Mac and a rule must hold on Windows. %s runs those tests on a runner and brings the results back.' % m('purlin:test --remote')),
    ('What the runner does', 'It runs the tests and saves the results. Its job fails only when a test fails.'),
], 'In every other case Purlin only works locally and does NOT add a pipeline file to your repository.',
 'One reason and no other. Where a runner exists it runs on a pushed signed tag and on the run '
 'branch purlin:test --remote creates, waits on and deletes. A result counts wherever it ran, and '
 'each records the machine and the operating system it came from.',
 lead='A remote runner is a machine your git host starts to run a job, as GitHub Actions does.', numbers=False)
slide('regulated', 'Regulated work', 'Purlin supplies evidence. It does not claim compliance.', [
    ('Purlin produces', 'Evidence for each rule: its tests and their results, what the audit found, and who signed.'),
    ('You hand over', 'The evidence package: one file for the version, made by %s.' % m('purlin:export')),
    ('Your system of record', 'The validated system your company uses for approval. It holds the document, decides who approves, and carries the approval that counts.'),
], '',
 'The package holds, for each rule: its words, its proofs, its tests, each result with when and '
 'where it ran, what the audit found and which model judged, and who signed, when and on which '
 'machine. A requirement number such as (URS-042) reaches it as a note in the rule\'s own words. '
 'The same tag always gives the same package, byte for byte.')
slide('anchors', 'Shared rules', 'Anchors: rules that every project must follow', [
    ('Shared inside one project', 'Write a rule once, such as an API contract. Every feature that names the anchor takes on its rules. A global anchor applies to every feature.'),
    ('Owned by another department', 'Security, GRC or GxP keep their rules in their own repository. Each project brings in the ones it must follow.'),
    ('Kept in step', '%s shows what changed at the source and updates the project. A rule whose words changed is signed again.' % m('purlin:anchor sync')),
    ('Design standards too', 'Design publishes its standards as an anchor. Every feature that produces a screen follows them, and proves it.'),
], '<b>An anchor\'s rules count like any other:</b> each has its tests, its audit and its signature in every project that uses it.',
 'An anchor is a spec for something shared. A feature names it with Requires, and an anchor marked '
 'Global applies to every feature without being named. Most projects keep their anchors in their own '
 'repository and sync nothing. A second repository is for rules two or more projects must share: '
 'each project keeps a copy pinned to one commit, and purlin:anchor sync moves the pin. A pinned rule '
 'is never edited in place; a change is made at the source.',
 lead='An anchor is a set of rules written once and applied to many features, or to many projects.', width=560, pad=16)
deck = {"v": 4, "createdOnFiles": {"v": 1, "at": "2026-09-26T18:00:00Z"},
        "title": "Purlin gate workflows",
        "order": ["why", "touches", "start", "fromcode", "passed", "strong", "signed", "remote", "regulated", "anchors"],
        "sections": {"s1": {"description": "What Purlin is for, how little it changes in a project and a workflow, and how to start in under ten minutes or from code you already have", "start": "why"},
                     "s2": {"description": "One slide per gate: what the gate checks, what you run, and when a version is finished", "start": "passed"},
                     "s3": {"description": "The one case where Purlin uses a remote runner, where Purlin stops in regulated work, and how anchors carry shared rules across projects", "start": "remote"}},
        "faces": {}, "designSystems": []}
with open(os.path.join(ROOT, 'deck.json'), 'w', encoding='utf-8') as h:
    json.dump(deck, h, indent=2); h.write('\n')
