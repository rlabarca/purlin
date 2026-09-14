"""What a CI run publishes: the pull request comment and the dashboard artifact.

A CI run's verify writes the record; these two functions are how anyone else
sees it. The comment carries the same seven-state rollup `purlin:status`
prints, so a reviewer reads one thing whether they are on the pull request or
in a checkout. The dashboard is copied into the runner's own temporary
directory, which is the one the workflow's upload step reads, so anyone with
repository access opens it from the run and nothing has to be provisioned.

Both return False, or an empty path, with a printed reason when the run is not
on a git host: a developer running verify locally is not an error.
"""

import json
import os
import shutil
import sys
import urllib.request

_RUN_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(_RUN_DIR))
_MCP_DIR = os.path.join(PLUGIN_ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

DASHBOARD_PAGE = os.path.join('scripts', 'report', 'purlin-report.html')
DATA_FILE = os.path.join('.purlin', 'report-data.js')
ARTIFACT_NAME = 'purlin-dashboard'

_GITHUB_API = 'https://api.github.com'


def post_pr_comment(project_root, text):
    """Post `text` as a comment on the pull request this run belongs to.

    True when the comment was posted. False, with a printed reason, when the
    run is not a pull request, the token is missing, or the git host refused.
    """
    host = _host()
    if host == 'azure':
        return _post_azure(text)
    if host == 'github':
        return _post_github(text)
    print('Not running on a git host, so no comment was posted.')
    return False


def _post_github(text):
    repo = os.environ.get('GITHUB_REPOSITORY') or ''
    token = os.environ.get('GITHUB_TOKEN') or ''
    number = _pr_number()
    if not repo or not token:
        print('No GITHUB_REPOSITORY and GITHUB_TOKEN, so no comment was '
              'posted.')
        return False
    if not number:
        print('This run is not a pull request, so no comment was posted.')
        return False
    url = '%s/repos/%s/issues/%s/comments' % (_GITHUB_API, repo, number)
    return _post(url, {'body': text},
                 {'Authorization': 'Bearer %s' % token,
                  'Accept': 'application/vnd.github+json'})


def _post_azure(text):
    token = os.environ.get('SYSTEM_ACCESSTOKEN') or ''
    collection = (os.environ.get('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI')
                  or '').rstrip('/')
    project = os.environ.get('SYSTEM_TEAMPROJECT') or ''
    repo = os.environ.get('BUILD_REPOSITORY_ID') or ''
    number = os.environ.get('SYSTEM_PULLREQUEST_PULLREQUESTID') or ''
    if not (token and collection and project and repo and number):
        print('This run is not an Azure DevOps pull request with a token, so '
              'no comment was posted.')
        return False
    url = ('%s/%s/_apis/git/repositories/%s/pullRequests/%s/threads'
           '?api-version=7.0' % (collection, project, repo, number))
    body = {'comments': [{'parentCommentId': 0, 'content': text,
                          'commentType': 'text'}],
            'status': 'closed'}
    return _post(url, body, {'Authorization': 'Bearer %s' % token})


def _post(url, body, headers):
    headers = dict(headers)
    headers.setdefault('Content-Type', 'application/json')
    headers.setdefault('User-Agent', 'purlin')
    request = urllib.request.Request(
        url, data=json.dumps(body).encode('utf-8'), headers=headers,
        method='POST')
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except Exception as error:  # the git host refused; say so and carry on
        print('The comment was not posted: %s' % error)
        return False
    response.close()
    return True


def _pr_number():
    """The pull request number this run belongs to, or ''."""
    number = (os.environ.get('GITHUB_PR_NUMBER') or '').strip()
    if number:
        return number
    event = os.environ.get('GITHUB_EVENT_PATH')
    if not event or not os.path.isfile(event):
        return ''
    try:
        with open(event, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError, UnicodeDecodeError):
        return ''
    return str((data.get('pull_request') or {}).get('number') or '')


def _host():
    if os.environ.get('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI'):
        return 'azure'
    if os.environ.get('GITHUB_REPOSITORY'):
        return 'github'
    return ''


def publish_dir(project_root):
    """The directory the dashboard is published to, which the run uploads.

    The upload step names a temporary directory the runner owns, so the
    directory has to be the one that runner's variable gives:
    `$RUNNER_TEMP/purlin-dashboard` on GitHub, `$AGENT_TEMPDIRECTORY/
    purlin-dashboard` on Azure DevOps. Off a runner neither variable is set
    and the dashboard goes to `.purlin/runtime/report` in the project, where
    nothing uploads it and it is read from disk.
    """
    for variable in ('RUNNER_TEMP', 'AGENT_TEMPDIRECTORY'):
        temp = os.environ.get(variable)
        if temp:
            return os.path.join(temp, ARTIFACT_NAME)
    return os.path.join(project_root, '.purlin', 'runtime', 'report')


def publish_dashboard(project_root, out_dir=None):
    """Copy the dashboard page and its data into `out_dir`, return that path.

    The workflow uploads the directory as the `purlin-dashboard` artifact.
    The page is one HTML file that opens from disk, so the artifact is the
    page, its data and nothing else. With no `out_dir` the directory is the
    one `publish_dir` names, which is the one the upload step reads.
    """
    if out_dir is None:
        out_dir = publish_dir(project_root)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    page = os.path.join(PLUGIN_ROOT, DASHBOARD_PAGE)
    if not os.path.isfile(page):
        page = os.path.join(project_root, 'purlin-report.html')
    if os.path.isfile(page):
        shutil.copyfile(page, os.path.join(out_dir, 'purlin-report.html'))
    else:
        print('No dashboard page was found, so the artifact carries the data '
              'alone.')

    data = os.path.join(project_root, DATA_FILE)
    if os.path.isfile(data):
        target = os.path.join(out_dir, '.purlin')
        if not os.path.isdir(target):
            os.makedirs(target)
        shutil.copyfile(data, os.path.join(target, 'report-data.js'))
    else:
        print('No dashboard data was found at %s.' % DATA_FILE)
    return out_dir
