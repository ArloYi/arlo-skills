from __future__ import annotations

import json
import functools
import http.server
import os
from pathlib import Path
import re
import subprocess
import ssl
import sys
import tempfile
import threading
import urllib.request
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
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=getattr(self, "cli_env", None),
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

    def start_test_site(self):
        root = Path(self.temp.name)
        cert, key = root / "cert.pem", root / "key.pem"
        config = root / "openssl.cnf"
        config.write_text("[req]\ndistinguished_name=dn\nx509_extensions=ext\n[dn]\n[ext]\n"
                          "subjectAltName=DNS:localhost\nbasicConstraints=critical,CA:TRUE\n")
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                        "-subj", "/CN=localhost", "-config", str(config), "-out", str(cert),
                        "-keyout", str(key)], check=True, capture_output=True)
        current = root / "current"
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(current))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.addCleanup(server.server_close)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(worker.join)
        self.addCleanup(server.shutdown)
        self.cli_env = {**os.environ, "SSL_CERT_FILE": str(cert), "no_proxy": "localhost"}
        url = f"https://localhost:{server.server_port}"
        profile_path = self.project / ".codex" / "release-profile.json"
        profile = json.loads(profile_path.read_text())
        profile["site"]["production_url"] = url
        profile["verification"]["urls"] = [{"url": url + "/runtime/index.html", "status": 200}]
        profile_path.write_text(json.dumps(profile))
        return current, url, ssl.create_default_context(cafile=str(cert))

    def test_live_release_then_rollback(self) -> None:
        current, url, tls = self.start_test_site()
        log_path = self.project / "docs" / "RELEASES.md"
        log_path.parent.mkdir()
        log_path.write_text(
            "# Example Site完整修改日志\n\n"
            "## 当前完整功能\n\n### 1. 发布\n\n- Publish a website\n\n"
            "## 完整迭代时间线\n\n"
            "## 当前仍未开放的功能\n\n- Add deployment analytics\n",
            encoding="utf-8",
        )
        first = "v2026.08.11.1"
        version = "v2026.08.11.2"
        commits = {}
        def activate(v):
            candidate = current.with_name("candidate")
            candidate.symlink_to(current.with_name(v))
            candidate.replace(current)

        for v, content, previous in [(first, "page A", "pre-launch"), (version, "page B", first)]:
            (self.project / "dist/index.html").write_text(content)
            self.git("add", ".")
            self.git("commit", "-m", v)
            sha = self.git("rev-parse", "HEAD").stdout.strip()
            commits[v] = sha
            stage = current.with_name(v)
            self.run_cli("stage", "--project", str(self.project), "--output", str(stage),
                         "--version", v, "--commit", sha)
            self.run_cli("verify-stage", "--stage", str(stage))
            activate(v)
            with urllib.request.urlopen(url + "/runtime/index.html", context=tls) as response:
                self.assertEqual(response.read().decode(), content)
            self.run_cli("record", "--project", str(self.project), "--status", "success",
                         "--version", v, "--commit", sha, "--rollback", previous, "--change", content)
        original = log_path.read_text()
        b_time = original.split(f"<!-- release:{version}:start -->")[1].split("- 时间：")[1].splitlines()[0]
        rollback = ["record", "--project", str(self.project), "--status", "rolled-back",
                    "--version", version, "--commit", commits[version], "--rollback", first,
                    "--change", "Rollback completed"]
        self.assertNotEqual(self.run_cli(*rollback, check=False).returncode, 0)
        self.assertEqual(log_path.read_text(), original)
        activate(first)
        self.run_cli(*rollback)
        self.run_cli(*rollback)
        with urllib.request.urlopen(url + "/release.json", context=tls) as response:
            live = json.load(response)
        with urllib.request.urlopen(url + "/runtime/index.html", context=tls) as response:
            self.assertEqual(response.read(), b"page A")
        log = (self.project / "docs" / "RELEASES.md").read_text(encoding="utf-8")
        self.assertEqual(log.count(f"### {version}"), 1)
        self.assertIn("状态：已回滚", log)
        self.assertIn("## 当前完整功能", log)
        self.assertIn("- Publish a website", log)
        self.assertIn("## 当前仍未开放的功能", log)
        self.assertIn("- Add deployment analytics", log)
        self.assertIn("### 本版改动", log)
        self.assertIn("- Rollback completed", log)
        self.assertIn(f"- 代码：`{commits[version]}`", log)
        self.assertIn("- page B", log)
        self.assertIn(f"- 时间：{b_time}", log.split(f"<!-- release:{version}:start -->")[1])
        self.assertEqual(log.count("#### 回滚记录"), 1)
        self.assertIn(f"- 回滚后线上：`{first}` / `{commits[first]}`", log)
        self.assertEqual(re.findall(r"当前线上版本：`([^`]+)` · 代码：`([^`]+)`", log),
                         [(live["version"], live["commit"])])
        updated = json.loads(
            (self.project / ".codex" / "release-profile.json").read_text(encoding="utf-8")
        )
        self.assertEqual((live["version"], live["commit"]), (first, commits[first]))
        self.assertEqual(updated["production"]["commit"], live["commit"])
        self.assertEqual(updated["production"]["last_successful_version"], live["version"])
        self.assertEqual(self.run_cli("next-version", "--project", str(self.project),
                                      "--date", "2026-08-11").stdout.strip(), "v2026.08.11.3")
        print(f"HTTPS rehearsal: A {commits[first][:8]} -> B {commits[version][:8]} -> A {live['commit'][:8]}; "
              "page, manifest, profile and log agree")

    def test_new_log_uses_complete_history_heading(self) -> None:
        profile_path = self.project / ".codex/release-profile.json"
        profile = json.loads(profile_path.read_text())
        profile["verification"] = {"urls": [], "version_command": [sys.executable, "-c",
            "import json; print(json.dumps(" + repr({"version": "v2026.08.11.1", "commit": self.commit}) + "))"]}
        profile_path.write_text(json.dumps(profile))
        self.run_cli(
            "record", "--project", str(self.project), "--status", "success",
            "--version", "v2026.08.11.1", "--commit", self.commit,
            "--rollback", "pre-launch", "--summary", "Initial release",
        )
        log = (self.project / "docs" / "RELEASES.md").read_text(encoding="utf-8")
        self.assertIn("# 本地完整修改日志", log)
        self.assertIn("## 完整迭代时间线", log)
        self.assertIn("### v2026.08.11.1", log)

    def test_empty_checks_and_status_only_cannot_record_release(self):
        current, url, _ = self.start_test_site()
        current.symlink_to(self.project / "dist")
        path = self.project / ".codex/release-profile.json"
        profile = json.loads(path.read_text())
        for urls in ([], [{"url": url + "/index.html"}]):
            profile["verification"] = {"urls": urls}
            before = json.dumps(profile)
            path.write_text(before)
            args = ["--project", str(self.project), "--version", "test", "--commit", self.commit]
            result = self.run_cli("verify-remote", *args, check=False)
            if urls:
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(json.loads(result.stdout)["version_verified"])
            else:
                self.assertNotEqual(result.returncode, 0)
            self.assertNotEqual(self.run_cli("record", *args, "--status", "success", "--change", "test",
                                             check=False).returncode, 0)
            self.assertFalse((self.project / "docs/RELEASES.md").exists())
            self.assertEqual(path.read_text(), before)

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
