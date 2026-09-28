/* The Rule screen: one rule, its level and the cells the gate reaches,
   what the audit found, the signature, and the proofs that stand for it with
   the tests that carry them. */

function ruleInView() {
  var feature = featureNamed(VIEW.feature);
  if (!feature) { return null; }
  var found = null;
  (feature.rules || []).forEach(function (r) {
    if (r.id === VIEW.rule) { found = r; }
  });
  return found ? {feature: feature, rule: found} : null;
}

/* One small box per operating system a counting run covered, in the tone of
   what that run found there. The board draws no such box; this is where the
   page says which platform passed, and the hover says where the run came from
   and how old it is. */
function platformBoxes(cell) {
  var platforms = (cell && cell.platforms) || {};
  return Object.keys(platforms).sort().map(function (os) {
    var entry = platforms[os];
    return '<span class="os ' + (entry.word === 'passed' ? 'pass'
        : entry.word === 'failed' ? 'fail' : 'none') + '"'
      + hover([[os, entry.word, entry.source || 'local',
        ageText(entry.at).text].join(' \u00b7 ')])
      + '>' + esc(os.slice(0, 3)) + '</span>';
  }).join(' ');
}

/* One row per cell the gate reaches: the word it reads, what the payload
   carries beside that word, then the reasons, each already a sentence
   fragment the payload wrote. The passed cell's platforms and the signed
   cell's signer and date are facts the word alone leaves out. */
function cellRow(rule, name) {
  var cell = cellOf(rule, name);
  if (!cell) { return ''; }
  var reasons = (cell.reasons || []).filter(function (text) {
    return text !== 'by ' + cell.signer
      && (showsProofs() || text !== 'no proof written');
  }).join('; ');
  var beside = name === 'passed' ? platformBoxes(cell)
    : name === 'signed' && cell.signer ? '<span class="mono sec">'
      + esc(cell.signer + ' \u00b7 ' + when(cell.at)) + '</span>' : '';
  return '<dt>' + esc(CELL_LABELS[name]) + '</dt><dd>' + pill(cell.word)
    + (beside ? ' ' + beside : '')
    + (reasons ? ' <span class="sec">' + esc(reasons) + '</span>' : '')
    + '</dd>';
}

/* What the audit found, and nothing about what to do with it: its answer,
   each finding on its own line as the audit wrote it, the test strength
   beside the minimum this gate asks for or `no mutation score measured`,
   then the model that read the rule and when. The audit writes sentences,
   so there is no list of check names to render here. */
function auditPanel(rule) {
  var cell = cellOf(rule, 'strong');
  if (!cell) { return ''; }
  var audit = rule.audit;
  var lines = [];
  var findings = (audit && audit.findings) || [];
  var answer = audit ? audit['verdict'] : null;
  if (!audit) {
    lines.push(line('No audit has read this rule\u2019s text, proof and '
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
  lines.push(line(cell.strength == null ? 'no mutation score measured'
    : 'Test strength ' + Math.round(cell.strength) + '%, against a minimum '
      + 'of ' + minStrength() + '%.'));
  if (audit) {
    lines.push('<p class="sec">Read by <span class="mono">'
      + esc(audit.model || 'unknown') + '</span> on '
      + esc(moment(audit.at)) + '</p>');
    if (audit.path) {
      lines.push('<p class="sec">' + hostLink(audit.path, audit.path) + '</p>');
    }
  }
  return '<div class="panel"><h2>Audit</h2>' + lines.join('') + '</div>';
}

function line(text) { return '<p class="sec">' + esc(text) + '</p>'; }

/* The signature files that bind this rule. One is named
   <RULE-N>.<hash8>.<signer-slug>.json, so the third part names who. */
function signaturesFor(feature, rule) {
  return (feature.signatures || []).filter(function (path) {
    return path.split('/').pop().indexOf(rule.id + '.') === 0;
  });
}

/* A signature is a signed commit, so this page cannot write one: it names the
   command that does, and reads back the signature already committed, with
   who signed, when, and on which machine and operating system. The panel is
   headed with what the queue calls the need, `Hand check` or `Signature`. */
function signPanel(feature, rule) {
  var cell = cellOf(rule, 'signed');
  if (!cell) { return ''; }
  if (cell.word === 'signed') {
    var where = cell.machine
      ? ', on ' + cell.machine + (cell.os ? ' (' + cell.os + ')' : '') : '';
    return '<div class="panel"><h2>Signed</h2><p class="sec">'
      + esc('Signed by ' + (cell.signer || 'a person') + ' on ' + moment(cell.at) + where
        + ', against the rule, its proofs, its tests and what the audit '
        + 'found as this screen shows them. The signature file beside the '
        + 'spec carries the commit that signed it.')
      + '</p></div>';
  }
  var row = queueRowFor(feature.name, rule.id);
  var hand = row && row.need === 'hand check';
  var command = row ? row.command
    : 'purlin:sign ' + feature.name + ' ' + rule.id;
  return '<div class="panel"><h2>' + (hand ? 'Hand check' : 'Signature')
    + '</h2><p><span class="cmd">' + esc(command) + '</span> '
    + '<span class="sec">from Claude Code</span></p>'
    + '<p class="sec">' + (rule.level !== 'signed'
      ? 'This rule\u2019s level is ' + esc(rule.level) + ', so it asks for no '
        + 'signature; one written anyway still counts.'
      : hand ? 'A hand check is a signature with a note of what you saw; the '
        + 'page shows it once it is committed.'
      : 'A signature is a signed commit that names its signer; the page '
        + 'shows it once it is committed.') + '</p></div>';
}

function proofPanel(proof) {
  var tests = (proof.tests || []).map(function (t) {
    return esc(t.file) + ' :: ' + esc(t.name);
  }).join('\n') || 'no test yet';
  var tags = (proof.manual ? ['@manual'] : [])
    .concat(proof.env ? ['@env(' + proof.env + ')'] : []);
  return '<div class="panel"><dl class="kv">'
    + '<dt>' + esc(proof.id) + '</dt><dd>' + esc(proof.text) + '</dd>'
    + (tags.length ? '<dt>Tags</dt><dd>' + tag(tags.join(' '), true) + '</dd>'
      : '')
    + '<dt>Tests</dt><dd><pre class="code">' + tests + '</pre></dd>'
    + '</dl></div>';
}

/* The link back closes the rule rather than leaving it open behind another
   screen, and it returns to the screen the rule was opened from. */
function backLink() {
  var from = VIEW.from === 'queue' && level('strong') ? 'queue' : 'board';
  var label = {queue: 'Queue', board: 'Board'}[from];
  return '<button class="btn" data-act="close" data-screen="' + from + '">← '
    + label + '</button>';
}

function renderRule() {
  var found = ruleInView();
  if (!found) {
    return '<div class="empty">That rule is not in this data. Go back to the '
      + 'board and pick one.</div>';
  }
  var feature = found.feature;
  var rule = found.rule;
  var rows = [];
  GATE_LEVELS.forEach(function (name) { rows.push(cellRow(rule, name)); });
  if (level('strong')) {
    rows.push('<dt>Level</dt><dd>' + levelTag(rule) + ' <span class="sec">'
      + esc(levelSource(rule)) + '</span></dd>');
  }
  rows.push('<dt>Spec</dt><dd>' + hostLink(feature.spec_path, feature.spec_path)
    + '</dd>');
  rows.push('<dt>Last run</dt><dd>' + runLine(feature) + '</dd>');
  var signatures = level('signed') ? signaturesFor(feature, rule) : [];
  if (signatures.length) {
    rows.push('<dt>Signatures</dt><dd>' + signatures.map(function (path) {
      return hostLink(path, path.split('/').pop());
    }).join('<br>') + '</dd>');
  }
  return backLink()
    + '<section style="margin-top:var(--space-6)">'
    + '<p class="eyebrow">' + esc(feature.name) + '</p>'
    + '<h1>' + esc(rule.id) + '</h1>'
    + '<p class="sec">' + esc(rule.text) + '</p></section>'
    + '<section class="stack"><div class="panel"><dl class="kv">'
    + rows.join('') + '</dl></div>'
    + auditPanel(rule) + signPanel(feature, rule) + '</section>'
    + (showsProofs() ? '<section><p class="eyebrow">Proofs</p>'
      + '<div class="stack">' + ((rule.proofs || []).length
        ? rule.proofs.map(proofPanel).join('')
        : '<div class="panel sec">No proof written.</div>')
      + '</div></section>' : '');
}
