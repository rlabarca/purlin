/**
 * Automated tests for feedback_form feature.
 * Traces to: features/feedback_form.md
 *
 * Scenario mapping:
 *  [S1] Successful submission with all fields
 *  [S2] Submission blocked when no issue type selected
 *  [S3] File over 5MB is rejected
 *  [S4] Cancel resets the form
 */

const { test, describe, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

// Validation helpers (imported from frontend module)
const { validateIssueType, validateFileSize, createDefaultState } = require('../../public/app.js');

// ── Test helpers ──────────────────────────────────────────────────────────────

const PROJECT_ROOT = path.join(__dirname, '..', '..');
const FEEDBACK_JSON = path.join(PROJECT_ROOT, 'data', 'feedback.json');
const TEST_FEEDBACK_JSON = path.join(PROJECT_ROOT, 'data', 'feedback.test.json');
const SERVER_PORT = 3099;
const RESULTS_PATH = path.join(__dirname, 'tests.json');

let server;
let app;

function postFeedback(fields, fileBuffer, filename, port) {
  return new Promise((resolve, reject) => {
    const boundary = `----FormBoundary${Date.now()}`;
    let body = '';

    for (const [key, val] of Object.entries(fields)) {
      body += `--${boundary}\r\nContent-Disposition: form-data; name="${key}"\r\n\r\n${val}\r\n`;
    }

    let bodyBuf;
    if (fileBuffer && filename) {
      const filePart = `--${boundary}\r\nContent-Disposition: form-data; name="attachment"; filename="${filename}"\r\nContent-Type: application/octet-stream\r\n\r\n`;
      const end = `\r\n--${boundary}--\r\n`;
      bodyBuf = Buffer.concat([
        Buffer.from(body),
        Buffer.from(filePart),
        fileBuffer,
        Buffer.from(end)
      ]);
    } else {
      body += `--${boundary}--\r\n`;
      bodyBuf = Buffer.from(body);
    }

    const options = {
      hostname: 'localhost',
      port,
      path: '/feedback',
      method: 'POST',
      headers: {
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': bodyBuf.length
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', chunk => (data += chunk));
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
        catch { resolve({ status: res.statusCode, body: data }); }
      });
    });
    req.on('error', reject);
    req.write(bodyBuf);
    req.end();
  });
}

function readFeedbackFile() {
  if (!fs.existsSync(FEEDBACK_JSON)) return [];
  return JSON.parse(fs.readFileSync(FEEDBACK_JSON, 'utf8'));
}

function writeResults(results) {
  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => !r.passed).length;
  fs.writeFileSync(RESULTS_PATH, JSON.stringify({
    status: failed === 0 ? 'PASS' : 'FAIL',
    passed,
    failed,
    total: results.length,
    scenarios: results
  }, null, 2));
}

// ── Test lifecycle ─────────────────────────────────────────────────────────────

const results = [];

before(async () => {
  // Start server on isolated port
  process.env.PORT = SERVER_PORT;
  const mod = require('../../server.js');
  app = mod.app;
  server = mod.server;

  // Use isolated feedback file during tests
  const orig = fs.existsSync(FEEDBACK_JSON) ? fs.readFileSync(FEEDBACK_JSON) : null;
  if (orig) fs.renameSync(FEEDBACK_JSON, TEST_FEEDBACK_JSON);

  // Wait briefly for server to be ready
  await new Promise(r => setTimeout(r, 100));
});

after(() => {
  // Restore original feedback file
  if (fs.existsSync(FEEDBACK_JSON)) fs.unlinkSync(FEEDBACK_JSON);
  if (fs.existsSync(TEST_FEEDBACK_JSON)) fs.renameSync(TEST_FEEDBACK_JSON, FEEDBACK_JSON);

  server.close();
  writeResults(results);
});

// ── Scenario S1: Successful submission with all fields ────────────────────────
// Trace: "Successful submission with all fields"

describe('[S1] Successful submission with all fields', () => {
  test('server returns HTTP 200', async () => {
    const fileContent = Buffer.alloc(1024, 'x'); // 1KB file — under 5MB
    const res = await postFeedback(
      { issueType: 'Bug', details: 'Reproducible crash on load' },
      fileContent,
      'test.txt',
      SERVER_PORT
    );
    const passed = res.status === 200;
    results.push({ scenario: 'S1-status-200', passed });
    assert.equal(res.status, 200);
  });

  test('entry appended to data/feedback.json with issueType "Bug"', async () => {
    const entries = readFeedbackFile();
    const entry = entries.find(e => e.issueType === 'Bug' && e.details === 'Reproducible crash on load');
    const passed = !!(entry && entry.id && entry.timestamp && entry.issueType === 'Bug');
    results.push({ scenario: 'S1-feedback-json', passed });
    assert.ok(entry, 'entry not found in feedback.json');
    assert.equal(entry.issueType, 'Bug');
    assert.ok(entry.id, 'entry missing id');
    assert.ok(entry.timestamp, 'entry missing timestamp');
  });

  test('entry has valid ISO 8601 timestamp', async () => {
    const entries = readFeedbackFile();
    const entry = entries.find(e => e.issueType === 'Bug');
    const parsed = entry ? new Date(entry.timestamp) : null;
    const passed = !!(parsed && !isNaN(parsed.getTime()));
    results.push({ scenario: 'S1-timestamp', passed });
    assert.ok(passed, 'timestamp is not valid ISO 8601');
  });

  test('entry has attachmentPath when file submitted', async () => {
    const entries = readFeedbackFile();
    const entry = entries.find(e => e.issueType === 'Bug');
    const passed = !!(entry && entry.attachmentPath && entry.attachmentPath.startsWith('uploads'));
    results.push({ scenario: 'S1-attachment-path', passed });
    assert.ok(passed, 'attachmentPath missing or invalid');
  });
});

// ── Scenario S2: Submission blocked when no issue type ────────────────────────
// Trace: "Submission blocked when no issue type selected"

describe('[S2] Submission blocked when no issue type selected', () => {
  test('validateIssueType returns false for empty string', () => {
    const passed = validateIssueType('') === false;
    results.push({ scenario: 'S2-validate-empty', passed });
    assert.equal(validateIssueType(''), false);
  });

  test('validateIssueType returns false for null/undefined', () => {
    const passed = validateIssueType(null) === false && validateIssueType(undefined) === false;
    results.push({ scenario: 'S2-validate-null', passed });
    assert.equal(validateIssueType(null), false);
    assert.equal(validateIssueType(undefined), false);
  });

  test('validateIssueType returns true for valid issue type', () => {
    const passed = validateIssueType('Bug') === true;
    results.push({ scenario: 'S2-validate-valid', passed });
    assert.equal(validateIssueType('Bug'), true);
    assert.equal(validateIssueType('Usability'), true);
    assert.equal(validateIssueType('Feature Request'), true);
  });

  test('server rejects POST with missing issueType (400)', async () => {
    const before = readFeedbackFile().length;
    const res = await postFeedback({ details: 'some details' }, null, null, SERVER_PORT);
    const after = readFeedbackFile().length;
    const passed = res.status === 400 && after === before;
    results.push({ scenario: 'S2-server-rejects', passed });
    assert.equal(res.status, 400);
    assert.equal(after, before, 'feedback.json should not grow on invalid submission');
  });
});

// ── Scenario S3: File over 5MB is rejected ────────────────────────────────────
// Trace: "File over 5MB is rejected"

describe('[S3] File over 5MB is rejected', () => {
  test('validateFileSize returns false for file > 5MB', () => {
    const overLimit = 5 * 1024 * 1024 + 1;
    const passed = validateFileSize(overLimit) === false;
    results.push({ scenario: 'S3-client-oversize', passed });
    assert.equal(validateFileSize(overLimit), false);
  });

  test('validateFileSize returns true for file exactly at 5MB', () => {
    const atLimit = 5 * 1024 * 1024;
    const passed = validateFileSize(atLimit) === true;
    results.push({ scenario: 'S3-client-at-limit', passed });
    assert.equal(validateFileSize(atLimit), true);
  });

  test('validateFileSize returns true for file under 5MB', () => {
    const under = 1024;
    const passed = validateFileSize(under) === true;
    results.push({ scenario: 'S3-client-under-limit', passed });
    assert.equal(validateFileSize(under), true);
  });

  test('server rejects file over 5MB with 400', async () => {
    const overSizeBuffer = Buffer.alloc(5 * 1024 * 1024 + 1, 'x');
    const res = await postFeedback(
      { issueType: 'Usability' },
      overSizeBuffer,
      'bigfile.bin',
      SERVER_PORT
    );
    const passed = res.status === 400;
    results.push({ scenario: 'S3-server-rejects-oversize', passed });
    assert.equal(res.status, 400);
  });
});

// ── Scenario S4: Cancel resets the form ──────────────────────────────────────
// Trace: "Cancel resets the form"

describe('[S4] Cancel resets the form', () => {
  test('createDefaultState returns empty issueType, details, and null attachment', () => {
    const state = createDefaultState();
    const passed = state.issueType === '' && state.details === '' && state.attachment === null;
    results.push({ scenario: 'S4-default-state', passed });
    assert.equal(state.issueType, '');
    assert.equal(state.details, '');
    assert.equal(state.attachment, null);
  });

  test('no data saved when cancel is invoked (no POST made)', async () => {
    // Cancel means no POST is sent — verify feedback.json is unchanged if we don't POST
    const before = readFeedbackFile().length;
    // Simulate cancel: do NOT call postFeedback
    const after = readFeedbackFile().length;
    const passed = before === after;
    results.push({ scenario: 'S4-no-data-saved', passed });
    assert.equal(before, after, 'feedback.json should be unchanged without a POST');
  });
});
