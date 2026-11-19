#!/usr/bin/env python3
"""Deterministic helpers for website-release-manager v2."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SKILL_STATE = Path.home() / ".codex" / "state" / "website-release-manager"
DEFAULT_REGISTRY = SKILL_STATE / "sites.json"
PROFILE_PATH = Path(".codex/release-profile.json")
SITE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION_RE = re.compile(r"^v(\d{4})\.(\d{2})\.(\d{2})\.(\d+)$")
IP_ADDRESS_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
SENSITIVE_KEYS = {"password", "secret", "token", "private_key", "access_key", "accesskey", "credential"}


class ReleaseError(RuntimeError):
    pass


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReleaseError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseError(f"expected JSON object: {path}")
    return value


def write_json_atomic(path: Path, value: dict) -> None:
    write_text_atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def run(command: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git(project: Path, *args: str) -> str:
    try:
        return run(["git", *args], project).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise ReleaseError(f"git {' '.join(args)} failed: {detail.strip()}") from exc


def project_root(value: str) -> Path:
    candidate = Path(value).expanduser().resolve()
    root = Path(git(candidate, "rev-parse", "--show-toplevel")).resolve()
    if root != candidate:
        raise ReleaseError(f"project must be Git root: expected {root}, got {candidate}")
    return root


def require_object(parent: dict, key: str) -> dict:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ReleaseError(f"profile field '{key}' must be an object")
    return value


def safe_relative(value: str, label: str) -> Path:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ReleaseError(f"{label} must be a safe relative path: {value!r}")
    return path


def sensitive_paths(value: object, prefix: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key).casefold() in SENSITIVE_KEYS:
                findings.append(path)
            findings.extend(sensitive_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(sensitive_paths(child, f"{prefix}[{index}]"))
    elif isinstance(value, str) and "BEGIN " in value and "PRIVATE KEY" in value:
        findings.append(prefix or "<root>")
    return findings


def load_profile(project: Path) -> tuple[Path, dict]:
    path = project / PROFILE_PATH
    return path, read_json(path)


def validate_profile(project: Path, profile: dict) -> list[str]:
    errors: list[str] = []
    secret_fields = sensitive_paths(profile)
    if secret_fields:
        errors.append("credential-like fields are forbidden: " + ", ".join(secret_fields))
    if profile.get("schema_version") != 2:
        errors.append("schema_version must be 2")

    for key in ("site", "repository", "release", "checks", "deployment", "verification"):
        if not isinstance(profile.get(key), dict):
            errors.append(f"{key} must be an object")

    site = profile.get("site", {})
    site_id = site.get("id")
    if not isinstance(site_id, str) or not SITE_ID_RE.fullmatch(site_id):
        errors.append("site.id must be lower-case hyphen-case")
    production_url = site.get("production_url")
    if production_url is not None and not str(production_url).startswith("https://"):
        errors.append("site.production_url must use https when configured")

    repository = profile.get("repository", {})
    for key in ("remote", "branch", "url"):
        if not isinstance(repository.get(key), str) or not repository[key]:
            errors.append(f"repository.{key} is required")

    commands = profile.get("checks", {}).get("commands")
    if not isinstance(commands, list):
        errors.append("checks.commands must be an array")
    elif any(not isinstance(command, list) or not command or any(not isinstance(arg, str) or not arg for arg in command) for command in commands):
        errors.append("each checks.commands entry must be a non-empty string array")

    artifacts = profile.get("artifacts")
    if artifacts is not None and not isinstance(artifacts, list):
        errors.append("artifacts must be an array when configured")
    elif artifacts:
        seen_targets: set[str] = set()
        for index, item in enumerate(artifacts):
            if not isinstance(item, dict):
                errors.append(f"artifacts[{index}] must be an object")
                continue
            try:
                source = safe_relative(str(item.get("source", "")), f"artifacts[{index}].source")
                target = safe_relative(str(item.get("target", "")), f"artifacts[{index}].target")
                if not (project / source).exists():
                    errors.append(f"artifact source missing: {source}")
                target_key = target.as_posix()
                if target_key in seen_targets:
                    errors.append(f"duplicate artifact target: {target_key}")
                seen_targets.add(target_key)
            except ReleaseError as exc:
                errors.append(str(exc))

    deployment = profile.get("deployment", {})
    remote_dir = deployment.get("remote_dir")
    if remote_dir is not None:
        if not isinstance(remote_dir, str) or not remote_dir.startswith("/") or remote_dir in {"/", "/var", "/var/www", "/home"}:
            errors.append("deployment.remote_dir must be a specific absolute website directory when configured")
    ssh_alias = deployment.get("ssh_host_alias")
    if deployment.get("ready") is True:
        if not deployment.get("provider"):
            errors.append("deployment.ready requires deployment.provider")
        if not (deployment.get("method") or deployment.get("strategy")):
            errors.append("deployment.ready requires deployment.method or deployment.strategy")
        if not isinstance(production_url, str) or not production_url.startswith("https://"):
            errors.append("deployment.ready requires site.production_url")

    verification = profile.get("verification", {})
    urls = verification.get("urls")
    if not isinstance(urls, list):
        errors.append("verification.urls must be an array")
    elif deployment.get("ready") is True and not any(verification.get(k) for k in
            ("urls", "protected_urls", "release_manifest_path", "version_command")):
        errors.append("deployment.ready requires online verification")

    release = profile.get("release", {})
    try:
        safe_relative(str(release.get("log_file", "")), "release.log_file")
    except ReleaseError as exc:
        errors.append(str(exc))

    return errors


def profile_warnings(profile: dict) -> list[str]:
    warnings: list[str] = []
    deployment = profile.get("deployment", {})
    rollback = profile.get("rollback", {})
    checks = profile.get("checks", {}).get("commands", [])
    if isinstance(checks, list) and not checks:
        warnings.append("no project checks are configured")
    retention = rollback.get("retention")
    if isinstance(retention, int) and retention < 2:
        warnings.append("rollback.retention should preserve at least one previous successful release when supported")
    ssh_alias = deployment.get("ssh_host_alias")
    if deployment.get("ready") is True and isinstance(ssh_alias, str):
        if "@" in ssh_alias or IP_ADDRESS_RE.fullmatch(ssh_alias):
            warnings.append("direct SSH user/host is less reusable than a named SSH alias")
    if rollback.get("last_known_good") is not None:
        warnings.append("legacy rollback.last_known_good should be split into last_known_good_version and infrastructure_backup")
    branch = profile.get("repository", {}).get("branch")
    if isinstance(branch, str) and branch.startswith(("codex/", "feature/", "fix/")):
        warnings.append(f"production branch looks temporary: {branch}")
    return warnings


def registry_path(value: Optional[str]) -> Path:
    return Path(value).expanduser().resolve() if value else DEFAULT_REGISTRY


def validate_registry(path: Path, registry: dict) -> list[str]:
    errors: list[str] = []
    secret_fields = sensitive_paths(registry)
    if secret_fields:
        errors.append("credential-like fields are forbidden: " + ", ".join(secret_fields))
    if registry.get("schema_version") != 1:
        errors.append("registry schema_version must be 1")
    sites = registry.get("sites")
    if not isinstance(sites, list):
        return errors + ["registry sites must be an array"]
    identities: dict[str, str] = {}
    for index, site in enumerate(sites):
        if not isinstance(site, dict):
            errors.append(f"sites[{index}] must be an object")
            continue
        site_id = site.get("id")
        if not isinstance(site_id, str) or not SITE_ID_RE.fullmatch(site_id):
            errors.append(f"sites[{index}].id is invalid")
            continue
        names = [site_id, str(site.get("name", "")), *site.get("aliases", [])]
        for name in filter(None, names):
            folded = str(name).casefold()
            if folded in identities:
                errors.append(f"duplicate site identity {name!r}: {identities[folded]} and {site_id}")
            identities[folded] = site_id
        root_value = site.get("project_root")
        if not isinstance(root_value, str) or not Path(root_value).expanduser().is_dir():
            errors.append(f"sites[{index}].project_root does not exist")
            continue
        profile_value = site.get("profile", PROFILE_PATH.as_posix())
        try:
            profile_rel = safe_relative(str(profile_value), f"sites[{index}].profile")
            if not (Path(root_value).expanduser() / profile_rel).is_file():
                errors.append(f"sites[{index}] profile does not exist")
        except ReleaseError as exc:
            errors.append(str(exc))
    return errors


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_artifact(project: Path, stage: Path, source_value: str, target_value: str) -> None:
    source_rel = safe_relative(source_value, "artifact source")
    target_rel = safe_relative(target_value, "artifact target")
    unresolved_source = project / source_rel
    if unresolved_source.is_symlink():
        raise ReleaseError(f"top-level artifact may not be a symlink: {source_rel}")
    source = unresolved_source.resolve()
    try:
        source.relative_to(project)
    except ValueError as exc:
        raise ReleaseError(f"artifact escapes project root: {source_rel}") from exc
    target = stage / target_rel
    if source.is_dir():
        nested_symlinks = [path.relative_to(project) for path in source.rglob("*") if path.is_symlink()]
        if nested_symlinks:
            raise ReleaseError(f"artifact directory contains symlink: {nested_symlinks[0]}")
        if target.exists():
            raise ReleaseError(f"artifact target already exists: {target_rel}")
        shutil.copytree(source, target, symlinks=False)
    elif source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise ReleaseError(f"artifact target already exists: {target_rel}")
        shutil.copy2(source, target)
    else:
        raise ReleaseError(f"artifact source is not a regular file or directory: {source_rel}")


def manifest_files(stage: Path) -> list[dict]:
    files: list[dict] = []
    for path in sorted(stage.rglob("*")):
        if path.is_symlink():
            raise ReleaseError(f"staged symlink is not allowed: {path.relative_to(stage)}")
        if path.is_file() and path != stage / "release.json":
            files.append({
                "path": path.relative_to(stage).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            })
    return files


def stage_manifest_path(stage: Path) -> Path:
    return stage.with_name(f"{stage.name}.manifest.json")


def command_profile_check(args: argparse.Namespace) -> None:
    project = project_root(args.project)
    _, profile = load_profile(project)
    errors = validate_profile(project, profile)
    if errors:
        raise ReleaseError("profile invalid:\n- " + "\n- ".join(errors))
    repository = profile["repository"]
    actual_remote = git(project, "remote", "get-url", repository["remote"])
    if actual_remote != repository["url"]:
        raise ReleaseError(f"Git remote mismatch: expected {repository['url']}, got {actual_remote}")
    print(f"profile valid: {profile['site']['id']}")
    for warning in profile_warnings(profile):
        print(f"warning: {warning}", file=sys.stderr)


def command_registry_check(args: argparse.Namespace) -> None:
    path = registry_path(args.registry)
    registry = read_json(path)
    errors = validate_registry(path, registry)
    if errors:
        raise ReleaseError("registry invalid:\n- " + "\n- ".join(errors))
    print(f"registry valid: {len(registry['sites'])} site(s)")


def repository_slug(url: str) -> str:
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not match:
        raise ReleaseError(f"cannot derive GitHub repository from URL: {url}")
    return f"{match.group(1)}/{match.group(2)}"


def command_registry_upsert(args: argparse.Namespace) -> None:
    project = project_root(args.project)
    _, profile = load_profile(project)
    errors = validate_profile(project, profile)
    if errors:
        raise ReleaseError("profile invalid:\n- " + "\n- ".join(errors))
    path = registry_path(args.registry)
    registry = read_json(path) if path.exists() else {"schema_version": 1, "sites": []}
    errors = validate_registry(path, registry) if path.exists() else []
    if errors:
        raise ReleaseError("registry invalid:\n- " + "\n- ".join(errors))
    site = profile["site"]
    entry = {
        "id": site["id"],
        "name": site.get("name", site["id"]),
        "aliases": site.get("aliases", []),
        "project_root": str(project),
        "profile": PROFILE_PATH.as_posix(),
        "repository": repository_slug(profile["repository"]["url"]),
        "production_url": site["production_url"],
    }
    sites = registry.setdefault("sites", [])
    matches = [index for index, existing in enumerate(sites) if existing.get("id") == site["id"]]
    if len(matches) > 1:
        raise ReleaseError(f"registry contains duplicate site id: {site['id']}")
    if matches:
        sites[matches[0]] = entry
        action = "updated"
    else:
        sites.append(entry)
        action = "added"
    sites.sort(key=lambda item: item["id"])
    write_json_atomic(path, registry)
    print(f"registry {action}: {site['id']}")


def command_resolve(args: argparse.Namespace) -> None:
    registry = read_json(registry_path(args.registry))
    errors = validate_registry(registry_path(args.registry), registry)
    if errors:
        raise ReleaseError("registry invalid:\n- " + "\n- ".join(errors))
    needle = args.name.casefold()
    matches = []
    for site in registry["sites"]:
        names = [site["id"], site.get("name", ""), *site.get("aliases", [])]
        if any(str(name).casefold() == needle for name in names):
            matches.append(site)
    if len(matches) != 1:
        raise ReleaseError(f"site resolution expected 1 match, got {len(matches)}")
    print(json.dumps(matches[0], ensure_ascii=False, indent=2))


def command_preflight(args: argparse.Namespace) -> None:
    project = project_root(args.project)
    _, profile = load_profile(project)
    errors = validate_profile(project, profile)
    if errors:
        raise ReleaseError("profile invalid:\n- " + "\n- ".join(errors))
    repository = profile["repository"]
    branch = git(project, "branch", "--show-current")
    if branch != repository["branch"]:
        raise ReleaseError(f"branch mismatch: expected {repository['branch']}, got {branch}")
    actual_remote = git(project, "remote", "get-url", repository["remote"])
    if actual_remote != repository["url"]:
        raise ReleaseError(f"Git remote mismatch: expected {repository['url']}, got {actual_remote}")
    status = git(project, "status", "--porcelain")
    if args.require_clean and status:
        raise ReleaseError("working tree is not clean")
    if args.run_checks:
        for command in profile["checks"]["commands"]:
            print(f"check: {json.dumps(command, ensure_ascii=False)}")
            try:
                completed = run(command, project)
            except subprocess.CalledProcessError as exc:
                sys.stdout.write(exc.stdout or "")
                sys.stderr.write(exc.stderr or "")
                raise ReleaseError(f"check failed: {command[0]}") from exc
            if completed.stdout:
                print(completed.stdout.rstrip())
            if completed.stderr:
                print(completed.stderr.rstrip(), file=sys.stderr)
    print(json.dumps({
        "site": profile["site"]["id"],
        "branch": branch,
        "commit": git(project, "rev-parse", "HEAD"),
        "working_tree_clean": not bool(status),
        "deployment_ready": profile["deployment"].get("ready") is True,
    }, ensure_ascii=False, indent=2))


def command_next_version(args: argparse.Namespace) -> None:
    project = project_root(args.project)
    _, profile = load_profile(project)
    if profile.get("release", {}).get("version_scheme") != "vYYYY.MM.DD.N":
        raise ReleaseError("unsupported version scheme")
    try:
        timezone = ZoneInfo(profile.get("release", {}).get("timezone", "UTC"))
    except ZoneInfoNotFoundError as exc:
        raise ReleaseError("release.timezone is invalid") from exc
    today = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(timezone).date()
    prefix = f"v{today:%Y.%m.%d}."
    previous = profile.get("production", {}).get("last_successful_version")
    sequence = 1
    if isinstance(previous, str) and previous.startswith(prefix):
        match = VERSION_RE.fullmatch(previous)
        if match:
            sequence = int(match.group(4)) + 1
    log_path = release_log_path(project, profile)
    if log_path.exists():
        for n in re.findall(r"^<!-- release:" + re.escape(prefix) + r"(\d+):start -->$",
                            log_path.read_text(encoding="utf-8"), re.MULTILINE):
            sequence = max(sequence, int(n) + 1)
    print(f"{prefix}{sequence}")


def command_stage(args: argparse.Namespace) -> None:
    project = project_root(args.project)
    _, profile = load_profile(project)
    errors = validate_profile(project, profile)
    if errors:
        raise ReleaseError("profile invalid:\n- " + "\n- ".join(errors))
    current_commit = git(project, "rev-parse", "HEAD")
    if current_commit != args.commit:
        raise ReleaseError(f"commit mismatch: HEAD is {current_commit}")
    if git(project, "status", "--porcelain"):
        raise ReleaseError("stage requires a clean working tree")
    stage = Path(args.output).expanduser().resolve()
    if stage.exists() and any(stage.iterdir()):
        raise ReleaseError(f"stage directory must be empty: {stage}")
    stage.mkdir(parents=True, exist_ok=True)
    artifacts = profile.get("artifacts", [])
    if not artifacts:
        raise ReleaseError("stage requires at least one configured artifact; use the project's native deployment path otherwise")
    for artifact in artifacts:
        copy_artifact(project, stage, artifact["source"], artifact["target"])
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    internal_manifest = {
        "schema_version": 1,
        "site_id": profile["site"]["id"],
        "version": args.version,
        "commit": args.commit,
        "generated_at": generated_at,
        "files": manifest_files(stage),
    }
    manifest_path = stage_manifest_path(stage)
    if manifest_path.exists():
        raise ReleaseError(f"internal manifest already exists: {manifest_path}")
    write_json_atomic(manifest_path, internal_manifest)
    public_release = {
        "schema_version": 2,
        "site_id": profile["site"]["id"],
        "version": args.version,
        "commit": args.commit,
        "generated_at": generated_at,
        "artifact_count": len(internal_manifest["files"]),
        "manifest_sha256": sha256(manifest_path),
    }
    write_json_atomic(stage / "release.json", public_release)
    print(json.dumps({
        "stage": str(stage),
        "internal_manifest": str(manifest_path),
        "files": len(internal_manifest["files"]),
        "version": args.version,
        "commit": args.commit,
    }, ensure_ascii=False, indent=2))


def command_verify_stage(args: argparse.Namespace) -> None:
    stage = Path(args.stage).expanduser().resolve()
    release = read_json(stage / "release.json")
    if isinstance(release.get("files"), list):
        expected = release["files"]
        manifest_path = None
    else:
        manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else stage_manifest_path(stage)
        manifest = read_json(manifest_path)
        for field in ("site_id", "version", "commit", "generated_at"):
            if manifest.get(field) != release.get(field):
                raise ReleaseError(f"public release and internal manifest disagree on {field}")
        expected = manifest.get("files")
        if not isinstance(expected, list):
            raise ReleaseError("internal manifest files must be an array")
        if release.get("artifact_count") != len(expected):
            raise ReleaseError("public release artifact_count does not match internal manifest")
        if release.get("manifest_sha256") != sha256(manifest_path):
            raise ReleaseError("public release manifest_sha256 does not match internal manifest")
    actual = manifest_files(stage)
    if actual != expected:
        raise ReleaseError("staged files do not match internal manifest")
    print(f"stage valid: {len(actual)} file(s), {release.get('version')}, {release.get('commit')}")


def open_remote(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "website-release-manager/2", "Cache-Control": "no-cache"})
    context = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or None)
    return urllib.request.urlopen(request, timeout=15, context=context)


def fetch_json(url: str) -> tuple[int, dict]:
    try:
        with open_remote(url) as response:
            status = response.status
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"failed to fetch JSON {url}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReleaseError(f"expected JSON object from {url}")
    return status, data


def fetch_status(url: str) -> int:
    try:
        with open_remote(url) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError as exc:
        raise ReleaseError(f"failed to fetch {url}: {exc}") from exc


def command_verify_remote(args: argparse.Namespace) -> None:
    project = project_root(args.project)
    _, profile = load_profile(project)
    result = verify_remote(project, profile, args.version, args.commit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["version_verified"]:
        raise ReleaseError("site reachable; version pending")


def verify_remote(project: Path, profile: dict, version: str, commit: str) -> dict:
    verification = profile["verification"]
    manifest_path = verification.get("release_manifest_path")
    manifest_result = "not configured"
    if manifest_path:
        base = profile["site"].get("production_url", "").rstrip("/")
        if not base:
            raise ReleaseError("pending verification: site.production_url is missing")
        status, remote = fetch_json(base + "/" + str(manifest_path).lstrip("/"))
        if status != 200 or remote.get("version") != version or remote.get("commit") != commit:
            raise ReleaseError("remote release marker does not match expected version and commit")
        manifest_result = "match"
    command = verification.get("version_command")
    if command is not None:
        if not isinstance(command, list) or not command or not all(isinstance(arg, str) and arg for arg in command):
            raise ReleaseError("verification.version_command must be a non-empty argument array")
        try:
            result = subprocess.run(command, cwd=project, capture_output=True, text=True, check=True, timeout=30)
            observed = json.loads(result.stdout)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            raise ReleaseError("production version command failed or returned invalid JSON") from exc
        if not isinstance(observed, dict) or observed.get("version") != version or observed.get("commit") != commit:
            raise ReleaseError("production version command did not confirm the expected version and commit")
    results = []
    for check in [*profile["verification"].get("urls", []), *profile["verification"].get("protected_urls", [])]:
        actual = fetch_status(check["url"])
        expected = int(check.get("status", 200))
        results.append({"url": check["url"], "expected": expected, "actual": actual})
        if actual != expected:
            raise ReleaseError(f"unexpected status for {check['url']}: {actual}, expected {expected}")
    matched = manifest_result == "match" or command is not None
    if not results and not matched:
        raise ReleaseError("pending verification: no production checks configured")
    return {"version_verified": matched, "release_manifest": manifest_result, "checks": results}


def release_log_path(project: Path, profile: dict) -> Path:
    log_rel = safe_relative(profile["release"]["log_file"], "release.log_file")
    return project / log_rel


def release_entry(history: str, version: str):
    return re.search(
        r"^<!-- release:" + re.escape(version) + r":start -->\n.*?^<!-- release:"
        + re.escape(version) + r":end -->$", history, re.MULTILINE | re.DOTALL,
    )


def entry_field(entry: str, label: str) -> Optional[str]:
    match = re.search(r"^- " + label + r"：`([^`\n]+)`$", entry, re.MULTILINE)
    return match.group(1) if match else None


def command_record(args: argparse.Namespace) -> None:
    project = project_root(args.project)
    lock = project / PROFILE_PATH.parent / ".release-record.lock"
    try:
        lock.mkdir()
    except FileNotFoundError:
        raise ReleaseError(f"missing project profile: {PROFILE_PATH}") from None
    except FileExistsError:
        raise ReleaseError("release record busy: another writer holds .release-record.lock") from None
    try:
        record_verified(project, args)
    finally:
        lock.rmdir()


def record_verified(project: Path, args: argparse.Namespace) -> None:
    profile_path, profile = load_profile(project)
    errors = validate_profile(project, profile)
    if errors:
        raise ReleaseError("profile invalid:\n- " + "\n- ".join(errors))
    try:
        timezone = ZoneInfo(profile.get("release", {}).get("timezone", "UTC"))
    except ZoneInfoNotFoundError as exc:
        raise ReleaseError("release.timezone is invalid") from exc
    now = dt.datetime.now(timezone).replace(microsecond=0)
    log_path = release_log_path(project, profile)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    changes = args.change or ([args.summary] if args.summary else [])
    if not changes:
        raise ReleaseError("record requires --change or --summary")
    if not args.commit:
        raise ReleaseError("--commit is required for release records")
    history = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    match = release_entry(history, args.version)
    original = match.group() if match else ""
    if match and entry_field(original, "代码") != args.commit:
        raise ReleaseError("version already recorded with a different commit")
    active_version, active_commit, fallback = args.version, args.commit, args.rollback
    if args.status == "rolled-back":
        if not match or not args.rollback or args.rollback == args.version:
            raise ReleaseError("rollback needs a recorded source and a distinct destination")
        target = release_entry(history, args.rollback)
        recorded_commit = entry_field(target.group(), "代码") if target else None
        if args.rollback_commit and recorded_commit and args.rollback_commit != recorded_commit:
            raise ReleaseError("rollback destination conflicts with release history")
        active_version, active_commit = args.rollback, recorded_commit or args.rollback_commit
        if not active_commit:
            raise ReleaseError("missing destination SHA: supply --rollback-commit for a legacy target")
        fallback = entry_field(target.group(), "回滚点") if target else None
        current = profile.get("production", {})
        source_matches = (current.get("last_successful_version"), current.get("commit")) == (args.version, args.commit)
        retry_matches = ("- 状态：已回滚" in original.splitlines() and
                         (current.get("last_successful_version"), current.get("commit")) == (active_version, active_commit))
        if not source_matches and not retry_matches:
            raise ReleaseError("rollback source is not the recorded production version")
    evidence = verify_remote(project, profile, active_version, active_commit)
    if not evidence["version_verified"]:
        raise ReleaseError("site reachable; version pending: configure release_manifest_path or version_command")
    marker_start = f"<!-- release:{args.version}:start -->"
    marker_end = f"<!-- release:{args.version}:end -->"
    lines = [
        marker_start,
        f"### {args.version} — {now.date().isoformat()}",
        "",
        "- 状态：成功",
        f"- 网站：{profile['site'].get('production_url', '未配置')}",
        f"- 代码：`{args.commit}`",
        f"- 时间：{now.isoformat()}",
    ]
    if args.rollback:
        lines.append(f"- 回滚点：`{args.rollback}`")
    lines.extend(["", "### 本版改动", "", *[f"- {change}" for change in changes]])
    lines.extend([marker_end, ""])
    block = "\n".join(lines)
    existing = history
    if args.status == "rolled-back":
        destination = f"- 回滚后线上：`{active_version}` / `{active_commit}`"
        if "- 状态：已回滚" in original.splitlines():
            if destination not in original.splitlines():
                raise ReleaseError("existing rollback record has a different or unknown destination")
            updated = existing
        else:
            prior = original.removesuffix(marker_end).replace("- 状态：成功\n", "- 状态：已回滚\n", 1)
            event = ["", "#### 回滚记录", "", f"- 回滚时间：{now.isoformat()}", destination,
                     *[f"- {item}" for item in changes], marker_end]
            updated = existing[:match.start()] + prior + "\n".join(event) + existing[match.end():]
    elif match:
        if "- 状态：成功" not in original.splitlines():
            raise ReleaseError("release version already rolled back; use a new version")
        updated = existing
    else:
        if re.search(rf"^##+\s+{re.escape(args.version)}(?:\s|$)", existing, flags=re.MULTILINE):
            raise ReleaseError(f"release log contains an unmanaged entry for {args.version}")
        if not existing:
            existing = "# 本地完整修改日志\n\n## 完整迭代时间线\n"
        timeline = re.search(r"^## 完整迭代时间线\s*$", existing, re.MULTILINE)
        following = re.compile(r"^## ", re.MULTILINE).search(existing, timeline.end()) if timeline else None
        pos = following.start() if following else len(existing)
        updated = existing[:pos].rstrip() + "\n\n" + block + "\n" + existing[pos:]
    # Preserve the event timestamp on retries, including recovery after a profile write failure.
    event_label = "回滚时间" if args.status == "rolled-back" else "时间"
    event_time = re.search(r"^- " + event_label + r"：(.+)$", release_entry(updated, args.version).group(), re.MULTILINE)
    if not event_time:
        raise ReleaseError("release history is missing its event time")
    snapshot = (f"<!-- production:start -->\n当前线上版本：`{active_version}` · "
                f"代码：`{active_commit}`\n<!-- production:end -->")
    snapshot_pattern = r"^<!-- production:start -->\n.*?^<!-- production:end -->$"
    if re.search(snapshot_pattern, updated, re.MULTILINE | re.DOTALL):
        updated = re.sub(snapshot_pattern, lambda _: snapshot, updated, count=1, flags=re.MULTILINE | re.DOTALL)
    else:
        title, _, rest = updated.partition("\n")
        updated = f"{title}\n\n{snapshot}\n{rest}"
    profile.setdefault("production", {}).update(last_successful_version=active_version, commit=active_commit,
                                                released_at=event_time.group(1), rollback_point=fallback)
    profile.setdefault("rollback", {})["last_known_good_version"] = active_version if args.status == "rolled-back" else fallback
    write_text_atomic(log_path, updated.rstrip() + "\n")
    write_json_atomic(profile_path, profile)
    print(f"recorded {args.status}: {args.version}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    profile_check = sub.add_parser("profile-check")
    profile_check.add_argument("--project", required=True)
    profile_check.set_defaults(func=command_profile_check)

    registry_check = sub.add_parser("registry-check")
    registry_check.add_argument("--registry")
    registry_check.set_defaults(func=command_registry_check)

    registry_upsert = sub.add_parser("registry-upsert")
    registry_upsert.add_argument("--project", required=True)
    registry_upsert.add_argument("--registry")
    registry_upsert.set_defaults(func=command_registry_upsert)

    resolve = sub.add_parser("resolve")
    resolve.add_argument("name")
    resolve.add_argument("--registry")
    resolve.set_defaults(func=command_resolve)

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--project", required=True)
    preflight.add_argument("--run-checks", action="store_true")
    preflight.add_argument("--require-clean", action="store_true")
    preflight.set_defaults(func=command_preflight)

    next_version = sub.add_parser("next-version")
    next_version.add_argument("--project", required=True)
    next_version.add_argument("--date")
    next_version.set_defaults(func=command_next_version)

    stage = sub.add_parser("stage")
    stage.add_argument("--project", required=True)
    stage.add_argument("--output", required=True)
    stage.add_argument("--version", required=True)
    stage.add_argument("--commit", required=True)
    stage.set_defaults(func=command_stage)

    verify_stage = sub.add_parser("verify-stage")
    verify_stage.add_argument("--stage", required=True)
    verify_stage.add_argument("--manifest")
    verify_stage.set_defaults(func=command_verify_stage)

    verify_remote = sub.add_parser("verify-remote")
    verify_remote.add_argument("--project", required=True)
    verify_remote.add_argument("--version", required=True)
    verify_remote.add_argument("--commit", required=True)
    verify_remote.set_defaults(func=command_verify_remote)

    record = sub.add_parser("record")
    record.add_argument("--project", required=True)
    record.add_argument("--status", choices=("success", "rolled-back"), required=True)
    record.add_argument("--version", required=True)
    record.add_argument("--commit")
    record.add_argument("--rollback")
    record.add_argument("--rollback-commit", help="destination SHA if the older release has no managed log entry")
    record.add_argument("--summary")
    record.add_argument("--change", action="append", default=[])
    record.set_defaults(func=command_record)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args.func(args)
    except ReleaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
