/* The Board: where every rule stands, and which specs hold the rules that
   have not got there yet. */

/* A rule the payload lists under the feature that owns it. An anchor's rule
   appears under every feature that requires it, so counting every entry would
   count that rule once per feature. */
function ownRules(feature) {
  return (feature.rules || []).filter(function (rule) {
    return rule.label === 'own';
  });
}

function statStrip() {
  var counts = DATA.states || {};
  return '<div class="tiles">' + STATES.map(function (state) {
    return '<div class="tile"><div class="tile-v" style="color:var(--state-'
      + tone(state) + ')">' + (counts[state] || 0) + '</div>'
      + '<div class="tile-l">' + esc(state) + '</div></div>';
  }).join('') + '</div>';
}

function riskGrid() {
  var table = {};
  RISKS.forEach(function (risk) { table[risk] = {}; });
  eachRule(function (rule, feature) {
    if (rule.label !== 'own') { return; }
    var risk = rule.risk || 'low';
    if (!table[risk]) { table[risk] = {}; }
    table[risk][rule.state] = (table[risk][rule.state] || 0) + 1;
  });
  var rows = RISKS.filter(function (risk) {
    return Object.keys(table[risk]).length > 0;
  });
  var head = '<tr><th>Risk</th>' + STATES.map(function (state) {
    return '<th>' + esc(state) + '</th>';
  }).join('') + '<th>Rules</th></tr>';
  var body = rows.map(function (risk) {
    var total = 0;
    var cells = STATES.map(function (state) {
      var n = table[risk][state] || 0;
      total += n;
      return '<td class="n' + (n ? '' : ' zero') + '">' + n + '</td>';
    }).join('');
    return '<tr><td>' + riskTag(risk) + '</td>' + cells
      + '<td class="n">' + total + '</td></tr>';
  }).join('');
  return '<section><p class="eyebrow">Risk by state</p>'
    + '<div class="panel"><table class="grid">' + head + body
    + '</table></div></section>';
}

/* The columns exist only where their artifacts do. */
function boardColumns() {
  var columns = [{label: 'Spec', width: '2.4fr'}];
  if (hasRisks()) { columns.push({label: 'Risk', width: '0.7fr'}); }
  columns.push({label: 'Coverage', width: '1.4fr'});
  columns.push({label: 'State', width: '1.1fr'});
  if (hasRecords()) {
    columns.push({label: 'Strength', width: '0.8fr'});
    columns.push({label: 'Latest record', width: '1.3fr'});
    columns.push({label: 'Re-verify', width: '0.9fr'});
  }
  if (hasApprovals()) {
    columns.push({label: 'Approvals', width: '0.9fr'});
  }
  return columns;
}

function highestRisk(feature) {
  var found = 'low';
  ownRules(feature).forEach(function (rule) {
    var risk = rule.risk || 'low';
    if (RISKS.indexOf(risk) < RISKS.indexOf(found)) { found = risk; }
  });
  return found;
}

function featureRow(feature, columns) {
  var rollup = feature.rollup || {};
  var open = !!VIEW.features[feature.name];
  var cells = ['<span class="name"><span class="caret">'
    + (open ? '▼' : '▶') + '</span>' + designThumb(feature)
    + '<span class="n">' + esc(feature.name) + '</span></span>'];
  if (hasRisks()) { cells.push(riskTag(highestRisk(feature))); }
  cells.push(coverage(rollup.proved || 0, rollup.rules || 0));
  cells.push(pill(rollup.lowest_state || 'Drafted'));
  if (hasRecords()) {
    cells.push(strength(feature.test_strength));
    cells.push(recordCell(feature));
    cells.push(rollup.re_verify_pending
      ? '<span class="mono" style="color:var(--state-warn)">'
        + rollup.re_verify_pending + ' pending</span>'
      : '<span class="mono muted">—</span>');
  }
  if (hasApprovals()) {
    cells.push('<span class="mono">' + (feature.approvals || []).length
      + '</span>');
  }
  var row = '<div class="tr" data-act="feature" data-feature="'
    + esc(feature.name) + '">' + cells.map(function (cell) {
      return '<div>' + cell + '</div>';
    }).join('') + '</div>';
  if (!open) { return row; }
  return row + visibleRules(feature).map(function (rule) {
    return '<div class="rule" data-act="rule" data-feature="'
      + esc(feature.name) + '" data-rule="' + esc(rule.id) + '">'
      + '<span class="rid">' + esc(rule.id) + '</span>'
      + '<span class="rt">' + esc(rule.text) + '</span>'
      + tag(rule.origin + ' · ' + rule.risk, true) + pill(rule.state)
      + '</div>';
  }).join('');
}

function groupBand(name, features, columns) {
  var open = VIEW.groups[name] !== false;
  var proved = 0;
  var total = 0;
  features.forEach(function (feature) {
    proved += (feature.rollup || {}).proved || 0;
    total += (feature.rollup || {}).rules || 0;
  });
  return '<div class="group" data-act="group" data-group="' + esc(name) + '">'
    + '<span class="caret">' + (open ? '▼' : '▶') + '</span>'
    + '<span class="gt">' + esc(name) + '</span>'
    + '<span class="muted">(' + features.length + ')</span>'
    + coverage(proved, total) + '</div>'
    + (open ? features.map(function (feature) {
      return featureRow(feature, columns);
    }).join('') : '');
}

function renderBoard() {
  var columns = boardColumns();
  var shown = (DATA.features || []).filter(function (feature) {
    return visibleRules(feature).length > 0;
  });
  var order = [];
  var groups = {};
  shown.forEach(function (feature) {
    var name = feature.category || 'specs';
    if (!groups[name]) { groups[name] = []; order.push(name); }
    groups[name].push(feature);
  });
  var rollup = DATA.project_rollup || {};
  var head = '<section><p class="eyebrow">' + esc(DATA.project || 'project')
    + '</p><h1>' + (rollup.rules || 0) + ' rules across '
    + (rollup.features || 0) + ' specs</h1>'
    + '<p class="sec">The lowest state any rule reached is '
    + esc(rollup.lowest_state || 'Drafted') + '. ' + (rollup.stale || 0)
    + ' stale, ' + (rollup.needs_review || 0) + ' on the review list.</p>'
    + '</section><section>' + statStrip() + '</section>';
  var table = order.length
    ? '<div class="tbl" style="--cols:' + columns.map(function (c) {
        return c.width;
      }).join(' ') + '"><div class="th">' + columns.map(function (c) {
        return '<div>' + esc(c.label) + '</div>';
      }).join('') + '</div>' + order.map(function (name) {
        return groupBand(name, groups[name], columns);
      }).join('') + '</div>'
    : '<div class="panel empty">No rule matches every filter you set.</div>';
  return head + (hasRisks() ? riskGrid() : '')
    + '<section><p class="eyebrow">Specs</p>' + filtersMarkup() + table
    + '</section>';
}
