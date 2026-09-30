/* The Rule screen: one rule and its cells, what the audit found, the proofs
   that stand for it with the tests that carry them, and the tests marked
   with the rule's own id. */

/* The open rule, by the spec that owns it and its id: opening
   `ai_audit RULE-1` and `security_no_dangerous_patterns RULE-1` opens two
   rules, wherever either was clicked. */
function ruleInView() {
  var feature = featureNamed(VIEW.feature);
  var found = ruleNamed(VIEW.feature, VIEW.rule);
  return feature && found ? {feature: feature, rule: found} : null;
}

/* One small box per operating system a counting run covered, in the tone of
   what that run found there, labelled with the system's short word. The
   board draws no such box; this is where the page says which system passed,
   and the hover names the system and says where the run came from and how
   old it is. */
function platformBoxes(cell) {
  var platforms = (cell && cell.platforms) || {};
  return Object.keys(platforms).sort().map(function (os) {
    var entry = platforms[os];
    return '<span class="os ' + (entry.word === 'passed' ? 'pass'
        : entry.word === 'failed' ? 'fail' : 'none') + '"'
      + hover([[systemWords(os).word, entry.word, entry.source || 'local',
        ageText(entry.at).text].join(DOT)])
      + '>' + esc(systemWords(os).short) + '</span>';
  }).join(' ');
}

/* One row per cell the page draws, the strong cell only where the audit has
   read the project: the word it reads, the passed cell's platforms, which
   the word alone leaves out, then the reasons, each already a sentence
   fragment the payload wrote. */
function cellRow(rule, name) {
  var cell = cellOf(rule, name);
  if (!cell || (name === 'strong' && !audited())) { return ''; }
  var reasons = (cell.reasons || []).filter(function (text) {
    return showsProofs() || text !== 'no proof written';
  }).join('; ');
  var beside = name === 'passed' ? platformBoxes(cell) : '';
  return '<dt>' + esc(CELL_LABELS[name]) + '</dt><dd>' + pill(cell.word)
    + (beside ? ' ' + beside : '')
    + (reasons ? ' <span class="sec">' + esc(reasons) + '</span>' : '')
    + '</dd>';
}

/* What the audit found, and nothing about what to do with it, drawn at
   either gate once the audit has read the project: its answer, each finding
   on its own line as the audit wrote it, the test strength where one was
   measured and nothing of strength where none was, then the model that read
   the rule and when.
   The answer is worded as the terminal words it, and the strength reads its
   whole-number part, as the board's cell does, so 85.7 reads 85 on both.
   The audit writes sentences, so there is no list of check names to render
   here. */
function auditPanel(rule) {
  var cell = cellOf(rule, 'strong');
  if (!cell || !audited()) { return ''; }
  var audit = rule.audit;
  var lines = [];
  var findings = (audit && audit.findings) || [];
  var answer = audit ? audit['verdict'] : null;
  if (!audit) {
    lines.push(line("No audit has read this rule's text, proof and "
      + 'test yet.'));
  } else if (answer === 'strong' && !findings.length) {
    lines.push(line('Strong. It found nothing.'));
  } else if (answer === 'undecided') {
    lines.push(line('Undecided. The AI audit could not decide, so the rule '
      + 'reads weak until its proof or test changes.'));
  } else {
    lines.push(line(answer === 'strong' ? 'Strong.' : 'Weak.'));
  }
  findings.forEach(function (text) { lines.push(line(text)); });
  if (cell.strength != null) {
    lines.push(line('Test strength ' + Math.floor(cell.strength) + '%.'));
  }
  if (audit) {
    lines.push('<p class="sec">Read by <span class="mono">'
      + esc(audit.model || 'unknown') + '</span> on '
      + unbroken(moment(audit.at)) + '</p>');
    if (audit.path) {
      lines.push('<p class="sec">' + hostLink(audit.path, audit.path) + '</p>');
    }
  }
  return '<div class="panel"><h2>Audit</h2>' + lines.join('') + '</div>';
}

function line(text) { return '<p class="sec">' + esc(text) + '</p>'; }

/* A value set on one line, so a date or an address never breaks inside
   itself; the sentence around it still wraps. */
function unbroken(text) {
  return '<span class="nowrap">' + esc(text) + '</span>';
}

/* A command the page cannot run, named as the line to type:
   `Type <command> in Claude Code.`, the command in the monospace face, after
   whatever the line says first. The sentence is one span, so a line that
   lays its parts out side by side, as a test's line does, keeps it whole. */
function typeLine(command, before) {
  return '<p class="sec"><span>' + esc(before) + 'Type <span class="cmd">'
    + esc(command) + '</span> in Claude Code.</span></p>';
}

/* What a proof or a rule with no test says, and the command that writes
   one for the spec that owns the rule. */
function noTestLine(owner) {
  return typeLine('purlin:build ' + owner, 'No test yet. ');
}

/* The word a test reads: the evidence writes `pass`, `fail`, `missing` or
   `not run`, and the page shows the cell word the run gave the rule for
   each, so a test and its rule never disagree. */
var TEST_WORDS = {pass: 'passed', fail: 'failed', missing: 'not run',
  'not run': 'not run'};

/* A proof's own word, as the payload wrote it. At the gate `passed` a
   `@manual` proof reads `manual`, because nothing checks it by hand there. */
function proofWord(proof) {
  var word = proof.result || 'not run';
  return word === 'hand check' && !level('signed') ? 'manual' : word;
}

/* What a `@manual` proof no test carries says under its tests. At the gate
   `signed` a person checks it in the sign-off walk and types what they saw;
   at `passed` nobody signs, and the release's evidence package lists it as
   not checked. */
function handCheckLine() {
  return '<p class="sec">' + esc(level('signed')
    ? 'Checked by hand when a release is signed, in the walk of purlin:sign.'
    : 'Checked by hand. A release at the gate passed lists it as not '
      + 'checked.') + '</p>';
}

/* Tests, one line each: a dot in the colour of the word its run gave it,
   the word in the dot's hover, then `file :: name`. A narrow line may break
   after a `::`, between a test's class and its name, rather than inside
   either. */
function testLines(tests) {
  return (tests || []).map(function (t) {
    var word = TEST_WORDS[t.result] || 'not run';
    return '<p><span class="dot" role="img" title="' + esc(word)
      + '" aria-label="' + esc(word) + '" style="color:var(--state-'
      + tone(word) + ')"></span><span class="mono">' + esc(t.file) + ' :: '
      + esc(t.name).split('::').join('::<wbr>') + '</span></p>';
  }).join('');
}

/* One proof: its id and words, its own result, its `@manual` and `@env`
   tags, which name the operating system it asks for, and its tests with
   what each found. The board draws it under a rule and the rule screen in
   its Proofs section, from this one function, so the two never disagree.
   A `@manual` proof no test carries is checked by hand, and says when.
   `rule.feature` is the spec that owns the rule, whose build writes a
   missing test. */
function proofDetail(proof, rule) {
  var owner = rule.feature;
  var tags = (proof.manual ? ['@manual'] : [])
    .concat(proof.env ? ['@env(' + proof.env + ')'] : []);
  var tests = testLines(proof.tests)
    || (proof.manual ? handCheckLine()
    : proofWord(proof) === 'not run'
      ? '<p class="sec">No run has listed its tests yet.</p>'
      : noTestLine(owner));
  return '<dl class="kv">'
    + '<dt>' + esc(proof.id) + '</dt><dd>' + esc(proof.text) + '</dd>'
    + '<dt>Result</dt><dd>' + pill(proofWord(proof)) + '</dd>'
    + (tags.length ? '<dt>Tags</dt><dd>' + tag(tags.join(' '), true) + '</dd>'
      : '')
    + '<dt>Tests</dt><dd class="ptests">' + tests + '</dd></dl>';
}

function proofPanel(proof, rule) {
  return '<div class="panel">' + proofDetail(proof, rule) + '</div>';
}

/* The tests marked with the rule's own id, one line each with its result.
   Shown wherever a rule lists any, and always where the page shows no
   proofs, so a rule at the gate `passed` shows the tests behind it. */
function testsSection(rule) {
  var tests = rule.tests || [];
  if (!tests.length && showsProofs()) { return ''; }
  var lines = testLines(tests) || noTestLine(rule.feature);
  return '<section><p class="eyebrow">Tests</p><div class="panel tests">'
    + lines + '</div></section>';
}

/* The link back closes the rule rather than leaving it open behind the
   board. */
function backLink() {
  return '<button class="btn" data-act="close">Back to the board</button>';
}

function renderRule() {
  var found = ruleInView();
  if (!found) {
    return '<div class="empty">That rule is not in this data. Go back to the '
      + 'board and pick one.</div>';
  }
  var feature = found.feature;
  var rule = found.rule;
  var rows = [cellRow(rule, 'passed'), cellRow(rule, 'strong')];
  rows.push('<dt>Spec</dt><dd>' + hostLink(feature.spec_path, feature.spec_path)
    + '</dd>');
  rows.push('<dt>Last run</dt><dd>' + runLine(feature) + '</dd>');
  return backLink()
    + '<section style="margin-top:var(--space-6)">'
    + '<p class="eyebrow">' + esc(feature.name) + '</p>'
    + '<h1>' + esc(rule.id) + '</h1>'
    + '<p class="sec">' + esc(rule.text) + '</p></section>'
    + '<section class="stack"><div class="panel"><dl class="kv">'
    + rows.join('') + '</dl></div>'
    + auditPanel(rule) + '</section>'
    + (showsProofs() ? '<section><p class="eyebrow">Proofs</p>'
      + '<div class="stack">' + ((rule.proofs || []).length
        ? rule.proofs.map(function (proof) {
          return proofPanel(proof, rule);
        }).join('')
        : '<div class="panel sec">No proof written.</div>')
      + '</div></section>' : '')
    + testsSection(rule);
}
