"""The two facts: whether the tests are met, and whether this code is signed.

A stub from the base commit of `dev/plans/d115-plan.md`: it answers `not met`
and `not signed` until the lane `states` fills it.
"""

TESTS_MET = 'met'
TESTS_NOT_MET = 'not met'
SIGNED_AT = 'signed %s at %s'                 # version, sha7 of the tagged commit
SIGNED_SINCE = 'signed %s, %d commits since'  # 'signed 0.1.0, 1 commit since' for one
NOT_SIGNED = 'not signed'


def tests_fact(payload):
    """`met` when no entry of `left` is of a kind in summary.BLOCKING, else `not met`."""
    return TESTS_NOT_MET


def signoff_fact(project_root):
    """{'word','version','commit','since'} for the newest signed/* tag on HEAD or an
    ancestor of it, numbered versions compared as numbers: SIGNED_AT where
    package.only_records_between(tag commit, HEAD), else SIGNED_SINCE with the count of
    commits from the tag to HEAD; word NOT_SIGNED and the rest None where there is none."""
    return {'word': NOT_SIGNED, 'version': None, 'commit': None, 'since': None}
