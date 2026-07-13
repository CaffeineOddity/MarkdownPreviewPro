# Agent instructions

## Package Control / channel PRs

- **Do not reformat** any file in `sublimehq/package_control_channel` (or forks of it).
  When updating `repository/*.json`, change only the `MarkdownPreviewEnhanced` entry
  (or insert a minimal new entry). Preserve existing indentation, key order, and
  surrounding packages.
- Channel package entries must be **minimal**. Prefer only:
  - `name`
  - `details` (GitHub repo URL)
  - `labels` (optional)
  - `releases`
- **Do not** add keys that GitHub already provides via repository metadata:
  `homepage`, `author`, `readme`, `issues`, `donate`, etc.

## Repository layout

- This GitHub repository root **is** the Sublime package root (Package Control
  requirement). Plugin modules live at the top level, not under a nested folder.
- Do not reintroduce `repository.json` / `repository.json.example` in this repo;
  they are not required for Package Control tagging releases.

## Editing hygiene

- Prefer surgical edits over wholesale reformatting of untouched files.
- Do not commit agent state (`.omc/`), `__pycache__/`, or local test dumps.
