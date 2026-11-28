"""Generate tiny synthetic Android projects for static inspection; never install them."""

import argparse
import sys
from pathlib import Path
from zipfile import ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/apk-page-size-check/tests"))
from test_cli import elf
sys.path.pop(0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path, help="New directory for synthetic projects")
    output = parser.parse_args().output_dir
    if output.exists():
        parser.error(f"choose a new output directory: {output}")
    for name in ("pass", "fail", "invalid", "no-matches", "java-only"):
        project = output / name
        project.mkdir(parents=True)
        (project / "pages.cpp").write_text(
            "// Synthetic advisory fixture; not an application.\n#define PAGE_SIZE 4096\nchar buffer[4096];\n",
            encoding="utf-8", newline="\n",
        )
        if name == "no-matches":
            continue
        aar = project / "app/libs/synthetic.aar"
        aar.parent.mkdir(parents=True)
        if name == "invalid":
            aar.write_bytes(b"invalid synthetic archive")
            continue
        with ZipFile(aar, "x") as archive:
            archive.writestr(ZipInfo("AndroidManifest.xml"), b"synthetic inspection fixture")
            if name != "java-only":
                archive.writestr(ZipInfo("jni/arm64-v8a/libsynthetic.so"),
                                 elf(alignment=4096 if name == "fail" else 16384))
    print(f"Synthetic projects written to {output}")


if __name__ == "__main__":
    main()
