# MarkdownPreviewEnhanced — Sublime Text Markdown 预览插件 设计文档

日期: 2026-07-07

## 目标

独立 Sublime Text 包，提供 markdown 实时预览，不打开外部 html 页面。

## 功能需求

1. 快捷键 `super+shift+m` 切换预览。预览面板放在编辑器**右侧**，与编辑区形成**左右两等分**布局。
2. 实时渲染：编辑 markdown 时防抖 500ms 后重新渲染。
3. 支持 mermaid 图表预览。
4. 支持代码块语法高亮。
5. 可安装到本机 Sublime Text 测试。
6. 可发布到 Package Control（README/LICENSE/dependencies.json/repository 片段）。

## 技术方案

- 预览渲染：Sublime output panel + `minihtml`，输出完整 HTML（内联 CSS、内联 SVG、Pygments span）。
- 布局：用 `window.set_layout` 将窗口分成左右两组（各 50%），预览 output panel 通过 `window.create_output_panel` 创建并显示在右侧 group。
- Markdown → HTML：python-markdown，扩展 `fenced_code`、`tables`、`codehilite`、`toc`、`attr_list`、`nl2br`。
- 代码高亮：Pygments（已装 2.19.1）+ codehilite。
- Mermaid：`npx -p @mermaid-js/mermaid-cli mmdc -i <tmp> -o -` 把每个 mermaid 块转成 SVG 内联。带缓存（hash(code+theme) → SVG 文件）。
- 实时更新：`on_modified_async` + 500ms 防抖，仅对 `text.html.markdown` scope 的 view 生效。
- 依赖：`dependencies.json` 声明 `markdown`；本地额外 `pip install markdown` 兜底。import 失败时降级为纯文本并状态栏提示。

## 包结构

```
MarkdownPreviewEnhanced/
  MarkdownPreviewEnhanced.py
  md_renderer.py
  mermaid_renderer.py
  code_highlight.py
  assets/preview.css
  assets/highlight.css
  dependencies.json
  messages/install.txt
  Default.sublime-commands
  Main.sublime-menu (optional)
  sublime-keymap files (Default/*.sublime-keymap)
README.md / LICENSE (repo root)
```

## Mermaid 降级

npx 未就绪或失败时，mermaid 块显示为带语言标签的原始代码，状态栏提示。

## 发布准备

- README：安装/快捷键/配置/mermaid 说明/发布步骤
- LICENSE: MIT
- repository.json 片段示例
- 发布检查清单（语义化 tag、git repo、提交 PR 到 package_control）

## 安装

- 拷贝 `MarkdownPreviewEnhanced` 到 `~/Library/Application Support/Sublime Text 3/Packages/`
