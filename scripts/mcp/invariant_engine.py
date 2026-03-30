"""Core operations for invariant files.

Provides detection, metadata extraction, content hashing, and format
validation for invariant anchor nodes (``i_*`` prefix files).

Consumer-facing, submodule-safe.
"""

import hashlib
import os
import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# All valid anchor type prefixes (including new ops_ and prodbrief_).
ANCHOR_PREFIXES = ('arch_', 'design_', 'policy_', 'ops_', 'prodbrief_')

# Invariant prefix.  Prepended to anchor type prefix: i_arch_*, i_policy_*, etc.
INVARIANT_PREFIX = 'i_'

# Current supported format version.
SUPPORTED_FORMAT_VERSION = '1.1'

# Required metadata fields for ALL invariant files.
_REQUIRED_METADATA = (
    'Format-Version',
    'Invariant',
    'Version',
    'Source',
    'Scope',
)

# Additional required fields for git-sourced invariants.
_GIT_REQUIRED_METADATA = (
    'Source-Path',
    'Source-SHA',
    'Synced-At',
)

# Additional required fields for Figma-sourced invariants.
_FIGMA_REQUIRED_METADATA = (
    'Figma-URL',
    'Synced-At',
)

# Required sections by anchor type prefix (after stripping i_).
# Maps type prefix -> list of section heading regexes.
# Canonical specs: references/invariant_type_{arch,design,policy,ops,prodbrief}.md
_REQUIRED_SECTIONS = {
    'arch_':      [r'##\s+Purpose', r'##\s+\w.*Invariants'],
    'policy_':    [r'##\s+Purpose', r'##\s+\w.*Invariants'],
    'ops_':       [r'##\s+Purpose', r'##\s+\w.*Invariants'],
    'design_':    [r'##\s+Purpose', r'##\s+(?:\w.*Invariants|Figma Source)'],
    'prodbrief_': [r'##\s+Purpose', r'##\s+User Stories', r'##\s+Success Criteria'],
}

# Additional required sections for Figma-sourced design invariants.
_FIGMA_DESIGN_REQUIRED_SECTIONS = [r'##\s+Annotations']

# Early-termination regex for metadata lines.
_METADATA_RE = re.compile(r'^>\s*([A-Za-z][\w-]*):\s*(.*)')


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def is_invariant_node(filename):
    """Check if a filename is an invariant node (``i_`` prefix + valid anchor type).

    Companion files (``*.impl.md``) and discovery sidecars (``*.discoveries.md``)
    are never invariants even if they match the prefix pattern.

    Args:
        filename: Basename of the file (e.g., ``i_arch_api.md``).

    Returns:
        True if the file is an invariant.
    """
    if not filename.startswith(INVARIANT_PREFIX):
        return False
    if filename.endswith('.impl.md') or filename.endswith('.discoveries.md'):
        return False
    rest = filename[len(INVARIANT_PREFIX):]
    return any(rest.startswith(p) for p in ANCHOR_PREFIXES)


def strip_invariant_prefix(filename):
    """Strip the ``i_`` prefix to reveal the anchor type prefix.

    Args:
        filename: Basename like ``i_arch_api.md``.

    Returns:
        The filename without the ``i_`` prefix (e.g., ``arch_api.md``),
        or the original filename if it is not an invariant.
    """
    if is_invariant_node(filename):
        return filename[len(INVARIANT_PREFIX):]
    return filename


def get_anchor_type(filename):
    """Get the anchor type prefix for a filename (invariant or regular anchor).

    Args:
        filename: Basename like ``i_arch_api.md`` or ``arch_api.md``.

    Returns:
        The matching anchor prefix (e.g., ``'arch_'``), or None if not an anchor.
    """
    name = strip_invariant_prefix(filename)
    for prefix in ANCHOR_PREFIXES:
        if name.startswith(prefix):
            return prefix
    return None


def is_anchor_node(filename):
    """Check if a filename is any anchor node (regular or invariant).

    Handles the full prefix set: arch_, design_, policy_, ops_, prodbrief_,
    and their i_* invariant variants.
    """
    return get_anchor_type(filename) is not None


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def extract_metadata(filepath):
    """Extract ``> Key: Value`` metadata from an invariant/anchor file.

    Uses early-termination: stops reading after the first non-metadata,
    non-blank, non-heading line (the body has started).

    Args:
        filepath: Absolute path to the markdown file.

    Returns:
        Dict mapping field names to string values.
    """
    metadata = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                # Skip blank lines and the title heading.
                if not stripped or stripped.startswith('#'):
                    continue
                m = _METADATA_RE.match(stripped)
                if m:
                    key = m.group(1)
                    value = m.group(2).strip().strip('"')
                    metadata[key] = value
                else:
                    # First non-metadata content line — stop.
                    break
    except (IOError, OSError):
        pass
    return metadata


# ---------------------------------------------------------------------------
# Content hashing
# ---------------------------------------------------------------------------

def compute_content_hash(filepath):
    """Compute SHA-256 hash of a file's content.

    Args:
        filepath: Absolute path to the file.

    Returns:
        Hex-encoded SHA-256 string, or None on read failure.
    """
    try:
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    except (IOError, OSError):
        return None


# ---------------------------------------------------------------------------
# Format validation
# ---------------------------------------------------------------------------

def validate_invariant(filepath):
    """Validate an invariant file's format, metadata, and required sections.

    Args:
        filepath: Absolute path to an ``i_*.md`` file.

    Returns:
        List of issue strings.  Empty list means the file is valid.
    """
    filename = os.path.basename(filepath)
    issues = []

    if not is_invariant_node(filename):
        issues.append(f'{filename}: not an invariant file (missing i_ prefix or invalid anchor type)')
        return issues

    metadata = extract_metadata(filepath)

    # Check required metadata fields.
    for field in _REQUIRED_METADATA:
        if field not in metadata:
            issues.append(f'{filename}: missing required metadata > {field}:')

    # Invariant field must be 'true'.
    if metadata.get('Invariant', '').lower() != 'true':
        issues.append(f'{filename}: > Invariant: must be "true"')

    # Scope must be 'global' or 'scoped'.
    scope = metadata.get('Scope', '')
    if scope and scope not in ('global', 'scoped'):
        issues.append(f'{filename}: > Scope: must be "global" or "scoped", got "{scope}"')

    # Format version compatibility.
    fmt_ver = metadata.get('Format-Version', '')
    if fmt_ver:
        try:
            major = int(fmt_ver.split('.')[0])
            supported_major = int(SUPPORTED_FORMAT_VERSION.split('.')[0])
            if major > supported_major:
                issues.append(
                    f'{filename}: Format-Version {fmt_ver} exceeds supported '
                    f'version {SUPPORTED_FORMAT_VERSION}'
                )
        except (ValueError, IndexError):
            issues.append(f'{filename}: invalid Format-Version "{fmt_ver}"')

    # Source-type-specific metadata.
    source = metadata.get('Source', '')
    if source == 'figma':
        for field in _FIGMA_REQUIRED_METADATA:
            if field not in metadata:
                issues.append(f'{filename}: Figma-sourced invariant missing > {field}:')
        # Warn about unsynced Figma invariants.
        version = metadata.get('Version', '')
        if version == 'pending-sync':
            issues.append(
                f'{filename}: Figma invariant not yet synced (Version: pending-sync). '
                f'Run purlin:invariant sync to fetch metadata, design variables, '
                f'and annotations.'
            )
    elif source:
        for field in _GIT_REQUIRED_METADATA:
            if field not in metadata:
                issues.append(f'{filename}: git-sourced invariant missing > {field}:')

    # Required sections by anchor type.
    anchor_type = get_anchor_type(filename)
    if anchor_type and anchor_type in _REQUIRED_SECTIONS:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, OSError):
            issues.append(f'{filename}: could not read file for section validation')
            return issues

        for pattern in _REQUIRED_SECTIONS[anchor_type]:
            if not re.search(pattern, content, re.IGNORECASE):
                issues.append(f'{filename}: missing required section matching /{pattern}/')

        # Figma-sourced design invariants have additional required sections.
        if anchor_type == 'design_' and source == 'figma':
            for pattern in _FIGMA_DESIGN_REQUIRED_SECTIONS:
                if not re.search(pattern, content, re.IGNORECASE):
                    issues.append(f'{filename}: Figma design invariant missing required section matching /{pattern}/')

    return issues
