"""Assemble full HTML documents for live preview and export."""
import os

# Local vendored KaTeX (no network required for the engine itself).
# Fonts still reference CDN URLs inside katex.min.css as a lightweight fallback.
_KATEX_CDN_CSS = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"
_KATEX_CDN_JS = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"
_KATEX_BOOT_CSS = "https://cdn.bootcdn.net/ajax/libs/KaTeX/0.16.9/katex.min.css"
_KATEX_BOOT_JS = "https://cdn.bootcdn.net/ajax/libs/KaTeX/0.16.9/katex.min.js"


def _load_asset(name):
    path = os.path.join(os.path.dirname(__file__), "assets", name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _katex_local_paths():
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "katex")
    css = os.path.join(base, "katex.min.css")
    js = os.path.join(base, "katex.min.js")
    if os.path.isfile(css) and os.path.isfile(js):
        return css, js
    return None, None


def _katex_urls(use_server=True):
    """Return (css_href, js_href) preferring local assets."""
    css_path, js_path = _katex_local_paths()
    if css_path and js_path:
        if use_server:
            return "/assets/katex/katex.min.css", "/assets/katex/katex.min.js"
        # file:// / export: absolute file URLs
        return "file://" + css_path, "file://" + js_path
    return _KATEX_CDN_CSS, _KATEX_CDN_JS


def _katex_head(enabled, use_server=True):
    """Load KaTeX: local first, then CDN / bootcdn fallbacks."""
    if not enabled:
        return ""
    css_href, js_href = _katex_urls(use_server=use_server)

    # Loader tries local/primary, then mirrors. Calls mdppRenderMath when ready.
    return (
        '  <link id="mdpp-katex-css" rel="stylesheet" href="%s">\n'
        '  <script>\n'
        '  (function(){\n'
        '    var cssFallbacks=%s;\n'
        '    var jsFallbacks=%s;\n'
        '    function loadCss(hrefs, i){\n'
        '      if(i>=hrefs.length) return;\n'
        '      var l=document.getElementById("mdpp-katex-css");\n'
        '      if(!l){l=document.createElement("link");l.rel="stylesheet";l.id="mdpp-katex-css";document.head.appendChild(l);}\n'
        '      l.onerror=function(){loadCss(hrefs,i+1);};\n'
        '      if(i>0) l.href=hrefs[i];\n'
        '    }\n'
        '    function loadJs(hrefs, i){\n'
        '      if(i>=hrefs.length){console.warn("[MDPP] KaTeX failed to load");return;}\n'
        '      var s=document.createElement("script");\n'
        '      s.src=hrefs[i];\n'
        '      s.onload=function(){if(window.mdppRenderMathSafe)window.mdppRenderMathSafe();'
        'else if(window.mdppRenderMath)window.mdppRenderMath();};\n'
        '      s.onerror=function(){loadJs(hrefs,i+1);};\n'
        '      document.head.appendChild(s);\n'
        '    }\n'
        '    loadCss(cssFallbacks, 0);\n'
        '    loadJs(jsFallbacks, 0);\n'
        '  })();\n'
        '  </script>\n'
    ) % (
        css_href,
        _json([css_href, _KATEX_CDN_CSS, _KATEX_BOOT_CSS]),
        _json([js_href, _KATEX_CDN_JS, _KATEX_BOOT_JS]),
    )


def _katex_rerender_snippet(enabled):
    """JS: render all .mdpp-math nodes with katex.render (idempotent + retry)."""
    if not enabled:
        return "window.mdppRenderMath=function(){return true;};window.mdppRenderMathSafe=function(){};"
    return r"""
window.mdppRenderMath = function mdppRenderMath() {
  if (!window.katex || typeof window.katex.render !== "function") {
    return false;
  }
  var nodes = document.querySelectorAll(".mdpp-math:not([data-mdpp-rendered])");
  for (var i = 0; i < nodes.length; i++) {
    var el = nodes[i];
    var tex = el.getAttribute("data-tex");
    if (tex == null || tex === "") {
      tex = (el.textContent || "").replace(/^\s+|\s+$/g, "");
    }
    if (!tex) {
      el.setAttribute("data-mdpp-rendered", "1");
      continue;
    }
    var display = el.getAttribute("data-display") === "true";
    try {
      // Clear previous plain-text children before render
      el.textContent = "";
      window.katex.render(tex, el, {
        displayMode: display,
        throwOnError: false,
        strict: "ignore",
        output: "html"
      });
      el.setAttribute("data-mdpp-rendered", "1");
    } catch (e) {
      el.textContent = tex;
      el.setAttribute("data-mdpp-rendered", "err");
      el.setAttribute("title", String(e && e.message ? e.message : e));
      console.warn("[MDPP] katex.render failed:", tex, e);
    }
  }
  return true;
};
window.mdppRenderMathSafe = function mdppRenderMathSafe() {
  if (window.mdppRenderMath && window.mdppRenderMath()) return;
  if (window.mdppRenderMathSafe._timer) return;
  var n = 0;
  window.mdppRenderMathSafe._timer = setInterval(function () {
    n += 1;
    if ((window.mdppRenderMath && window.mdppRenderMath()) || n > 80) {
      clearInterval(window.mdppRenderMathSafe._timer);
      window.mdppRenderMathSafe._timer = null;
    }
  }, 100);
};
""".strip()


def build_preview_shell(
    body_html,
    toc_html="",
    show_toc=True,
    enable_katex=True,
    scroll_sync=True,
    use_server=True,
    custom_css="",
    title="Markdown Preview",
):
    """Build the stable shell page (polls /api/content when use_server)."""
    css = _load_asset("preview.css")
    hl_css = _load_asset("highlight.css")
    js = _load_asset("preview.js")
    if custom_css:
        try:
            with open(os.path.expanduser(custom_css), "r", encoding="utf-8") as f:
                css = css + "\n" + f.read()
        except Exception:
            pass

    toc_block = ""
    layout_class = "mdpp-layout"
    if show_toc and toc_html:
        toc_block = (
            '<aside id="mdpp-toc" class="mdpp-toc">%s</aside>' % toc_html
        )
        layout_class += " mdpp-has-toc"
    elif show_toc:
        toc_block = '<aside id="mdpp-toc" class="mdpp-toc mdpp-toc-empty"></aside>'
        layout_class += " mdpp-has-toc"

    mode = "server" if use_server else "file"
    config_js = (
        "window.MDPP_CONFIG=%s;" % _json({
            "mode": mode,
            "scrollSync": bool(scroll_sync),
            "showToc": bool(show_toc),
            "katex": bool(enable_katex),
        })
    )

    meta_refresh = ""
    if not use_server:
        meta_refresh = '<meta http-equiv="refresh" content="2">\n'

    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"zh-CN\">\n"
        "<head>\n"
        "<meta charset=\"utf-8\">\n"
        "%s"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>%s</title>\n"
        "%s"
        "<style>\n%s\n%s\n</style>\n"
        "<script>%s</script>\n"
        "</head>\n"
        "<body class=\"%s\" data-mdpp-mode=\"%s\">\n"
        "<div class=\"mdpp-wrap\">\n"
        "%s\n"
        "<main id=\"mdpp-content\" class=\"markdown-body\">%s</main>\n"
        "</div>\n"
        "<script>%s</script>\n"
        "<script>%s</script>\n"
        "<script>%s</script>\n"
        "</body>\n"
        "</html>\n"
    ) % (
        meta_refresh,
        _escape_html(title),
        _katex_head(enable_katex, use_server=use_server),
        css,
        hl_css,
        config_js,
        layout_class,
        mode,
        toc_block,
        body_html,
        _katex_rerender_snippet(enable_katex),
        js,
        "document.addEventListener('DOMContentLoaded',function(){"
        "if(window.mdppInit)mdppInit();"
        "if(window.mdppRenderMathSafe)mdppRenderMathSafe();"
        "});",
    )


def build_export_html(
    body_html,
    toc_html="",
    show_toc=True,
    enable_katex=True,
    custom_css="",
    title="Markdown Export",
):
    """Standalone HTML (no polling JS). Suitable for sharing / print-to-PDF."""
    css = _load_asset("preview.css")
    hl_css = _load_asset("highlight.css")
    if custom_css:
        try:
            with open(os.path.expanduser(custom_css), "r", encoding="utf-8") as f:
                css = css + "\n" + f.read()
        except Exception:
            pass

    toc_block = ""
    layout_class = "mdpp-layout mdpp-export"
    if show_toc and toc_html:
        toc_block = '<aside class="mdpp-toc">%s</aside>' % toc_html
        layout_class += " mdpp-has-toc"

    # Export prefers CDN so the file is portable without package assets.
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"zh-CN\">\n"
        "<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>%s</title>\n"
        "%s"
        "<style>\n%s\n%s\n"
        "@media print { .mdpp-toc { display: none !important; } "
        ".mdpp-wrap { display:block !important; } "
        ".markdown-body { max-width:none !important; } }\n"
        "</style>\n"
        "</head>\n"
        "<body class=\"%s\">\n"
        "<div class=\"mdpp-wrap\">\n"
        "%s\n"
        "<main class=\"markdown-body\">%s</main>\n"
        "</div>\n"
        "<script>%s</script>\n"
        "<script>"
        "document.addEventListener('DOMContentLoaded',function(){"
        "if(window.mdppRenderMathSafe)mdppRenderMathSafe();"
        "});"
        "</script>\n"
        "</body>\n"
        "</html>\n"
    ) % (
        _escape_html(title),
        _katex_head(enable_katex, use_server=False),
        css,
        hl_css,
        layout_class,
        toc_block,
        body_html,
        _katex_rerender_snippet(enable_katex),
    )


def _json(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)


def _escape_html(s):
    import html as _html
    return _html.escape(s or "")
