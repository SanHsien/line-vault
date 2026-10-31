"""Repository governance and maintenance contract tests."""

import re
from pathlib import Path

from tools.check_links import find_broken_links

REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = (
    "README.md",
    "README.en.md",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "REVIEW.md",
    "docs/DEVELOPMENT.md",
    "docs/DECISIONS.md",
    "docs/ROADMAP.md",
    "docs/ROADMAP.en.md",
    "tools/dev_check.ps1",
    "tools/test_product.ps1",
    "tools/bootstrap_dev.ps1",
    "tools/check_links.py",
    "tools/check_dependency_freshness.py",
)

FORBIDDEN_PATTERNS = [
    re.compile(r"\bos\.system\s*\("),
    re.compile(r"\bshell\s*=\s*True\b"),
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"except\s+Exception\s*:\s*pass"),
]


def test_required_governance_files_exist():
    """Verify all required documentation and maintenance scripts exist."""
    missing = [rel for rel in REQUIRED_FILES if not (REPO_ROOT / rel).is_file()]
    assert not missing, f"Missing required repository files: {missing}"


def test_markdown_links_integrity():
    """Verify check_links.py finds zero broken relative links across maintained documents."""
    broken = find_broken_links()
    assert broken == [], f"Broken relative links found: {broken}"


def test_no_forbidden_code_patterns_in_codebase():
    """Verify no Python files in line_vault/ or tools/ use unsafe or prohibited code constructs."""
    violations: list[str] = []
    scan_dirs = [REPO_ROOT / "line_vault", REPO_ROOT / "tools"]

    for s_dir in scan_dirs:
        for py_path in s_dir.rglob("*.py"):
            if py_path.resolve() == Path(__file__).resolve():
                continue
            text = py_path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_PATTERNS:
                match = pattern.search(text)
                if match:
                    violations.append(
                        f"{py_path.relative_to(REPO_ROOT)}: forbidden pattern '{match.group(0)}' matched"
                    )

    assert violations == [], "Prohibited code patterns found:\n" + "\n".join(violations)


def test_ci_workflow_contracts():
    """Verify CI workflow is configured for windows-latest and defines read-only permissions."""
    ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    assert ci_path.is_file(), "Missing .github/workflows/ci.yml"
    ci_text = ci_path.read_text(encoding="utf-8")

    assert "windows-latest" in ci_text
    assert "permissions:" in ci_text
    assert "contents: read" in ci_text
