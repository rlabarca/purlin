#!/usr/bin/env python3
"""GitHub Wiki sync utility functions for Purlin docs sync.

Provides utility functions used by the sync_docs_to_github_wiki release
step. Similar in role to dev/confluence_upload_images.py for the
Confluence sync step.

These functions handle:
- Wiki repo URL derivation from GitHub remote URLs
- Wiki page name derivation from markdown filenames
- Purlin sync marker detection and extraction
- Relative markdown link to wiki link conversion
- Sidebar navigation content generation
"""
import re


def derive_wiki_repo_url(remote_url):
    """Derive wiki repo URL from a GitHub remote URL.

    Replaces .git with .wiki.git at the end.
    Example: 'git@github.com:rlabarca/purlin.git' -> 'git@github.com:rlabarca/purlin.wiki.git'
    Example: 'https://github.com/rlabarca/purlin.git' -> 'https://github.com/rlabarca/purlin.wiki.git'
    If URL doesn't end in .git, append .wiki.git.
    """
    if remote_url.endswith('.git'):
        return remote_url[:-4] + '.wiki.git'
    return remote_url + '.wiki.git'


def derive_wiki_page_name(filename):
    """Derive wiki page name from a markdown filename.

    Remove .md extension, title-case each hyphen-separated word,
    rejoin with hyphens, re-add .md extension.
    Example: 'testing-workflow-guide.md' -> 'Testing-Workflow-Guide.md'
    Example: 'overview.md' -> 'Overview.md'
    """
    stem = filename
    if stem.endswith('.md'):
        stem = stem[:-3]
    parts = stem.split('-')
    title_parts = [p.capitalize() for p in parts]
    return '-'.join(title_parts) + '.md'


def has_purlin_sync_marker(content):
    """Check if markdown content has a purlin-sync marker.

    Looks for <!-- purlin-sync: ... --> at the end of the content.
    Returns True if found, False otherwise.
    """
    stripped = content.rstrip()
    return bool(re.search(r'<!--\s*purlin-sync:\s*.+?\s*-->$', stripped))


def extract_purlin_sync_source(content):
    """Extract the source path from a purlin-sync marker.

    Returns the source path string, or None if no marker found.
    Example: content ending with '<!-- purlin-sync: testing-workflow-guide.md -->'
    Returns: 'testing-workflow-guide.md'
    """
    stripped = content.rstrip()
    match = re.search(r'<!--\s*purlin-sync:\s*(.+?)\s*-->$', stripped)
    if match:
        return match.group(1)
    return None


def convert_links_to_wiki(markdown_content):
    """Convert relative markdown links to wiki links.

    [Title](filename.md) -> [[Page-Name]]
    where Page-Name uses the same derivation as derive_wiki_page_name
    but without the .md extension.
    Example: '[Testing Guide](testing-workflow-guide.md)' -> '[[Testing-Workflow-Guide]]'
    """
    def _replace_link(match):
        filename = match.group(2)
        if not filename.endswith('.md'):
            return match.group(0)
        page_name = derive_wiki_page_name(filename)
        if page_name.endswith('.md'):
            page_name = page_name[:-3]
        return f'[[{page_name}]]'

    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _replace_link, markdown_content)


def generate_sidebar_content(page_names):
    """Generate _Sidebar.md content from a list of page names.

    Returns markdown with 'Purlin Docs' heading and wiki links for each page.
    page_names: list of strings like 'Testing-Workflow-Guide'
    """
    lines = ['# Purlin Docs', '']
    for name in page_names:
        lines.append(f'* [[{name}]]')
    lines.append('')
    return '\n'.join(lines)
