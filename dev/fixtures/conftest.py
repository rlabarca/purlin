"""Keep the consumer fixture out of this repository's own pytest session.

`dev/fixtures/consumer-ci/` is a complete consumer project, so it carries the
`conftest.py` `purlin:init` writes, which names the proof plugin in
`pytest_plugins`. That file is correct where it lives, at the root of its own
project, and pytest refuses it below the root of this one. The fixture's tests
are run by `dev/test_consumer_ci.py`, in a session of their own.
"""

collect_ignore = ['consumer-ci']
