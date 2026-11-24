# Android MCP Inspector

[![CI](https://github.com/LeeJUNhao791/android-mcp-inspector/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/LeeJUNhao791/android-mcp-inspector/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/LeeJUNhao791/android-mcp-inspector)](https://github.com/LeeJUNhao791/android-mcp-inspector/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[English](README.md)

本地 MCP 服务，通过 stdio 提供 `inspect_apk_16kb` 工具，检查 APK 的 ELF 段与 ZIP 布局是否满足 Android 16 KB 对齐要求。可结合同一次构建的 AAR 清单和原生库溯源数据，查找候选依赖。

工具读取你拥有或获准检查的本地文件，不修改 APK 或修复 ELF。静态检查结果不等于真机安装、启动或运行验证。

## 安装与自检

使用 Python 3.11 或更新版本。在仓库根目录执行，把虚拟环境放在仓库外。

Windows PowerShell：

```powershell
$inspectorEnv = Join-Path $env:TEMP 'android-mcp-inspector-venv'
python -m venv $inspectorEnv
$inspectorPython = Join-Path $inspectorEnv 'Scripts/python.exe'
& $inspectorPython -m pip install -r requirements.txt
& $inspectorPython -B -m unittest discover -s tests -v
```

Ubuntu：

```bash
python3 -m venv ~/.venvs/android-mcp-inspector
~/.venvs/android-mcp-inspector/bin/python -m pip install -r requirements.txt
~/.venvs/android-mcp-inspector/bin/python -B -m unittest discover -s tests -v
```

依赖固定在 [requirements.txt](requirements.txt)。测试使用官方 Python MCP 客户端，通过真实 stdio 启动服务，并与检查器直接运行的完整输出比较；输入使用合成样例。

## 接入 MCP 客户端

将虚拟环境中的 Python 可执行文件设为启动命令，`server.py` 设为唯一参数。

### VS Code 编辑器管理的 MCP

在 VS Code 打开仓库目录，创建 `.vscode/mcp.json`。把 `command` 替换为虚拟环境 Python 的绝对路径。

```json
{
  "servers": {
    "android-mcp-inspector": {
      "type": "stdio",
      "command": "C:/path/to/android-mcp-inspector-venv/Scripts/python.exe",
      "args": ["${workspaceFolder}/server.py"]
    }
  }
}
```

在命令面板运行 **MCP: List Servers**，启动 `android-mcp-inspector`。编辑器配置与 Copilot 转发方式见 [Microsoft 配置参考](https://code.visualstudio.com/docs/agents/reference/mcp-configuration#editor-managed-configuration-for-local-harness-compatibility)。

### 使用 `mcpServers` 的客户端

Python 和 `server.py` 均填写绝对路径。

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

## 试用合成 APK

从 `v0.1.1` 起，发布的源码包包含此示例。从源码根目录生成样例，输出目录必须尚不存在：

```powershell
python -B examples/make_trial.py 'C:/Temp/Android MCP Trial'
```

生成器仅使用 Python 标准库和仓库内测试夹具，可离线运行。生成 `trial.apk`、`device.aar`、`decoy.aar` 和 `aar-manifest.json`。这些合成归档仅供检查，不用于安装运行。

在客户端调用 `inspect_apk_16kb`，传入以下参数；若修改了生成目录，同时修改两个路径：

```json
{
  "apk_path": "C:/Temp/Android MCP Trial/trial.apk",
  "aar_manifest": "C:/Temp/Android MCP Trial/aar-manifest.json"
}
```

这个样例故意不满足 ELF 对齐要求，成功复现时应返回失败报告：

| 字段 | 预期值 |
| --- | --- |
| `exit_code`、`report.status`、`report.page_size` | `1`、`fail`、`16384` |
| `report.libraries[0].entry` | `lib/arm64-v8a/libdevice.so` |
| 同一库的 `elf`、`zip`、`zip_data_offset` | `fail`、`pass`、`16384` |
| `load_issues[0].p_align` | `4096` |
| `origin.status`、`origin.candidates[0].coordinate` | `single_candidate`、`example:device-native:1` |
| `origin.sha256` | `7240b15ae351fa6c080791c11a763db475d3286c134d956ac6b8cf38adac5b88` |

两个 AAR 都含有 `jni/arm64-v8a/libdevice.so`，只有 `device.aar` 的库字节与 APK 中相同。

## 检查自己的 APK

路径指向运行服务的机器。可选的 `aar_manifest` 和 `native_provenance` 必须来自 APK 的同一次构建；提供 `native_provenance` 时必须同时提供 `aar_manifest`。

```json
{
  "apk_path": "C:/Android builds/app-debug.apk",
  "aar_manifest": "C:/Android builds/resolved aars.json",
  "native_provenance": "C:/Android builds/native provenance.json"
}
```

结构化响应包含 `exit_code` 和完整的 `report`。以下四种检查结果都会作为工具结果返回；其中 `fail` 表示检查完成后发现不对齐。

| 退出码 | 报告状态 | 含义 |
| --- | --- | --- |
| `0` | `pass` | 已检查的库满足适用的对齐检查。 |
| `1` | `fail` | 至少一个已检查库未通过 ELF 或 ZIP 对齐检查。 |
| `2` | `invalid` | APK 或附带输入被检查器拒绝。 |
| `3` | `not_applicable` | 没有 arm64-v8a 或 x86_64 共享库，且所有适用的 ZIP 对齐检查通过。 |

溯源结果保留 `single_candidate`、`multiple_candidates` 或 `unknown`。候选 AAR 及证据方法以报告为准；同名库不代表已经确认来源。

## 反馈与上游

首次使用合成样例的体验请回复 [Issue #3](https://github.com/LeeJUNhao791/android-mcp-inspector/issues/3)。可复现的缺陷请使用 [Bug 模板](https://github.com/LeeJUNhao791/android-mcp-inspector/issues/new?template=bug_report.md)，删除私有路径并使用可公开的样例。

内置检查器和 CLI 测试来自 [Android SDK Toolkit v0.8.0](https://github.com/LeeJUNhao791/android-sdk-toolkit/tree/dbd640e7b4ccd8a87beb8ca1ed21be3b301b979c/skills/apk-page-size-check)，适用本仓库的 [MIT 许可证](LICENSE)。可独立运行内置 CLI 测试：

```sh
python -B -m unittest discover -s vendor/apk-page-size-check/tests -v
```
