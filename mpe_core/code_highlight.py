"""Code highlighting helpers.

Pygments is wired in via markdown's codehilite extension, so this module only
provides a helper to locate the bundled highlight stylesheet and a thin wrapper
used by the renderer if codehilite is unavailable.
"""
import os

from . import PACKAGE_ROOT


def highlight_css_path():
    return os.path.join(PACKAGE_ROOT, "assets", "highlight.css")
