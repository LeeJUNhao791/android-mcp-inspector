# 验证真实 MediaPipe APK

[English](mediapipe.md)

构建 Google MediaPipe 的 Image Classification Android 示例，用 Inspector 正式版的内置 CLI 和通过 MCP stdio 调用的 `inspect_apk_16kb` 检查同一个 debug APK 和同一批 Gradle 证据。此示例验证 APK 的静态对齐和原生库溯源，真机安装、启动和运行均需另外验证。

## 1. 准备固定版本的源码

在 Ubuntu 24.04 的 Bash 中运行，准备 Git、JDK 17、带 `venv` 的 Python 3.11，以及 `$ANDROID_HOME` 下的 Android SDK 命令行工具。把 `JAVA_HOME` 指向 JDK 17。构建时需要联网获取源码、SDK 组件、Gradle 依赖和模型文件。

从包含 `examples/verify_mediapipe.py` 的仓库根目录开始，三步都在同一个 Bash 会话执行。

```bash
set -e
example_root="$PWD"
work="$(mktemp -d)"

git clone --depth 1 --branch v0.1.1 \
  https://github.com/LeeJUNhao791/android-mcp-inspector.git "$work/inspector"
test "$(git -C "$work/inspector" rev-parse HEAD)" = 7073a55c12483e0717193d5041a4b8872d26a2f8

git clone --depth 1 --branch v0.8.0 \
  https://github.com/LeeJUNhao791/android-sdk-toolkit.git "$work/toolkit"
test "$(git -C "$work/toolkit" rev-parse HEAD)" = dbd640e7b4ccd8a87beb8ca1ed21be3b301b979c

git clone --filter=blob:none --sparse \
  https://github.com/google-ai-edge/mediapipe-samples.git "$work/mediapipe-samples"
git -C "$work/mediapipe-samples" sparse-checkout set examples/image_classification/android android-common
git -C "$work/mediapipe-samples" checkout --detach 46d60d66baf21ae91977c488ea0875f0e13c4d2b

python3.11 -m venv "$work/venv"
"$work/venv/bin/python" -m pip install -r "$work/inspector/requirements.txt"
```

## 2. 构建 APK 并导出溯源数据

如果 SDK 提示许可协议，按提示接受。用示例自带的 Gradle Wrapper 和 Toolkit 的初始化脚本运行 `:app:exportDebugNativeProvenance`。该任务会构建 debug APK，记录解析后的 AAR 路径及原生库去除调试符号前后的哈希。

```bash
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --install \
  "platforms;android-36" "build-tools;36.0.0" "ndk;27.0.12077973"

sample="$work/mediapipe-samples/examples/image_classification/android"
exporter="$work/toolkit/skills/apk-page-size-check/examples/export-debug-native-provenance.init.gradle"
(
  cd "$sample"
  ./gradlew --no-daemon --no-configuration-cache --init-script "$exporter" \
    :app:verifyModels :app:exportDebugNativeProvenance :android-common:testing:testDebugUnitTest
)
```

保留同一次构建的 APK 和两份 JSON，在构建机器上检查，确保 `resolved-aars.json` 记录的路径仍能访问对应 AAR。只复制 APK 和报告会丢失这些依赖。如果 APK、清单或 AAR 路径有变化，重新构建并导出。

## 3. 比较 CLI 和 MCP 的报告

```bash
apk="$sample/app/build/outputs/apk/debug/app-debug.apk"
evidence="$sample/app/build/reports/apk-16kb"
"$work/venv/bin/python" -B "$example_root/examples/verify_mediapipe.py" \
  --inspector "$work/inspector" \
  --apk "$apk" \
  --aar-manifest "$evidence/resolved-aars.json" \
  --native-provenance "$evidence/native-provenance.json"
```

成功时脚本退出码为 `0`，并输出包含下列结果的 JSON 摘要。

| 摘要字段 | 预期值 |
| --- | --- |
| `cli_exit_code`、`mcp_exit_code`、`reports_equal` | `0`、`0`、`true` |
| `status`、`page_size` | `pass`、`16384` |
| `native_provenance.status`、`native_provenance.variant` | `verified`、`debug` |
| `libmediapipe_tasks_jni.so` 条目 | `arm64-v8a`、`armeabi-v7a`、`x86`、`x86_64` |
| 每个 ABI 的溯源方式、唯一 AAR 坐标 | `gradle_strip_chain`、`com.google.mediapipe:tasks-core:1.2.2` |

摘要包含 APK、AAR 清单和原生库溯源 JSON 的 SHA-256，不输出本地路径或完整报告。表中的四个 ABI 都有库溯源结果。16 KB ELF 检查适用于 64 位库，ZIP 对齐检查适用于未压缩的库条目。

还可用 Android Build Tools 单独检查 APK 的 ZIP 对齐：

```bash
"$ANDROID_HOME/build-tools/36.0.0/zipalign" -c -P 16 4 "$apk"
```

## 实际验证

这次 [GitHub Actions 验证](https://github.com/LeeJUNhao791/android-mcp-inspector/actions/runs/45309496959) 用固定版本构建 APK，确认了上面的所有结果，并通过了独立的 `zipalign` 检查。运行的 `mediapipe-mcp-evidence` 附件包含验收摘要和 SHA-256。
