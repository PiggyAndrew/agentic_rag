from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Rules:
    forbidden_import_substrings: tuple[str, ...]
    allow_ui_infrastructure_import_files: tuple[str, ...]
    allow_application_infrastructure_import_files: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Finding:
    file: Path
    line: int
    message: str


def _load_rules(repo_root: Path) -> Rules:
    rules_path = repo_root / "backend" / "docs" / "architecture" / "ddd" / "rules.json"
    data = json.loads(rules_path.read_text(encoding="utf-8"))
    return Rules(
        forbidden_import_substrings=tuple(data.get("forbidden_import_substrings", [])),
        allow_ui_infrastructure_import_files=tuple(data.get("allow_ui_infrastructure_import_files", [])),
        allow_application_infrastructure_import_files=tuple(data.get("allow_application_infrastructure_import_files", [])),
    )


def _is_import_line(line: str) -> bool:
    s = line.lstrip()
    return s.startswith("import ") or s.startswith("from ")


def _check_files(repo_root: Path, files: list[Path], *, allowlist: set[Path], forbidden: tuple[str, ...]) -> list[Finding]:
    findings: list[Finding] = []
    for f in files:
        rel = f.relative_to(repo_root)
        if rel in allowlist:
            continue
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines, start=1):
            if not _is_import_line(line):
                continue
            for frag in forbidden:
                if frag and frag in line:
                    findings.append(Finding(file=rel, line=i, message=f"forbidden dependency: {frag}"))
                    break
    return findings


def _render(findings: list[Finding]) -> str:
    if not findings:
        return "DDD check passed.\n"
    out = ["DDD check failed:", ""]
    for f in findings:
        out.append(f"- {f.file}:{f.line} {f.message}")
    out.append("")
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser(prog="ddd_check.py")
    p.add_argument("--repo-root", default=".", help="Repository root")
    args = p.parse_args()

    repo_root = Path(args.repo_root).resolve()
    rules = _load_rules(repo_root)

    allow_ui = {Path(p) for p in rules.allow_ui_infrastructure_import_files}
    allow_app = {Path(p) for p in rules.allow_application_infrastructure_import_files}

    ui_files = [p.resolve() for p in (repo_root / "backend" / "api").rglob("*.py")]
    app_files = [p.resolve() for p in (repo_root / "backend" / "modules").rglob("application")]
    app_py_files: list[Path] = []
    for d in app_files:
        if d.is_dir():
            app_py_files.extend([p.resolve() for p in d.rglob("*.py")])

    findings: list[Finding] = []
    findings.extend(_check_files(repo_root, ui_files, allowlist=allow_ui, forbidden=rules.forbidden_import_substrings))
    findings.extend(_check_files(repo_root, app_py_files, allowlist=allow_app, forbidden=rules.forbidden_import_substrings))

    sys.stdout.write(_render(findings))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

