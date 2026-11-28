# PageGuard 双仓库源码预览包

[English](https://github.com/LeeJUNhao791/android-mcp-inspector/blob/main/docs/portable-preview.md)

此预览包将 Android MCP Inspector 与兼容的 Android SDK Toolkit 源码放在一起。
它是源码 ZIP，不是正式发布、注册表软件包或自带运行环境的可执行程序。
Python 和固定版本的 MCP 依赖需要单独准备。静态检查无需 Android SDK、Gradle
构建、设备、账号、API Key 或模型下载。

包内包含 `android-mcp-inspector/`、`android-sdk-toolkit/`、中英文说明和
`bundle-manifest.json`。清单记录两个仓库的精确 Git 提交及其余每个文件的
SHA-256；ZIP 旁的 `SHA256SUMS` 记录整个压缩包的 SHA-256。请保留两个目录及
Toolkit 内的同级 Skills。两个仓库的 MIT `LICENSE`、Inspector 已有的 APK
检查器副本及 README 中的来源说明均保留。

## 解压与准备

先将 ZIP 哈希与单独提供的 `SHA256SUMS` 核对。PowerShell 可用
`Get-FileHash <zip> -Algorithm SHA256`，Linux 可用 `sha256sum -c SHA256SUMS`。
解压到开发工作区以外的全新目录，路径可以包含空格。

已验证环境为 Windows、Python 3.11.4、MCP 2.3.0。精确的 MCP 运行依赖闭包在
`android-mcp-inspector/requirements-portable.txt` 中，Windows 共 29 个发行包，
其中 `pywin32` 只在 Windows 安装。Inspector 要求 Python 3.11+；其他 Python
版本和平台仍需单独验证。下面的 Linux 命令是等价使用方法，不代表已完成 Linux 验收。

Windows PowerShell，在解压后的根目录运行：

```powershell
Set-Location 'C:/PageGuard/pageguard-preview-2026.11.28'
$pageguardEnv = Join-Path (Split-Path $PWD -Parent) 'pageguard-venv'
python -m venv $pageguardEnv
$pageguardPython = Join-Path $pageguardEnv 'Scripts/python.exe'
& $pageguardPython -m pip install -r android-mcp-inspector/requirements-portable.txt
& $pageguardPython -m pip check
$env:ANDROID_SDK_TOOLKIT_ROOT = 'android-sdk-toolkit'
& $pageguardPython -B android-mcp-inspector/server.py
```

最后一条命令启动标准 MCP stdio 服务并等待客户端，不会出现交互式命令提示。
配置客户端前先停止该进程。首次安装依赖可能需要网络，检查过程本身可以离线。
如果已有经过批准、版本与清单一致的 Python 环境，可以跳过创建环境和安装步骤，
直接选择该 Python。已有本地 wheel 缓存时可使用 pip 标准参数
`--no-index --find-links <wheel目录>`；预览包不含 wheel 和 Python 运行环境。

Linux，在解压后的根目录运行：

```sh
python3 -m venv ../pageguard-venv
../pageguard-venv/bin/python -m pip install -r android-mcp-inspector/requirements-portable.txt
../pageguard-venv/bin/python -m pip check
ANDROID_SDK_TOOLKIT_ROOT=android-sdk-toolkit ../pageguard-venv/bin/python -B android-mcp-inspector/server.py
```

## 连接标准 stdio 客户端

以 Codex 为例，设置本地服务，并将 `cwd` 指向解压后的根目录。替换以下两个示例
目录即可。本说明不会直接修改客户端配置。

```toml
[mcp_servers.pageguard_preview]
command = "C:/PageGuard/pageguard-venv/Scripts/python.exe"
args = ["-B", "android-mcp-inspector/server.py"]
cwd = "C:/PageGuard/pageguard-preview-2026.11.28"

[mcp_servers.pageguard_preview.env]
ANDROID_SDK_TOOLKIT_ROOT = "android-sdk-toolkit"
```

Toolkit 配置是相对服务进程工作目录解析的、受信任的可执行源码路径，不是项目
输入。不要采用待检查项目提供的不可信 Toolkit 路径。若客户端不支持 `cwd`，
请把 `server.py` 和 `ANDROID_SDK_TOOLKIT_ROOT` 都改成绝对路径。其他标准 stdio
客户端使用相同的启动命令、参数、工作目录和环境变量，无需改服务代码或全局安装。

## 试用合成项目

在解压根目录的新终端中生成合成输入，放在预览包外：

```powershell
& $pageguardPython -B android-mcp-inspector/examples/make_project_trial.py '../synthetic-projects'
& $pageguardPython -I -B android-sdk-toolkit/skills/android-project-check/scripts/check_project.py '../synthetic-projects/pass' --source-file pages.cpp --output-dir '../synthetic-pass-evidence'
```

重试时使用新的输出目录。CLI 将完整 JSON 输出到标准输出，同时在证据目录生成
`report.json` 和中英双语供应商草稿 `report.md`。MCP 工具只读，返回相同的完整
报告和 `exit_code`，不写文件。通过 MCP 调用 `inspect_android_project_16kb`：

```json
{
  "project_root": "C:/PageGuard/synthetic-projects/pass",
  "source_files": ["pages.cpp"]
}
```

以上输入均为合成样例。`PAGE_SIZE 4096` 定义产生一条建议，普通
`char buffer[4096]` 不产生建议。建议不改变 AAR 状态，也不证明源代码缺陷或
运行兼容性；无法据此修复闭源 AAR。不会生成或应用补丁。

| 项目目录 | 退出码 / 报告状态 | 含义 |
| --- | --- | --- |
| `pass` | `0` / `pass` | 合成 ARM64 ELF LOAD 对齐通过 |
| `fail` | `1` / `fail` | 合成 ELF 的 `p_align=4096` |
| `invalid` | `2` / `invalid` | 故意损坏的 AAR |
| `no-matches` | `3` / `no_matches` | 未发现 AAR，不代表通过 |
| `java-only` | `0` / `pass`，`elf64_count=0` | 未评估任何 64 位 ELF |

给 `java-only` 增加 `expected_abis: ["arm64-v8a"]` 会失败。缺少 Toolkit
配置会返回 MCP 工具错误，不会伪装成扫描报告。以上仅为静态 AAR 检查；最终 APK
ZIP 对齐、安装以及 16 KB Android 设备上的 JNI 行为需要另行验证。
Toolkit v0.12.0 发布 ZIP 不含 `--source-file`，请使用预览包中配套的源码。

从解压后的 Inspector 目录运行现有协议测试，可比较合成输入的完整 CLI 报告与
真实 MCP stdio 返回结果（打包回归测试还需要 Git）：

```powershell
Push-Location android-mcp-inspector
$env:ANDROID_SDK_TOOLKIT_ROOT = '../android-sdk-toolkit'
& $pageguardPython -B -m unittest discover -s tests -v
& $pageguardPython -B -m unittest discover -s vendor/apk-page-size-check/tests -v
Pop-Location
```

## 重新制作源码预览包

维护者需要 Git 和两个干净且已提交的仓库；ZIP 使用者不需要 Git。在 Inspector
根目录运行，并传入已检查的 Toolkit 源码目录：

```sh
python -B scripts/build_portable.py --toolkit ../android-sdk-toolkit --version 2026.11.28 --output-dir ../pageguard-package
```

打包脚本只使用标准库，通过 `git -c core.autocrlf=false archive` 读取已提交、
受版本管理的文件，保留 Unix shell 脚本字节和文件权限。源码存在修改、未跟踪
文件或输出目录已存在时会拒绝打包。Git 忽略的本地文件不会进入包中。打包前请
检查受版本管理的文件：凭据、私有输入、AAR、node_modules、运行环境和构建产物
不得提交。脚本不会自行加入运行环境、合成归档、私有路径或下载依赖。ZIP 文件顺序
和时间戳固定；逐文件清单不包含清单自身。该操作只制作本地预览，不创建标签、
正式发布、注册表条目或新仓库。
