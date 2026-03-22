#!/usr/bin/env python3
"""Confluence image attachment uploader for Purlin docs sync.

Uploads image files to Confluence pages via REST API v1. Used by the
sync_docs_to_confluence release step for images that cannot be handled
by the Atlassian MCP server.

Usage:
    python3 dev/confluence_upload_images.py --page-id <id> --files img1.png img2.png

Output: JSON mapping of local paths to Confluence attachment URLs on stdout.
"""
import argparse
import base64
import json
import os
import re
import sys


def load_credentials(creds_path=None):
    """Load Confluence API credentials from the standard path.

    Returns dict with keys: email, token, base_url.
    Raises FileNotFoundError if the credentials file is missing.
    Raises ValueError if required fields are absent.
    """
    if creds_path is None:
        project_root = os.environ.get('PURLIN_PROJECT_ROOT')
        if not project_root:
            d = os.path.dirname(os.path.abspath(__file__))
            while d != os.path.dirname(d):
                if os.path.isdir(os.path.join(d, '.purlin')):
                    project_root = d
                    break
                d = os.path.dirname(d)
        if not project_root:
            raise FileNotFoundError(
                "Cannot find project root (.purlin/ directory)")
        creds_path = os.path.join(
            project_root, '.purlin', 'runtime',
            'confluence', 'credentials.json')

    with open(creds_path) as f:
        creds = json.load(f)

    required = ('email', 'token', 'base_url')
    missing = [k for k in required if k not in creds]
    if missing:
        raise ValueError(
            f"Missing credential fields: {', '.join(missing)}")

    return creds


def get_auth_header(creds):
    """Build Basic auth header value from credentials."""
    raw = f"{creds['email']}:{creds['token']}".encode()
    return f"Basic {base64.b64encode(raw).decode()}"


def get_existing_attachments(base_url, page_id, auth_header):
    """Fetch existing attachments for a page.

    Returns dict mapping filename to {'size': int, 'url': str}.
    """
    url = (f"{base_url}/wiki/rest/api/content/{page_id}"
           f"/child/attachment")

    try:
        import requests
        resp = requests.get(url, headers={
            'Authorization': auth_header,
            'Accept': 'application/json'
        })
        resp.raise_for_status()
        data = resp.json()
    except ImportError:
        import urllib.request
        req = urllib.request.Request(url, headers={
            'Authorization': auth_header,
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())

    attachments = {}
    for att in data.get('results', []):
        title = att.get('title', '')
        size = att.get('extensions', {}).get('fileSize', -1)
        dl_link = att.get('_links', {}).get('download', '')
        if dl_link:
            att_url = f"{base_url}/wiki{dl_link}"
        else:
            att_url = (f"{base_url}/wiki/download/attachments"
                       f"/{page_id}/{title}")
        attachments[title] = {'size': int(size), 'url': att_url}

    return attachments


def upload_attachment(base_url, page_id, file_path, auth_header):
    """Upload a single file as an attachment to a Confluence page.

    Returns the attachment download URL.
    """
    url = (f"{base_url}/wiki/rest/api/content/{page_id}"
           f"/child/attachment")
    filename = os.path.basename(file_path)

    try:
        import requests
        with open(file_path, 'rb') as f:
            resp = requests.post(
                url,
                headers={
                    'Authorization': auth_header,
                    'X-Atlassian-Token': 'no-check'
                },
                files={'file': (filename, f)}
            )
        resp.raise_for_status()
        data = resp.json()
    except ImportError:
        import urllib.request
        boundary = '----PurlinUploadBoundary'
        with open(file_path, 'rb') as f:
            file_data = f.read()
        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="file"; '
            f'filename="{filename}"\r\n'
            f'Content-Type: application/octet-stream\r\n\r\n'
        ).encode() + file_data + f'\r\n--{boundary}--\r\n'.encode()

        req = urllib.request.Request(url, data=body, headers={
            'Authorization': auth_header,
            'X-Atlassian-Token': 'no-check',
            'Content-Type':
                f'multipart/form-data; boundary={boundary}'
        })
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())

    results = data.get('results', [data]) if isinstance(data, dict) \
        else data
    if results:
        result = results[0] if isinstance(results, list) else results
        dl_link = result.get('_links', {}).get('download', '')
        if dl_link:
            return f"{base_url}/wiki{dl_link}"

    return (f"{base_url}/wiki/download/attachments"
            f"/{page_id}/{filename}")


def should_upload(file_path, existing_attachments):
    """Determine if a file needs uploading based on size comparison.

    Returns True if the file is new or its size differs from the
    existing attachment.
    """
    filename = os.path.basename(file_path)
    if filename not in existing_attachments:
        return True
    local_size = os.path.getsize(file_path)
    remote_size = existing_attachments[filename]['size']
    return local_size != remote_size


def derive_page_title(filename):
    """Derive a Confluence page title from a markdown filename.

    Removes .md extension, replaces hyphens with spaces, title-cases.
    Example: 'testing-workflow-guide.md' -> 'Testing Workflow Guide'
    """
    stem = filename
    if stem.endswith('.md'):
        stem = stem[:-3]
    return stem.replace('-', ' ').title()


def derive_section_title(subdirectory):
    """Derive a Confluence section page title from a subdirectory name.

    Special case: 'reference' maps to 'Technical Reference'.
    All others: title-case the directory name.
    """
    if subdirectory.lower() == 'reference':
        return 'Technical Reference'
    return subdirectory.title()


def scan_image_references(markdown_content):
    """Scan markdown content for image references.

    Returns list of (alt_text, image_path) tuples for all
    ![alt](path) patterns found.
    """
    return re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', markdown_content)


def replace_image_paths(markdown_content, url_mapping):
    """Replace local image paths with Confluence URLs in markdown.

    url_mapping: dict of {local_path: confluence_url}
    Returns the updated markdown content.
    """
    result = markdown_content
    for local_path, confluence_url in url_mapping.items():
        result = result.replace(local_path, confluence_url)
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Upload images to Confluence page attachments')
    parser.add_argument(
        '--page-id', required=True,
        help='Confluence page ID to attach images to')
    parser.add_argument(
        '--files', nargs='+', required=True,
        help='Image file paths to upload')
    parser.add_argument(
        '--credentials', default=None,
        help='Path to credentials.json (optional override)')
    args = parser.parse_args()

    try:
        creds = load_credentials(args.credentials)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        sys.exit(1)

    auth_header = get_auth_header(creds)
    base_url = creds['base_url'].rstrip('/')

    existing = get_existing_attachments(
        base_url, args.page_id, auth_header)

    url_mapping = {}
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} does not exist, skipping",
                  file=sys.stderr)
            continue

        filename = os.path.basename(file_path)

        if should_upload(file_path, existing):
            att_url = upload_attachment(
                base_url, args.page_id, file_path, auth_header)
            url_mapping[file_path] = att_url
        else:
            url_mapping[file_path] = existing[filename]['url']

    print(json.dumps(url_mapping))


if __name__ == '__main__':
    main()
