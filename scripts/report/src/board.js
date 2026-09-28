/* The Board: where every rule stands against the gate, and which specs hold
   the rules that have not got there yet. */

/* One tile per level the gate reaches, plus the two below them and `Partial`,
   each counting the rules that got at least that far, and at `signed` two
   flag cards beside them: the rules waiting for a person, and the
   signatures that no longer match. A flag is counted beside the tiles, never
   instead of one, so it never shares their row. Each tile carries the hover
   its column carries, read over every spec. */
function statStrip() {
  var summary = DATA.summary || {};
  var project = wholeProject();
  var shown = BUCKETS.filter(function (bucket) {
    return GATE_LEVELS.indexOf(bucket) < 0 || level(bucket);
  });
  var tiles = shown.map(function (bucket) {
    return '<div class="tile"' + hover(tileHover(bucket, project))
      + '><div class="tile-v" style="color:var(--state-'
      + bucketTone(bucket) + ')">' + reached(summary, bucket) + '</div>'
      + '<div class="tile-l">' + esc(BUCKET_LABELS[bucket]) + '</div></div>';
  }).join('');
  var flags = level('signed')
    ? '<div class="flags">'
      + flagCard('Queue', summary.queue || 0, 'warn', queueLines())
      + flagCard('Stale', summary.stale || 0, 'fail', staleLines())
      + '</div>' : '';
  return '<div class="strip' + (flags ? ' flagged' : '') + '">'
    + '<div class="tiles">' + tiles + '</div>' + flags + '</div>';
}

/* One flag card: a count the tiles do not hold, in its own tone once it is
   above zero, with the hover that says which rules make it up. */
function flagCard(label, count, hue, lines) {
  return '<div class="flag' + (count ? ' on ' + hue : '') + '"'
    + hover(lines) + '><div class="flag-v">' + count
    + '</div><div class="flag-l">' + esc(label) + '</div></div>';
}

/* How many rules of each spec wait on a person, which is what the `Queue`
   card counts for the project and what the Queue tab lists. */
function queueLines() {
  var byFeature = {};
  var names = [];
  ((DATA.queue || [])).forEach(function (entry) {
    if (!byFeature[entry.feature]) {
      byFeature[entry.feature] = 0;
      names.push(entry.feature);
    }
    byFeature[entry.feature] += 1;
  });
  if (!names.length) { return ['No rule is waiting for a person.']; }
  return names.sort().map(function (name) {
    return name + DOT + byFeature[name];
  });
}

/* Which rules carry a signature that no longer matches, one line per spec. */
function staleLines() {
  var byFeature = {};
  var names = [];
  everyRule().forEach(function (pair) {
    if (!(pair.rule.flags || {}).stale) { return; }
    var name = pair.feature.name;
    if (!byFeature[name]) { byFeature[name] = []; names.push(name); }
    byFeature[name].push(pair.rule.id);
  });
  if (!names.length) { return ['Every signature still matches.']; }
  return names.sort().map(function (name) {
    return name + DOT + byFeature[name].join(', ');
  });
}

/* What a tile says beyond its count. The three cumulative tiles say what
   their column says for one spec: where the runs happened, where the audit
   came from, who signed. The three below them name what they count. */
function tileHover(bucket, project) {
  if (bucket === 'passed') { return platformLines(project); }
  if (bucket === 'strong') { return auditLines(project); }
  if (bucket === 'untested' && !showsProofs()) {
    return [TILE_HOVER.untested_no_proofs];
  }
  return bucket === 'signed' ? signerLines(project) : [TILE_HOVER[bucket]];
}

/* The columns the gate reaches, and no others. Every when, who and platform
   detail is in the cell's hover rather than a column of its own, which is
   what lets six columns fit a 1024-wide window.

   `width` is the share of the table the column asks for, and `floor` is the
   width below which it stops being read: a track narrower than its heading
   ran that heading into the next one. Each floor is the heading, or the
   longest single part of a count cell, whichever is wider. The shares are
   set so that no floor binds at 1024 and every count cell holds its first
   two parts on one line at 1280; under the sum of the floors, 554 pixels,
   which with the four gaps and the padding is 650, the table scrolls
   sideways rather than squeezing a column past one. */
function boardColumns() {
  var columns = [{label: COLUMNS[0], width: '2.3fr', floor: 132},
                 {label: COLUMNS[1], width: '0.7fr', floor: 58}];
  if (showsProofs()) {
    columns.push({label: COLUMNS[2], width: '2.15fr', floor: 180});
  }
  columns.push({label: COLUMNS[3], width: '2.15fr', floor: 120});
  if (level('strong')) {
    columns.push({label: COLUMNS[4], width: '1.5fr', floor: 110});
  }
  if (level('signed')) {
    columns.push({label: COLUMNS[5], width: '1.1fr', floor: 90});
  }
  return columns;
}

/* How many proof lines this spec holds, and how many of them no marked test
   runs. A proof nothing tests is the gap between what the spec claims and
   what the tests check, so it is on the board rather than one screen deeper,
   and its ids are in the hover. Both numbers are the rollup's own, so the
   cell reads what `board.proofs_cell` reads: a `@manual` proof declares that
   no test is written for it, and only the payload knows that. */
function proofsCell(feature) {
  var rollup = feature.rollup || {};
  var ids = rollup.proofs_without_test_ids || [];
  return '<span' + hover([ids.length ? 'no test' + DOT + ids.join(', ')
      : 'every proof has a test']) + '>'
    + counts([[rollup.proofs || 0, '', ''],
      [rollup.proofs_without_test || 0, WORDS.without_test, 'warn']]) + '</span>';
}

/* What the marked tests found, as the passed cells read it: how many of the
   spec's rules passed everywhere they ran, then the two words that say they
   did not. The hover says which platforms ran and what each found. */
function testsCell(feature) {
  var found = {};
  var rules = ownRules(feature);
  rules.forEach(function (rule) {
    var word = cellWord(rule, 'passed');
    found[word] = (found[word] || 0) + 1;
  });
  return '<span' + hover(platformLines(feature)) + '>'
    + counts([share(found.passed || 0, rules.length),
      [found.partial || 0, WORDS.partial, 'warn'],
      [found.failed || 0, WORDS.failing, 'fail']]) + '</span>';
}

/* `n of m` as the first part of a count cell: the share reads pass when every
   rule is there, warn while some are, and idle while none is. */
function share(count, total) {
  return [count + ' ' + WORDS.of + ' ' + total, '',
          total && count === total ? 'pass' : count ? 'warn' : 'idle'];
}

/* How many of this spec's rules the audit proved strong, and the strength of
   the newest record beside it. A signed rule is still strong, so the share is
   read the way the tiles are: this level and every level above it. */
function strongCell(feature) {
  var rollup = feature.rollup || {};
  var value = rollup.test_strength == null
    ? feature.test_strength : rollup.test_strength;
  return '<span' + hover(auditLines(feature)) + '>'
    + counts([share(reached(rollup, 'strong'), rollup.rules || 0),
      [value == null ? 'n/a' : Math.floor(value) + '%', '',
        value == null ? 'idle' : value >= minStrength() ? 'pass' : 'fail']])
    + '</span>';
}

/* How many of this spec's rules carry a signature that counts. Who signed
   them and how many signatures stopped matching are in the hover; the `Stale`
   flag card carries the project's stale count. */
function signedCell(feature) {
  var rollup = feature.rollup || {};
  return '<span' + hover(signerLines(feature)) + '>'
    + counts([share(rollup.signed || 0, rollup.rules || 0)]) + '</span>';
}

/* A spec that names no files: Purlin cannot tell which code it covers, so a
   default `purlin:test` always runs it and, at `signed`, none of its rules
   can be signed. The name says so, and the hover says why. */
function noScope(feature) {
  if (!feature.incomplete) { return ''; }
  return '<span class="sec ns"' + hover([feature.incomplete_reason
      || 'no > Scope: line']) + '>' + esc(DOT.replace(/^ /, '') + 'no scope')
    + '</span>';
}

function featureRow(feature, columns) {
  var rollup = feature.rollup || {};
  var open = !!VIEW.features[feature.name];
  var cells = ['<span class="name"><span class="caret">'
    + (open ? '▼' : '▶') + '</span>'
    + '<span class="n"' + hover([feature.spec_path || feature.name]) + '>'
    + esc(feature.name) + '</span>' + noScope(feature) + '</span>'];
  cells.push('<span class="mono">' + (rollup.rules || 0) + '</span>');
  if (showsProofs()) { cells.push(proofsCell(feature)); }
  cells.push(testsCell(feature));
  if (level('strong')) { cells.push(strongCell(feature)); }
  if (level('signed')) { cells.push(signedCell(feature)); }
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
      + '<span class="rp">' + GATE_LEVELS.map(function (name) {
        var cell = cellOf(rule, name);
        return cell ? pill(cell.word) : '';
      }).join('') + '</span></div>';
  }).join('');
}

/* The band over a category's specs, and what its two numbers are. `MCP (6) 5
   of 113` left the reader to guess both, so the band says them: how many specs
   the category holds, then how many of their rules pass their tests, in the
   same words and the same mono face the headline uses. The gate ratio is not
   here: the `Signed` column carries it for each spec and the headline's
   second line carries it for the project. */
function groupBand(name, features, columns) {
  var open = VIEW.groups[name] !== false;
  var passing = 0;
  var total = 0;
  features.forEach(function (feature) {
    passing += reached(feature.rollup || {}, 'passed');
    total += (feature.rollup || {}).rules || 0;
  });
  return '<div class="group" data-act="group" data-group="' + esc(name) + '">'
    + '<span class="caret">' + (open ? '▼' : '▶') + '</span>'
    + '<span class="gt">' + esc(name) + '</span><span class="muted">·</span>'
    + '<span class="sec">' + features.length
    + (features.length === 1 ? ' spec' : ' specs')
    + '</span><span class="muted">·</span>' + ratio(passing, total, 'pass')
    + '</div>'
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
  var summary = DATA.summary || {};
  var floor = columns.reduce(function (sum, c) { return sum + c.floor; }, 0);
  /* What the board is mainly about is the tests: how many rules pass them,
     how many fail, how many pass on one platform and not another, and how
     many nothing has run against. The gate is the second line, because the
     signed layer is one column's business. */
  var head = '<section class="ledger"><h1 class="line"><b>'
    + reached(summary, 'passed') + '</b> of <b>' + (summary.rules || 0)
    + '</b> rules pass their tests<span class="sep">·</span><b>'
    + (summary.failing || 0) + '</b> failing<span class="sep">·</span><b>'
    + (summary.partial || 0) + '</b> partial<span class="sep">·</span><b>'
    + (summary.untested || 0) + '</b> untested</h1>'
    + '<p class="line">' + headline(summary, gateName())
    + '</p></section><section>' + statStrip() + '</section>';
  var table = order.length
    ? '<div class="tbl" style="--cols:' + columns.map(function (c) {
        /* minmax sizes every track from these two numbers alone. A bare fr
           track grows to fit its widest cell, and the header and each row are
           separate grids, so their columns drifted apart. The floor is what
           keeps a heading and its content readable once the window narrows. */
        return 'minmax(' + c.floor + 'px,' + c.width + ')';
      }).join(' ') + ';--cols-floor:' + floor + 'px;--cols-gaps:'
      + (columns.length - 1) + '"><div class="th">' + columns.map(function (c) {
        return '<div>' + esc(c.label) + '</div>';
      }).join('') + '</div>' + order.map(function (name) {
        return groupBand(name, groups[name], columns);
      }).join('') + '</div>'
    : '<div class="panel empty">No rule matches every filter you set.</div>';
  return head + '<section><p class="eyebrow">Specs</p>' + filtersMarkup()
    + table + '</section>';
}
