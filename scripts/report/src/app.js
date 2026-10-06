/* The shell: the data file, the chrome, the router and the marks the two
   screens share.

   The data file declares a const, and a const cannot be declared twice in one
   window, so it is read inside a throwaway iframe that posts the value back.
   srcdoc inherits this page's base URL and origin, so .purlin/report-data.js
   resolves exactly as a script tag here would, on file:// as well, where
   fetch is blocked. The query string defeats the file:// cache. */

var DATA = null;
var VIEW = {screen: 'board', feature: null, rule: null,
            features: {}, groups: {}};
var SCHEMA = 18;

/* The two facts the top bar states, as the payload gives them: whether the
   tests are met on the committed evidence, the payload's `met`, and whether
   this code is signed, the payload's `signoff`, whose `word` reads
   `signed <version> at <commit>`, `signed <version>, <n> commits since` or
   `not signed`. The page works out neither. */
var TESTS = 'Tests';
var SIGNOFF = 'Sign-off';
var MET = 'met';
var NOT_MET = 'not met';
var NOT_SIGNED = 'not signed';

/* What the audit found, as the payload's `summary.audit` counts it for the
   summary line the terminal prints, `summary.AUDIT_WORDS` in its order. The
   `Strong` box's hover reads these counts. */
var AUDIT_WORDS = [['strong', 'strong'], ['weak', 'weak'],
  ['spot_checked', 'spot-checked'], ['out_of_date', 'out of date'],
  ['not_audited', 'not audited']];
var LAST_AUDIT = 'Last audit: ';
/* The first line of the hover of an anchor's `Strong` cell. */
var NO_ANCHOR_BUG = 'No bug is planted for an anchor\'s rule.';

/* The boxes: `No proof` counts the rules of the kind `no_proof`, drawn
   wherever the project writes a proof line; `Passing` counts the rules whose
   tests pass now, the payload's `summary.steps.passed`, and is complete once
   every other rule is checked at sign-off, `summary.steps.by_hand`; `Strong`
   counts the rules the audit found strong, the payload's
   `summary.audit.strong`, drawn only where a rule has an audit entry;
   `Failing` counts the rules whose passed cell reads `failed`, and is drawn
   only where there is one. */
var PASSING = 'Passing';
var FAILING = 'Failing';
var STRONG = 'Strong';
var NO_PROOF = 'No proof';

/* The board's five column headings and the words its cells append, in one
   place. `scripts/mcp/purlin/board.py` renders the same columns for
   `purlin:status`, so these are its
   `COLUMNS` and its cell words: a string changed there is changed here in
   the same commit. `Proofs` is drawn where `showsProofs` says, as
   `board.shows_proofs` decides it for the status table, and `Strong` where
   `audited` says. */
var COLUMNS = ['Spec', 'Rules', 'Proofs', 'Tests', 'Strong'];

/* The one separator every cell, hover and line puts between two parts, which
   is `board.DOT`. */
var DOT = ' \u00b7 ';
var WORDS = {of: 'of', no_test: 'no test', by_hand: 'by hand',
             partial: 'partial', failing: 'failing', passed: 'passed',
             failed: 'failed', not_run: 'not run', out_of_date: 'out of date'};

/* Every word a cell can read, and the tone it reads in. A word carries the
   same hue wherever it is drawn, so a pill on the board, a row on the rule
   screen and a proof beneath a rule agree. */
var CELL_TONES = {'passed': 'pass',
  'failed': 'fail', 'no test': 'warn', 'not run': 'warn', 'partial': 'warn',
  'out of date': 'warn', 'strong': 'pass', 'weak': 'warn',
  'spot-checked': 'neutral',
  'waiting': 'neutral', 'checked at sign-off': 'neutral',
  'not audited': 'idle', 'no proof': 'warn'};

var CELL_LABELS = {passed: 'Passed', strong: 'Strong'};


function loadData(callback) {
  var frame = document.createElement('iframe');
  var done = false;
  frame.setAttribute('hidden', '');
  frame.setAttribute('aria-hidden', 'true');
  frame.style.display = 'none';

  function finish(value) {
    if (done) { return; }
    done = true;
    window.removeEventListener('message', onMessage);
    callback(value);
  }
  function onMessage(event) {
    if (event.source !== frame.contentWindow) { return; }
    if (!event.data || typeof event.data !== 'object') { return; }
    if (!('purlin' in event.data)) { return; }
    finish(event.data.purlin);
  }
  window.addEventListener('message', onMessage);
  frame.srcdoc = '<script src=".purlin/report-data.js?t=' + Date.now()
    + '"><\/script><script>parent.postMessage({purlin: '
    + '(typeof PURLIN_DATA === "undefined") ? null : PURLIN_DATA}, "*");<\/script>';
  document.body.appendChild(frame);
  setTimeout(function () { finish(null); }, 3000);
}

/* Whether the page names proofs at all: a project that writes no proof line
   is shown no `No proof` box, no `Proofs` column, no proofs section and no
   reason naming them. `board.shows_proofs` answers the same for
   `purlin:status`. */
function showsProofs() {
  return ((DATA && DATA.summary) || {}).proofs > 0;
}

/* Whether an audit has read a rule: a rule carries an audit entry, or the
   payload's `summary.audit` counts one `strong`, `weak`, `spot_checked` or
   `out_of_date`, as `board.shows_strong` reads it for the status table. The
   audit is a tool a person runs and nothing waits on it, so the `Strong`
   box, column, badge, cell and panel are drawn only where it has read a
   rule: a board that names a check nobody ran reads as a project falling
   short. A project whose every entry reads `spot-checked` or is out of date
   has them all, with nothing counted strong. */
function audited() {
  var found = ((DATA && DATA.summary) || {}).audit || {};
  if ((found.strong || 0) + (found.weak || 0) + (found.spot_checked || 0)
      + (found.out_of_date || 0) > 0) { return true; }
  return ((DATA && DATA.features) || []).some(function (feature) {
    return (feature.rules || []).some(function (rule) { return !!rule.audit; });
  });
}

/* --- marks the screens share ----------------------------------------- */

function esc(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
    return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
  });
}

function tone(word) { return CELL_TONES[word] || 'idle'; }

function pill(word) {
  return '<span class="pill" style="color:var(--state-' + tone(word) + ')"><b>'
    + esc(String(word).toUpperCase()) + '</b></span>';
}

/* The words a person reads for an operating system, from the payload's
   `os_words`: `Windows`, `macOS` and `Linux/Unix`, and in a small box `Win`,
   `Mac` and `Lin`. A system that is none of the three reads as `linux`. */
function systemWords(os) {
  var words = (DATA && DATA.os_words) || {};
  return words[os] || words.linux || {word: os, short: os};
}

function tag(text, plain) {
  return '<span class="tag' + (plain ? ' plain' : '') + '">' + esc(text) + '</span>';
}

/* Every rule the project holds, each paired with the spec that owns it. */
function everyRule() {
  var out = [];
  (DATA.features || []).forEach(function (feature) {
    (feature.rules || []).forEach(function (rule) {
      out.push({feature: feature, rule: rule});
    });
  });
  return out;
}

/* The rule one owner and one id name. A rule is always addressed by the
   spec that owns it and its id together, since every spec numbers its rules
   from `RULE-1`. */
function ruleNamed(owner, id) {
  var feature = featureNamed(owner);
  var found = null;
  (feature ? feature.rules || [] : []).forEach(function (r) {
    if (r.id === id) { found = r; }
  });
  return found;
}

/* Several counts in one cell, each labelled with the word it counts and set
   in that word's tone. `24 passed · 2 failing` says what a bare `24 · 2 · 0`
   left the reader to work out from the heading. The first part is always
   drawn, because the column's total is the number the row is about; a later
   part at zero is not, because nothing is waiting there. Each item is
   `[count, word, tone]`, and a word may be empty where the count already
   reads as a sentence (`5 of 24`); a fourth member, where there is one, is
   the part's own hover. The separator rides inside the part it
   introduces, so a cell narrow enough to wrap breaks between parts and never
   leaves a lone dot at the end of a line. */
function counts(items) {
  return '<span class="trio">' + items.filter(function (item, index) {
    return index === 0 || item[0];
  }).map(function (item, index) {
    var hue = index === 0 && !item[0] ? 'idle' : item[2];
    return '<b' + (item[3] ? hover(item[3]) : '')
      + (hue ? ' style="color:var(--state-' + hue + ')"' : '') + '>'
      + (index ? '<i class="sec">·</i> ' : '')
      + esc(item[1] ? item[0] + ' ' + item[1] : item[0]) + '</b>';
  }).join('') + '</span>';
}

/* A hover is a `title` attribute: one item to a line, the parts of an item
   separated by the middot the rest of the board uses. The page carries no
   script beyond its own render, and a native tooltip is what a page opened
   from disk, printed, or read by a screen reader can still show. */
function hover(lines) { return ' title="' + esc(lines.join('\n')) + '"'; }

/* The whole project as one feature, so a tile's hover is its column's hover
   read over every spec rather than a second set of sums. */
function wholeProject() {
  var rules = [];
  var rollup = {};
  var latest = null;
  Object.keys(DATA.summary || {}).forEach(function (key) {
    rollup[key] = DATA.summary[key];
  });
  (DATA.features || []).forEach(function (feature) {
    (feature.rules || []).forEach(function (rule) { rules.push(rule); });
    var found = newestRun(feature);
    if (found && (!latest || newer(found.at, latest.at))) { latest = found; }
  });
  return {rules: rules, rollup: rollup, newest: latest};
}

/* The newest section of a spec's evidence in either source: where it sits,
   whose run it was and when, or null where nothing has run. */
function newestRun(feature) {
  if (feature.newest !== undefined) { return feature.newest; }
  var best = null;
  ['local', 'ci'].forEach(function (source) {
    var file = (feature.evidence || {})[source];
    if (!file) { return; }
    Object.keys(file.platforms || {}).forEach(function (os) {
      var section = file.platforms[os];
      if (!best || newer(section.at, best.at)) {
        best = {path: file.path, source: source, at: section.at};
      }
    });
  });
  return best;
}

/* One ISO stamp against another, either of which may be missing. */
function newer(one, two) { return (one || '') > (two || ''); }

/* One line per operating system this spec's counting runs covered, newest
   run first: what ran there, where the run came from, how old it is, and how
   its rules came out. The passed cell of each rule carries the map; a rule
   nothing current ran against carries none, so it is on no line. */
function platformLines(feature) {
  var byOs = {};
  var names = [];
  (feature.rules || []).forEach(function (rule) {
    var platforms = ((rule.cells || {}).passed || {}).platforms || {};
    Object.keys(platforms).forEach(function (os) {
      var entry = platforms[os];
      if (!byOs[os]) { byOs[os] = {at: '', words: {}}; names.push(os); }
      var found = byOs[os];
      found.words[entry.word] = (found.words[entry.word] || 0) + 1;
      if (newer(entry.at, found.at)) { found.at = entry.at; found.source = entry.source; }
    });
  });
  if (!names.length) { return ['No counting run has covered a platform yet.']; }
  return names.sort(function (a, b) { return newer(byOs[a].at, byOs[b].at) ? -1 : 1; })
    .map(function (os) {
      var found = byOs[os];
      return [systemWords(os).word, found.source || 'local',
        ageText(found.at).text].concat(
        [WORDS.passed, WORDS.failed, WORDS.not_run].filter(function (word) {
          return found.words[word];
        }).map(function (word) { return found.words[word] + ' ' + word; }))
        .join(DOT);
    });
}

/* Where the newest audit came from and how old it is. Each rule carries its
   own audit, so the newest of them answers for the spec. */
function auditLines(feature) {
  var newest = null;
  (feature.rules || []).forEach(function (rule) {
    var audit = rule.audit;
    if (audit && audit.at && (!newest || newer(audit.at, newest.at))) {
      newest = audit;
    }
  });
  return [newest ? 'audit' + DOT + sourceOf(newest.path) + DOT
      + ageText(newest.at).text
    : 'No audit has read a rule here.'];
}

/* The source an evidence file belongs to: the folder it sits in. */
function sourceOf(path) {
  var parts = String(path || '').split('/');
  return parts.length > 1 ? parts[parts.length - 2] : 'local';
}

/* This spec's newest run: where it came from and how old it is. Which
   platform found what is on the passed cell row above it. */
function runLine(feature) {
  var run = newestRun(feature);
  if (!run) { return '<span class="mono muted">\u2014</span>'; }
  return '<span class="mono">' + esc(run.source + DOT + ageText(run.at).text)
    + '</span>';
}

function ageText(iso) {
  var then = Date.parse(iso || '');
  if (!then) { return {text: 'age unknown', old: true}; }
  var seconds = Math.max(0, (Date.now() - then) / 1000);
  if (seconds < 90) { return {text: 'less than a minute old', old: false}; }
  if (seconds < 5400) {
    return {text: Math.round(seconds / 60) + ' minutes old', old: false};
  }
  if (seconds < 172800) {
    return {text: Math.round(seconds / 3600) + ' hours old', old: true};
  }
  return {text: Math.round(seconds / 86400) + ' days old', old: true};
}

/* The date part of an ISO stamp, where a whole day is precise enough. */
function when(iso) { return String(iso || '').slice(0, 10) || 'date unknown'; }

/* An ISO stamp, which is UTC wherever it was written, as the person looking
   at the page reads the clock: the date, the hour and minute, 24-hour, and
   the browser's short name for their timezone at that moment, or its offset
   where it has none, as `GMT+5:30`. Null where the stamp is no time. */
function localParts(iso) {
  var date = new Date(String(iso || ''));
  if (isNaN(date.getTime())) { return null; }
  var parts = {};
  new Intl.DateTimeFormat('en-US', {year: 'numeric', month: '2-digit',
    day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    timeZoneName: 'short'}).formatToParts(date).forEach(function (part) {
    parts[part.type] = part.value;
  });
  return {day: parts.year + '-' + parts.month + '-' + parts.day,
    time: parts.hour + ':' + parts.minute, zone: parts.timeZoneName};
}

/* The date and the minute of a stamp in the viewer's own timezone:
   `2026-09-12 06:02 EDT`. */
function moment(iso) {
  var local = localParts(iso);
  return local ? local.day + ' ' + local.time + ' ' + local.zone : when(iso);
}

/* One cell of one rule, or null where the payload carries none. */
function cellOf(rule, name) {
  return (rule.cells || {})[name] || null;
}

function cellWord(rule, name) {
  return (cellOf(rule, name) || {}).word || null;
}

/* What a rule has reached, as the boxes count it: its passed cell reads
   `passed`, and then, where the audit read the project, the audit found it
   strong. A rule checked by hand alone reads `checked at sign-off` there
   until a sign-off notes it, and has reached neither. The audit reads only
   a rule whose tests pass, so a rule that has not reached the first has not
   reached the second. */
function reachedSteps(rule) {
  var out = [];
  if (cellWord(rule, 'passed') !== 'passed') { return out; }
  out.push('passed');
  if (audited() && cellWord(rule, 'strong') === 'strong') {
    out.push('strong');
  }
  return out;
}

/* Whether a test of the rule failed: its passed cell reads `failed`, or a
   run on one operating system failed it while another passed it. */
function testFailed(rule) {
  var cell = cellOf(rule, 'passed') || {};
  if (cell.word === 'failed') { return true; }
  var platforms = cell.platforms || {};
  return Object.keys(platforms).some(function (os) {
    return platforms[os].word === 'failed';
  });
}

/* Whether a spec holds a rule whose passed cell reads `failed`: the rules
   the `Failing` box counts, and the specs the board lists first. */
function hasFailing(feature) {
  return (feature.rules || []).some(function (rule) {
    return cellWord(rule, 'passed') === 'failed';
  });
}

/* The badges a rule's row carries: one per step it has reached, and
   `FAILED` where a test fails. A step not reached draws nothing; why it was
   not reached is read on the rule's own screen. */
function badges(rule) {
  return reachedSteps(rule).map(pill).join('')
    + (testFailed(rule) ? pill('failed') : '');
}

function featureNamed(name) {
  var found = null;
  (DATA.features || []).forEach(function (f) {
    if (f.name === name) { found = f; }
  });
  return found;
}

/* --- chrome and router ------------------------------------------------ */

/* The checkout state the data describes and when it was written:
   `main at a1b2c3d, written 06:42 EDT`, the branch, the first 7 characters of
   the commit, and the hour and minute the writing command stamped, shown in
   the viewer's own timezone and naming it, so the line reads the same
   however long the page stays open. On a detached HEAD the payload names no
   branch and the line opens `detached`. The hover gives the date and time in
   full in that zone, then the UTC time: `2026-10-01 06:42 EDT (10:42 UTC)`.
   The line is two parts, the checkout state and the time, so a narrow
   screen sets the time beneath the state and breaks neither. */
function stampLine() {
  var at = String(DATA.generated_at || '');
  var local = localParts(at);
  return {where: (DATA.branch || 'detached') + ' at '
      + String(DATA.commit || '').slice(0, 7) + ',',
    written: 'written '
      + (local ? local.time + ' ' + local.zone : at.slice(11, 16)),
    full: local ? moment(at) + ' (' + at.slice(11, 16) + ' UTC)' : when(at)};
}

/* One of the top bar's two boxes: its label, then the payload's word in
   the tone it reads in, and its hover where it has one. */
function factBox(label, word, hue, lines) {
  return '<span class="fact"' + (lines && lines.length ? hover(lines) : '')
    + ' style="color:var(--' + (hue ? 'state-' + hue : 'text-secondary')
    + ')"><span class="fact-l">' + esc(label) + '</span><b>' + esc(word)
    + '</b></span>';
}

/* A spec's rules the audit can speak of: those that pass their tests and
   have a tested proof, whose strong cell reads one of the audit's five
   words. */
function auditRead(feature) {
  var words = AUDIT_WORDS.map(function (pair) { return pair[1]; });
  return (feature.rules || []).filter(function (rule) {
    return words.indexOf(cellWord(rule, 'strong')) !== -1;
  });
}

/* The share of strong rules, as `summary.audit_share` counts it for the
   terminal's sentence: `over` is the rules the audit can find strong, those
   it can speak of that are not an anchor's, and `strong` how many of them
   it did. No bug is planted for an anchor's rule, so the share counts
   none. */
function auditShare() {
  var share = {strong: 0, over: 0};
  ((DATA && DATA.features) || []).forEach(function (feature) {
    if (feature.is_anchor) { return; }
    auditRead(feature).forEach(function (rule) {
      share.over += 1;
      if (cellWord(rule, 'strong') === 'strong') { share.strong += 1; }
    });
  });
  return share;
}

/* The audit's counts, for the `Strong` box's hover: every count that is not
   zero, `strong` always, one to a line, then the date of the newest entry. */
function auditCountLines() {
  var found = ((DATA && DATA.summary) || {}).audit || {};
  var lines = [];
  AUDIT_WORDS.forEach(function (pair) {
    var count = found[pair[0]] || 0;
    if (pair[0] === 'strong' || count) { lines.push(count + ' ' + pair[1]); }
  });
  var newest = '';
  everyRule().forEach(function (pair) {
    var at = (pair.rule.audit || {}).at || '';
    if (newer(at, newest)) { newest = at; }
  });
  if (newest) { lines.push(LAST_AUDIT + when(newest)); }
  return lines;
}

/* The two boxes, one for each fact. The tests read in the pass tone once met
   and the warn tone until then; the sign-off in the pass tone at the signed
   commit, the warn tone once commits have followed it, and in no tone before
   any: `not signed` and its box are drawn in the secondary text colour. */
function factBoxes() {
  var signoff = DATA.signoff || {};
  var word = signoff.word || NOT_SIGNED;
  var hue = !signoff.version ? ''
    : / at [0-9a-f]+$/.test(word) ? 'pass' : 'warn';
  return '<span class="facts">'
    + factBox(TESTS, DATA.met ? MET : NOT_MET, DATA.met ? 'pass' : 'warn')
    + factBox(SIGNOFF, word, hue) + '</span>';
}

/* The top bar. Over data the page cannot read it draws the mark and the
   theme button alone, rather than fields it cannot read. */
function topBar(readable) {
  var stamp = readable ? stampLine() : null;
  return '<header class="topbar"><span class="brand"><img id="brand-mark" src="'
    + logoSrc() + '" alt="Purlin"><span>purlin</span></span>'
    + (stamp ? '<span class="stamp"' + hover([stamp.full]) + '><span>'
      + esc(stamp.where) + '</span> <span>' + esc(stamp.written)
      + '</span></span>' : '')
    + '<span class="spacer"></span>' + (readable ? factBoxes() : '')
    + themeButton() + '</header>';
}

/* One notice: a dot in its tone, then the line whole. A notice that counts
   several specs names every one of them in its hover, one to a line. */
function notice(line, hue, names) {
  return '<div class="notice"' + (names ? hover(names) : '')
    + '><span class="dot" '
    + 'style="color:var(--state-' + hue + ')"></span><span class="notice-text">'
    + line.split(' ').map(noticeWord).join(' ') + '</span></div>';
}

/* The kinds of line the status writes about one spec, each as the pattern
   its line matches, the spec's name the pattern's one group, and what the
   one notice drawn for three or more of the kind says of those specs: the
   verb for several specs, the verb for one, then the rest. A line that
   matches none is about no one spec and always keeps its own notice. */
var NOTICE_KINDS = [
  [/^(\S+): \d+ lines? under ## Rules (?:is|are) not numbered/,
    'hold', 'holds', 'a line under ## Rules with no number'],
  [/^(\S+): RULE-\d+ is written twice/,
    'write', 'writes', 'a rule\'s number twice'],
  [/^(\S+): PROOF-\d+ is written twice/,
    'write', 'writes', 'a proof\'s number twice'],
  [/^(\S+): \d+ lines? (?:is|are) left from a merge conflict/,
    'hold', 'holds', 'a line left from a merge conflict'],
  [/^(.+?): the name holds a character other than letters/,
    'have', 'has', 'a name no test comment can name'],
  [/^(\S+): a line under ## Proof cannot be read/,
    'hold', 'holds', 'a proof line Purlin cannot read'],
  [/^(\S+): the first line names /,
    'name', 'names', 'another spec on the first line'],
  [/^(\S+): PROOF-\d+ is tagged @slow and @manual/,
    'tag', 'tags', 'a proof @slow and @manual'],
  [/^(\S+): > Requires: is not read/,
    'carry', 'carries', '> Requires:, which Purlin does not read'],
  [/^(\S+): > Global: is not read/,
    'carry', 'carries', '> Global:, which Purlin does not read'],
  [/^(\S+): > Scope: is not read on an anchor/,
    'carry', 'carries', '> Scope:, which Purlin does not read on an anchor'],
  [/^(\S+): its source, .* which Purlin does not read on an anchor/,
    'come', 'comes', 'from a source with a line Purlin does not read'],
  [/^.+:\d+ names (\S+) (?:PROOF|RULE)-\d+, whose wording changed after/,
    'have', 'has', 'a proof reworded after its test was last changed'],
  [/^\.purlin\/evidence\/[^\/ ]+\/(\S+)\.json (?:is not valid JSON|is not a JSON object|carries the schema |names the source )/,
    'have', 'has', 'an evidence file Purlin ignores'],
  [/^(\S+): \d+ files? its scope names (?:is|are) not written yet/,
    'name', 'names', 'a file in the scope that is not written yet'],
  [/^(\S+) RULE-\d+ passes with nothing to check here: /,
    'have', 'has', 'a rule that passes with nothing to check here']
];

/* The lines as the board draws them, each `{line, names}`: three or more
   lines of one kind become one line, where the first of them stood, counting
   the specs they name and naming the first two; `names` is every spec it
   counts, for its hover. Any other line stands as it came, whole. */
function groupedLines(lines) {
  var found = lines.map(function (line) {
    for (var kind = 0; kind < NOTICE_KINDS.length; kind++) {
      var match = NOTICE_KINDS[kind][0].exec(line);
      if (match) { return {kind: kind, name: match[1]}; }
    }
    return null;
  });
  var groups = {};
  found.forEach(function (hit) {
    if (!hit) { return; }
    var group = groups[hit.kind] = groups[hit.kind] || {lines: 0, names: []};
    group.lines += 1;
    if (group.names.indexOf(hit.name) < 0) { group.names.push(hit.name); }
  });
  var out = [];
  lines.forEach(function (line, index) {
    var hit = found[index];
    var group = hit && groups[hit.kind];
    if (!group || group.lines < 3) { out.push({line: line}); return; }
    if (group.drawn) { return; }
    group.drawn = true;
    out.push({line: groupLine(NOTICE_KINDS[hit.kind], group),
              names: group.names});
  });
  return out;
}

/* The one line for a kind: `<n> specs <what>: <first two names>, and <n-2>
   more. Run purlin:status for each.` Two specs are both named, and one spec
   is named with how many places its lines name. */
function groupLine(kind, group) {
  var names = group.names;
  if (names.length === 1) {
    return names[0] + ' ' + kind[2] + ' ' + kind[3] + ', in ' + group.lines
      + ' places. Run purlin:status ' + names[0] + '.';
  }
  return names.length + ' specs ' + kind[1] + ' ' + kind[3] + ': '
    + (names.length === 2 ? names[0] + ' and ' + names[1]
      : names[0] + ', ' + names[1] + ', and ' + (names.length - 2) + ' more')
    + '. Run purlin:status for each.';
}

/* The notices, which stand below the boxes and above the two tables: the
   uncommitted working tree, then the warnings the data carries, in the warn
   tone; then the lines of information, in the neutral tone. Between them the two lists hold every
   line the status prints between its table and its summary sentence, which
   `report_data.with_status_lines` sees to. Three or more of one kind are
   drawn as one notice. */
function notices() {
  var lines = DATA.dirty
    ? [{line: 'The working tree has uncommitted changes, so what is on this '
       + 'board is not what a commit would carry.'}] : [];
  lines = lines.concat(groupedLines(DATA.warnings || []));
  var drawn = lines.map(function (item) {
    return notice(item.line, 'warn', item.names);
  }).join('') + groupedLines(DATA.information || []).map(function (item) {
    return notice(item.line, 'neutral', item.names);
  }).join('');
  return drawn ? '<section class="notices">' + drawn + '</section>' : '';
}

/* A path, which a narrow screen may break after a `/` or a `_` and nowhere
   else: each part between two such places is set on one line. A part over 32
   characters is left to break where it must, so the page never scrolls
   sideways. */
function pathText(path) {
  return (String(path == null ? '' : path).match(/[^\/_]*[\/_]|[^\/_]+$/g)
    || []).map(function (part) {
      return part.length > 32 ? esc(part)
        : '<span class="nowrap">' + esc(part) + '</span>';
    }).join('<wbr>');
}

/* One word of a notice. A path or a name never breaks inside itself, except
   a path too long for a phone's width, which breaks after a `/` and nowhere
   else, so the page never scrolls sideways. */
function noticeWord(word) {
  if (!/[\/\-._]/.test(word)) { return esc(word); }
  var text = word.length > 36 ? esc(word).replace(/\//g, '/<wbr>') : esc(word);
  return '<span class="nowrap">' + text + '</span>';
}

function render() {
  var app = document.getElementById('app');
  if (!DATA) {
    app.innerHTML = '<div class="wrap"><div class="empty">No board data yet. '
      + 'Run purlin:status to write .purlin/report-data.js, then reload this '
      + 'page.</div></div>';
    return;
  }
  if (DATA.schema_version !== SCHEMA) {
    app.innerHTML = topBar(false) + '<div class="wrap"><div class="notice">'
      + esc('This data was written for schema ' + DATA.schema_version
        + ' and this page reads schema ' + SCHEMA + '. Run purlin:status to '
        + 'write it again.') + '</div></div>';
    return;
  }
  if (VIEW.screen !== 'rule') { VIEW.screen = 'board'; }
  /* The notices are about the tree the whole payload came from, so the board
     carries them once rather than every screen repeating them. */
  var body = VIEW.screen === 'rule' ? renderRule() : renderBoard();
  app.innerHTML = topBar(true) + '<div class="wrap">' + body + '</div>';
}

function onClick(event) {
  var node = event.target;
  while (node && node !== document && !node.getAttribute('data-act')) {
    node = node.parentNode;
  }
  if (!node || node === document) { return; }
  var act = node.getAttribute('data-act');
  if (act === 'theme') { toggleTheme(); }
  else if (act === 'close') {
    VIEW.screen = 'board';
    VIEW.rule = VIEW.feature = null;
  } else if (act === 'group') {
    var group = node.getAttribute('data-group');
    VIEW.groups[group] = VIEW.groups[group] === false;
  } else if (act === 'feature') {
    var name = node.getAttribute('data-feature');
    VIEW.features[name] = !VIEW.features[name];
  } else if (act === 'rule') {
    VIEW.feature = node.getAttribute('data-feature');
    VIEW.rule = node.getAttribute('data-rule');
    VIEW.screen = 'rule';
  }
  render();
}

restoreTheme();
document.getElementById('app').addEventListener('click', onClick);
/* A band is a control drawn as a row, so Enter and Space press it as they
   press a button, and the focus comes back to it once the page is drawn. */
document.getElementById('app').addEventListener('keydown', function (event) {
  var group = event.target.getAttribute('data-group');
  if (!group || (event.key !== 'Enter' && event.key !== ' ')) { return; }
  event.preventDefault();
  onClick(event);
  document.querySelector('.group[data-group="' + CSS.escape(group) + '"]').focus();
});
loadData(function (payload) {
  DATA = payload;
  render();
});
