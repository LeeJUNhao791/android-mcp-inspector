"""Package two clean, committed source checkouts as a versioned PageGuard preview."""

import argparse
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True,
    ).stdout


def build(inspector, toolkit, output, version):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", version):
        raise ValueError("version must be 1-64 letters, digits, dots, underscores or hyphens")
    if output.exists():
        raise ValueError("choose a new output directory")
    files = {}
    sources = {}
    for name, repo in (("android-mcp-inspector", inspector), ("android-sdk-toolkit", toolkit)):
        if git(repo, "status", "--porcelain").strip():
            raise ValueError(f"{name} must be clean and committed before packaging")
        revision = git(repo, "rev-parse", "HEAD").decode().strip()
        sources[name] = {"commit": revision,
                         "repository": f"https://github.com/LeeJUNhao791/{name}"}
        with ZipFile(io.BytesIO(git(repo, "-c", "core.autocrlf=false", "archive", "--format=zip", revision))) as archive:
            for item in archive.infolist():
                if not item.is_dir():
                    files[f"{name}/{item.filename}"] = (archive.read(item), item.external_attr)
    for filename, source in (("README.md", "portable-preview.md"),
                             ("README.zh-CN.md", "portable-preview.zh-CN.md")):
        files[filename] = files[f"android-mcp-inspector/docs/{source}"]
    manifest = {
        "version": version, "kind": "source-preview", "sources": sources,
        "files": {name: hashlib.sha256(data).hexdigest() for name, (data, _) in sorted(files.items())},
    }
    files["bundle-manifest.json"] = (
        (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"), 0o100644 << 16,
    )
    output.mkdir(parents=True)
    stem = f"pageguard-preview-{version}"
    path = output / f"{stem}.zip"
    with ZipFile(path, "x", compression=ZIP_DEFLATED) as bundle:
        for name, (data, attributes) in sorted(files.items()):
            item = ZipInfo(f"{stem}/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            item.create_system = 3
            item.external_attr = attributes
            item.compress_type = ZIP_DEFLATED
            bundle.writestr(item, data)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return {"archive": str(path), "sha256": digest, "sources": sources}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspector", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--toolkit", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = build(args.inspector.resolve(), args.toolkit.resolve(), args.output_dir.resolve(), args.version)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Portable source packaging failed: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
