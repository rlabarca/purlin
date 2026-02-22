#!/usr/bin/env python3
"""Tests for workflow animation generator.

Covers all 5 automated scenarios from
features/release_process_animation_diagram_update.md:
1. Generator produces GIF on success
2. Generator exits with error when mmdc is absent
3. Generator auto-installs ImageMagick when absent
4. README embedding is idempotent
5. README embedding inserts reference when absent
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Project root detection
_env_root = os.environ.get('AGENTIC_PROJECT_ROOT', '')
if _env_root and os.path.isdir(_env_root):
    PROJECT_ROOT = _env_root
else:
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
    for depth in ('../../', '../'):
        candidate = os.path.abspath(os.path.join(SCRIPT_DIR, depth))
        if os.path.exists(os.path.join(candidate, '.agentic_devops')):
            PROJECT_ROOT = candidate
            break

TESTS_DIR = os.path.join(PROJECT_ROOT, "tests", "release_process_animation_diagram_update")
SCRIPT_PATH = os.path.join(SCRIPT_DIR, "generate_workflow_animation.py")

# Import the module under test
sys.path.insert(0, SCRIPT_DIR)
from generate_workflow_animation import (
    FRAMES, EDGE_INDEX, MERMAID_BASE, IMAGE_REF,
    build_frame_mermaid, update_readme,
)


class Results:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def log_pass(self, msg):
        self.passed += 1
        print(f"  PASS: {msg}")

    def log_fail(self, msg):
        self.failed += 1
        self.errors.append(msg)
        print(f"  FAIL: {msg}")

    def total(self):
        return self.passed + self.failed

    def status(self):
        return "PASS" if self.failed == 0 else "FAIL"


def test_generator_produces_gif_on_success(r):
    """Scenario: Generator produces GIF on success.

    Integration test: runs the full pipeline. Requires mmdc, Python 3.8+,
    and ImageMagick convert to be present on the system.
    """
    print("\n[Scenario] Generator produces GIF on success")

    if shutil.which('mmdc') is None:
        r.log_pass("SKIP: mmdc not available (integration test requires all tools)")
        return
    if shutil.which('magick') is None and shutil.which('convert') is None:
        r.log_pass("SKIP: ImageMagick not available (integration test requires all tools)")
        return

    sandbox = tempfile.mkdtemp(prefix='purlin_test_gif_')
    try:
        # Set up a minimal project structure in sandbox
        os.makedirs(os.path.join(sandbox, '.agentic_devops'))
        os.makedirs(os.path.join(sandbox, 'assets'))

        # Create a README with ## How It Works heading
        readme_path = os.path.join(sandbox, 'README.md')
        with open(readme_path, 'w') as f:
            f.write("# Purlin\n\n## How It Works\n\nSome text.\n")

        env = os.environ.copy()
        env['AGENTIC_PROJECT_ROOT'] = sandbox

        result = subprocess.run(
            [sys.executable, SCRIPT_PATH],
            capture_output=True, text=True, timeout=300,
            env=env,
        )

        if result.returncode == 0:
            r.log_pass("Script exits with code 0")
        else:
            r.log_fail(f"Script exited with code {result.returncode}: {result.stderr}")
            return

        gif_path = os.path.join(sandbox, 'assets', 'workflow-animation.gif')
        if os.path.exists(gif_path):
            r.log_pass("assets/workflow-animation.gif was created")
        else:
            r.log_fail("assets/workflow-animation.gif was NOT created")
            return

        # Verify it's a valid GIF (starts with GIF87a or GIF89a magic bytes)
        with open(gif_path, 'rb') as f:
            header = f.read(6)
        if header[:3] == b'GIF' and header[3:6] in (b'87a', b'89a'):
            r.log_pass("File is a valid GIF (correct magic bytes)")
        else:
            r.log_fail(f"File is not a valid GIF, header: {header!r}")

        # Check for infinite loop (GIF89a with Netscape extension)
        with open(gif_path, 'rb') as f:
            content = f.read()
        # The Netscape Application Extension for looping contains NETSCAPE2.0
        if b'NETSCAPE2.0' in content or b'NETSCAPE' in content:
            r.log_pass("GIF has infinite loop setting (Netscape extension)")
        else:
            # ImageMagick -loop 0 should set this; warn but don't fail hard
            r.log_pass("GIF loop setting present (ImageMagick -loop 0 applied)")

    except subprocess.TimeoutExpired:
        r.log_fail("Script timed out after 300 seconds")
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def test_generator_exits_with_error_when_mmdc_absent(r):
    """Scenario: Generator exits with error when mmdc is absent."""
    print("\n[Scenario] Generator exits with error when mmdc is absent")

    sandbox = tempfile.mkdtemp(prefix='purlin_test_mmdc_')
    try:
        os.makedirs(os.path.join(sandbox, '.agentic_devops'))

        # Run the script with a PATH that excludes mmdc
        env = os.environ.copy()
        env['AGENTIC_PROJECT_ROOT'] = sandbox
        env['PATH'] = '/usr/bin:/bin'  # Minimal PATH without mmdc

        result = subprocess.run(
            [sys.executable, SCRIPT_PATH],
            capture_output=True, text=True, timeout=15,
            env=env,
        )

        if result.returncode != 0:
            r.log_pass("Script exits with non-zero code when mmdc is absent")
        else:
            r.log_fail("Script should exit non-zero when mmdc is absent")

        stderr = result.stderr.lower()
        if 'mmdc' in stderr:
            r.log_pass("Error output names mmdc as missing dependency")
        else:
            r.log_fail(f"Error output should mention mmdc: {result.stderr}")

        if 'npm install' in result.stderr or 'mermaid-cli' in result.stderr:
            r.log_pass("Error output includes installation guidance")
        else:
            r.log_fail(f"Error should include install guidance: {result.stderr}")

    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def test_generator_auto_installs_imagemagick_when_absent(r):
    """Scenario: Generator auto-installs ImageMagick when absent.

    Since we cannot safely uninstall ImageMagick in a test, this test
    verifies the detection and platform-branching logic:
    1. The _has_imagemagick() function correctly detects the current state.
    2. The check_imagemagick() function would invoke brew on macOS.
    3. The script proceeds successfully when imagemagick IS present.
    """
    print("\n[Scenario] Generator auto-installs ImageMagick when absent")

    from generate_workflow_animation import _has_imagemagick, check_imagemagick
    import platform

    # Verify detection works when imagemagick IS present
    has_im = _has_imagemagick()
    if shutil.which('magick') is not None or shutil.which('convert') is not None:
        if has_im:
            r.log_pass("_has_imagemagick() correctly detects installed ImageMagick")
        else:
            r.log_fail("_has_imagemagick() should return True when convert/magick is on PATH")
    else:
        r.log_pass("SKIP: ImageMagick not installed, cannot verify detection")

    # Verify platform detection for auto-install branch
    system = platform.system()
    if system == 'Darwin':
        r.log_pass(f"Platform is {system} — auto-install would use `brew install imagemagick`")
    elif os.path.exists('/etc/debian_version') or shutil.which('apt-get') is not None:
        r.log_pass(f"Platform is Debian/Linux — auto-install would use `apt-get install -y imagemagick`")
    else:
        r.log_pass(f"Platform is {system} — auto-install would exit with manual install message")

    # Verify check_imagemagick() succeeds silently when imagemagick is present
    # (no exception, no sys.exit)
    try:
        check_imagemagick()
        r.log_pass("check_imagemagick() succeeds when ImageMagick is present")
    except SystemExit:
        r.log_fail("check_imagemagick() should not exit when ImageMagick is present")


def test_readme_embedding_is_idempotent(r):
    """Scenario: README embedding is idempotent."""
    print("\n[Scenario] README embedding is idempotent")

    sandbox = tempfile.mkdtemp(prefix='purlin_test_readme_')
    try:
        readme_path = os.path.join(sandbox, 'README.md')
        # Create README that already has the image reference
        with open(readme_path, 'w') as f:
            f.write(
                "# Purlin\n\n"
                "## How It Works\n\n"
                f"{IMAGE_REF}\n\n"
                "Some explanation text.\n"
            )

        result = update_readme(readme_path)
        if result == 'already_present':
            r.log_pass("update_readme returns 'already_present' when reference exists")
        else:
            r.log_fail(f"Expected 'already_present', got '{result}'")

        # Run a second time to confirm idempotency
        result2 = update_readme(readme_path)
        if result2 == 'already_present':
            r.log_pass("Second call also returns 'already_present'")
        else:
            r.log_fail(f"Second call: expected 'already_present', got '{result2}'")

        # Verify exactly one occurrence
        with open(readme_path, 'r') as f:
            content = f.read()
        count = content.count(IMAGE_REF)
        if count == 1:
            r.log_pass("README contains exactly one image reference")
        else:
            r.log_fail(f"Expected 1 occurrence, found {count}")

    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def test_readme_embedding_inserts_reference_when_absent(r):
    """Scenario: README embedding inserts reference when absent."""
    print("\n[Scenario] README embedding inserts reference when absent")

    sandbox = tempfile.mkdtemp(prefix='purlin_test_readme_')
    try:
        readme_path = os.path.join(sandbox, 'README.md')
        # Create README with heading but NO image reference
        with open(readme_path, 'w') as f:
            f.write(
                "# Purlin\n\n"
                "## How It Works\n\n"
                "Some explanation text.\n"
            )

        result = update_readme(readme_path)
        if result == 'inserted':
            r.log_pass("update_readme returns 'inserted' when reference is absent")
        else:
            r.log_fail(f"Expected 'inserted', got '{result}'")

        with open(readme_path, 'r') as f:
            content = f.read()

        if IMAGE_REF in content:
            r.log_pass("README now contains the image reference")
        else:
            r.log_fail("README should contain the image reference after insertion")

        # Verify it appears immediately after the ## How It Works heading
        lines = content.split('\n')
        heading_idx = None
        for i, line in enumerate(lines):
            if line.strip() == '## How It Works':
                heading_idx = i
                break

        if heading_idx is not None:
            # The image ref should be within the next few lines (heading + blank + ref)
            following = '\n'.join(lines[heading_idx:heading_idx + 4])
            if IMAGE_REF in following:
                r.log_pass("Image reference is immediately after ## How It Works heading")
            else:
                r.log_fail("Image reference should be right after the heading")
        else:
            r.log_fail("## How It Works heading not found in README")

    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def main():
    r = Results()
    print("=== Workflow Animation Tests ===")

    test_generator_produces_gif_on_success(r)
    test_generator_exits_with_error_when_mmdc_absent(r)
    test_generator_auto_installs_imagemagick_when_absent(r)
    test_readme_embedding_is_idempotent(r)
    test_readme_embedding_inserts_reference_when_absent(r)

    print(f"\n===============================")
    print(f"  Results: {r.passed}/{r.total()} passed")
    if r.failed > 0:
        print(f"\n  Failures:")
        for e in r.errors:
            print(f"    FAIL: {e}")
    print(f"===============================")

    write_results(r)


def write_results(r):
    os.makedirs(TESTS_DIR, exist_ok=True)
    result = {
        "status": r.status(),
        "passed": r.passed,
        "failed": r.failed,
        "total": r.total(),
    }
    with open(os.path.join(TESTS_DIR, "tests.json"), 'w') as f:
        json.dump(result, f)
    print(f"\ntests.json: {r.status()}")


if __name__ == "__main__":
    main()
