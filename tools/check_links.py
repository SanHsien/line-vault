#!/usr/bin/env python3
"""Check relative links across maintained repository Markdown documents.

Validates that all local relative links point to existing files.

    python tools/check_links.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent

LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HTML_SRC_PATTERN = re.compile(r"""(?is)<img[^>]+src=["']([^"']+)["']""")

SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#")
SKIP_NAMES = {
    "dependency-freshness-report.md",
}

MAINTAINED_DOCUMENTS = (
    "README.md",
    "README.en.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "REVIEW.md",
    "docs/DEVELOPMENT.md",
    "docs/DECISIONS.md",
    "docs/ROADMAP.md",
    "docs/ROADMAP.en.md",
    ".github/pull_request_template.md",
)


def iter_documents() -> list[Path]:
    """Return all maintained markdown document paths."""
    missing = [relative for relative in MAINTAINED_DOCUMENTS if not (ROOT / relative).is_file()]
    if missing:
        raise FileNotFoundError("Maintained documents missing: " + ", ".join(missing))

    required = [ROOT / relative for relative in MAINTAINED_DOCUMENTS]
    seen = {path.resolve() for path in required}

    github_dir = ROOT / ".github"
    if github_dir.is_dir():
        for path in github_dir.rglob("*.md"):
            if path.is_file() and path.name not in SKIP_NAMES and path.resolve() not in seen:
                required.append(path)
                seen.add(path.resolve())

    return required


def _missing_relative(path: Path, target: str) -> str | None:
    target = target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1:target.index(">")]
    else:
        target = target.split(None, 1)[0] if target else target

    if not target or target.startswith(SKIP_PREFIXES):
        return None

    file_part = unquote(target.split("#", 1)[0])
    if not file_part:
        return None

    resolved = (path.parent / file_part).resolve()
    if resolved.exists():
        return None

    try:
        shown = resolved.relative_to(ROOT)
    except ValueError:
        shown = resolved
    return f"{target} -> 找不到 {shown}"


def check_document(path: Path) -> list[str]:
    """Check all markdown links in a single file."""
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    for pattern in (LINK_PATTERN, IMAGE_PATTERN, HTML_SRC_PATTERN):
        for match in pattern.finditer(text):
            missing = _missing_relative(path, match.group(1))
            if missing:
                problems.append(missing)
    return problems


def find_broken_links() -> list[tuple[Path, str]]:
    """Scan all maintained documents and return broken link tuples (path, error)."""
    broken: list[tuple[Path, str]] = []
    for doc in iter_documents():
        for err in check_document(doc):
            broken.append((doc, err))
    return broken


def main() -> int:
    documents = iter_documents()
    if not documents:
        print("找不到任何維護用 Markdown 檔")
        return 1

    failures = 0
    for path in documents:
        problems = check_document(path)
        rel = path.relative_to(ROOT)
        if problems:
            failures += 1
            for problem in problems:
                print(f"FAIL {rel}: {problem}")
        else:
            print(f"OK   {rel}")

    print(f"\n共 {len(documents)} 份文件，{failures} 份有斷掉的相對連結。")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
