#!/usr/bin/env python3
"""Migrate .claude/commands/pl-*.md to skills/*/SKILL.md with plugin transforms."""

import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMANDS_DIR = os.path.join(PROJECT_ROOT, ".claude", "commands")
SKILLS_DIR = os.path.join(PROJECT_ROOT, "skills")


def derive_skill_name(filename):
    """pl-build.md -> build, pl-update-purlin.md -> update"""
    stem = filename.replace(".md", "").replace("pl-", "", 1)
    # Special case: update-purlin -> update
    if stem == "update-purlin":
        return "update"
    return stem


def extract_description(content):
    """Extract description from the 'Purlin agent: ...' line or first meaningful line."""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("Purlin agent:"):
            desc = line.replace("Purlin agent:", "").strip()
            # Remove trailing period for frontmatter
            desc = desc.rstrip(".")
            # Truncate if too long
            if len(desc) > 120:
                desc = desc[:117] + "..."
            return desc
        if line.startswith("**Purlin mode:"):
            continue
        if line.startswith("**Purlin command:"):
            continue
        if line and not line.startswith("#") and not line.startswith("---") and not line.startswith(">"):
            desc = line.rstrip(".")
            if len(desc) > 120:
                desc = desc[:117] + "..."
            return desc
    return "Purlin skill"


def apply_transforms(content):
    """Apply the four mechanical transforms to skill content."""
    # 1. Cross-reference transform: /pl-<name> -> purlin:<name>
    # Match /pl- followed by word chars and hyphens, but not in file paths
    # Be careful with patterns like `/pl-build.md` (file refs) vs `/pl-build` (skill invocations)
    # We want to transform invocations like `/pl-build`, `/pl-verify feature_name`
    # But NOT file paths like `.claude/commands/pl-build.md`

    # Transform skill invocations: /pl-name (not preceded by / or commands/)
    content = re.sub(
        r'(?<!/commands/)(?<!\w)/pl-([a-z][-a-z]*)',
        lambda m: 'purlin:' + m.group(1),
        content
    )

    # 2. Script path transform: ${TOOLS_ROOT}/ -> ${CLAUDE_PLUGIN_ROOT}/scripts/
    content = content.replace("${TOOLS_ROOT}/", "${CLAUDE_PLUGIN_ROOT}/scripts/")
    content = content.replace("{tools_root}/", "${CLAUDE_PLUGIN_ROOT}/scripts/")
    # Also catch bare TOOLS_ROOT references (variable name mentions)
    content = content.replace('"${TOOLS_ROOT}"', '"${CLAUDE_PLUGIN_ROOT}/scripts"')

    # 3. Reference path transform: instructions/references/ -> ${CLAUDE_PLUGIN_ROOT}/references/
    content = content.replace("instructions/references/", "${CLAUDE_PLUGIN_ROOT}/references/")

    # Also handle backtick-wrapped variants
    content = content.replace("`references/", "`${CLAUDE_PLUGIN_ROOT}/references/")

    # 4. Replace the legacy Path Resolution preamble
    content = re.sub(
        r'## Path Resolution\n\n> See `\$\{CLAUDE_PLUGIN_ROOT\}/references/path_resolution\.md`\. Produces `TOOLS_ROOT`\.',
        '## Path Resolution\n\n> Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/`. References at `${CLAUDE_PLUGIN_ROOT}/references/`.',
        content
    )
    # Also catch the resume variant with trailing text
    content = re.sub(
        r'> See `\$\{CLAUDE_PLUGIN_ROOT\}/references/path_resolution\.md`\. Produces `TOOLS_ROOT`\. This skill reads.*\n',
        '> Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/`. References at `${CLAUDE_PLUGIN_ROOT}/references/`.\n',
        content
    )

    return content


def migrate_skill(filename):
    """Migrate a single skill file."""
    source = os.path.join(COMMANDS_DIR, filename)
    skill_name = derive_skill_name(filename)
    dest_dir = os.path.join(SKILLS_DIR, skill_name)
    dest = os.path.join(dest_dir, "SKILL.md")

    with open(source, "r") as f:
        content = f.read()

    description = extract_description(content)
    transformed = apply_transforms(content)

    # Build the final content with frontmatter
    frontmatter = f"""---
name: {skill_name}
description: {description}
---

"""
    final = frontmatter + transformed

    os.makedirs(dest_dir, exist_ok=True)
    with open(dest, "w") as f:
        f.write(final)

    return skill_name, description


def main():
    if not os.path.isdir(COMMANDS_DIR):
        print(f"ERROR: {COMMANDS_DIR} not found", file=sys.stderr)
        sys.exit(1)

    files = sorted(f for f in os.listdir(COMMANDS_DIR) if f.startswith("pl-") and f.endswith(".md"))
    print(f"Found {len(files)} skill files to migrate\n")

    migrated = []
    for f in files:
        name, desc = migrate_skill(f)
        migrated.append(name)
        print(f"  {f:40s} -> skills/{name}/SKILL.md")

    print(f"\nMigrated {len(migrated)} skills successfully.")
    print(f"\nSkill directories created: {', '.join(migrated)}")


if __name__ == "__main__":
    main()
