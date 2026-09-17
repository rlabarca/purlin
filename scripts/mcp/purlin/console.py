"""What every command-line entry point does to its own output streams.

Purlin prints `→`, `▶`, `▼` and `─`. A Windows console hands Python cp1252,
which cannot encode any of them, so the first status table a run prints ends
the process with `UnicodeEncodeError: 'charmap' codec can't encode characters`
and no output at all. Reconfiguring the two streams to UTF-8 is the whole fix,
and it belongs in one place because eight entry points need it.

`line_buffering` is the second half of the same problem. Python block-buffers
stdout when it is not a terminal, so a hosted runner's log stays empty until
the buffer fills or the process exits. A run that is killed first prints
nothing at all and a reader cannot tell how far it got. A long-running entry
point asks for line buffering so its progress reaches the log as it happens.
"""

import sys


def force_utf8_stdio(line_buffering=False):
    """Reconfigure stdout and stderr to UTF-8, optionally line-buffered.

    Every stream that cannot be reconfigured is left alone: a caller that
    replaced `sys.stdout` with a plain object still works, and so does a
    Python old enough to lack `reconfigure` (3.6). Nothing here raises.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            continue
        if line_buffering:
            try:
                reconfigure(line_buffering=True)
            except (AttributeError, ValueError, OSError):
                continue
