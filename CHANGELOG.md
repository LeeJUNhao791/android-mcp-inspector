# Changelog

Dates are GitHub Release publication dates in UTC.

## Unreleased

- Show actual output from an official Python MCP client inspecting a real MediaPipe debug APK, with reproduction details. The output covers static alignment checks, not device behavior.
- Add contribution guidance and a pull request template distinguishing CLI, MCP, and device evidence. [#7](https://github.com/LeeJUNhao791/android-mcp-inspector/pull/7)

## [v0.1.2](https://github.com/LeeJUNhao791/android-mcp-inspector/releases/tag/v0.1.2) - 2026-11-24

- Add English and Chinese guides for building the pinned MediaPipe Image Classification sample and inspecting its debug APK.
- Include `examples/verify_mediapipe.py` in the source archive to compare the bundled CLI exit code and complete JSON report with `inspect_apk_16kb` over local MCP stdio.
- Record matching reports, passing alignment checks, and Gradle provenance for the tested APK. These checks cover static APK alignment and native library provenance.

## Earlier releases

- [v0.1.1](https://github.com/LeeJUNhao791/android-mcp-inspector/releases/tag/v0.1.1)
- [v0.1.0](https://github.com/LeeJUNhao791/android-mcp-inspector/releases/tag/v0.1.0)
