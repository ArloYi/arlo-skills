from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release_manager.py"
SKILL_ROOT = Path(__file__).resolve().parents[1]


class ReleaseManagerTests(unittest.TestCase):
    def test_skill_bundle_contains_only_placeholder_network_identity(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL_ROOT.rglob("*")
            if path.is_file()
            and "tests" not in path.relative_to(SKILL_ROOT).parts
            and path.suffix in {".md", ".py", ".yaml"}
        )
        self.assertNotRegex(text, r"/Users/[^/<\s]+|/home/[^/<\s]+|[A-Za-z]:\\Users\\")
        self.assertNotRegex(text, r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
        domains = set(re.findall(r"https?://([^/\s\"'<>]+)", text, re.I))
        self.assertLessEqual(domains, {"github.com", "site.invalid"})

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        self.project.mkdir()
        (self.project / ".codex").mkdir()
        (self.project / "dist").mkdir()
        (self.project / "dist" / "index.html").write_text("hello\n", encoding="utf-8")
        profile = {
            "schema_version": 2,
            "site": {
                "id": "example-site",
                "name": "Example Site",
                "aliases": ["example"],
                "production_url": "https://site.invalid/",
            },
            "repository": {
                "provider": "github",
                "visibility": "private",
                "remote": "origin",
                "branch": "main",
                "url": "https://github.com/example/example-site.git",
            },
            "release": {
                "version_scheme": "vYYYY.MM.DD.N",
                "timezone": "UTC",
                "log_file": "docs/RELEASES.md",
                "tag_successful_release": True,
            },
            "checks": {"commands": [["python3", "-c", "print('ok')"]]},
            "artifacts": [{"source": "dist", "target": "runtime"}],
            "deployment": {
                "provider": "example-provider",
                "method": "verified-project-method",
                "ready": False,
            },
            "verification": {
                "urls": [{"url": "https://site.invalid/", "status": 200}],
                "protected_urls": [],
                "release_manifest_path": "/release.json",
            },
            "rollback": {
                "strategy": "project-defined",
                "verified": False,
                "last_known_good_version": None,
                "infrastructure_backup": None,
            },
            "production": {
                "last_successful_version": None,
                "commit": None,
                "released_at": None,
                "rollback_point": None,
            },
            "approvals": {
                "routine_deploy": "approved",
                "dns_changes": "always-confirm",
                "edge_config_changes": "always-confirm",
                "certificate_changes": "always-confirm",
                "paid_resources": "always-confirm",
                "destructive_sync": "always-confirm",
                "cross_project_changes": "always-confirm",
            },
        }
        (self.project / ".codex" / "release-profile.json").write_text(
            json.dumps(profile, indent=2) + "\n", encoding="utf-8"
        )
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.com")
        self.git("remote", "add", "origin", profile["repository"]["url"])
        self.git("add", ".")
        self.git("commit", "-m", "Initial")
        self.commit = self.git("rev-parse", "HEAD").stdout.strip()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=self.project, check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def run_cli(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], check=check, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def test_stage_uses_public_summary_and_private_manifest(self) -> None:
        stage = Path(self.temp.name) / "stage"
        self.run_cli(
            "stage", "--project", str(self.project), "--output", str(stage),
            "--version", "v2026.08.11.1", "--commit", self.commit,
        )
        public = json.loads((stage / "release.json").read_text(encoding="utf-8"))
        private_path = stage.with_name("stage.manifest.json")
        private = json.loads(private_path.read_text(encoding="utf-8"))
        self.assertNotIn("files", public)
        self.assertEqual(public["artifact_count"], 1)
        self.assertEqual(private["files"][0]["path"], "runtime/index.html")
        self.run_cli("verify-stage", "--stage", str(stage))

        (stage / "runtime" / "index.html").write_text("tampered\n", encoding="utf-8")
        result = self.run_cli("verify-stage", "--stage", str(stage), check=False)
        self.assertNotEqual(result.returncode, 0)

    def test_success_record_is_replaced_by_rollback(self) -> None:
        version = "v2026.08.11.1"
        log_path = self.project / "docs" / "RELEASES.md"
        log_path.parent.mkdir()
        log_path.write_text(
            "# Example Site完整修改日志\n\n"
            "## 当前完整功能\n\n### 1. 发布\n\n- Publish a website\n\n"
            "## 完整迭代时间线\n\n"
            "## 当前仍未开放的功能\n\n- Add deployment analytics\n",
            encoding="utf-8",
        )
        self.run_cli(
            "record", "--project", str(self.project), "--status", "success",
            "--version", version, "--commit", self.commit,
            "--rollback", "v2026.08.10.1", "--change", "Release complete",
            "--change", "Document rollback",
        )
        self.run_cli(
            "record", "--project", str(self.project), "--status", "rolled-back",
            "--version", version, "--commit", self.commit,
            "--rollback", "v2026.08.10.1", "--change", "Rollback completed",
        )
        log = (self.project / "docs" / "RELEASES.md").read_text(encoding="utf-8")
        self.assertEqual(log.count(f"### {version}"), 1)
        self.assertIn("状态：已回滚", log)
        self.assertIn("## 当前完整功能", log)
        self.assertIn("- Publish a website", log)
        self.assertIn("## 当前仍未开放的功能", log)
        self.assertIn("- Add deployment analytics", log)
        self.assertIn("### 本版改动", log)
        self.assertIn("- Rollback completed", log)
        self.assertIn(f"- 代码：`{self.commit}`", log)
        self.assertIn("- 回滚点：`v2026.08.10.1`", log)
        updated = json.loads(
            (self.project / ".codex" / "release-profile.json").read_text(encoding="utf-8")
        )
        self.assertEqual(updated["production"]["commit"], self.commit)
        self.assertEqual(updated["rollback"]["last_known_good_version"], "v2026.08.10.1")

    def test_new_log_uses_complete_history_heading(self) -> None:
        self.run_cli(
            "record", "--project", str(self.project), "--status", "success",
            "--version", "v2026.08.11.1", "--commit", self.commit,
            "--rollback", "pre-launch", "--summary", "Initial release",
        )
        log = (self.project / "docs" / "RELEASES.md").read_text(encoding="utf-8")
        self.assertIn("# 本地完整修改日志", log)
        self.assertIn("## 完整迭代时间线", log)
        self.assertIn("### v2026.08.11.1", log)

    def test_registry_upsert_is_idempotent(self) -> None:
        registry = Path(self.temp.name) / "sites.json"
        for _ in range(2):
            self.run_cli(
                "registry-upsert", "--project", str(self.project),
                "--registry", str(registry),
            )
        value = json.loads(registry.read_text(encoding="utf-8"))
        self.assertEqual(len(value["sites"]), 1)
        self.assertEqual(value["sites"][0]["repository"], "example/example-site")

    def test_incomplete_first_launch_profile_can_be_checked(self) -> None:
        profile_path = self.project / ".codex" / "release-profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile.pop("artifacts")
        profile["site"].pop("production_url")
        profile["checks"]["commands"] = []
        profile["verification"]["urls"] = []
        profile["verification"].pop("release_manifest_path")
        profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

        result = self.run_cli("profile-check", "--project", str(self.project))
        self.assertIn("profile valid", result.stdout)
        self.assertIn("no project checks are configured", result.stderr)


if __name__ == "__main__":
    unittest.main()
