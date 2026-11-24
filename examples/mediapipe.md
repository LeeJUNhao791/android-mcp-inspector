# Verify a real MediaPipe APK

[简体中文](mediapipe.zh-CN.md)

Build the Google MediaPipe Image Classification Android sample, then compare the released Inspector's bundled CLI with its `inspect_apk_16kb` tool over MCP stdio. Both read the same debug APK and Gradle evidence. This example checks static APK alignment and native library provenance. Device installation, launch, and runtime behavior require separate testing.

## 1. Set up the pinned sources

Use Bash on Ubuntu 24.04 with Git, JDK 17, Python 3.11 with `venv`, and the Android SDK command-line tools under `$ANDROID_HOME`. Set `JAVA_HOME` to JDK 17. The build needs network access for the source checkouts, SDK packages, Gradle dependencies, and model files.

Run from the root of the checkout containing `examples/verify_mediapipe.py`. Keep the same Bash session through all three steps.

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

## 2. Build the APK and export provenance

Accept the Android SDK licenses if prompted. Use the sample's Gradle wrapper and the Toolkit init script that registers `:app:exportDebugNativeProvenance`. The export task builds the debug APK and records the resolved AAR paths and the pre-strip and post-strip native library hashes.

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

Keep the APK and both JSON files from this build. Run the checker on the build machine while the AARs are still present at the paths recorded in `resolved-aars.json`. Copying just the APK and reports does not preserve these dependencies. Rebuild and export again if the APK, manifest, or resolved AAR paths have changed.

## 3. Compare the CLI and MCP reports

```bash
apk="$sample/app/build/outputs/apk/debug/app-debug.apk"
evidence="$sample/app/build/reports/apk-16kb"
"$work/venv/bin/python" -B "$example_root/examples/verify_mediapipe.py" \
  --inspector "$work/inspector" \
  --apk "$apk" \
  --aar-manifest "$evidence/resolved-aars.json" \
  --native-provenance "$evidence/native-provenance.json"
```

On success the helper exits with code `0` and prints a JSON summary with these values.

| Summary field | Expected value |
| --- | --- |
| `cli_exit_code`, `mcp_exit_code`, `reports_equal` | `0`, `0`, `true` |
| `status`, `page_size` | `pass`, `16384` |
| `native_provenance.status`, `native_provenance.variant` | `verified`, `debug` |
| `libmediapipe_tasks_jni.so` entries | `arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64` |
| Method and sole AAR coordinate for each ABI | `gradle_strip_chain`, `com.google.mediapipe:tasks-core:1.2.2` |

The summary includes SHA-256 digests for the APK, AAR manifest, and native provenance file. It omits local paths and the full report. The four ABI entries show library attribution. The 16 KB ELF checks apply to the 64-bit libraries, and the ZIP alignment checks apply to uncompressed library entries.

To cross-check the APK's ZIP alignment with Android Build Tools, run:

```bash
"$ANDROID_HOME/build-tools/36.0.0/zipalign" -c -P 16 4 "$apk"
```

## Verified run

The [GitHub Actions verification](https://github.com/LeeJUNhao791/android-mcp-inspector/actions/runs/45309496959) built the pinned APK and confirmed all results above, including the independent `zipalign` check. The `mediapipe-mcp-evidence` artifact contains the verified summary and SHA-256 digests.
