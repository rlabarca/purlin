/* The Review list: the rules whose next step is a person, highest risk first.
   The group header already says the risk, so a row says the things the group
   cannot: which rule, what it claims, which cell blocks it, and why. */

/* Long enough to read the claim, short enough that a list of two hundred rows
   stays one column of text. The rest of the rule is on its own screen. */
var RULE_TEXT_MAX = 90;

/* The closed set of tokens the payload puts on an entry, as sentences. A
   token this page does not recognise is still read out, so a new one added
   upstream reaches the reader unchanged. */
var WHY_SENTENCES = {
  'unsigned': 'Nobody has signed it.',
  'stale': 'Its signature no longer matches the rule, proof and test it was '
    + 'written against.',
  'held': 'A person holds it: the test does not prove the proof.',
  'manual test': 'Its proof is @manual, so a person runs the test and states '
    + 'what they saw.',
  'manual audit': 'The model review could not settle it, so a person judges '
    + 'the proof against the test.'
};

/* The five counts the risk summary carries, in the order it prints them. Each
   token counts under its own name, because each names different work. */
var WHY_COUNTS = ['unsigned', 'stale', 'held', 'manual test', 'manual audit'];

function shortText(text) {
  var value = String(text == null ? '' : text);
  if (value.length <= RULE_TEXT_MAX) { return value; }
  return value.slice(0, RULE_TEXT_MAX).replace(/\s+\S*$/, '') + '…';
}

/* The rule the entry points at, from the feature entry that owns it. */
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

function whySentence(token) {
  return WHY_SENTENCES[token] || 'It is on the review list because ' + token
    + '.';
}

/* What the blocking cell says beyond its one word. The cell's own reasons are
   the specific ones, so they are printed where there are any; the tokens the
   entry carries stand in where there are none. */
function reviewRowReasons(entry, rule) {
  var cell = rule ? cellOf(rule, entry.cell) : null;
  var reasons = (cell && cell.reasons) || [];
  if (reasons.length) { return reasons.join('; '); }
  return (entry.why || []).map(whySentence).join(' ');
}

function reviewRow(entry) {
  var rule = reviewRule(entry);
  var cell = rule ? cellOf(rule, entry.cell) : null;
  return '<div class="rev" data-act="rule" data-feature="'
    + esc(entry.feature) + '" data-rule="' + esc(entry.rule) + '">'
    + '<span>' + esc(entry.feature) + '</span>'
    + '<span class="mono">' + esc(entry.rule) + '</span>'
    + '<span>' + esc(rule ? shortText(rule.text) : '') + '</span>'
    + riskTag(entry.risk)
    + (cell ? pill(cell.word) : '<span></span>')
    + '<span class="sec">' + esc(reviewRowReasons(entry, rule)) + '</span>'
    + '</div>';
}

/* Stale and held first inside a group: a signature that stopped counting and
   a rule a colleague stopped are the two a person came here to settle. */
function reviewOrder(entries) {
  var first = [];
  var rest = [];
  entries.forEach(function (entry) {
    var why = entry.why || [];
    if (why.indexOf('stale') >= 0 || why.indexOf('held') >= 0) {
      first.push(entry);
    } else { rest.push(entry); }
  });
  return first.concat(rest);
}

/* One line per risk that has a row, with the five counts that say what kind
   of answer each rule is waiting for. */
function riskSummary(entries) {
  var lines = RISKS.map(function (risk) {
    var group = entries.filter(function (entry) {
      return (entry.risk || 'low') === risk;
    });
    if (!group.length) { return ''; }
    var totals = {};
    group.forEach(function (entry) {
      (entry.why || []).forEach(function (token) {
        if (WHY_COUNTS.indexOf(token) >= 0) {
          totals[token] = (totals[token] || 0) + 1;
        }
      });
    });
    return '<p class="rsum">' + riskTag(risk)
      + WHY_COUNTS.map(function (name) {
        var n = totals[name] || 0;
        return '<span class="' + (n ? 'sec' : 'muted') + '"><b>' + n
          + '</b> ' + esc(name) + '</span>';
      }).join('<i>·</i>') + '</p>';
  }).join('');
  return lines ? '<div class="panel">' + lines + '</div>' : '';
}

function renderReview() {
  var entries = DATA.review_list || [];
  if (!entries.length) {
    return '<section><p class="eyebrow">Review list</p>'
      + '<div class="panel empty">No rule is waiting for a person. A rule '
      + 'arrives here when the machine cannot settle it, when a signature '
      + 'stops matching, when someone holds it, or when it is unsigned at or '
      + 'above the risk this project signs from.</div></section>';
  }
  var head = '<section><p class="eyebrow">Review list</p><h1>'
    + entries.length + (entries.length === 1 ? ' rule needs' : ' rules need')
    + ' a person</h1>'
    + riskSummary(entries) + '</section>';
  var body = RISKS.map(function (risk) {
    var group = entries.filter(function (entry) {
      return (entry.risk || 'low') === risk;
    });
    if (!group.length) { return ''; }
    return '<div class="group"><span class="gt">' + esc(risk)
      + ' risk</span><span class="muted">(' + group.length + ')</span></div>'
      + reviewOrder(group).map(reviewRow).join('');
  }).join('');
  return head + '<section><div class="tbl">' + body + '</div></section>';
}
