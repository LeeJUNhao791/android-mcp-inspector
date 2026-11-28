import asyncio
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED

from mcp import Client, StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "vendor/apk-page-size-check/scripts/check_apk.py"
sys.path.insert(0, str(CHECKER.parent.parent / "tests"))
import test_cli as apk_fixtures
from test_cli import ARM, elf
sys.path.pop(0)


class InspectorStdioTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="android mcp fixtures ")
        self.addCleanup(directory.cleanup)
        self.apk_fixture = apk_fixtures.ApkPageSizeCheck()
        self.apk_fixture.apk = Path(directory.name) / "app build.apk"

    def client(self):
        return Client(StdioServerParameters(
            command=sys.executable, args=[str(ROOT / "server.py")],
            cwd=self.apk_fixture.apk.parent,
        ))

    async def check(self, client, code, status, *, apk_path=None, **paths):
        args = [f"--{name.replace('_', '-')}={path}" for name, path in paths.items()]
        apk = self.apk_fixture.apk if apk_path is None else apk_path
        direct = await asyncio.to_thread(
            subprocess.run, [sys.executable, str(CHECKER), *args, "--", str(apk)],
            cwd=self.apk_fixture.apk.parent, capture_output=True, encoding="utf-8",
        )
        self.assertEqual(direct.returncode, code, direct.stderr or direct.stdout)
        report = json.loads(direct.stdout)
        self.assertEqual(report["status"], status)
        result = await client.call_tool(
            "inspect_apk_16kb", {"apk_path": str(apk), **{key: str(path) for key, path in paths.items()}},
        )
        self.assertFalse(result.is_error, result.content)
        self.assertEqual(result.structured_content, {"exit_code": code, "report": report})
        return report

    async def test_exposes_read_only_inspection_tools(self):
        self.assertTrue((ROOT / "server.py").is_file(), "MCP server entry point is missing")
        async with self.client() as client:
            tools = (await client.list_tools()).tools
            self.assertEqual([tool.name for tool in tools], ["inspect_apk_16kb", "inspect_android_project_16kb"])
            self.assertEqual(set(tools[1].input_schema["properties"]),
                             {"project_root", "expected_abis", "source_files"})
            self.assertEqual(tools[1].input_schema["required"], ["project_root"])
            self.assertTrue(tools[1].annotations.read_only_hint)
            self.assertFalse(tools[1].annotations.open_world_hint)
            self.assertEqual(set(tools[0].input_schema["properties"]),
                             {"apk_path", "aar_manifest", "native_provenance"})
            self.assertEqual(tools[0].input_schema["required"], ["apk_path"])
            self.assertTrue(tools[0].annotations.read_only_hint)

    async def test_preserves_all_four_checker_statuses(self):
        async with self.client() as client:
            self.apk_fixture.fixture((ARM, elf(), ZIP_DEFLATED, None))
            await self.check(client, 0, "pass")
            self.apk_fixture.fixture((ARM, elf(alignment=4096), ZIP_DEFLATED, None))
            await self.check(client, 1, "fail")
            self.apk_fixture.apk.write_bytes(b"invalid APK")
            await self.check(client, 2, "invalid")
            self.apk_fixture.fixture()
            await self.check(client, 3, "not_applicable")

    async def test_preserves_missing_manifest_error_with_provenance(self):
        self.apk_fixture.fixture((ARM, elf(), ZIP_DEFLATED, None))
        async with self.client() as client:
            report = await self.check(client, 2, "invalid", native_provenance="--help")
        self.assertIn("--native-provenance requires --aar-manifest", report["error"])

    async def test_treats_a_switch_like_apk_path_as_a_filename(self):
        self.apk_fixture.apk = self.apk_fixture.apk.with_name("--help build.apk")
        self.apk_fixture.fixture((ARM, elf(), ZIP_DEFLATED, None))
        async with self.client() as client:
            await self.check(client, 0, "pass", apk_path=self.apk_fixture.apk.name)

    async def test_preserves_the_three_origin_states_and_zip_only_failure(self):
        elf_failure = elf(alignment=4096)
        zip_failure = elf()
        shared = "lib/arm64-v8a/libshared.so"
        changed = "lib/arm64-v8a/libchanged.so"
        self.apk_fixture.fixture(
            (ARM, elf_failure, ZIP_DEFLATED, None),
            (shared, zip_failure, ZIP_STORED, 4096),
            (changed, elf_failure + b"different bytes", ZIP_DEFLATED, None),
        )
        primary = self.apk_fixture.aar("first build.aar", {
            "jni/arm64-v8a/libdevice.so": elf_failure,
            "jni/arm64-v8a/libshared.so": zip_failure,
            "jni/arm64-v8a/libchanged.so": elf_failure,
        })
        duplicate = self.apk_fixture.aar("second build.aar", {"jni/arm64-v8a/libshared.so": zip_failure})
        manifest = self.apk_fixture.aar_manifest(("example:first:1", primary), ("example:second:1", duplicate))
        async with self.client() as client:
            report = await self.check(client, 1, "fail", aar_manifest=manifest)
        libraries = {entry["entry"]: entry for entry in report["libraries"]}
        self.assertEqual(libraries[ARM]["origin"]["status"], "single_candidate")
        self.assertEqual(libraries[shared]["origin"]["status"], "multiple_candidates")
        self.assertEqual((libraries[shared]["elf"], libraries[shared]["zip"]), ("pass", "fail"))
        self.assertEqual(libraries[changed]["origin"]["status"], "unknown")
        self.assertEqual(libraries[changed]["origin"]["candidates"], [])

    async def test_verified_strip_chain_wins_over_final_byte_lookalike(self):
        stripped = elf(alignment=4096)
        merged = stripped + b"debug symbols"
        self.apk_fixture.fixture((ARM, stripped, ZIP_DEFLATED, None))
        entry = "jni/arm64-v8a/libdevice.so"
        source = self.apk_fixture.aar("with symbols.aar", {entry: merged})
        lookalike = self.apk_fixture.aar("same final bytes.aar", {entry: stripped})
        manifest = self.apk_fixture.aar_manifest(("example:source:1", source), ("example:lookalike:1", lookalike))
        provenance = self.apk_fixture.apk.with_name("native provenance.json")
        provenance.write_text(json.dumps({
            "variant": "debug",
            "apk_sha256": hashlib.sha256(self.apk_fixture.apk.read_bytes()).hexdigest(),
            "aar_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "libraries": {ARM: {
                "merged_sha256": hashlib.sha256(merged).hexdigest(),
                "stripped_sha256": hashlib.sha256(stripped).hexdigest(),
            }},
        }), encoding="utf-8")
        async with self.client() as client:
            report = await self.check(client, 1, "fail", aar_manifest=manifest, native_provenance=provenance)
        self.assertEqual(report["native_provenance"]["status"], "verified")
        origin = report["libraries"][0]["origin"]
        self.assertEqual(origin["method"], "gradle_strip_chain")
        self.assertEqual(origin["status"], "single_candidate")
        self.assertEqual([candidate["coordinate"] for candidate in origin["candidates"]], ["example:source:1"])
