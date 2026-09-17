"""What a CI run publishes: the pull request comment and the dashboard artifact.

A CI run's audit writes the record; these two functions are how anyone else
sees it. The comment carries the same rollup `purlin:status` prints, so a
reader reads one thing whether they are on the pull request or in a
checkout. The dashboard is copied into the runner's own temporary
directory, which is the one the workflow's upload step reads, so anyone with
repository access opens it from the run and nothing has to be provisioned.

Both return False, or an empty path, with a printed reason when the run is not
on a git host: a developer running an audit locally is not an error.

Both also refuse a project that is not the workspace the job checked out. A
test suite that drives an audit over a fixture project inherits the runner's
whole environment, token and pull request included, so without that check
every fixture posts its own table to the real pull request and overwrites the
job's artifact directory. `is_the_workspace` is the one question both ask.
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

# What each git host calls the directory the job checked the repository out
# into. A run against any other directory is a run against something else.
_WORKSPACE_VARIABLES = ('GITHUB_WORKSPACE', 'BUILD_SOURCESDIRECTORY')


def is_the_workspace(project_root):
    """True when `project_root` is the directory this job checked out.

    Off a runner no workspace variable is set and every project is its own,
    so the answer is True and nothing changes for a person running an audit
    on their own machine. On a runner the answer is False for a temporary
    fixture project, which is what stops a test suite from speaking for the
    job it happens to be running inside.
    """
    for variable in _WORKSPACE_VARIABLES:
        workspace = (os.environ.get(variable) or '').strip()
        if not workspace:
            continue
        try:
            return (os.path.realpath(project_root)
                    == os.path.realpath(workspace))
        except (OSError, ValueError):
            return False
    return True


def post_pr_comment(project_root, text):
    """Post `text` as a comment on the pull request this run belongs to.

    True when the comment was posted. False, with a printed reason, when the
    project is not the job's workspace, the run is not a pull request, the
    token is missing, or the git host refused.
    """
    if not is_the_workspace(project_root):
        print('%s is not the workspace this job checked out, so no comment '
              'was posted.' % project_root)
        return False
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

    A project that is not the job's workspace goes to its own project
    directory too, whatever the runner's variables say. A fixture project
    that wrote to the runner's directory would replace the job's own page and
    logs with its own, and the artifact the job uploads would describe a
    temporary project nobody has.
    """
    for variable in ('RUNNER_TEMP', 'AGENT_TEMPDIRECTORY'):
        temp = os.environ.get(variable)
        if temp and is_the_workspace(project_root):
            # The workflow names this directory with a forward slash, and the
            # upload step has to read the directory the run wrote to. On a
            # Windows runner the variable holds a backslash path, so joining
            # with the local separator would spell it one way here and the
            # other way there; Windows reads either separator, so both sides
            # use the one the workflow can write.
            return '%s/%s' % (temp.rstrip('/\\'), ARTIFACT_NAME)
    return os.path.join(project_root, '.purlin', 'runtime', 'report')


def publish_dashboard(project_root, out_dir=None, logs=None):
    """Copy the dashboard page, its data and the arm logs into `out_dir`.

    Returns that path. The workflow uploads the directory as the
    `purlin-dashboard-<runner>` artifact, one name per matrix job: two jobs
    uploading one name leave only the job that finished last, and the other
    job's page and logs are gone. The page is one HTML file that opens from
    disk. With no `out_dir` the directory is the one `publish_dir` names,
    which is the one the upload step reads.

    `logs` maps an arm's framework name to everything that arm printed. Each
    lands at `logs/<arm>.log`, so a job that reports missing evidence is read
    back in full from the artifact rather than from the runner's own disk,
    which the run throws away.
    """
    if out_dir is None:
        out_dir = publish_dir(project_root)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    for arm, text in sorted((logs or {}).items()):
        target = os.path.join(out_dir, 'logs')
        if not os.path.isdir(target):
            os.makedirs(target)
        with open(os.path.join(target, '%s.log' % arm), 'w',
                  encoding='utf-8') as handle:
            handle.write(text if text.endswith('\n') else text + '\n')

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
