# Android MCP Inspector

A local MCP server that checks Android APKs for 16 KB alignment and traces native libraries to candidate AARs. The stdio tool `inspect_apk_16kb` checks the ELF segments and ZIP layout of an APK you own or are authorized to inspect.

## Set up

Use Python 3.11 or newer. Run these commands from the repository root with a virtual environment outside the checkout.

Windows (PowerShell)

```powershell
$inspectorEnv = Join-Path $env:TEMP 'android-mcp-inspector-venv'
python -m venv $inspectorEnv
$inspectorPython = Join-Path $inspectorEnv 'Scripts/python.exe'
& $inspectorPython -m pip install -r requirements.txt
& $inspectorPython -B -m unittest discover -s tests -v
```

Ubuntu

```bash
python3 -m venv ~/.venvs/android-mcp-inspector
~/.venvs/android-mcp-inspector/bin/python -m pip install -r requirements.txt
~/.venvs/android-mcp-inspector/bin/python -B -m unittest discover -s tests -v
```

The smoke tests launch the server using the [official Python MCP client over stdio](https://py.sdk.modelcontextprotocol.io/client/transports/#stdio) and compare complete responses with direct CLI runs on synthetic fixtures.

## Connect a client

Configure a local stdio server with the virtual environment's Python executable as its command and the full path to `server.py` as its only argument. For clients that use `mcpServers` JSON, a Windows example is:

```json
{
  "mcpServers": {
    "android-mcp-inspector": {
      "command": "C:/path/to/android-mcp-inspector-venv/Scripts/python.exe",
      "args": ["C:/path/to/android-mcp-inspector/server.py"]
    }
  }
}
```

## Call the tool

Pass the APK's absolute path on the machine that runs the server. Supply the two optional inputs from the same build as the APK. If you provide `native_provenance`, also provide `aar_manifest`.

```json
{
  "apk_path": "C:/Android builds/app-debug.apk",
  "aar_manifest": "C:/Android builds/resolved aars.json",
  "native_provenance": "C:/Android builds/native provenance.json"
}
```

The structured response contains `exit_code` and `report`. The checker supplies the exit code and the full JSON report. All four checker outcomes are returned as tool results.

| Exit code | Report status | Meaning |
| --- | --- | --- |
| 0 | `pass` | Checked libraries pass the applicable alignment checks. |
| 1 | `fail` | At least one checked library fails ELF or ZIP alignment. |
| 2 | `invalid` | The checker rejected the APK or an accompanying input. |
| 3 | `not_applicable` | No arm64-v8a or x86_64 shared libraries were found, and all applicable ZIP alignment checks passed. |

When attribution is available, the report preserves `single_candidate`, `multiple_candidates`, or `unknown` and identifies the evidence method when the checker reports one.

## Upstream code

The bundled checker and its CLI tests come from [Android SDK Toolkit v0.8.0](https://github.com/LeeJUNhao791/android-sdk-toolkit/tree/dbd640e7b4ccd8a87beb8ca1ed21be3b301b979c/skills/apk-page-size-check). The included [MIT license](LICENSE) covers these files. To run the upstream CLI suite, use `python -B -m unittest discover -s vendor/apk-page-size-check/tests -v`.
