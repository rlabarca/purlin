<?php
/**
 * Purlin proof collector for PHPUnit.
 *
 * Standalone script that runs PHPUnit tests, parses proof markers from
 * docblock annotations, and emits feature-scoped proof JSON files.
 *
 * Marker syntax in test files:
 *   /** @purlin feature_name PROOF-1 RULE-1 unit * /
 *   public function testValidLogin() { ... }
 *
 * Usage:
 *   php scripts/proof/phpunit_purlin.php <test_file>
 *
 * Or as a PHPUnit printer:
 *   phpunit --printer=PurlinProofPrinter tests/
 */

// When run standalone, parse a PHP test file and emit proof JSON to stdout.
// The actual test execution happens via `php -r` — this script orchestrates.

function parse_proof_markers(string $filepath): array {
    $content = file_get_contents($filepath);
    $markers = [];

    // Match @purlin docblock annotations
    // Pattern: @purlin feature_name PROOF-N RULE-N [tier]
    preg_match_all(
        '/@purlin\s+(\w+)\s+(PROOF-\d+)\s+(RULE-\d+)(?:\s+(\w+))?.*?\n\s*(?:public\s+)?function\s+(\w+)/s',
        $content,
        $matches,
        PREG_SET_ORDER
    );

    foreach ($matches as $m) {
        $markers[] = [
            'feature' => $m[1],
            'id' => $m[2],
            'rule' => $m[3],
            'tier' => $m[4] ?? 'unit',
            'test_name' => $m[5],
        ];
    }

    return $markers;
}

function run_php_test(string $filepath, string $function_name): bool {
    // Include the test file and run the function, capturing the exit code
    $cmd = sprintf(
        'php -r \'require "%s"; try { %s(); echo "PASS"; } catch (Throwable $e) { echo "FAIL: " . $e->getMessage(); exit(1); }\' 2>&1',
        addslashes($filepath),
        $function_name
    );
    $output = [];
    $exit_code = 0;
    exec($cmd, $output, $exit_code);
    return $exit_code === 0;
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

function write_proofs(array $proofs_by_key, string $test_file): void {
    $spec_dirs = resolve_spec_dirs();

    foreach ($proofs_by_key as $key => $new_entries) {
        [$feature, $tier] = explode(':', $key);
        $spec_dir = $spec_dirs[$feature] ?? null;
        if ($spec_dir === null) {
            fwrite(STDERR, "WARNING: No spec found for feature \"{$feature}\" — writing proofs to specs/{$feature}.proofs-{$tier}.json. Create a spec with: purlin:spec {$feature}\n");
            $spec_dir = 'specs';
        }

        $path = "{$spec_dir}/{$feature}.proofs-{$tier}.json";

        // Load existing
        $existing = [];
        if (file_exists($path)) {
            $data = json_decode(file_get_contents($path), true);
            $existing = $data['proofs'] ?? [];
        }

        // Feature-scoped overwrite
        $kept = array_filter($existing, fn($e) => ($e['feature'] ?? '') !== $feature);

        // Atomic write
        $tmp = $path . '.tmp';
        file_put_contents($tmp, json_encode(
            ['tier' => $tier, 'proofs' => array_values(array_merge($kept, $new_entries))],
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

    $markers = parse_proof_markers($test_file);
    if (empty($markers)) {
        echo json_encode(['proofs' => []], JSON_PRETTY_PRINT) . "\n";
        exit(0);
    }

    $proofs_by_key = [];
    foreach ($markers as $marker) {
        $passed = run_php_test($test_file, $marker['test_name']);
        $key = $marker['feature'] . ':' . $marker['tier'];
        $proofs_by_key[$key][] = [
            'feature' => $marker['feature'],
            'id' => $marker['id'],
            'rule' => $marker['rule'],
            'test_file' => $test_file,
            'test_name' => $marker['test_name'],
            'status' => $passed ? 'pass' : 'fail',
            'tier' => $marker['tier'],
        ];
    }

    write_proofs($proofs_by_key, $test_file);

    // Also emit to stdout for inspection
    $all = [];
    foreach ($proofs_by_key as $entries) {
        $all = array_merge($all, $entries);
    }
    echo json_encode(['proofs' => $all], JSON_PRETTY_PRINT) . "\n";
}
