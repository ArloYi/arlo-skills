#!/usr/bin/env python3
"""Validate the structure and metadata of every skill in this collection."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "design-compass",
    "website-release-manager",
    "wealth-compass",
    "youtube-kol-sourcing",
)
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing opening YAML delimiter")
    try:
        raw_frontmatter, body = text[4:].split("\n---\n", 1)
    except ValueError as exc:
        raise ValueError("missing closing YAML delimiter") from exc

    metadata: dict[str, str] = {}
    for line in raw_frontmatter.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata, body


def validate_skill(name: str) -> list[str]:
    errors: list[str] = []
    folder = ROOT / name
    skill_file = folder / "SKILL.md"
    agent_file = folder / "agents" / "openai.yaml"

    if not skill_file.is_file():
        return [f"{name}: missing SKILL.md"]
    if not agent_file.is_file():
        errors.append(f"{name}: missing agents/openai.yaml")

    try:
        metadata, body = parse_frontmatter(skill_file)
    except ValueError as exc:
        return [f"{name}: {exc}"]

    if set(metadata) != {"name", "description"}:
        errors.append(f"{name}: frontmatter must contain only name and description")
    if metadata.get("name") != name:
        errors.append(f"{name}: frontmatter name must match folder name")
    if not NAME_PATTERN.fullmatch(metadata.get("name", "")):
        errors.append(f"{name}: invalid skill name")
    description = metadata.get("description", "")
    if not description or len(description) > 1024:
        errors.append(f"{name}: description must be 1-1024 characters")
    if len(skill_file.read_text(encoding="utf-8").splitlines()) > 500:
        errors.append(f"{name}: SKILL.md exceeds 500 lines")

    for target in LINK_PATTERN.findall(body):
        if "://" in target or target.startswith("#"):
            continue
        resolved = folder / target.split("#", 1)[0]
        if not resolved.exists():
            errors.append(f"{name}: broken local link {target}")
    return errors


def main() -> int:
    errors: list[str] = []
    for name in SKILLS:
        errors.extend(validate_skill(name))

    eval_path = ROOT / "evals" / "trigger-cases.json"
    try:
        evals = json.loads(eval_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"evals: cannot read trigger-cases.json: {exc}")
    else:
        if set(evals) != set(SKILLS):
            errors.append("evals: skill names do not match the catalog")
        for name, cases in evals.items():
            if not cases.get("should_trigger") or not cases.get("should_not_trigger"):
                errors.append(f"evals: {name} needs positive and negative trigger cases")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Validated {len(SKILLS)} skills and their trigger cases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
