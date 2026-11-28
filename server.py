import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations


CHECKER = Path(__file__).resolve().parent / "vendor/apk-page-size-check/scripts/check_apk.py"
TOOLKIT_ROOT = os.environ.get("ANDROID_SDK_TOOLKIT_ROOT")
mcp = MCPServer("android-mcp-inspector")


@dataclass
class InspectionResult:
    exit_code: int
    report: dict[str, Any]


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
def inspect_apk_16kb(
    apk_path: str, aar_manifest: str | None = None, native_provenance: str | None = None,
) -> InspectionResult:
    """Inspect 16 KB Android ELF and ZIP alignment in an APK you are authorized to inspect.

    Supply the local APK path and, optionally, the same-build AAR manifest and
    native provenance JSON paths. Native provenance requires the AAR manifest.
    The result includes the checker's exit code and complete JSON report.
    """
    command = [sys.executable, "-I", str(CHECKER)]
    if aar_manifest is not None:
        command.append(f"--aar-manifest={aar_manifest}")
    if native_provenance is not None:
        command.append(f"--native-provenance={native_provenance}")

    # Treat a switch-like APK path as a positional argument.
    completed = subprocess.run(
        [*command, "--", apk_path], stdin=subprocess.DEVNULL, capture_output=True,
    )
    return InspectionResult(exit_code=completed.returncode, report=json.loads(completed.stdout))


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
def inspect_android_project_16kb(
    project_root: str, expected_abis: list[str] | None = None,
    source_files: list[str] | None = None,
) -> InspectionResult:
    """Inspect local Android/UTS AARs with the configured Android SDK Toolkit.

    Read-only: no builds, downloads, patches or output files. Optional source_files
    are project-relative C/C++ files for advisory hints, not defect/runtime proof.
    AAR checks do not prove APK ZIP alignment or device behavior. no_matches is
    distinct from pass; elf64_count=0 means no 64-bit alignment was evaluated.
    Returns the complete CLI JSON and exit code, including invalid inputs.
    """
    if not TOOLKIT_ROOT:
        raise ToolError("Configure ANDROID_SDK_TOOLKIT_ROOT with the compatible Toolkit checkout.")
    checker = Path(TOOLKIT_ROOT).resolve() / "skills/android-project-check/scripts/check_project.py"
    if not checker.is_file():
        raise ToolError("ANDROID_SDK_TOOLKIT_ROOT does not contain the project scanner.")
    options = [f"--expect-abi={abi}" for abi in expected_abis or []]
    options += [f"--source-file={name}" for name in source_files or []]
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(checker), *options, "--", project_root],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ToolError("Toolkit project scanner could not finish; check setup or reduce scan inputs.") from error
    try:
        report = json.loads(completed.stdout)
    except (ValueError, UnicodeError) as error:
        raise ToolError("Toolkit project scanner returned no valid JSON; check setup and arguments. "
                           + completed.stderr.decode("utf-8", errors="replace")[:2000]) from error
    if (not isinstance(report, dict)
            or {"pass": 0, "fail": 1, "invalid": 2, "no_matches": 3}.get(report.get("status")) != completed.returncode
            or (source_files and "source_advisories" not in report)):
        raise ToolError("Incompatible Toolkit project report; check ANDROID_SDK_TOOLKIT_ROOT revision.")
    return InspectionResult(exit_code=completed.returncode, report=report)


if __name__ == "__main__":
    mcp.run(transport="stdio")
