"""Verify the pinned MediaPipe debug APK through the released Inspector CLI and MCP server."""

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


ABIS = ("arm64-v8a", "armeabi-v7a", "x86", "x86_64")
COORDINATE = "com.google.mediapipe:tasks-core:1.2.2"
TIMEOUT_SECONDS = 120


async def inspect_over_stdio(inspector, paths):
    server = StdioServerParameters(
        command=sys.executable, args=["-B", str(inspector / "server.py")], cwd=inspector,
    )
    async with asyncio.timeout(TIMEOUT_SECONDS):
        async with Client(server, read_timeout_seconds=TIMEOUT_SECONDS) as client:
            return await client.call_tool("inspect_apk_16kb", paths)


def verify(inspector, paths):
    checker = inspector / "vendor/apk-page-size-check/scripts/check_apk.py"
    if not checker.is_file() or not (inspector / "server.py").is_file():
        raise ValueError("--inspector must point to a released Inspector checkout.")

    direct = subprocess.run(
        [sys.executable, "-I", str(checker), f"--aar-manifest={paths['aar_manifest']}",
         f"--native-provenance={paths['native_provenance']}", "--", paths["apk_path"]],
        cwd=inspector, stdin=subprocess.DEVNULL, capture_output=True, timeout=TIMEOUT_SECONDS,
    )
    if direct.returncode != 0:
        raise ValueError(f"Expected CLI exit code 0, got {direct.returncode}.")
    report = json.loads(direct.stdout)

    try:
        result = asyncio.run(inspect_over_stdio(inspector, paths))
    except TimeoutError as error:
        raise ValueError("MCP stdio verification timed out.") from error
    except Exception as error:
        raise ValueError(f"MCP stdio call failed ({type(error).__name__}).") from error
    if result.is_error:
        raise ValueError("MCP stdio returned a tool error.")
    if result.structured_content != {"exit_code": 0, "report": report}:
        raise ValueError("MCP stdio exit code or full JSON report differs from the CLI.")

    if (report.get("status"), report.get("page_size")) != ("pass", 16384):
        raise ValueError("Expected a passing 16384-byte alignment report.")
    provenance = report.get("native_provenance", {})
    if (provenance.get("status"), provenance.get("variant")) != ("verified", "debug"):
        raise ValueError("Expected verified debug native provenance.")

    libraries = {library["entry"]: library for library in report["libraries"]}
    origins = {}
    for abi in ABIS:
        entry = f"lib/{abi}/libmediapipe_tasks_jni.so"
        origin = libraries.get(entry, {}).get("origin", {})
        candidates = [candidate["coordinate"] for candidate in origin.get("candidates", [])]
        if (origin.get("status"), origin.get("method"), candidates) != (
            "single_candidate", "gradle_strip_chain", [COORDINATE],
        ):
            raise ValueError(f"Expected {entry} to resolve to {COORDINATE} via gradle_strip_chain.")
        origins[abi] = {"method": origin["method"], "coordinate": candidates[0]}

    summary = {
        "cli_exit_code": direct.returncode,
        "mcp_exit_code": result.structured_content["exit_code"],
        "reports_equal": True,
        "status": report["status"],
        "page_size": report["page_size"],
        "native_provenance": {"status": provenance["status"], "variant": provenance["variant"]},
        "libmediapipe_tasks_jni.so": origins,
    }
    for name, path in paths.items():
        with Path(path).open("rb") as stream:
            summary[f"{name.removesuffix('_path')}_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("inspector", "apk", "aar-manifest", "native-provenance"):
        parser.add_argument(f"--{option}", required=True, type=Path)
    args = parser.parse_args()
    try:
        inspector = args.inspector.resolve()
        if inspector == Path(__file__).resolve().parents[1]:
            raise ValueError("--inspector must point to a separate released checkout.")
        paths = {
            "apk_path": str(args.apk.resolve()),
            "aar_manifest": str(args.aar_manifest.resolve()),
            "native_provenance": str(args.native_provenance.resolve()),
        }
        summary = verify(inspector, paths)
    except subprocess.TimeoutExpired:
        sys.exit("MediaPipe verification failed: CLI timed out.")
    except (OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(f"MediaPipe verification failed: {error}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
