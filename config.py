"""Settings helpers for MarkdownPreviewEnhanced."""
import os

import sublime

_SETTINGS_FILE = "MarkdownPreviewEnhanced.sublime-settings"
_DEFAULT_OUT = os.path.expanduser("~/Downloads/MarkdownPreviewEnhanced")


def settings():
    return sublime.load_settings(_SETTINGS_FILE)


def get(key, default=None):
    return settings().get(key, default)


def output_dir():
    """Return the preview/export output directory (created if needed)."""
    raw = get("output_dir", "") or ""
    raw = str(raw).strip()
    if not raw:
        # Prefer Sublime cache when available; fall back to Downloads.
        try:
            base = sublime.cache_path()
            path = os.path.join(base, "MarkdownPreviewEnhanced")
        except Exception:
            path = _DEFAULT_OUT
    else:
        path = os.path.expanduser(raw)
    os.makedirs(path, exist_ok=True)
    return path


def preview_path():
    return os.path.join(output_dir(), "preview.html")


def debug_log_path():
    return os.path.join(output_dir(), "debug.log")


def last_html_path():
    return os.path.join(output_dir(), "last_html.html")


def media_cache_dir():
    path = os.path.join(output_dir(), "media")
    os.makedirs(path, exist_ok=True)
    return path
