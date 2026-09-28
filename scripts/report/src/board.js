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
  if (bucket === 'untested') {
    return [showsProofs() ? TILE_HOVER.untested : TILE_HOVER.untested_no_proofs]
      .concat(untestedLines());
  }
  return bucket === 'signed' ? signerLines(project) : [TILE_HOVER[bucket]];
}

/* The untested rules by what their passed cell reads, `no test · 3` then
   `not run · 552`: a rule with no marked test is a gap in the tests, and a
   rule whose test has not run is waiting on a run. */
function untestedLines() {
  var counts = {};
  var order = [];
  everyRule().forEach(function (pair) {
    if (pair.rule.bucket !== 'untested') { return; }
    var word = ((pair.rule.cells || {}).passed || {}).word || 'no test';
    if (!(word in counts)) { counts[word] = 0; order.push(word); }
    counts[word] += 1;
  });
  return order.sort().map(function (word) {
    return word + DOT + counts[word];
  });
}

/* The columns the gate reaches, and no others. Every when, who and platform
   detail is in the cell's hover rather than a column of its own, which is
   what lets six columns fit a 1024-wide window.

   `width` is the share of the table the column asks for, and `floor` is the
   width below which it stops being read: a track narrower than its heading
   ran that heading into the next one. Each floor is the heading, or the
   longest single part of a count cell, whichever is wider: `Rules` holds
   `· plus 18 shared`. The shares are set so that the floors fit a
   1024-wide window and every count cell holds its first two parts on one
   line at 1280; under the sum of the floors, 776 pixels, which with the
   five gaps and the padding is 884, the table scrolls sideways rather than
   squeezing a column past one. */
function boardColumns() {
  var columns = [{label: COLUMNS[0], width: '1.7fr', floor: 132},
                 {label: COLUMNS[1], width: '1.6fr', floor: 144}];
  if (showsProofs()) {
    columns.push({label: COLUMNS[2], width: '2fr', floor: 180});
  }
  columns.push({label: COLUMNS[3], width: '2fr', floor: 120});
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
      [rollup.proofs_without_test || 0, WORDS.no_test, 'warn']]) + '</span>';
}

/* How many rules the spec owns, then how many it proves from an anchor it
   requires or from a global anchor, as `15 · plus 6 shared`, with the hover
   naming each anchor and how many rules come from it. Shared rules count
   toward the spec everywhere, and are listed once, under their anchor. A
   spec with none reads its own count alone, as `board.rules_cell` does. */
function rulesCell(feature) {
  var shared = sharedBy(feature);
  var own = ownRules(feature).length;
  if (!shared.length) { return '<span class="mono">' + own + '</span>'; }
  var more = shared.reduce(function (sum, pair) { return sum + pair[1]; }, 0);
  return '<span' + hover(shared.map(function (pair) {
      return pair[0] + DOT + pair[1];
    })) + '>' + counts([[own, '', ''], ['plus ' + more + ' shared', '', '']])
    + '</span>';
}

/* What the marked tests found, as the passed cells read it: how many of the
   rules the spec proves passed everywhere they ran, its own and the shared
   ones alike, then the two words that say they did not. The hover says
   which platforms ran and what each found. */
function testsCell(feature) {
  var found = {};
  var rules = feature.rules || [];
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
  cells.push(rulesCell(feature));
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
    var shown = !!VIEW.proofs[rule.feature + ' ' + rule.id];
    return '<div class="rule" data-act="rule" data-feature="'
      + esc(rule.feature) + '" data-rule="' + esc(rule.id) + '">'
      + '<span class="rid">' + esc(rule.id) + '</span>'
      + '<span class="rt">' + esc(rule.text) + '</span>'
      + '<span class="rp">' + GATE_LEVELS.map(function (name) {
        var cell = cellOf(rule, name);
        return cell ? pill(cell.word) : '';
      }).join('') + '</span>'
      + '<span class="rm">' + proofsToggle(rule, shown) + '</span></div>'
      + (shown ? proofsUnder(rule) : '');
  }).join('');
}

/* The control that opens a rule's proofs beneath its row. Closed, it says
   how many proofs the rule has, `2 proofs`, in the warn tone when one of
   them reads `failed` or `no test`, and `no proof` where it has none. A
   project at `passed` that writes no proof line is told nothing about
   proofs: the control opens the tests marked with the rule's own id,
   `1 test`, and is absent where there are none. */
function proofsToggle(rule, shown) {
  var proofs = rule.proofs || [];
  var tests = rule.tests || [];
  var label;
  var warn = false;
  if (showsProofs()) {
    label = proofs.length ? proofs.length + (proofs.length === 1 ? ' proof'
      : ' proofs') : 'no proof';
    warn = proofs.some(function (proof) {
      var word = proofWord(proof);
      return word === 'failed' || word === 'no test';
    });
  } else if (tests.length) {
    label = tests.length + (tests.length === 1 ? ' test' : ' tests');
    warn = tests.some(function (t) { return t.result === 'fail'; });
  } else {
    return '';
  }
  return '<button class="more" data-act="proofs" data-feature="'
    + esc(rule.feature) + '" data-rule="' + esc(rule.id) + '" aria-expanded="'
    + (shown ? 'true' : 'false') + '"><span class="caret" aria-hidden="true">'
    + (shown ? '▼' : '▶') + '</span><span'
    + (warn ? ' style="color:var(--state-warn)"' : '') + '>' + esc(label)
    + '</span></button>';
}

/* A rule's proofs, open beneath its row: each proof as the rule screen
   draws it. A rule with no proof shows the tests marked with its own id the
   same way, and one with neither says no proof is written. */
function proofsUnder(rule) {
  var proofs = rule.proofs || [];
  var body = proofs.length ? proofs.map(function (proof) {
    return '<div class="proof">' + proofDetail(proof) + '</div>';
  }).join('')
    : (rule.tests || []).length ? '<div class="proof"><dl class="kv">'
      + '<dt>Tests</dt><dd class="ptests">' + testLines(rule.tests)
      + '</dd></dl></div>'
    : '<p class="sec">No proof written.</p>';
  return '<div class="rule-proofs">' + body + '</div>';
}

/* The band over a category's specs, and what its two numbers are. `MCP (6) 5
   of 113` left the reader to guess both, so the band says them: how many specs
   the category holds, then how many of their rules pass their tests, in the
   same words and the same mono face the tiles use. The gate ratio is not
   here: the `Signed` column carries it for each spec and the top bar's gate
   chip carries it for the project. */
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
  var floor = columns.reduce(function (sum, c) { return sum + c.floor; }, 0);
  /* The board opens on the tiles, which carry every count the tests give;
     how many rules meet the gate sits beside the gate in the top bar. */
  var head = '<section>' + statStrip() + '</section>';
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
