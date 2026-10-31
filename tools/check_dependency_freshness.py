"""Compare the declared requirement ranges against the latest PyPI releases.

Reads requirements.txt and requirements-dev.txt, queries PyPI for the current
release of each, and writes a Markdown report.

    python tools/check_dependency_freshness.py --output report.md --github-output
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "line-vault-dependency-freshness"

REQUIREMENT_FILES = (
    "requirements.txt",
    "requirements-dev.txt",
)

_REQUIREMENT_RE = re.compile(r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*(.*)$")
_MINIMUM_RE = re.compile(r"(>=|>|==|~=)\s*([0-9][0-9A-Za-z.!+_-]*)")
_RELEASE_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)*")
HOLD_MARKER = "freshness-hold:"
DEFERRALS_PATH = REPO_ROOT / ".github" / "dependency-deferrals.json"


class DependencyCheckError(RuntimeError):
    """Raised when a requirements file cannot be read."""


def release_key(version: str) -> tuple[int, ...] | None:
    match = _RELEASE_RE.match(version.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.group(0).split("."))


def is_newer_version(latest: str, declared: str) -> bool:
    latest_key = release_key(latest)
    declared_key = release_key(declared)
    if latest_key is None or declared_key is None:
        return False
    depth = len(declared_key)
    padded = latest_key + (0,) * (depth - len(latest_key))
    return padded[:depth] > declared_key


def parse_requirements(text: str, filename: str) -> list[dict]:
    packages: list[dict] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        comment = ""
        if " #" in raw:
            line, comment = raw.split(" #", 1)
            line = line.strip()
            comment = comment.strip()
        elif raw.startswith("#"):
            continue
        match = _REQUIREMENT_RE.match(line)
        if not match:
            continue
        name, spec = match.group(1), match.group(2).strip()
        min_match = _MINIMUM_RE.search(spec)
        declared_floor = min_match.group(2) if min_match else ""
        hold_reason = ""
        if HOLD_MARKER in comment:
            hold_reason = comment.split(HOLD_MARKER, 1)[1].strip()
        packages.append(
            {
                "name": name,
                "file": filename,
                "line": line_number,
                "raw_spec": spec,
                "declared_floor": declared_floor,
                "hold": hold_reason,
            }
        )
    return packages


def load_declared_requirements(repo_root: Path = REPO_ROOT) -> list[dict]:
    declared: list[dict] = []
    for rel_path in REQUIREMENT_FILES:
        full_path = repo_root / rel_path
        if not full_path.is_file():
            continue
        try:
            content = full_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise DependencyCheckError(f"cannot read {full_path}: {exc}") from exc
        declared.extend(parse_requirements(content, rel_path))
    return declared


def load_deferrals(path: Path = DEFERRALS_PATH) -> dict[str, tuple[str, str]]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    deferrals = data.get("deferrals", {})
    if not isinstance(deferrals, dict):
        return {}
    result: dict[str, tuple[str, str]] = {}
    for key, value in deferrals.items():
        if isinstance(value, dict) and "deferredLatest" in value and "reason" in value:
            result[key.lower()] = (str(value["deferredLatest"]), str(value["reason"]))
    return result


def fetch_pypi_version(package_name: str) -> str | None:
    safe_name = urllib.parse.quote(package_name)
    url = f"https://pypi.org/pypi/{safe_name}/json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("info", {}).get("version")
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None


def collect_status(packages: list[dict], deferrals: dict[str, tuple[str, str]]) -> list[dict]:
    rows: list[dict] = []
    for package in packages:
        name = package["name"]
        latest = fetch_pypi_version(name)
        declared = package["declared_floor"]
        outdated = False
        if latest and declared:
            outdated = is_newer_version(latest, declared)
        deferral = deferrals.get(name.lower())
        rows.append(
            {
                **package,
                "latest": latest or "unknown",
                "outdated": outdated,
                "deferral": deferral,
            }
        )
    return rows


def needs_review(row: dict) -> bool:
    if row["hold"]:
        return False
    if row["latest"] == "unknown":
        return True
    if not row["outdated"]:
        return False
    if row["deferral"]:
        deferred_version, _ = row["deferral"]
        if not is_newer_version(row["latest"], deferred_version):
            return False
    return True


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "# Dependency Freshness Report",
        "",
        "| Package | File | Declared | Latest PyPI | Status |",
        "|---|---|---|---|---|",
    ]
    attention_count = 0
    for row in rows:
        name = row["name"]
        file = row["file"]
        declared = row["declared_floor"] or row["raw_spec"] or "any"
        latest = row["latest"]
        if needs_review(row):
            status = "**UNKNOWN (PyPI lookup failed)**" if latest == "unknown" else "**OUTDATED**"
            attention_count += 1
        elif row["hold"]:
            status = f"HELD: {row['hold']}"
        elif row["deferral"]:
            status = f"DEFERRED: {row['deferral'][1]}"
        elif row["outdated"]:
            status = "newer available"
        else:
            status = "fresh"
        lines.append(f"| `{name}` | `{file}` | `{declared}` | `{latest}` | {status} |")
    lines.append("")
    if attention_count > 0:
        lines.append(f"**Attention needed**: {attention_count} dependencies are behind or could not be checked and require review.\n")
    else:
        lines.append("All declared dependencies are fresh, held, or deferred.\n")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "dependency-freshness-report.md")
    parser.add_argument("--github-output", action="store_true")
    args = parser.parse_args()

    declared = load_declared_requirements(REPO_ROOT)
    deferrals = load_deferrals(DEFERRALS_PATH)
    rows = collect_status(declared, deferrals)

    report = render_markdown(rows)
    args.output.write_text(report, encoding="utf-8")
    print(report)

    has_attention = any(needs_review(r) for r in rows)
    if args.github_output and "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"needs_attention={'true' if has_attention else 'false'}\n")

    return 1 if has_attention else 0


if __name__ == "__main__":
    raise SystemExit(main())
