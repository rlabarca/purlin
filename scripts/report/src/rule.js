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

function findingLabel(name) { return FINDING_LABELS[name] || name; }

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
  var findings = findingsOf(rule).map(findingLabel);
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
  var approvals = (feature.approvals || []).filter(function (path) {
    return path.split('/').pop().indexOf(rule.id + '.') === 0;
  });
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
  var summary = reason
    ? 'On the review list because ' + reason + '.'
    : 'Not on the review list.';
  if (findings.length) {
    summary += ' The free checks name ' + findings.join(', ') + '.';
  }
  return '<button class="btn" data-act="nav" data-screen="board">'
    + '← Board</button>'
    + '<section style="margin-top:var(--space-6)">'
    + '<p class="eyebrow">' + esc(feature.name) + '</p>'
    + '<h1>' + esc(rule.id) + '</h1>'
    + '<p class="sec">' + esc(rule.text) + '</p></section>'
    + '<section class="stack"><div class="panel"><dl class="kv">'
    + rows.map(function (row) {
      return '<dt>' + esc(row[0]) + '</dt><dd>' + row[1] + '</dd>';
    }).join('') + '</dl></div>'
    + '<div class="panel"><h2>Review</h2><p class="sec">' + esc(summary)
    + '</p></div></section>'
    + '<section><p class="eyebrow">Proofs</p><div class="stack">'
    + ((rule.proofs || []).length
      ? rule.proofs.map(proofPanel).join('')
      : '<div class="panel sec">This rule has no proof yet.</div>')
    + '</div></section>';
}
