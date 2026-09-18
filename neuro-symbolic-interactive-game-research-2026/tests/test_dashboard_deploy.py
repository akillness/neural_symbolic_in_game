"""Exercise release staging without an engine build or a remote deployment."""

import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DashboardDeployTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        self.deploy = self.root / "scripts/deploy_vercel_dashboard.sh"
        shutil.copyfile(ROOT / "scripts/deploy_vercel_dashboard.sh", self.deploy)
        web = self.root / "game-track/web"
        (web / "public").mkdir(parents=True)
        (web / "public/index.pck").write_text("stale export")
        (web / "public/index.wasm").write_text("wasm")
        (web / "public/vercel.json").write_text("private export configuration")
        (web / "dashboard").mkdir()
        (web / "dashboard/index.html").write_text("dashboard")
        (web / "vercel.dashboard.json").write_text('{"outputDirectory":"dist"}')
        for language in ("en", "ko"):
            paper = self.root / f"paper/latex/{language}/main.pdf"
            paper.parent.mkdir(parents=True)
            paper.write_bytes(f"%PDF-{language}".encode())
        builder = self.root / "scripts/build_godot_web.sh"
        builder.write_text(
            '#!/bin/sh\ncd "$(dirname "$0")/.."\n'
            'printf "current export" > game-track/web/public/index.pck\n'
            "touch build-was-run\n"
        )
        builder.chmod(0o755)

    def run_deploy(self, *arguments):
        return subprocess.run(
            ["bash", str(self.deploy), *arguments],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_dry_run_rebuilds_stale_export_and_binds_both_manuscripts(self):
        result = self.run_deploy("--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.root / "build-was-run").is_file())
        self.assertIn(hashlib.sha256(b"current export").hexdigest(), result.stdout)
        self.assertNotIn(hashlib.sha256(b"stale export").hexdigest(), result.stdout)
        for language in ("en", "ko"):
            digest = hashlib.sha256(f"%PDF-{language}".encode()).hexdigest()
            self.assertIn(digest, result.stdout)
            self.assertIn(f"./dist/paper/{language}.pdf", result.stdout)
        self.assertIn("./dist/dashboard/index.html", result.stdout)
        self.assertNotIn("./dist/public/vercel.json", result.stdout)
        self.assertIn("Dry run: not deploying", result.stdout)

    def test_missing_manuscript_stops_before_build_or_deploy(self):
        (self.root / "paper/latex/ko/main.pdf").unlink()
        result = self.run_deploy("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing ko manuscript", result.stderr)
        self.assertFalse((self.root / "build-was-run").exists())

    def test_unknown_option_cannot_accidentally_deploy(self):
        for arguments in (("--dryrun",), ("--dry-run", "unexpected")):
            with self.subTest(arguments=arguments):
                result = self.run_deploy(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn("Usage:", result.stderr)
                self.assertFalse((self.root / "build-was-run").exists())
