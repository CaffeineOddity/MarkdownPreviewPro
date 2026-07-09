/* MarkdownPreviewPro client: smart refresh, TOC, scroll sync, scroll restore */
(function () {
  "use strict";

  var cfg = window.MDPP_CONFIG || { mode: "file", scrollSync: true, showToc: true };
  var currentHash = "";
  var scrollKey = "mdpp-scroll-y";
  var suppressEditorPoll = false;
  var lastReportedLine = 0;
  var lastEditorLine = 0;
  var pollTimer = null;

  function $(id) {
    return document.getElementById(id);
  }

  function saveScroll() {
    try {
      localStorage.setItem(scrollKey, String(window.scrollY || 0));
    } catch (e) {}
  }

  function restoreScroll() {
    try {
      var y = parseInt(localStorage.getItem(scrollKey) || "0", 10);
      if (y > 0) window.scrollTo(0, y);
    } catch (e) {}
  }

  function callRenderMath() {
    // Shell defines window.mdppRenderMath / window.mdppRenderMathSafe.
    // Always re-run after content swaps so new .mdpp-math nodes get painted.
    try {
      if (typeof window.mdppRenderMath === "function") {
        if (window.mdppRenderMath()) return;
      }
      if (typeof window.mdppRenderMathSafe === "function") {
        window.mdppRenderMathSafe();
      }
    } catch (e) {
      console.warn("[MDPP] math render error", e);
    }
  }

  function updateToc(tocHtml) {
    var toc = $("mdpp-toc");
    if (!toc) return;
    if (tocHtml) {
      toc.innerHTML = tocHtml;
      toc.classList.remove("mdpp-toc-empty");
    }
  }

  function applyContent(data) {
    if (!data || data.hash === currentHash) return;
    var y = window.scrollY || 0;
    var content = $("mdpp-content");
    if (content && typeof data.html === "string") {
      content.innerHTML = data.html;
    }
    if (typeof data.toc === "string") {
      updateToc(data.toc);
    }
    currentHash = data.hash || currentHash;
    window.scrollTo(0, y);
    saveScroll();
    callRenderMath();
    bindTocClicks();
  }

  function pollContent() {
    if (cfg.mode !== "server") return;
    fetch("/api/content")
      .then(function (r) {
        return r.json();
      })
      .then(applyContent)
      .catch(function () {});
  }

  function findNearestLine() {
    var nodes = document.querySelectorAll("[data-line]");
    var best = 0;
    var bestTop = -Infinity;
    var viewTop = window.scrollY || 0;
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var top = el.getBoundingClientRect().top + viewTop;
      var line = parseInt(el.getAttribute("data-line"), 10) || 0;
      if (top <= viewTop + 80 && top > bestTop) {
        bestTop = top;
        best = line;
      }
    }
    return best;
  }

  function reportBrowserScroll() {
    if (cfg.mode !== "server" || !cfg.scrollSync) return;
    var line = findNearestLine();
    if (!line || line === lastReportedLine) return;
    lastReportedLine = line;
    fetch("/api/browser_scroll", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ line: line }),
    }).catch(function () {});
  }

  function scrollToLine(line) {
    if (!line) return;
    var nodes = document.querySelectorAll("[data-line]");
    var target = null;
    var bestDiff = Infinity;
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var l = parseInt(el.getAttribute("data-line"), 10) || 0;
      var diff = Math.abs(l - line);
      if (diff < bestDiff) {
        bestDiff = diff;
        target = el;
      }
      if (l === line) {
        target = el;
        break;
      }
    }
    if (target) {
      suppressEditorPoll = true;
      target.scrollIntoView({ block: "start", behavior: "smooth" });
      setTimeout(function () {
        suppressEditorPoll = false;
      }, 400);
    }
  }

  function pollEditorLine() {
    if (cfg.mode !== "server" || !cfg.scrollSync || suppressEditorPoll) return;
    fetch("/api/editor_line")
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.line) return;
        if (data.line === lastEditorLine) return;
        lastEditorLine = data.line;
        scrollToLine(data.line);
      })
      .catch(function () {});
  }

  function bindTocClicks() {
    var toc = $("mdpp-toc");
    if (!toc) return;
    toc.onclick = function (ev) {
      var a = ev.target.closest ? ev.target.closest("a") : null;
      if (!a) return;
      var href = a.getAttribute("href") || "";
      if (href.charAt(0) === "#") {
        var id = decodeURIComponent(href.slice(1));
        var el = document.getElementById(id);
        if (el) {
          ev.preventDefault();
          el.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }
    };
  }

  function onScroll() {
    saveScroll();
    if (cfg.scrollSync) {
      if (onScroll._t) clearTimeout(onScroll._t);
      onScroll._t = setTimeout(reportBrowserScroll, 150);
    }
  }

  window.mdppInit = function mdppInit() {
    restoreScroll();
    callRenderMath();
    bindTocClicks();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("beforeunload", saveScroll);

    if (cfg.mode === "server") {
      // Seed hash so the first poll always applies server content (incl. math).
      var content = $("mdpp-content");
      currentHash = content ? "init-" + content.innerHTML.length : "";
      pollContent();
      pollTimer = setInterval(function () {
        pollContent();
        pollEditorLine();
      }, 400);
    }
  };
})();
