"""No engine: nothing breaks the code, so nothing measures test strength.

This is the answer for a shell or sql project, for a project whose config
names no engine, and for a project whose engine is not installed. Every rule
carries `attribution: unavailable` and a score of None, which a caller
displays as `n/a`. The reason is a sentence, because it is printed to a person
who is deciding whether to install the engine.
"""

from . import empty_features, result

DEFAULT_REASON = ('no engine breaks shell or sql code, so test strength is '
                  'not measured for these rules')


def run(project_root, scope_by_feature, tests_by_rule, tier=None, reason=None):
    """The empty answer, with `reason` naming what is missing."""
    features = empty_features(scope_by_feature, tests_by_rule, 'none',
                              'unavailable')
    return result('none', False, reason or DEFAULT_REASON, features, '')
