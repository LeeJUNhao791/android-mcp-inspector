import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


class PortableSourceTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="portable source test ")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.inspector = self.root / "inspector"
        self.toolkit = self.root / "toolkit"
        for repo in (self.inspector, self.toolkit):
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "LICENSE").write_text("MIT fixture\n", encoding="utf-8")
        for name in ("portable-preview.md", "portable-preview.zh-CN.md"):
            path = self.inspector / "docs" / name
            path.parent.mkdir(exist_ok=True)
            path.write_text("Synthetic packaging documentation\n", encoding="utf-8")
        (self.inspector / "server.py").write_text("# synthetic server\n", encoding="utf-8")
        shell = self.toolkit / "example.sh"
        shell.write_bytes(b"#!/bin/sh\necho synthetic\n")
        # A local credential is deliberately untracked and must block packaging.
        for repo in (self.inspector, self.toolkit):
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                            "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)

    def build(self):
        return subprocess.run([
            sys.executable, "-B", str(ROOT / "scripts/build_portable.py"),
            "--inspector", str(self.inspector), "--toolkit", str(self.toolkit),
            "--version", "test.1", "--output-dir", str(self.root / "output"),
        ], capture_output=True, text=True, encoding="utf-8")

    def test_archive_is_reproducible_and_manifest_covers_every_source_file(self):
        first = self.build()
        self.assertEqual(first.returncode, 0, first.stderr)
        output = self.root / "output"
        archive = output / "pageguard-preview-test.1.zip"
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual((output / "SHA256SUMS").read_text().strip(), f"{digest}  {archive.name}")
        with ZipFile(archive) as bundle:
            prefix = "pageguard-preview-test.1/"
            manifest = json.loads(bundle.read(prefix + "bundle-manifest.json"))
            self.assertEqual(set(manifest["files"]),
                             {name.removeprefix(prefix) for name in bundle.namelist()
                              if name != prefix + "bundle-manifest.json"})
            for name, expected in manifest["files"].items():
                self.assertEqual(hashlib.sha256(bundle.read(prefix + name)).hexdigest(), expected)
            self.assertEqual(bundle.read(prefix + "android-sdk-toolkit/example.sh"),
                             b"#!/bin/sh\necho synthetic\n")
            self.assertTrue(all(".git/" not in name for name in bundle.namelist()))
        archive.rename(output / "first.zip")
        output.rename(self.root / "first output")
        self.assertEqual(self.build().returncode, 0)
        self.assertEqual(hashlib.sha256((output / archive.name).read_bytes()).hexdigest(), digest)

    def test_dirty_source_is_rejected_without_creating_output(self):
        (self.toolkit / "private-credential.txt").write_text("synthetic secret", encoding="utf-8")
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("clean", result.stderr)
        self.assertFalse((self.root / "output").exists())

    def test_existing_output_is_preserved(self):
        output = self.root / "output"
        output.mkdir()
        marker = output / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        self.assertNotEqual(self.build().returncode, 0)
        self.assertEqual(marker.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
