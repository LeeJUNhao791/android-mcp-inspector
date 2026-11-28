# PageGuard paired source preview

[简体中文](https://github.com/LeeJUNhao791/android-mcp-inspector/blob/main/docs/portable-preview.zh-CN.md)

This preview pairs Android MCP Inspector with a compatible Android SDK Toolkit.
It is a source ZIP, not a release, registry package or self-contained executable.
Python and the pinned MCP dependencies are installed separately. No Android SDK,
Gradle build, device, account, API key or model download is required for inspection.

The ZIP contains `android-mcp-inspector/`, `android-sdk-toolkit/`, both READMEs and
`bundle-manifest.json`. The manifest records both exact Git commits and SHA-256
for every other bundled file. `SHA256SUMS` beside the ZIP records its SHA-256.
Keep the directories together: the Toolkit's sibling Skills are required.
Each repository retains its MIT `LICENSE`; Inspector's existing vendored APK
checker and attribution in its README are retained.

## Extract and set up

Verify the ZIP hash against the independently supplied `SHA256SUMS` before
extracting. In PowerShell use `Get-FileHash <zip> -Algorithm SHA256`; on Linux
use `sha256sum -c SHA256SUMS`. Extract into a new directory outside the source
checkouts. Paths containing spaces are supported.

The tested environments are Windows with Python 3.11.4 or 3.12.7 and MCP 2.3.0. The exact
MCP runtime dependency closure is `android-mcp-inspector/requirements-portable.txt`
(29 Windows distributions; `pywin32` is conditional). Python 3.11+ is required
by Inspector; other Python/platform combinations require their own verification.
The Linux commands below describe the equivalent setup, not a Linux acceptance result.

Windows (PowerShell), from the extracted root:

```powershell
Set-Location 'C:/PageGuard/pageguard-preview-2026.11.28.1'
$pageguardEnv = Join-Path (Split-Path $PWD -Parent) 'pageguard-venv'
python -m venv $pageguardEnv
$pageguardPython = Join-Path $pageguardEnv 'Scripts/python.exe'
& $pageguardPython -m pip install -r android-mcp-inspector/requirements-portable.txt
& $pageguardPython -m pip check
$env:ANDROID_SDK_TOOLKIT_ROOT = 'android-sdk-toolkit'
& $pageguardPython -B android-mcp-inspector/server.py
```

The last command starts a standard MCP stdio server and waits for a client.
It does not provide an interactive prompt; stop it before configuring a client.
Dependencies may require network access on first install. Inspection itself is
offline. To use an existing approved runtime with the exact pins, skip venv and
installation and select that Python executable. A local wheel cache can be
used with pip's standard `--no-index --find-links <wheel-directory>` options;
the preview contains no wheels or Python runtime.

Linux, from the extracted root:

```sh
python3 -m venv ../pageguard-venv
../pageguard-venv/bin/python -m pip install -r android-mcp-inspector/requirements-portable.txt
../pageguard-venv/bin/python -m pip check
ANDROID_SDK_TOOLKIT_ROOT=android-sdk-toolkit ../pageguard-venv/bin/python -B android-mcp-inspector/server.py
```

## Connect a standard stdio client

For Codex, add a local server entry using the extracted root as `cwd`. Replace
the two example directories with your installation paths. This guide does not
modify your client configuration.

```toml
[mcp_servers.pageguard_preview]
command = "C:/PageGuard/pageguard-venv/Scripts/python.exe"
args = ["-B", "android-mcp-inspector/server.py"]
cwd = "C:/PageGuard/pageguard-preview-2026.11.28.1"

[mcp_servers.pageguard_preview.env]
ANDROID_SDK_TOOLKIT_ROOT = "android-sdk-toolkit"
```

Prior Codex CLI acceptance covered seven synthetic cases in each of the preview
and installed configurations, with complete CLI report parity. Existing desktop
chat tool discovery and invocation have not been accepted; CLI and official SDK
results do not establish desktop integration.

The Toolkit setting is a trusted, executable source path relative to the server
process's working directory; it is never a project input. Do not copy a Toolkit
path supplied by an untrusted inspected project. A client without `cwd` support
must use absolute paths for `server.py` and `ANDROID_SDK_TOOLKIT_ROOT`. Generic
stdio clients use these same command, arguments, working directory and environment.
No server code change or global installation is needed.

## Try the synthetic project cases

After setup, at the extracted root, generate fixtures outside the bundle:

```powershell
& $pageguardPython -B android-mcp-inspector/examples/make_project_trial.py '../synthetic-projects'
& $pageguardPython -I -B android-sdk-toolkit/skills/android-project-check/scripts/check_project.py '../synthetic-projects/pass' --source-file pages.cpp --output-dir '../synthetic-pass-evidence'
```

Use a new output directory on each retry. The CLI writes complete JSON to
stdout and `report.json` plus a bilingual supplier draft `report.md` to that
directory. The MCP tool is read-only and returns the same complete report plus
`exit_code`, without writing files. In MCP call `inspect_android_project_16kb`:

```json
{
  "project_root": "C:/PageGuard/synthetic-projects/pass",
  "source_files": ["pages.cpp"]
}
```

The source is explicitly synthetic. The `PAGE_SIZE 4096` definition produces
one advisory; `char buffer[4096]` produces none. Hints do not change the AAR
status and do not prove a source defect or runtime compatibility. A closed AAR
cannot be fixed by these hints. No patch is generated or applied.

| Fixture directory | Exit / report status | Interpretation |
| --- | --- | --- |
| `pass` | `0` / `pass` | Synthetic ARM64 ELF LOAD alignment passes |
| `fail` | `1` / `fail` | Synthetic ELF has `p_align=4096` |
| `invalid` | `2` / `invalid` | Deliberately malformed AAR |
| `no-matches` | `3` / `no_matches` | No discovered AAR; not a pass |
| `java-only` | `0` / `pass`, `elf64_count=0` | No 64-bit ELF evaluated |

`java-only` with `expected_abis: ["arm64-v8a"]` returns fail. Missing Toolkit
configuration produces an MCP tool error, not a scanner report. These are
static AAR checks: final APK ZIP alignment, installation and JNI behavior on a
16 KB Android device require separate evidence. Toolkit v0.12.0's published ZIP
does not contain `--source-file`; use the paired source in this preview.

To compare complete CLI reports with real MCP stdio responses on synthetic
inputs, run the test suites from the extracted Inspector directory (packaging
regression tests additionally require Git):

```powershell
Push-Location android-mcp-inspector
# Tests launch child servers in temporary working directories.
$env:ANDROID_SDK_TOOLKIT_ROOT = (Resolve-Path '../android-sdk-toolkit').Path
& $pageguardPython -B -m unittest discover -s tests -v
& $pageguardPython -B -m unittest discover -s vendor/apk-page-size-check/tests -v
Pop-Location
```

## Before inspecting your own project

Select the project root that directly contains `app/libs/*.aar` or
`uni_modules/*/utssdk/app-android/libs/*.aar`. The scanner does not recursively
discover arbitrary dependency caches or project layouts. A repository may need
its nested `demo/` as `project_root`; scanning the repository root can return
`no_matches` (exit 3), which is not a pass. Select C/C++ source files explicitly
with project-relative `source_files`; no recursive source search is performed.

A read-only trial on 2026-11-28 checked existing Android and uni-app UTS project
AARs. Both returned `pass` with `elf64_count: 0`, so neither established native
16 KB compatibility. Requiring `arm64-v8a` returned `fail` for the missing ABI.
Use `expected_abis` only when every AAR must contain that ABI; a Java-only AAR
can otherwise pass without any 64-bit ELF evaluation. The six trial responses
matched the complete direct CLI reports through the official MCP SDK over
stdio, with input hashes unchanged. This is separate from Codex desktop
acceptance, final APK packaging and device/runtime validation.

## Build another source preview

Maintainers need Git and two clean, committed checkouts; users of the ZIP do
not need Git. Run from Inspector with an inspected Toolkit checkout:

```sh
python -B scripts/build_portable.py --toolkit ../android-sdk-toolkit --version 2026.11.28.1 --output-dir ../pageguard-package
```

This standard-library builder packages committed tracked files using
`git -c core.autocrlf=false archive`, retaining Unix shell-script bytes and file
modes. It refuses dirty/untracked source files and existing output directories.
Git-ignored local files are excluded. Review the tracked inventory before
packaging: credentials, private inputs, AARs, node_modules, runtime environments
and build outputs must not be committed. No runtime, fixtures, private paths or
downloaded dependencies are added by the builder. The ZIP has reproducible
ordering and timestamps; its per-file manifest excludes itself. This is a local
preview operation: it creates no tag, release, registry entry or repository.
