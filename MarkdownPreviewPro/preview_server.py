"""Local HTTP server for live preview, media, and scroll-sync APIs."""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse


class PreviewState:
    """Shared mutable state between the plugin and the HTTP server."""

    def __init__(self):
        self.lock = threading.Lock()
        self.content_hash = ""
        self.body_html = ""
        self.toc_html = ""
        self.full_html = ""
        self.doc_dir = None  # directory of the current markdown file
        self.editor_line = 0  # cursor line in editor (1-based) → browser
        self.browser_line = 0  # visible line reported by browser → editor
        self.browser_line_seq = 0
        self.output_dir = None
        self.shell_html = ""  # stable shell; body swapped via API
        self.last_activity = 0.0  # unix time of last HTTP request


_STATE = PreviewState()


def state():
    return _STATE


def touch_activity():
    """Record that a client is still talking to the server."""
    with _STATE.lock:
        _STATE.last_activity = time.time()


def seconds_since_activity():
    with _STATE.lock:
        if not _STATE.last_activity:
            return 1e9
        return time.time() - _STATE.last_activity


def update_content(body_html, toc_html, full_html, content_hash, doc_dir, shell_html=None):
    with _STATE.lock:
        _STATE.body_html = body_html or ""
        _STATE.toc_html = toc_html or ""
        _STATE.full_html = full_html or ""
        _STATE.content_hash = content_hash or ""
        if doc_dir:
            _STATE.doc_dir = doc_dir
        if shell_html is not None:
            _STATE.shell_html = shell_html
        # Publishing new content is activity (browser may still be loading).
        _STATE.last_activity = time.time()


def set_editor_line(line):
    with _STATE.lock:
        _STATE.editor_line = int(line or 0)


def pop_browser_line():
    """Return (line, seq) if browser reported a new scroll target for the editor."""
    with _STATE.lock:
        line = _STATE.browser_line
        seq = _STATE.browser_line_seq
        return line, seq


def set_output_dir(path):
    with _STATE.lock:
        _STATE.output_dir = path


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Silence default stderr spam; plugin has its own logger.
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def do_OPTIONS(self):
        touch_activity()
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        touch_activity()
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/preview.html", "/index.html"):
            self._serve_shell()
            return
        if path == "/api/content":
            self._api_content()
            return
        if path == "/api/editor_line":
            self._api_editor_line()
            return
        if path.startswith("/doc/"):
            self._serve_doc(path[len("/doc/"):])
            return
        if path.startswith("/assets/"):
            self._serve_package_asset(path[len("/assets/"):])
            return
        # Fallback: files under output_dir
        self._serve_output(path.lstrip("/"))

    def do_POST(self):
        touch_activity()
        parsed = urlparse(self.path)
        if parsed.path == "/api/browser_scroll":
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception:
                data = {}
            line = int(data.get("line") or 0)
            with _STATE.lock:
                if line > 0:
                    _STATE.browser_line = line
                    _STATE.browser_line_seq += 1
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return
        self.send_error(404)

    def _serve_shell(self):
        with _STATE.lock:
            html = _STATE.shell_html or _STATE.full_html or "<html><body>Loading…</body></html>"
        data = html.encode("utf-8")
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _api_content(self):
        with _STATE.lock:
            payload = {
                "hash": _STATE.content_hash,
                "html": _STATE.body_html,
                "toc": _STATE.toc_html,
            }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _api_editor_line(self):
        with _STATE.lock:
            payload = {"line": _STATE.editor_line}
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _safe_join(self, root, rel):
        rel = unquote(rel).replace("\\", "/")
        # prevent path traversal
        parts = []
        for p in rel.split("/"):
            if p in ("", "."):
                continue
            if p == "..":
                return None
            parts.append(p)
        full = os.path.normpath(os.path.join(root, *parts))
        root_norm = os.path.normpath(root)
        if not full.startswith(root_norm + os.sep) and full != root_norm:
            return None
        return full

    def _serve_file(self, full, content_type=None):
        if not full or not os.path.isfile(full):
            self.send_error(404)
            return
        try:
            with open(full, "rb") as f:
                data = f.read()
        except Exception:
            self.send_error(404)
            return
        if not content_type:
            ext = os.path.splitext(full)[1].lower()
            content_type = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".svg": "image/svg+xml",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
                ".json": "application/json",
            }.get(ext, "application/octet-stream")
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_doc(self, rel):
        with _STATE.lock:
            doc_dir = _STATE.doc_dir
        if not doc_dir:
            self.send_error(404)
            return
        full = self._safe_join(doc_dir, rel)
        self._serve_file(full)

    def _serve_package_asset(self, rel):
        assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        full = self._safe_join(assets, rel)
        self._serve_file(full)

    def _serve_output(self, rel):
        with _STATE.lock:
            out = _STATE.output_dir
        if not out:
            self.send_error(404)
            return
        full = self._safe_join(out, rel)
        self._serve_file(full)


class PreviewServer:
    def __init__(self):
        self._httpd = None
        self._thread = None
        self.port = None
        self.host = "127.0.0.1"

    @property
    def running(self):
        return self._httpd is not None

    @property
    def base_url(self):
        if not self.port:
            return None
        return "http://%s:%d" % (self.host, self.port)

    def start(self, port=8765, log=None):
        log = log or (lambda m: None)
        if self.running:
            touch_activity()
            return self.base_url

        # Try preferred port, then next few.
        last_err = None
        for p in range(int(port), int(port) + 20):
            try:
                httpd = ThreadingHTTPServer((self.host, p), _Handler)
                self._httpd = httpd
                self.port = p
                break
            except OSError as e:
                last_err = e
                continue
        if self._httpd is None:
            log("server start failed: %s" % last_err)
            return None

        def _run():
            try:
                self._httpd.serve_forever(poll_interval=0.3)
            except Exception:
                pass

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        touch_activity()
        log("preview server on %s" % self.base_url)
        return self.base_url

    def stop(self, log=None):
        log = log or (lambda m: None)
        if self._httpd is None:
            return
        try:
            self._httpd.shutdown()
        except Exception:
            pass
        try:
            self._httpd.server_close()
        except Exception:
            pass
        self._httpd = None
        self._thread = None
        self.port = None
        log("preview server stopped")


# Module-level singleton used by the plugin.
SERVER = PreviewServer()
