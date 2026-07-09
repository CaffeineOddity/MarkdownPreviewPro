"""Export rendered markdown to standalone HTML or PDF."""
import os
import subprocess
import tempfile

from .browser import find_chrome_binary
from .html_builder import build_export_html
from .md_renderer import render as render_markdown, rewrite_image_srcs


def export_html(
    text,
    dest_path,
    base_dir=None,
    mermaid_theme="default",
    show_toc=True,
    enable_katex=True,
    custom_css="",
    title="Markdown Export",
    log=None,
):
    log = log or (lambda m: None)
    result = render_markdown(
        text,
        mermaid_theme=mermaid_theme,
        base_dir=base_dir,
        image_mode="file",
        enable_toc=show_toc,
    )
    body = result["body_html"]
    toc = result["toc_html"] if show_toc else ""
    # Prefer absolute file:// images for offline HTML
    if base_dir:
        body = rewrite_image_srcs(body, base_dir, mode="file")

    html = build_export_html(
        body,
        toc_html=toc,
        show_toc=show_toc and bool(toc),
        enable_katex=enable_katex,
        custom_css=custom_css,
        title=title,
    )
    dest_path = os.path.expanduser(dest_path)
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(html)
    log("exported HTML → %s" % dest_path)
    return dest_path, result.get("errors") or []


def export_pdf(
    text,
    dest_path,
    base_dir=None,
    mermaid_theme="default",
    show_toc=False,
    enable_katex=True,
    custom_css="",
    title="Markdown Export",
    log=None,
):
    """Render via headless Chrome/Chromium --print-to-pdf."""
    log = log or (lambda m: None)
    chrome = find_chrome_binary()
    if not chrome:
        raise RuntimeError(
            "No Chrome/Chromium/Edge found for PDF export. "
            "Install Chrome or export HTML and print manually."
        )

    # Write a temp HTML then print.
    fd, tmp_html = tempfile.mkstemp(suffix=".html", prefix="mdpp_export_")
    os.close(fd)
    try:
        export_html(
            text,
            tmp_html,
            base_dir=base_dir,
            mermaid_theme=mermaid_theme,
            show_toc=show_toc,
            enable_katex=enable_katex,
            custom_css=custom_css,
            title=title,
            log=log,
        )
        dest_path = os.path.expanduser(dest_path)
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        # file:// URL for local html
        url = "file://" + tmp_html
        cmd = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            # Allow KaTeX CDN scripts to finish before capture.
            "--virtual-time-budget=10000",
            "--run-all-compositor-stages-before-draw",
            "--print-to-pdf=" + dest_path,
            url,
        ]
        r = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        if r.returncode != 0 or not os.path.isfile(dest_path):
            err = (r.stderr or b"").decode("utf-8", errors="replace")[:500]
            raise RuntimeError("PDF export failed: %s" % (err or "unknown"))
        log("exported PDF → %s" % dest_path)
        return dest_path
    finally:
        try:
            os.unlink(tmp_html)
        except Exception:
            pass
