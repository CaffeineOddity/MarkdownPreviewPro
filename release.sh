#!/bin/bash
set -euo pipefail

# release.sh — tag a release & open/update the Package Control channel PR.
#
# Usage:
#   ./release.sh <version>          e.g.  ./release.sh 1.1.0
#   ./release.sh <version> --dry-run
#
# Channel entry is minimal (details + releases only). GitHub metadata supplies
# homepage / author / readme / issues. The channel file is updated surgically
# so the rest of repository/m.json is not reformatted.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

VERSION="${1:-}"
DRY_RUN=false
if [ $# -ge 2 ] && [ "$2" = "--dry-run" ]; then
    DRY_RUN=true
fi

if [ -z "$VERSION" ]; then
    echo -e "${RED}Usage: $0 <version> [--dry-run]${NC}"
    exit 1
fi

if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+'; then
    echo -e "${YELLOW}Warning: '$VERSION' does not look like semver (x.y.z). Continue? [y/N]${NC}"
    read -r ans
    [ "$ans" = "y" ] || [ "$ans" = "Y" ] || exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "master" ]; then
    echo -e "${YELLOW}Not on master branch (current: $BRANCH). Continue? [y/N]${NC}"
    read -r ans
    [ "$ans" = "y" ] || [ "$ans" = "Y" ] || exit 1
fi

if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}Working tree is dirty. Commit or stash changes first.${NC}"
    git status --short
    exit 1
fi

REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github.com[:/]([^/]+/[^/.]+)(\.git)?$|\1|')
OWNER="${OWNER_REPO%%/*}"
REPO_NAME="${OWNER_REPO##*/}"

PKG_NAME="MarkdownPreviewEnhanced"

echo -e "${GREEN}=== Releasing $REPO_NAME v$VERSION ===${NC}"
echo "  owner: $OWNER"
echo "  package: $PKG_NAME"
echo

echo -e "${YELLOW}[1/4] Building & tagging${NC}"

if [ -x build.sh ]; then
    ./build.sh
fi

if $DRY_RUN; then
    echo -e "${YELLOW}  [DRY-RUN] Would create and push tag $VERSION${NC}"
else
    if git rev-parse "refs/tags/$VERSION" >/dev/null 2>&1; then
        echo -e "${YELLOW}  Tag $VERSION already exists, skipping tag creation.${NC}"
    else
        git tag "$VERSION"
        echo -e "${GREEN}  Tag $VERSION created${NC}"
    fi
    git push
    git push --tags
    echo -e "${GREEN}  Pushed master + tag $VERSION${NC}"
fi

CHANNEL_REPO="sublimehq/package_control_channel"
CHANNEL_DIR="/tmp/package_control_channel_$$"

echo
echo -e "${YELLOW}[2/4] Forking $CHANNEL_REPO${NC}"

if $DRY_RUN; then
    echo -e "${YELLOW}  [DRY-RUN] Would fork & clone $CHANNEL_REPO${NC}"
else
    gh repo fork "$CHANNEL_REPO" --clone --remote-name origin "$CHANNEL_DIR" 2>&1 | tail -1
    cd "$CHANNEL_DIR"
    git remote add upstream "https://github.com/$CHANNEL_REPO.git" 2>/dev/null || true
fi

echo
echo -e "${YELLOW}[3/4] Updating repository/m.json (surgical, no full reformat)${NC}"

if $DRY_RUN; then
    echo -e "${YELLOW}  [DRY-RUN] Would upsert minimal $PKG_NAME entry${NC}"
else
    python3 << PYEOF
import re
import sys

path = "$CHANNEL_DIR/repository/m.json"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Minimal entry — GitHub metadata fills homepage/author/readme/issues.
# Use tabs to match package_control_channel style.
entry = (
    "\t{\n"
    "\t\t\"name\": \"$PKG_NAME\",\n"
    "\t\t\"details\": \"https://github.com/$OWNER/$REPO_NAME\",\n"
    "\t\t\"labels\": [\"markdown\", \"preview\", \"mermaid\", \"live preview\", \"syntax highlighting\"],\n"
    "\t\t\"releases\": [\n"
    "\t\t\t{\n"
    "\t\t\t\t\"sublime_text\": \">=4107\",\n"
    "\t\t\t\t\"tags\": true\n"
    "\t\t\t}\n"
    "\t\t]\n"
    "\t}"
)

# Match an existing top-level package object whose "name" is MarkdownPreviewEnhanced.
# Brace-aware scan of the packages array items is fragile; use a constrained
# regex for objects that contain our name key near the start.
pattern = re.compile(
    r'\{\s*"name"\s*:\s*"MarkdownPreviewEnhanced"\s*,.*?\n\t\}',
    re.DOTALL,
)

if pattern.search(text):
    # Replace only our entry; leave the rest of the file byte-identical in style.
    new_text, n = pattern.subn(entry, text, count=1)
    if n != 1:
        print("ERROR: expected exactly one MarkdownPreviewEnhanced entry", file=sys.stderr)
        sys.exit(1)
    print("Updated existing MarkdownPreviewEnhanced entry")
else:
    # Insert alphabetically before the first package name >= ours.
    # Find packages array and insert a comma-terminated entry.
    m = re.search(r'("packages"\s*:\s*\[)', text)
    if not m:
        print("ERROR: packages array not found", file=sys.stderr)
        sys.exit(1)

    # Find insertion point: first {"name": "X"} where X >= MarkdownPreviewEnhanced
    insert_at = None
    for m2 in re.finditer(r'\{\s*"name"\s*:\s*"([^"]+)"', text):
        name = m2.group(1)
        if name.lower() >= "markdownpreviewenhanced":
            insert_at = m2.start()
            break

    if insert_at is None:
        # Append before the closing of packages array: last ] of packages
        # Find "packages": [ ... ]
        start = m.end()
        # crude: insert before the final \n]
        idx = text.rfind("\n]")
        if idx < 0:
            print("ERROR: cannot find end of packages", file=sys.stderr)
            sys.exit(1)
        # ensure previous entry has trailing comma
        before = text[:idx].rstrip()
        if not before.endswith(","):
            before += ","
        new_text = before + "\n" + entry + text[idx:]
    else:
        new_text = text[:insert_at] + entry + ",\n" + text[insert_at:]
    print("Inserted MarkdownPreviewEnhanced entry")

with open(path, "w", encoding="utf-8", newline="\n") as f:
    f.write(new_text)
print("Wrote", path)
PYEOF
    echo -e "${GREEN}  Done${NC}"
fi

echo
echo -e "${YELLOW}[4/4] Creating PR${NC}"

if $DRY_RUN; then
    echo -e "${YELLOW}  [DRY-RUN] Would push branch and create PR${NC}"
else
    cd "$CHANNEL_DIR"
    BRANCH_NAME="add-markdownpreviewenhanced"

    if git rev-parse --verify "origin/$BRANCH_NAME" >/dev/null 2>&1; then
        git checkout -b "$BRANCH_NAME" "origin/$BRANCH_NAME"
    else
        git checkout -b "$BRANCH_NAME"
    fi

    git add repository/m.json
    if git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}  No changes to repository/m.json — skipping PR.${NC}"
    else
        git commit -m "Update MarkdownPreviewEnhanced package entry"

        git push -f origin "$BRANCH_NAME"

        EXISTING_PR=$(gh pr list \
            --repo "$CHANNEL_REPO" \
            --head "$OWNER:$BRANCH_NAME" \
            --state open \
            --json number \
            --jq '.[0].number' 2>/dev/null || echo "")

        if [ -n "$EXISTING_PR" ]; then
            echo -e "${GREEN}  PR #$EXISTING_PR already exists — updated branch.${NC}"
            echo -e "${GREEN}  PR URL: https://github.com/$CHANNEL_REPO/pull/$EXISTING_PR${NC}"
        else
            PR_URL=$(gh pr create \
                --repo "$CHANNEL_REPO" \
                --head "$OWNER:$BRANCH_NAME" \
                --base master \
                --title "Add MarkdownPreviewEnhanced package (v$VERSION)" \
                --body "## MarkdownPreviewEnhanced v$VERSION

**Repository:** https://github.com/$OWNER/$REPO_NAME
**Tag:** \`$VERSION\`

Live markdown preview in an external browser (full HTML/CSS, tables, Mermaid, KaTeX).

Package Control entry is minimal (\`details\` + \`releases\` only).
" 2>&1)
            echo -e "${GREEN}  PR created: $PR_URL${NC}"
        fi
    fi
fi

echo
echo -e "${GREEN}=== Release v$VERSION complete! ===${NC}"
if $DRY_RUN; then
    echo -e "${YELLOW}  (Dry run — nothing was actually pushed)${NC}"
fi

rm -rf "$CHANNEL_DIR"
