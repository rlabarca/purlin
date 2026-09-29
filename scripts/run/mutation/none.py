"""No engine: nothing breaks the code, so nothing measures test strength.

This is the answer for a go, shell or sql project, for a project whose config
names no engine, and for an engine that cannot run on this system. Every
feature carries a score of None and an empty `missing`: the selected engine
did not fail to measure, there is none. The reason is a sentence, because it
is printed to a person.
"""

from . import empty_features, result

DEFAULT_REASON = ('no engine breaks go, shell or sql code, so test strength '
                  'is not measured for these rules')


def run(project_root, scope_by_feature, reason=None):
    """The empty answer, with `reason` naming why there is no engine."""
    return result('none', False, reason or DEFAULT_REASON,
                  empty_features(scope_by_feature), '')
