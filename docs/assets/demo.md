# Demo evidence / 演示依据

The PNG visualizes selected output from a real MCP stdio call on 2026-11-26. The official Python MCP client discovered `inspect_apk_16kb`, called it on Google's compiled MediaPipe Image Classification debug APK, and compared the full structured result with the bundled CLI. It is a static visualization, not a recording or an AI-generated tool response. No APK is distributed here.

PNG 展示 2026-11-26 本轮真实 MCP stdio 调用的部分输出。官方 Python MCP 客户端发现并调用 `inspect_apk_16kb`，检查实际编译的 Google MediaPipe 图像分类调试 APK，再与内置 CLI 比较完整结构化结果。这是实际输出的静态可视化，不是录屏或 AI 编造的工具结果。本仓库不分发 APK。

| Evidence / 依据 | Value / 值 |
| --- | --- |
| Inspector source base / 工具源码基线 | `7b390bd1f845f70e87c7f1b3208a6281cf883522` |
| MediaPipe source / 输入源码 | [`46d60d66baf21ae91977c488ea0875f0e13c4d2b`](https://github.com/google-ai-edge/mediapipe-samples/tree/46d60d66baf21ae91977c488ea0875f0e13c4d2b/examples/image_classification/android) |
| APK SHA-256 | `abfdbc8b45775414f315509675ad1577b7bf0afdcdd7f4c3c0a562e80d06cfb8` |
| MCP result / MCP 结果 | `is_error=false`, `exit_code=0`, `report.status=pass`, `page_size=16384` |
| Native library entries / 原生库条目 | `16`; ELF: `8` 64-bit pass / 64 位通过, `8` 32-bit `not_applicable` / 32 位不适用; ZIP: `16` pass / 通过 |
| Full MCP result vs CLI / 完整 MCP 结果与 CLI 比较 | Equal / 一致 |

## Reproduce / 复现

Install the [pinned dependencies](../../requirements.txt) in a Python 3.11+ environment as described in the README. Use an APK you are authorized to inspect. The [MediaPipe guide](../../examples/mediapipe.md) covers building the pinned sample; this alignment-only call does not use AAR or provenance inputs. Rebuilds may produce a different APK hash.

按 README 在 Python 3.11+ 环境安装[固定依赖](../../requirements.txt)，准备获准检查的 APK。[MediaPipe 指南](../../examples/mediapipe.zh-CN.md)包含固定源码构建步骤；本演示仅检查对齐，不传 AAR 或溯源输入。重新构建的 APK 哈希可能不同。

Save the following as `mcp-demo.py` outside the repository. Run it from the repository root using the same Python environment. The full result is written to `build/mcp-demo-result.json` and can include local paths; review it before sharing.

将以下内容存为仓库外的 `mcp-demo.py`，用同一个 Python 环境在仓库根目录运行。完整结果写入 `build/mcp-demo-result.json`，可能包含本机路径，分享前需检查。

```python
import asyncio
import json
from pathlib import Path
import subprocess
import sys
from mcp import Client, StdioServerParameters

async def main():
    repo = Path.cwd()
    apk = str(Path(sys.argv[1]).resolve())
    direct = subprocess.run(
        [sys.executable, "-I", str(repo / "vendor/apk-page-size-check/scripts/check_apk.py"), "--", apk],
        capture_output=True, text=True, check=False,
    )
    server = StdioServerParameters(command=sys.executable, args=["-B", str(repo / "server.py")])
    async with asyncio.timeout(120):
        async with Client(server, read_timeout_seconds=120) as client:
            names = [tool.name for tool in (await client.list_tools()).tools]
            result = await client.call_tool("inspect_apk_16kb", {"apk_path": apk})
    assert not result.is_error
    assert result.structured_content == {"exit_code": direct.returncode, "report": json.loads(direct.stdout)}
    output = repo / "build/mcp-demo-result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result.structured_content, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"tools": names, "exit_code": direct.returncode,
                      "status": result.structured_content["report"]["status"], "full_report_matches_cli": True}))

asyncio.run(main())
```

```sh
python -B path/to/mcp-demo.py path/to/app-debug.apk
```

The captured input returned `pass` / exit `0`. Other inputs can return a different checker status while the MCP transport still works. This run does not establish AAR attribution, device installation, or JNI execution.

本轮输入返回 `pass`、退出码 `0`。其他 APK 可返回不同检查结论，MCP 通道本身仍可能正常。本轮未验证 AAR 来源、设备安装或 JNI 运行。
