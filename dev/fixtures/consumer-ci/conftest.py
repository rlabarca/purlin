# Purlin proof plugin, wired by purlin:init.
#
# `.purlin` is not an importable package name, so the plugin's
# directory goes on sys.path and the plugin is named by module.
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".purlin", "plugins"))

pytest_plugins = ["pytest_purlin"]
