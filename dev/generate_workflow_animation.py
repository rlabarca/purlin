#!/usr/bin/env python3
"""Generate the Purlin workflow animation GIF.

Produces assets/workflow-animation.gif showing the Architect, Builder, QA,
Critic/CDD, and features/ nodes cycling through a feature's complete lifecycle.

Usage:
    python3 dev/generate_workflow_animation.py

Requirements:
    - Python 3.8+
    - mmdc (Mermaid CLI): npm install -g @mermaid-js/mermaid-cli
    - ImageMagick convert: auto-installed on macOS/Debian if absent
"""
import os
import platform
import shutil
import subprocess
import sys
import tempfile

# --- Project root detection (submodule-safe) ---
_env_root = os.environ.get('AGENTIC_PROJECT_ROOT', '')
if _env_root and os.path.isdir(_env_root):
    PROJECT_ROOT = _env_root
else:
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(_script_dir, '..'))
    for depth in ('../../', '../'):
        candidate = os.path.abspath(os.path.join(_script_dir, depth))
        if os.path.exists(os.path.join(candidate, '.agentic_devops')):
            PROJECT_ROOT = candidate
            break

OUTPUT_PATH = os.path.join(PROJECT_ROOT, 'assets', 'workflow-animation.gif')
README_PATH = os.path.join(PROJECT_ROOT, 'README.md')
IMAGE_REF = '![Purlin Agent Workflow](assets/workflow-animation.gif)'

# --- Canvas dimensions ---
DIAGRAM_WIDTH = 800
DIAGRAM_HEIGHT = 460
CAPTION_HEIGHT = 40

# --- Colors ---
CAPTION_BG = '#162531'
CAPTION_TEXT = '#E2E8F0'

CLASS_COLORS = {
    'active': '#38BDF8',
    'warning': '#F97316',
    'success': '#34D399',
}

# --- Mermaid base diagram (hub-spoke, CRITIC at center) ---
# Uses an invisible subgraph to force three-tier layout:
#   Row 1 (top): ARCH, BLDR, QA — arranged horizontally via direction LR
#   Row 2 (center): CRITIC — the hub
#   Row 3 (bottom): FEAT — the feature directory
# The subgraph is styled transparent to avoid visible borders.
MERMAID_BASE = """\
%%{init: {'theme': 'dark', 'themeVariables': {'background': '#0B131A', 'primaryColor': '#162531', 'primaryTextColor': '#E2E8F0', 'edgeLabelBackground': '#162531', 'clusterBkg': 'transparent', 'clusterBorder': 'transparent'}}}%%
graph TD
    subgraph agents[" "]
        direction LR
        ARCH["Architect"]
        BLDR["Builder"]
        QA["QA Agent"]
    end
    CRITIC["Critic / CDD"]
    FEAT["features/"]
    ARCH -.-> CRITIC
    BLDR -.-> CRITIC
    QA -.-> CRITIC
    CRITIC -.-> FEAT
    ARCH -.-> FEAT
    BLDR -.-> FEAT
    QA -.-> FEAT
    style agents fill:transparent,stroke:transparent,color:transparent
"""

# Edge index mapping (0-based, matches declaration order above)
EDGE_INDEX = {
    ('ARCH', 'CRITIC'): 0,
    ('BLDR', 'CRITIC'): 1,
    ('QA', 'CRITIC'): 2,
    ('CRITIC', 'FEAT'): 3,
    ('ARCH', 'FEAT'): 4,
    ('BLDR', 'FEAT'): 5,
    ('QA', 'FEAT'): 6,
}

# --- 16-frame canonical sequence (source of truth: spec Section 2.7) ---
FRAMES = [
    {
        'id': 'title',
        'scene': 'Title',
        'caption': 'Purlin: Continuous Design-Driven Development',
        'highlight': {'CRITIC': 'active'},
        'active_arrows': [],
        'duration_ms': 2000,
    },
    {
        'id': 'critic_intro',
        'scene': 'Critic Intro',
        'caption': 'The Critic coordinates the project...',
        'highlight': {'CRITIC': 'active'},
        'active_arrows': [],
        'duration_ms': 2000,
    },
    {
        'id': 'arch_reads_critic',
        'scene': 'Architect Reads Critic',
        'caption': 'Architect reads the Critic report...',
        'highlight': {'ARCH': 'active', 'CRITIC': 'active'},
        'active_arrows': [{'from': 'ARCH', 'to': 'CRITIC'}],
        'duration_ms': 2000,
    },
    {
        'id': 'arch_writes_feature',
        'scene': 'Architect Writes Feature',
        'caption': 'Architect designs a feature specification in features/',
        'highlight': {'ARCH': 'active', 'FEAT': 'active'},
        'active_arrows': [{'from': 'ARCH', 'to': 'FEAT'}],
        'duration_ms': 2000,
    },
    {
        'id': 'critic_detects_feature',
        'scene': 'Critic Detects Feature',
        'caption': 'Critic detects the new feature \u2014 status: [TODO]',
        'highlight': {'CRITIC': 'active', 'FEAT': 'active'},
        'active_arrows': [{'from': 'CRITIC', 'to': 'FEAT'}],
        'duration_ms': 2000,
    },
    {
        'id': 'builder_reads_critic',
        'scene': 'Builder Reads Critic',
        'caption': 'Builder reads Critic report: feature is ready...',
        'highlight': {'BLDR': 'active', 'CRITIC': 'active'},
        'active_arrows': [{'from': 'BLDR', 'to': 'CRITIC'}],
        'duration_ms': 2000,
    },
    {
        'id': 'builder_reads_feature',
        'scene': 'Builder Reads Feature',
        'caption': 'Builder reads feature spec and begins implementation',
        'highlight': {'BLDR': 'active', 'FEAT': 'active'},
        'active_arrows': [{'from': 'BLDR', 'to': 'FEAT'}],
        'duration_ms': 2000,
    },
    {
        'id': 'builder_marks_ready',
        'scene': 'Builder Marks Ready',
        'caption': 'Builder marks feature [Ready for Verification]',
        'highlight': {'BLDR': 'active', 'FEAT': 'active'},
        'active_arrows': [{'from': 'BLDR', 'to': 'FEAT'}],
        'duration_ms': 2000,
    },
    {
        'id': 'critic_flags_qa',
        'scene': 'Critic Flags QA',
        'caption': 'Critic flags the feature for QA verification',
        'highlight': {'CRITIC': 'active', 'FEAT': 'active'},
        'active_arrows': [{'from': 'CRITIC', 'to': 'FEAT'}],
        'duration_ms': 2000,
    },
    {
        'id': 'qa_reads_critic',
        'scene': 'QA Reads Critic',
        'caption': 'QA reads Critic action items',
        'highlight': {'QA': 'active', 'CRITIC': 'active'},
        'active_arrows': [{'from': 'QA', 'to': 'CRITIC'}],
        'duration_ms': 2000,
    },
    {
        'id': 'qa_reads_scenarios',
        'scene': 'QA Reads Scenarios',
        'caption': 'QA executes manual scenarios from the feature spec',
        'highlight': {'QA': 'active', 'FEAT': 'active'},
        'active_arrows': [{'from': 'QA', 'to': 'FEAT'}],
        'duration_ms': 2000,
    },
    {
        'id': 'qa_records_bug',
        'scene': 'QA Records Bug',
        'caption': 'QA records a [BUG] discovery in the feature spec',
        'highlight': {'QA': 'active', 'FEAT': 'warning'},
        'active_arrows': [{'from': 'QA', 'to': 'FEAT'}],
        'duration_ms': 2000,
    },
    {
        'id': 'arch_revises_spec',
        'scene': 'Architect Revises Spec',
        'caption': 'Architect revises the spec to address the discovery',
        'highlight': {'ARCH': 'active', 'FEAT': 'active'},
        'active_arrows': [{'from': 'ARCH', 'to': 'FEAT'}],
        'duration_ms': 2000,
    },
    {
        'id': 'builder_reimplements',
        'scene': 'Builder Reimplements',
        'caption': 'Builder re-implements to match the updated spec',
        'highlight': {'BLDR': 'active', 'FEAT': 'active'},
        'active_arrows': [{'from': 'BLDR', 'to': 'FEAT'}],
        'duration_ms': 2000,
    },
    {
        'id': 'qa_verifies_clean',
        'scene': 'QA Verifies Clean',
        'caption': 'QA verifies all scenarios pass \u2014 status: CLEAN',
        'highlight': {'QA': 'active', 'FEAT': 'success'},
        'active_arrows': [{'from': 'QA', 'to': 'FEAT'}],
        'duration_ms': 2000,
    },
    {
        'id': 'release_ready',
        'scene': 'Release Ready',
        'caption': 'Critic signals all features CLEAN \u2014 ready for release!',
        'highlight': {
            'CRITIC': 'success', 'ARCH': 'success',
            'BLDR': 'success', 'QA': 'success', 'FEAT': 'success',
        },
        'active_arrows': [],
        'duration_ms': 3000,
    },
]


# --- Dependency checks ---

def check_python_version():
    if sys.version_info < (3, 8):
        print(
            f"ERROR: Python 3.8+ required, got {sys.version}",
            file=sys.stderr,
        )
        sys.exit(1)


def check_mmdc():
    if shutil.which('mmdc') is None:
        print(
            "ERROR: mmdc (Mermaid CLI) not found on PATH.\n"
            "Install it with: npm install -g @mermaid-js/mermaid-cli",
            file=sys.stderr,
        )
        sys.exit(1)


def _has_imagemagick():
    return shutil.which('magick') is not None or shutil.which('convert') is not None


def check_imagemagick():
    if _has_imagemagick():
        return

    system = platform.system()
    if system == 'Darwin':
        print("ImageMagick not found. Installing via Homebrew...")
        result = subprocess.run(
            ['brew', 'install', 'imagemagick'],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(
                f"ERROR: Failed to install ImageMagick via brew:\n{result.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)
    elif os.path.exists('/etc/debian_version') or shutil.which('apt-get') is not None:
        print("ImageMagick not found. Installing via apt-get...")
        result = subprocess.run(
            ['apt-get', 'install', '-y', 'imagemagick'],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(
                f"ERROR: Failed to install ImageMagick via apt-get:\n{result.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print(
            f"ERROR: ImageMagick not found and unsupported platform '{system}'.\n"
            "Please install ImageMagick manually.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not _has_imagemagick():
        print(
            "ERROR: ImageMagick still not found after installation attempt.",
            file=sys.stderr,
        )
        sys.exit(1)


# --- Rendering helpers ---

def _convert_cmd():
    """Return the ImageMagick convert command prefix."""
    if shutil.which('magick') is not None:
        return ['magick']
    return ['convert']


def detect_inter_font():
    """Detect if Inter font is available in ImageMagick."""
    cmd = _convert_cmd()
    try:
        result = subprocess.run(
            cmd + ['-list', 'font'],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            if 'inter' in line.lower():
                return 'Inter'
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return 'sans-serif'


def build_frame_mermaid(frame):
    """Build the complete Mermaid diagram string for a single frame."""
    lines = [MERMAID_BASE]

    used_classes = set(frame['highlight'].values())
    for cls in sorted(used_classes):
        color = CLASS_COLORS[cls]
        lines.append(f"    classDef {cls} fill:{color},stroke:{color},color:#0B131A")

    for node_id, cls in frame['highlight'].items():
        lines.append(f"    class {node_id} {cls}")

    for arrow in frame['active_arrows']:
        key = (arrow['from'], arrow['to'])
        if key in EDGE_INDEX:
            idx = EDGE_INDEX[key]
            lines.append(f"    linkStyle {idx} stroke:#38BDF8,stroke-width:2px")

    return '\n'.join(lines) + '\n'


def render_frame_png(mermaid_str, output_path, tmpdir):
    """Render a Mermaid diagram to PNG via mmdc, then resize to exact dimensions."""
    mmd_path = os.path.join(tmpdir, 'frame.mmd')
    with open(mmd_path, 'w') as f:
        f.write(mermaid_str)

    raw_path = output_path + '.raw.png'
    result = subprocess.run(
        ['mmdc', '-i', mmd_path, '-o', raw_path,
         '-w', str(DIAGRAM_WIDTH), '-H', str(DIAGRAM_HEIGHT),
         '-b', 'transparent', '--scale', '1'],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"mmdc failed: {result.stderr}")

    # Resize to exact canvas dimensions (mmdc may produce different sizes
    # due to DPI scaling or diagram content bounds)
    cmd = _convert_cmd()
    subprocess.run(
        cmd + [
            raw_path,
            '-resize', f'{DIAGRAM_WIDTH}x{DIAGRAM_HEIGHT}!',
            '-background', '#0B131A',
            '-alpha', 'remove',
            '-alpha', 'off',
            output_path,
        ],
        capture_output=True, text=True, timeout=10,
        check=True,
    )


def create_caption_strip(text, output_path, font_name):
    """Create an 800x40px caption strip with centered text."""
    cmd = _convert_cmd()
    subprocess.run(
        cmd + [
            '-size', f'{DIAGRAM_WIDTH}x{CAPTION_HEIGHT}',
            f'xc:{CAPTION_BG}',
            '-font', font_name,
            '-pointsize', '16',
            '-fill', CAPTION_TEXT,
            '-gravity', 'Center',
            '-annotate', '+0+0', text,
            output_path,
        ],
        capture_output=True, text=True, timeout=10,
        check=True,
    )


def composite_frame(diagram_png, caption_png, output_path):
    """Composite diagram (800x460) + caption (800x40) into a single 800x500 frame."""
    cmd = _convert_cmd()
    canvas_h = DIAGRAM_HEIGHT + CAPTION_HEIGHT
    subprocess.run(
        cmd + [
            diagram_png, caption_png,
            '-append',
            output_path,
        ],
        capture_output=True, text=True, timeout=10,
        check=True,
    )
    # Verify final dimensions and fill any remaining transparency
    subprocess.run(
        cmd + [
            output_path,
            '-resize', f'{DIAGRAM_WIDTH}x{canvas_h}!',
            '-background', '#0B131A',
            '-alpha', 'remove',
            '-alpha', 'off',
            output_path,
        ],
        capture_output=True, text=True, timeout=10,
        check=True,
    )


def assemble_gif(frame_paths_with_delays, output_path):
    """Assemble individual frames into an animated GIF."""
    cmd = _convert_cmd()
    args = list(cmd)
    for fpath, delay_cs in frame_paths_with_delays:
        args.extend(['-delay', str(delay_cs), fpath])
    args.extend(['-loop', '0', output_path])

    subprocess.run(args, capture_output=True, text=True, timeout=120, check=True)


# --- README embedding ---

def update_readme(readme_path=None):
    """Insert the GIF reference into README.md if absent (idempotent).

    Returns:
        str: 'inserted', 'already_present', or 'no_heading'
    """
    path = readme_path or README_PATH
    if not os.path.exists(path):
        print("WARNING: README.md not found, skipping README update.", file=sys.stderr)
        return 'no_heading'

    with open(path, 'r') as f:
        content = f.read()

    if IMAGE_REF in content:
        return 'already_present'

    heading = '## How It Works'
    if heading not in content:
        print(
            "WARNING: No '## How It Works' heading in README.md, skipping update.",
            file=sys.stderr,
        )
        return 'no_heading'

    lines = content.split('\n')
    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if not inserted and line.strip() == heading:
            new_lines.append('')
            new_lines.append(IMAGE_REF)
            inserted = True

    with open(path, 'w') as f:
        f.write('\n'.join(new_lines))

    return 'inserted'


# --- Main pipeline ---

def generate():
    """Main generation pipeline."""
    check_python_version()
    check_mmdc()
    check_imagemagick()

    font_name = detect_inter_font()
    tmpdir = tempfile.mkdtemp(prefix='purlin_anim_')

    try:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

        frame_data = []
        for i, frame in enumerate(FRAMES):
            print(f"  Rendering frame {i + 1}/{len(FRAMES)}: {frame['scene']}...")

            mmd_str = build_frame_mermaid(frame)
            diagram_png = os.path.join(tmpdir, f'diagram_{i:02d}.png')
            render_frame_png(mmd_str, diagram_png, tmpdir)

            caption_png = os.path.join(tmpdir, f'caption_{i:02d}.png')
            create_caption_strip(frame['caption'], caption_png, font_name)

            frame_png = os.path.join(tmpdir, f'frame_{i:02d}.png')
            composite_frame(diagram_png, caption_png, frame_png)

            delay_cs = frame['duration_ms'] // 10
            frame_data.append((frame_png, delay_cs))

        print("  Assembling animated GIF...")
        assemble_gif(frame_data, OUTPUT_PATH)

        result = update_readme()
        if result == 'inserted':
            print("  README.md updated with animation reference.")
        elif result == 'already_present':
            print("  README.md already contains animation reference.")
        else:
            print("  README.md update skipped (no heading found).")

        print(f"  Done: {OUTPUT_PATH}")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == '__main__':
    generate()
