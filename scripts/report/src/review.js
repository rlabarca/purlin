/* The Review list: what CI put in front of a person, highest risk first. The
   group header already says the risk, so a row says the things the group
   cannot: which rule, what it claims, where it stands, and what is wrong with
   it beyond the risk it shares with every other row in the group. */

/* Long enough to read the claim, short enough that a list of two hundred rows
   stays one column of text. The rest of the rule is on its own screen. */
var RULE_TEXT_MAX = 90;

function shortText(text) {
  var value = String(text == null ? '' : text);
  if (value.length <= RULE_TEXT_MAX) { return value; }
  return value.slice(0, RULE_TEXT_MAX).replace(/\s+\S*$/, '') + '…';
}

/* The rule the entry points at, from the feature entry that proves it. */
function reviewRule(entry) {
  var feature = featureNamed(entry.feature);
  var found = null;
  if (feature) {
    (feature.rules || []).forEach(function (rule) {
      if (rule.id === entry.rule) { found = rule; }
    });
  }
  return found;
}

/* The reasons worth printing beside a row: the risk is the group it sits in,
   so repeating it would read the same on every row under that header. A free
   check is read out by its short label; the Rule screen carries the sentence. */
function reviewRowReasons(entry) {
  var reasons = [];
  (entry.reasons || []).forEach(function (reason) {
    if (/^risk (high|medium|low)$/.test(reason)) { return; }
    reasons.push(findingLabel(reason));
  });
  return reasons;
}

function reviewRow(entry) {
  var rule = reviewRule(entry);
  return '<div class="rev" data-act="rule" data-feature="'
    + esc(entry.feature) + '" data-rule="' + esc(entry.rule) + '">'
    + '<span>' + esc(entry.feature) + '</span>'
    + '<span class="mono">' + esc(entry.rule) + '</span>'
    + '<span>' + esc(rule ? shortText(rule.text) : '') + '</span>'
    + (rule ? pill(rule.state) : '<span></span>')
    + '<span class="sec">' + esc(reviewRowReasons(entry).join('; '))
    + '</span></div>';
}

function renderReview() {
  var entries = DATA.review_list || [];
  if (!entries.length) {
    return '<section><p class="eyebrow">Review list</p>'
      + '<div class="panel empty">Nothing is waiting for a look. CI adds a '
      + 'rule here when its risk asks for one, when an approval goes stale, '
      + 'or when the test strength falls below the minimum.</div></section>';
  }
  var head = '<section><p class="eyebrow">Review list</p><h1>'
    + entries.length + ' rules need a look</h1>'
    + '<p class="sec">Ordered by risk. Open a rule to read its proof, then '
    + 'approve it, add a case, or skip it.</p></section>';
  var body = RISKS.map(function (risk) {
    var group = entries.filter(function (entry) {
      return (entry.risk || 'low') === risk;
    });
    if (!group.length) { return ''; }
    return '<div class="group"><span class="gt">' + esc(risk)
      + ' risk</span><span class="muted">(' + group.length + ')</span></div>'
      + group.map(reviewRow).join('');
  }).join('');
  return head + '<section><div class="tbl">' + body + '</div></section>';
}
