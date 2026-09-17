"""The consumer project's one module: a greeting and the host's own name."""

import sys


def greet(name):
    """`Hello, <name>!`, and `Hello, world!` when the name is empty."""
    return 'Hello, {}!'.format(name or 'world')


def os_tag():
    """What the host calls itself: `linux` on an Ubuntu runner, `darwin` on a Mac."""
    return sys.platform
