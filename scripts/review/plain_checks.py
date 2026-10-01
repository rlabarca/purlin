"""The heuristic spot tests: what a test's own source shows, with no model.

A stub from the base commit of `dev/plans/d115-plan.md`: it finds nothing
until the lane `spot` fills it.
"""

CHECKS = ('The test checks nothing', 'The check cannot fail', 'The test swallows the error',
          'The test checks the code against itself', 'The test replaces what it is testing',
          'The test never checks the result the proof expects')
NOT_READ = '%s is not read in %s tests.'                 # check, 'shell'


def check(project_root, feature, proof, test):
    """[(check, finding)] for one tied test, from its source and the proof's words.
    `proof` is {'id', 'text'}; `test` is {'file', 'name', 'source'}. A check the test's
    language cannot be read for is given as (check, None)."""
    return []
