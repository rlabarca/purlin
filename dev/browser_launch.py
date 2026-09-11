"""Shared Playwright browser launch, with a fallback to an installed Chrome.

`playwright install chromium` downloads a ~150MB browser, which fails on any
machine behind a TLS-inspecting proxy (the Node downloader reports
UNABLE_TO_GET_ISSUER_CERT_LOCALLY) or without network access. Every dashboard
proof then becomes unrunnable, which is how purlin_report's @e2e proofs came to
be committed from one machine and never re-executed anywhere else.

Playwright can drive an already-installed Google Chrome instead, so try the
bundled Chromium first and fall back to the system browser.
"""

_CHANNELS = ('chrome', 'msedge')
_PATHS = (
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
)


def launch_browser(playwright, **kwargs):
    """Launch Chromium, falling back to an installed Chrome/Edge.

    Raises the original bundled-Chromium error if nothing can be launched, so the
    failure still names the missing download rather than a fallback detail.
    """
    import os

    try:
        return playwright.chromium.launch(**kwargs)
    except Exception as bundled_error:
        for channel in _CHANNELS:
            try:
                return playwright.chromium.launch(channel=channel, **kwargs)
            except Exception:
                continue
        for path in _PATHS:
            if os.path.exists(path):
                try:
                    return playwright.chromium.launch(executable_path=path, **kwargs)
                except Exception:
                    continue
        raise bundled_error
