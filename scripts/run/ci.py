"""What a CI run may speak for: the project root the job checked out, and
nothing else.

A run branch run commits its evidence through the git host's API, and that
is the whole of what CI publishes. It posts no comment and uploads no
artifact: the one run this release starts is a remote run, whose evidence
`purlin:test --remote` pulls home. There is no pull request run to comment on.

A run refuses a project that is not the project root the job checked out. A
test suite that drives a run over a fixture project inherits the runner's
whole environment and token, so without that check every fixture would commit
its own evidence to the real repository. `is_the_checkout` is the one question
asked, and `scripts/run/host.py` asks it before every API commit.
"""

import os

# What each git host calls the directory the job checked the repository out
# into. A run against any other directory is a run against something else.
_CHECKOUT_VARIABLES = ('GITHUB_WORKSPACE', 'BUILD_SOURCESDIRECTORY')


def is_the_checkout(project_root):
    """True when `project_root` is the directory this job checked out.

    Off a runner neither variable is set and every project is its own,
    so the answer is True and nothing changes for a person running an audit
    on their own machine. On a runner the answer is False for a temporary
    fixture project, which is what stops a test suite from speaking for the
    job it happens to be running inside.
    """
    for variable in _CHECKOUT_VARIABLES:
        checkout = (os.environ.get(variable) or '').strip()
        if not checkout:
            continue
        try:
            return (os.path.realpath(project_root)
                    == os.path.realpath(checkout))
        except (OSError, ValueError):
            return False
    return True
