/* The Rule screen: one rule, the proofs that stand for it, the tests that run
   them, and the evidence that has accumulated. */

var FINDING_LABELS = {
  'no_expected_value': 'no expected value',
  'vague_verb': 'vague verb',
  'missing_trigger': 'missing trigger',
  'tier_mismatch': 'tier mismatch',
  'implementation_coupling': 'names a symbol, not an outcome',
  'happy_path_only': 'no negative case'
};

/* The sentence the free checks already write, one per finding, copied from
   the checks module so the page and the brief say the same thing about the
   same proof rather than keeping a second set of words. */
var FINDING_TEXT = {
  'no_expected_value': 'Names no literal, number, quoted string or named constant, so almost any assertion would satisfy it.',
  'vague_verb': 'Uses a vague verb with no expected value beside it. A proof should be readable straight into a test.',
  'missing_trigger': 'Nothing runs before the assertion, so the proof reads an artifact that exists whether or not the code is right.',
  'tier_mismatch': 'An @e2e proof must read as an observable flow. Drive the real interface or retag the proof to the tier it exercises.',
  'implementation_coupling': 'Names a private symbol, a selector or a path instead of an observable outcome, so a refactor breaks the proof without changing behaviour.',
  'happy_path_only': 'No proof of this rule names a rejection, an error or a boundary.'
};

function findingLabel(name) { return FINDING_LABELS[name] || name; }

function findingText(name) { return FINDING_TEXT[name] || findingLabel(name); }

function ruleInView() {
  var feature = featureNamed(VIEW.feature);
  if (!feature) { return null; }
  var found = null;
  (feature.rules || []).forEach(function (rule) {
    if (rule.id === VIEW.rule) { found = rule; }
  });
  return found ? {feature: feature, rule: found} : null;
}

function reviewReason(featureName, ruleId) {
  var reason = null;
  (DATA.review_list || []).forEach(function (entry) {
    if (entry.feature === featureName && entry.rule === ruleId) {
      reason = entry.reason;
    }
  });
  return reason;
}

/* Why a person has to look, in words rather than in the payload's shorthand.
   A reason this page does not recognise is still read out, so a new one added
   upstream reaches the reader unchanged. */
function reviewReasonSentence(reason) {
  var risk = /^risk (high|medium|low) needs a look$/.exec(reason || '');
  if (risk) {
    return 'Its risk is ' + risk[1]
      + ', so a person looks before it can be approved.';
  }
  if (reason === 'the approval is stale') {
    return 'Its approval is stale, so a person looks at it again before it '
      + 'counts.';
  }
  return 'It is on the review list because ' + reason + '.';
}

/* Why it is listed, then one sentence per finding naming the proofs that
   carry it. A finding the checks raise against the rule as a whole lands on
   every proof, so grouping by finding states it once. */
function reviewPanel(rule, reason) {
  var lines = [];
  var order = [];
  var ids = {};
  if (reason) {
    lines.push('<p class="sec">' + esc(reviewReasonSentence(reason)) + '</p>');
  }
  (rule.proofs || []).forEach(function (proof) {
    (proof.findings || []).forEach(function (name) {
      if (!ids[name]) { ids[name] = []; order.push(name); }
      if (ids[name].indexOf(proof.id) < 0) { ids[name].push(proof.id); }
    });
  });
  order.forEach(function (name) {
    lines.push('<p class="sec"><span class="mono">' + esc(ids[name].join(', '))
      + '</span>: ' + esc(findingText(name)) + '</p>');
  });
  if (!lines.length) {
    lines.push('<p class="sec">This rule is not on the review list, and the '
      + 'free checks found nothing to raise.</p>');
  }
  return '<div class="panel"><h2>Review</h2>' + lines.join('') + '</div>';
}

/* The approval files that bind this rule. One is named
   <RULE-N>.<hash8>.<approver>.json, so the third part names who. */
function approvalsFor(feature, rule) {
  return (feature.approvals || []).filter(function (path) {
    return path.split('/').pop().indexOf(rule.id + '.') === 0;
  });
}

function approverOf(path) {
  var parts = path.split('/').pop().split('.');
  var slug = parts.length > 2 ? parts[2] : '';
  return slug === 'ci' ? 'CI' : slug;
}

/* An approval is a signed commit, so this page cannot make one: it names the
   command that does, and reads back the approvals already on the branch. */
function approvePanel(feature, rule) {
  var approvals = approvalsFor(feature, rule);
  if (rule.state === 'Approved' && approvals.length) {
    var who = approvals.map(approverOf).filter(function (name) {
      return !!name;
    }).join(', ');
    return '<div class="panel"><h2>Approved</h2><p class="sec">'
      + esc('Approved by ' + (who || 'someone on the approver list')
        + ' against the rule, proof and test text this screen shows. The '
        + 'approval file beside the spec carries the commit that signed it.')
      + '</p></div>';
  }
  return '<div class="panel"><h2>To approve</h2>'
    + '<p><span class="cmd">purlin:approve ' + esc(feature.name) + ' '
    + esc(rule.id) + '</span> <span class="sec">from Claude Code</span></p>'
    + '<p class="sec">An approval is a signed commit by someone on the '
    + 'approver list; the page shows it once it is on the branch.</p></div>';
}

function proofPanel(proof) {
  var tests = (proof.tests || []).map(function (test) {
    return esc(test.file) + ' :: ' + esc(test.name);
  }).join('\n') || 'no tagged test yet';
  var findings = (proof.findings || []).map(function (name) {
    return '<span class="finding">' + esc(findingLabel(name)) + '</span>';
  }).join(', ');
  return '<div class="panel"><dl class="kv">'
    + '<dt>' + esc(proof.id) + '</dt><dd>' + esc(proof.text) + '</dd>'
    + '<dt>Tier</dt><dd>' + tag(proof.tier + (proof.env ? ' · ' + proof.env : ''), true)
    + '</dd>'
    + '<dt>Tests</dt><dd><pre class="code">' + tests + '</pre></dd>'
    + (findings ? '<dt>Free checks</dt><dd>' + findings + '</dd>' : '')
    + '</dl></div>';
}

/* The link back closes the rule rather than leaving it open behind another
   screen, and it returns to the screen the rule was opened from. */
function backLink() {
  var from = VIEW.from === 'review' ? 'review' : 'board';
  return '<button class="btn" data-act="close" data-screen="' + from + '">'
    + (from === 'review' ? '← Review list' : '← Board') + '</button>';
}

function renderRule() {
  var found = ruleInView();
  if (!found) {
    return '<div class="empty">That rule is not in this data. Go back to the '
      + 'board and pick one.</div>';
  }
  var feature = found.feature;
  var rule = found.rule;
  var record = feature.latest_record;
  var reason = reviewReason(feature.name, rule.id);
  var rows = [
    ['State', pill(rule.state)],
    ['Risk', tag(rule.risk, rule.risk === 'low')],
    ['Origin', tag(rule.origin, true)],
    ['Spec', hostLink(feature.spec_path, feature.spec_path)]
  ];
  if (rule.criterion) {
    rows.splice(3, 0, ['Criterion', tag(rule.criterion, true)]);
  }
  if (feature.test_strength != null || record) {
    rows.push(['Test strength', strength(feature.test_strength)]);
    rows.push(['Latest record', record
      ? recordCell(record) + ' '
        + hostLink(record.path, record.timestamp || record.path)
      : '<span class="mono muted">none</span>']);
  }
  var approvals = approvalsFor(feature, rule);
  if (approvals.length) {
    rows.push(['Approvals', approvals.map(function (path) {
      return hostLink(path, path.split('/').pop());
    }).join('<br>')]);
  }
  if ((rule.missing_env || []).length) {
    rows.push(['Waiting on', '<span class="mono" '
      + 'style="color:var(--state-warn)">'
      + esc(rule.missing_env.join(', ')) + ': no record yet</span>']);
  }
  if ((rule.flags || {}).re_verify_pending) {
    rows.push(['Re-verify', '<span class="mono" '
      + 'style="color:var(--state-warn)">pending</span>']);
  }
  return backLink()
    + '<section style="margin-top:var(--space-6)">'
    + '<p class="eyebrow">' + esc(feature.name) + '</p>'
    + '<h1>' + esc(rule.id) + '</h1>'
    + '<p class="sec">' + esc(rule.text) + '</p></section>'
    + '<section class="stack"><div class="panel"><dl class="kv">'
    + rows.map(function (row) {
      return '<dt>' + esc(row[0]) + '</dt><dd>' + row[1] + '</dd>';
    }).join('') + '</dl></div>'
    + reviewPanel(rule, reason)
    + approvePanel(feature, rule) + '</section>'
    + '<section><p class="eyebrow">Proofs</p><div class="stack">'
    + ((rule.proofs || []).length
      ? rule.proofs.map(proofPanel).join('')
      : '<div class="panel sec">This rule has no proof yet.</div>')
    + '</div></section>';
}
