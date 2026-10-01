"""The project's name.

A stub from the base commit of `dev/plans/d115-plan.md`: it answers the
folder's name until the lane `states` fills it.
"""

import os


def project_name(project_root):
    """The project's name, read each time and never written. The first found of: `name`
    under `[project]`, then under `[tool.poetry]`, in pyproject.toml; `name` in
    package.json; the first root `*.csproj` file's name without `.csproj`; the last
    segment of `git remote get-url origin` without `.git`; the folder's name."""
    return os.path.basename(os.path.abspath(project_root))
