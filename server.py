import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations


CHECKER = Path(__file__).resolve().parent / "vendor/apk-page-size-check/scripts/check_apk.py"
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
