"""Core internals for MarkdownPreviewEnhanced.

These modules live in a subpackage so that Sublime Text does not load each one
as an independent root-level plugin. Only ``MarkdownPreviewEnhanced.py`` at the
package root defines ``sublime_plugin`` entry points; everything else is imported
through this package via relative imports.
"""

import os

# Absolute path to the MarkdownPreviewEnhanced package root (the directory
# that contains ``assets/`` and this ``mpe_core/`` subpackage). Modules use this
# instead of ``os.path.dirname(__file__)`` because they now live one level deeper.
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
