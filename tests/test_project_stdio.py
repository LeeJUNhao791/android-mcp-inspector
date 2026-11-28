import asyncio
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from mcp import Client, StdioServerParameters
from test_stdio import elf

ROOT = Path(__file__).resolve().parents[1]
TOOLKIT = os.environ.get("ANDROID_SDK_TOOLKIT_ROOT")


class ProjectStdioTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="project mcp fixtures ")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name) / "--project with spaces"
        self.root.mkdir()
        self.assertTrue(TOOLKIT, "Set ANDROID_SDK_TOOLKIT_ROOT to the compatible Toolkit checkout")
        self.checker = Path(TOOLKIT) / "skills/android-project-check/scripts/check_project.py"

    def client(self, toolkit=TOOLKIT):
        return Client(StdioServerParameters(
            command=sys.executable, args=[str(ROOT / "server.py")], cwd=self.root.parent,
            env={**os.environ, "ANDROID_SDK_TOOLKIT_ROOT": toolkit or ""},
        ))

    def aar(self, name="device.aar", alignment=16384):
        path = self.root / "app/libs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(path, "w") as archive:
            archive.writestr("AndroidManifest.xml", "synthetic fixture")
            if alignment is not None:
                archive.writestr("jni/arm64-v8a/libdevice.so", elf(alignment=alignment))
        return path

    def snapshot(self):
        return {path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob("*") if path.is_file()}

    async def check(self, client, code, status, *, project=None, expected_abis=None, source_files=None):
        project = project or str(self.root)
        options = [f"--expect-abi={abi}" for abi in expected_abis or []]
        options += [f"--source-file={name}" for name in source_files or []]
        before = self.snapshot()
        direct = await asyncio.to_thread(subprocess.run,
            [sys.executable, "-I", "-B", str(self.checker), *options, "--", project],
            cwd=self.root.parent, capture_output=True, encoding="utf-8", timeout=120)
        self.assertEqual(direct.returncode, code, direct.stderr or direct.stdout)
        report = json.loads(direct.stdout)
        self.assertEqual(report["status"], status)
        result = await client.call_tool("inspect_android_project_16kb", {
            "project_root": project, "expected_abis": expected_abis, "source_files": source_files,
        })
        self.assertFalse(result.is_error, result.content)
        self.assertEqual(result.structured_content, {"exit_code": code, "report": report})
        self.assertEqual(self.snapshot(), before)
        for artifact in report["artifacts"]:
            self.assertEqual(artifact["sha256"], before[artifact["source"]])
        return report

    async def test_project_statuses_hashes_and_no_elf_preserve_full_cli_reports(self):
        async with self.client() as client:
            await self.check(client, 3, "no_matches")
            self.aar()
            await self.check(client, 0, "pass", project=self.root.name)
            self.aar(alignment=4096)
            report = await self.check(client, 1, "fail")
            self.assertEqual(report["artifacts"][0]["libraries"][0]["load_issues"][0]["p_align"], 4096)
            self.aar("java.aar", alignment=None)
            broken = self.root / "app/libs/broken.aar"
            broken.write_bytes(b"invalid synthetic AAR")
            report = await self.check(client, 2, "invalid")
            self.assertEqual([item["status"] for item in report["artifacts"]], ["invalid", "fail", "pass"])
            broken.unlink()
            self.aar(alignment=None)
            report = await self.check(client, 0, "pass")
            self.assertTrue(all(item["elf64_count"] == 0 and not item["libraries"] for item in report["artifacts"]))
            await self.check(client, 1, "fail", expected_abis=["arm64-v8a"])
            await self.check(client, 2, "invalid", project=str(self.root / "missing"))

    async def test_source_hints_are_advisory_with_no_matches_and_java_aar(self):
        (self.root / "pages.cpp").write_text("#define PAGE_SIZE 4096\nchar buffer[4096];\n", encoding="utf-8")
        async with self.client() as client:
            report = await self.check(client, 3, "no_matches", source_files=["pages.cpp"])
            self.assertEqual(report["source_advisories"]["hints"],
                [{"source": "pages.cpp", "line": 1, "rule": "page_size_definition"}])
            self.aar(alignment=None)
            await self.check(client, 0, "pass", source_files=["pages.cpp"])
            report = await self.check(client, 2, "invalid", source_files=["../pages.cpp"])
            self.assertEqual(report["artifacts"][0]["status"], "pass")

    async def test_missing_toolkit_is_a_tool_error_and_apk_tool_stays_available(self):
        for toolkit in (None, str(self.root / "missing toolkit")):
            async with self.client(toolkit) as client:
                result = await client.call_tool("inspect_android_project_16kb", {"project_root": str(self.root)})
                self.assertTrue(result.is_error)
                self.assertIsNone(result.structured_content)
                self.assertIn("ANDROID_SDK_TOOLKIT_ROOT", str(result.content))
                apk = await client.call_tool("inspect_apk_16kb", {"apk_path": str(self.root / "missing.apk")})
                self.assertFalse(apk.is_error)
                self.assertEqual(apk.structured_content["report"]["status"], "invalid")

    async def test_bad_options_and_request_limits_are_tool_errors(self):
        async with self.client() as client:
            for extra in ({"expected_abis": ["--help"]}, {"source_files": ["pages.cpp"] * 101}):
                result = await client.call_tool("inspect_android_project_16kb", {"project_root": str(self.root), **extra})
                self.assertTrue(result.is_error)
                self.assertIsNone(result.structured_content)
