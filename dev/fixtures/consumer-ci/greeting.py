"""The consumer project's one module: a greeting and the host's platform tag."""

import sys


def greet(name):
    """`Hello, <name>!`, and `Hello, world!` when the name is empty."""
    return 'Hello, {}!'.format(name or 'world')


def platform_tag():
    """`sys.platform`: `linux` on an Ubuntu runner, `darwin` on a Mac."""
    return sys.platform
