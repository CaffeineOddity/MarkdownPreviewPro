# MarkdownPreviewPro

Live Markdown preview in an external browser with full HTML+CSS rendering —
native tables, Mermaid diagrams, KaTeX math, task lists, footnotes, and more.

## Features

- **Browser preview** — full HTML+CSS (GitHub-style), not minihtml compromises
- **Smart live refresh** — updates content in-place and **keeps scroll position**
- **Relative images** — `![alt](./img/preview.png)` resolves from the markdown file dir
- **Mermaid diagrams** — SVG via [mermaid-cli](https://github.com/mermaid-js/mermaid-cli)
- **KaTeX math** — `$inline$`, `$$block$$`, `\(...\)`, `\[...\]`
- **Task lists / footnotes / frontmatter** — GFM-style checkboxes, `[^1]`, YAML strip
- **TOC sidebar** — sticky outline of headings
- **Scroll sync** — editor cursor ↔ preview heading (with local server)
- **Export** — standalone HTML or PDF (Chrome headless)
- **Cross-platform browser** — macOS / Windows / Linux auto-detect
- **Configurable** — output dir, port, browser, toggles for each feature
- **Zero external Python deps** — python-markdown and Pygments vendored under `lib/`

## Requirements

- Sublime Text 4 (Build 4107+)
- **Node.js** optional — only for Mermaid (`npx` / mermaid-cli)
- **Chrome / Chromium / Edge** optional — only for PDF export
- Network optional — KaTeX loads from jsDelivr CDN when enabled

## Usage

1. Open a `.md` file.
2. Press `super+shift+m` (macOS) / `ctrl+shift+m` (Windows/Linux).
3. A browser tab opens with the live preview.
4. Edit the markdown — the body updates without losing scroll (server mode).
5. Press the shortcut again to **focus the existing preview tab** (and refresh).
   Use **Close Preview** (Command Palette) to actually close the tab and stop the server.

### Commands

| Command | Description |
| --- | --- |
| `MarkdownPreviewPro: Toggle Preview` | Open / reopen browser preview |
| `MarkdownPreviewPro: Close Preview` | Close browser window |
| `MarkdownPreviewPro: Refresh Preview` | Force re-render |
| `MarkdownPreviewPro: Export HTML…` | Write a standalone HTML file |
| `MarkdownPreviewPro: Export PDF…` | Print to PDF via headless Chrome |

### Settings

Preferences → Package Settings → MarkdownPreviewPro → Settings

| Setting | Default | Description |
| --- | --- | --- |
| `mermaid_theme` | `"default"` | `default`, `dark`, `forest`, `neutral` |
| `output_dir` | `""` | Empty = Sublime cache; else e.g. `~/Downloads/MarkdownPreviewPro` |
| `use_local_server` | `true` | Local HTTP server for smart refresh / images / scroll sync |
| `server_port` | `8765` | Preferred port (tries next ports if busy) |
| `server_idle_seconds` | `45` | Auto-stop server if browser tab is closed (no HTTP activity). `0` = only stop on Close command |
| `browser` | `"auto"` | `auto`, `default`, `chrome`, `safari`, `firefox`, `edge`, … |
| `debounce_ms` | `500` | Live re-render debounce |
| `show_toc` | `true` | Sticky TOC sidebar |
| `enable_katex` | `true` | Math rendering |
| `enable_task_lists` | `true` | `- [ ]` / `- [x]` |
| `enable_footnotes` | `true` | `[^1]` footnotes |
| `strip_frontmatter` | `true` | Strip leading YAML `---` blocks |
| `scroll_sync` | `true` | Editor ↔ preview scroll (needs local server) |
| `custom_css` | `""` | Path to extra CSS file |

Example:

```jsonc
{
    "mermaid_theme": "forest",
    "output_dir": "~/Downloads/MarkdownPreviewPro",
    "browser": "chrome",
    "scroll_sync": true
}
```

## How it works

1. Read the current markdown buffer (strip frontmatter if enabled).
2. Extract Mermaid fences → SVG via `mmdc` (cached).
3. Convert with python-markdown (tables, fenced_code, codehilite, toc, footnotes, …).
4. Apply task lists, heading `data-line` markers, rewrite relative images.
5. Serve via local HTTP (`127.0.0.1`) when `use_local_server` is on:
   - `/` shell page with TOC + content
   - `/api/content` body+hash for in-place refresh
   - `/doc/...` images relative to the markdown file
   - `/api/editor_line` + `/api/browser_scroll` for scroll sync
6. Browser JS swaps `#mdpp-content` when the hash changes and restores scroll.
7. **Server lifetime**: Close Preview / Toggle-off stops the HTTP server immediately.
   Closing the browser tab alone also frees the port after `server_idle_seconds`
   (default 45s) of no client polling.

Fallback without server: `file://` preview + meta refresh + `localStorage` scroll restore.

## Installation

### Via Package Control

Command Palette → `Package Control: Install Package` → `MarkdownPreviewPro`.

### Manual

Copy the `MarkdownPreviewPro` folder into Sublime Text `Packages/`:

| Platform | Path |
| --- | --- |
| macOS | `~/Library/Application Support/Sublime Text/Packages/` |
| Linux | `~/.config/sublime-text/Packages/` |
| Windows | `%APPDATA%\Sublime Text\Packages\` |

## Development

```bash
./build.sh                    # rsync into ST Packages/ with backup
./release.sh 1.1.0            # tag + push + Package Control PR
./release.sh 1.1.0 --dry-run  # preview only
```

### Debug logs

Under `output_dir` (default: Sublime cache `MarkdownPreviewPro/`):

| File | Content |
| --- | --- |
| `preview.html` | Live shell HTML |
| `body.html` | Last body fragment |
| `last_html.html` | Snapshot |
| `debug.log` | Timestamped logs |

## License

测试改动

MIT — see [LICENSE](LICENSE).
