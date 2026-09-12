<?php
/**
 * Purlin proof collector for PHPUnit.
 *
 * Standalone script that runs PHPUnit tests, parses proof markers from
 * docblock annotations, and emits write-scoped proof JSON files.
 *
 * Marker syntax in test files:
 *   /** @purlin feature_name PROOF-1 RULE-1 unit * /
 *   public function testValidLogin() { ... }
 *   /** @purlin feature_name PROOF-2 RULE-2 unit on(windows-2022) * /
 *   /** @purlin feature_name PROOF-3 RULE-3 on(windows, macos) * /   (tier omitted: unit)
 *
 * A marker that declares on(...) writes its entry to
 * <feature>.proofs-<tier>@<host>.json, where <host> is PURLIN_PLATFORM when set
 * and otherwise the detected OS family (windows, macos, linux); every entry in
 * that file carries an eighth field, "platform", equal to <host>. A marker with
 * no on(...) writes the agnostic <feature>.proofs-<tier>.json with the seven
 * standard fields, whatever PURLIN_PLATFORM says. The collector never evaluates
 * version constraints.
 *
 * At the end of the run, the same moment the proof files are written, the
 * collector writes or merges the project's run marker
 * .purlin/runtime/test_run.json (proof_common RULE-19), so a receipt issued in
 * a consumer project can record which run its evidence came from.
 *
 * Usage:
 *   php scripts/proof/phpunit_purlin.php <test_file>
 *
 * Or as a PHPUnit printer:
 *   phpunit --printer=PurlinProofPrinter tests/
 */

// When run standalone, parse a PHP test file and emit proof JSON to stdout.
// Each annotated function runs in its own child php process; this script
// orchestrates and collects the results.

// PURLIN_PLATFORM when set, else the OS family. The only place the collector
// looks at the host; nothing else in it branches on the operating system.
function host_platform(): string {
    $env = trim((string)getenv('PURLIN_PLATFORM'));
    if ($env !== '') {
        return $env;
    }
    $families = ['Windows' => 'windows', 'Darwin' => 'macos', 'Linux' => 'linux'];
    return $families[PHP_OS_FAMILY] ?? strtolower(PHP_OS_FAMILY);
}

function parse_proof_markers(string $filepath): array {
    $content = file_get_contents($filepath);
    $markers = [];

    // Match @purlin docblock annotations
    // Pattern: @purlin feature_name PROOF-N RULE-N [tier] [on(a, b)]
    preg_match_all(
        '/@purlin\s+(\w+)\s+(PROOF-\d+)\s+(RULE-\d+)(?:\s+(?!on\()(\w+))?(?:\s+on\(([^)]*)\))?.*?\n\s*(?:public\s+)?function\s+(\w+)/s',
        $content,
        $matches,
        PREG_SET_ORDER
    );

    foreach ($matches as $m) {
        $declared = array_values(array_filter(array_map('trim', explode(',', $m[5] ?? ''))));
        $markers[] = [
            'feature' => $m[1],
            'id' => $m[2],
            'rule' => $m[3],
            'tier' => ($m[4] ?? '') !== '' ? $m[4] : 'unit',
            'platform' => count($declared) ? host_platform() : '',
            'test_name' => $m[6],
        ];
    }

    return $markers;
}

function run_php_test(string $filepath, string $function_name): bool {
    // The child process is started from an argv array, so no shell string is
    // ever built and nothing in the path can be read as an option or an
    // operator (proof_plugins_php RULE-3). The path is embedded in the -r
    // program as a PHP literal via var_export; the function name comes from
    // the marker regex, which matches word characters only.
    $code = sprintf(
        'require %s; try { %s(); echo "PASS"; } '
        . 'catch (Throwable $e) { echo "FAIL: " . $e->getMessage(); exit(1); }',
        var_export($filepath, true),
        $function_name
    );
    $descriptors = [
        0 => ['pipe', 'r'],
        1 => ['pipe', 'w'],
        2 => ['pipe', 'w'],
    ];
    $pipes = [];
    $process = proc_open(['php', '-r', $code], $descriptors, $pipes);
    if (!is_resource($process)) {
        return false;
    }
    fclose($pipes[0]);
    stream_get_contents($pipes[1]);
    fclose($pipes[1]);
    stream_get_contents($pipes[2]);
    fclose($pipes[2]);
    return proc_close($process) === 0;
}

function resolve_spec_dirs(): array {
    $dirs = [];
    foreach (glob('specs/**/*.md', GLOB_BRACE) as $spec) {
        // glob with ** doesn't work recursively in PHP, use recursive scan
    }
    // Use a recursive directory iterator instead
    $iterator = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator('specs', RecursiveDirectoryIterator::SKIP_DOTS)
    );
    foreach ($iterator as $file) {
        if ($file->getExtension() === 'md') {
            $stem = pathinfo($file->getFilename(), PATHINFO_FILENAME);
            $dirs[$stem] = $file->getPath();
        }
    }
    return $dirs;
}

// ── The run marker (proof_common RULE-19) ───────────────────────────────────
// Written or merged at the same moment the proof files are written, so a
// consumer receipt can record which run its evidence came from.

// HEAD in $root, or null when $root is not inside a git work tree.
function run_marker_commit(string $root): ?string {
    $descriptors = [1 => ['pipe', 'w'], 2 => ['pipe', 'w']];
    $pipes = [];
    $process = @proc_open(['git', 'rev-parse', 'HEAD'], $descriptors, $pipes, $root);
    if (!is_resource($process)) {
        return null;
    }
    $out = stream_get_contents($pipes[1]);
    fclose($pipes[1]);
    stream_get_contents($pipes[2]);
    fclose($pipes[2]);
    proc_close($process);
    $out = trim((string)$out);
    return $out === '' ? null : $out;
}

/**
 * Write or merge <root>/.purlin/runtime/test_run.json (RULE-19).
 *
 * Nothing is written when <root>/.purlin is absent: that is not a Purlin
 * project. An existing marker whose commit equals this run's commit is merged
 * into: test_files unioned, the three counts summed, this run appended to
 * runs, ok and-ed, and every other top-level field carried through untouched.
 * A marker naming another commit is replaced. The file is written to a temp
 * file in the same directory and renamed over the target, so a concurrent
 * reader sees one whole marker or the other; a read that lands on unparsable
 * JSON is retried before this run starts a fresh marker.
 */
function write_run_marker(string $root, string $sweep, array $test_files,
                          int $passed, int $failed, int $skipped): void {
    if (!is_dir($root . '/.purlin')) {
        return;
    }
    $path = $root . '/.purlin/runtime/test_run.json';
    if (!is_dir(dirname($path))) {
        mkdir(dirname($path), 0777, true);
    }
    $commit = run_marker_commit($root);
    $at = gmdate('Y-m-d\TH:i:s') . '+00:00';
    $files = [];
    foreach ($test_files as $f) {
        $f = str_replace('\\', '/', (string)$f);
        if ($f !== '') {
            $files[$f] = true;
        }
    }
    $files = array_keys($files);
    sort($files);

    $marker = [];
    for ($attempt = 0; $attempt < 3; $attempt++) {
        if (!file_exists($path)) {
            break;
        }
        $raw = @file_get_contents($path);
        $existing = $raw === false ? null : json_decode($raw, true);
        if (is_array($existing)) {
            if (($existing['commit'] ?? null) === $commit) {
                $marker = $existing;
            }
            break;
        }
        usleep(50000);  // a concurrent writer is mid-replace: read again
    }

    $runs = $marker['runs'] ?? [];
    $runs[] = ['plugin' => $sweep, 'at' => $at, 'test_files' => $files,
               'passed' => $passed, 'failed' => $failed, 'skipped' => $skipped];
    $merged = array_values(array_unique(array_merge($marker['test_files'] ?? [], $files)));
    sort($merged);

    $marker['at'] = $at;
    $marker['commit'] = $commit;
    $marker['sweep'] = $sweep;
    $marker['test_files'] = $merged;
    $marker['passed'] = (int)($marker['passed'] ?? 0) + $passed;
    $marker['failed'] = (int)($marker['failed'] ?? 0) + $failed;
    $marker['skipped'] = (int)($marker['skipped'] ?? 0) + $skipped;
    $marker['ok'] = ($marker['ok'] ?? true) && $failed === 0;
    $marker['runs'] = $runs;

    $tmp = $path . '.' . getmypid() . '.tmp';
    file_put_contents($tmp, json_encode(
        $marker,
        JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES
    ) . "\n");
    rename($tmp, $path);
}

function write_proofs(array $proofs_by_key, string $test_file): void {
    $spec_dirs = resolve_spec_dirs();

    foreach ($proofs_by_key as $key => $new_entries) {
        [$feature, $tier, $platform] = explode(':', $key);
        $suffix = $platform !== '' ? "{$tier}@{$platform}" : $tier;
        $spec_dir = $spec_dirs[$feature] ?? null;
        if ($spec_dir === null) {
            fwrite(STDERR, "WARNING: No spec found for feature \"{$feature}\" — writing proofs to specs/{$feature}.proofs-{$suffix}.json. Create a spec with: purlin:spec {$feature}\n");
            $spec_dir = 'specs';
        }

        $path = "{$spec_dir}/{$feature}.proofs-{$suffix}.json";

        // Load existing
        $existing = [];
        if (file_exists($path)) {
            $data = json_decode(file_get_contents($path), true);
            $existing = $data['proofs'] ?? [];
        }

        // Write-scoped overwrite keyed by (feature, tier, platform, test_file), per
        // proof_common RULE-4 (the file carries tier and platform, so within it the
        // key is (feature, test_file)), plus orphan reaping of vanished test files (RULE-11).
        $run_files = [];
        foreach ($new_entries as $e) {
            $run_files[$e['test_file'] ?? ''] = true;
        }
        $kept = array_filter($existing, function($e) use ($feature, $run_files) {
            if (($e['feature'] ?? '') !== $feature) {
                return true;
            }
            $tf = $e['test_file'] ?? '';
            return $tf !== '' && !isset($run_files[$tf]) && file_exists($tf);
        });

        $payload = ['tier' => $tier];
        if ($platform !== '') {
            $payload['platform'] = $platform;
        }
        $payload['proofs'] = array_values(array_merge($kept, $new_entries));

        // Atomic write
        $tmp = $path . '.tmp';
        file_put_contents($tmp, json_encode(
            $payload,
            JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES
        ) . "\n");
        rename($tmp, $path);
    }
}

// --- Main ---
if (php_sapi_name() === 'cli' && isset($argv[1])) {
    $test_file = $argv[1];
    if (!file_exists($test_file)) {
        fwrite(STDERR, "File not found: {$test_file}\n");
        exit(2);
    }
    // Recorded with "/" separators on every OS (proof_common RULE-15); the
    // path as given is still used to run the tests.
    $recorded_file = str_replace('\\', '/', $test_file);

    $markers = parse_proof_markers($test_file);
    if (empty($markers)) {
        echo json_encode(['proofs' => []], JSON_PRETTY_PRINT) . "\n";
        exit(0);
    }

    $proofs_by_key = [];
    foreach ($markers as $marker) {
        $passed = run_php_test($test_file, $marker['test_name']);
        $key = $marker['feature'] . ':' . $marker['tier'] . ':' . $marker['platform'];
        $entry = [
            'feature' => $marker['feature'],
            'id' => $marker['id'],
            'rule' => $marker['rule'],
            'test_file' => $recorded_file,
            'test_name' => $marker['test_name'],
            'status' => $passed ? 'pass' : 'fail',
            'tier' => $marker['tier'],
        ];
        if ($marker['platform'] !== '') {
            $entry['platform'] = $marker['platform'];
        }
        $proofs_by_key[$key][] = $entry;
    }

    write_proofs($proofs_by_key, $test_file);

    // RULE-19: the run marker, written at the same moment as the proof files.
    // A PHP function that is never called records nothing, so the collector has
    // no skip signal and $skipped is 0.
    $marker_files = [];
    $marker_passed = 0;
    $marker_failed = 0;
    foreach ($proofs_by_key as $entries) {
        foreach ($entries as $e) {
            $marker_files[] = $e['test_file'];
            if ($e['status'] === 'pass') {
                $marker_passed++;
            } else {
                $marker_failed++;
            }
        }
    }
    write_run_marker(getcwd(), 'phpunit_purlin', $marker_files,
                     $marker_passed, $marker_failed, 0);

    // Also emit to stdout for inspection
    $all = [];
    foreach ($proofs_by_key as $entries) {
        $all = array_merge($all, $entries);
    }
    echo json_encode(['proofs' => $all], JSON_PRETTY_PRINT) . "\n";
}
